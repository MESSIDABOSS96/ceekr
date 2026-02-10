"""FastAPI backend for Twitter Account Finder."""

import asyncio
import json
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from config import validate_config
from core.llm import LLMClient
from core.twitter import SearchOrchestrator, TwitterClient

app = FastAPI(title="Twitter Account Finder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    errors = validate_config()
    return {"ok": len(errors) == 0, "errors": errors}


def _serialize_account(ranked):
    """Serialize a RankedAccount to a JSON-safe dict."""
    acc = ranked.account
    return {
        "user_id": acc.user_id,
        "handle": acc.handle,
        "name": acc.name,
        "bio": acc.bio,
        "followers_count": acc.followers_count,
        "following_count": acc.following_count,
        "tweet_count": acc.tweet_count,
        "profile_url": acc.profile_url,
        "profile_image_url": acc.profile_image_url,
        "recent_tweets": [
            {
                "id": t.id,
                "text": t.text,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "like_count": t.like_count,
                "retweet_count": t.retweet_count,
                "reply_count": t.reply_count,
            }
            for t in acc.recent_tweets
        ],
        "matched_queries": acc.matched_queries,
        "location": acc.location,
        "verified": acc.verified,
        "created_at": acc.created_at.isoformat() if acc.created_at else None,
        "network": {
            "you_follow": acc.network.you_follow,
            "follows_you": acc.network.follows_you,
            "mutual_followers": acc.network.mutual_followers,
        },
        "relevance_score": ranked.relevance_score,
        "score_reasoning": ranked.score_reasoning,
        "why_relevant": ranked.why_relevant,
        "suggested_approach": ranked.suggested_approach,
    }


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    filters = body.get("filters", {})
    results_summary = body.get("current_results_summary", "No results yet.")

    if not messages:
        return {"response": "No message provided.", "action": None}

    # Build filters summary string for the LLM
    filter_parts = []
    if filters.get("keywords"):
        filter_parts.append(f"Keywords: {', '.join(filters['keywords'])}")
    if filters.get("followerMin", 0) > 0 or filters.get("followerMax") is not None:
        fmin = filters.get("followerMin", 0)
        fmax = filters.get("followerMax", "no max")
        filter_parts.append(f"Followers: {fmin} - {fmax}")
    if filters.get("location"):
        filter_parts.append(f"Location: {filters['location']}")
    if filters.get("verified") is True:
        filter_parts.append("Verified only")
    if filters.get("postingFrequency"):
        filter_parts.append(f"Posting: {', '.join(filters['postingFrequency'])}")
    if filters.get("accountAge"):
        filter_parts.append(f"Account age: {', '.join(filters['accountAge'])}")
    filters_summary = "; ".join(filter_parts) if filter_parts else "None active"

    try:
        llm = LLMClient()
        result = await asyncio.to_thread(
            llm.chat_respond, messages, filters_summary, results_summary
        )
        return result
    except Exception as e:
        traceback.print_exc()
        return {"response": f"Sorry, something went wrong: {e}", "action": None}


@app.post("/api/search")
async def search(request: Request):
    body = await request.json()
    query = body.get("query", "").strip()
    exclude_user_ids = set(body.get("exclude_user_ids", []))

    if not query:
        async def error_stream():
            yield {"event": "error", "data": json.dumps({"message": "Query is required"})}
        return EventSourceResponse(error_stream())

    async def event_stream():
        try:
            llm = LLMClient()
            queue: asyncio.Queue = asyncio.Queue()

            # Step 1: Extract intent
            yield {"event": "progress", "data": json.dumps({"message": "Analyzing your request..."})}

            intent = await asyncio.to_thread(llm.extract_intent, query, None)

            yield {
                "event": "intent",
                "data": json.dumps({
                    "is_clear": intent.is_clear,
                    "questions": [
                        {"question": q.question, "reason": q.reason}
                        for q in intent.questions
                    ],
                    "persona": intent.persona,
                    "topic": intent.topic,
                    "goal": intent.goal,
                    "specificity": intent.specificity,
                }),
            }

            if not intent.is_clear:
                return

            # Step 2: Generate queries
            yield {"event": "progress", "data": json.dumps({"message": "Generating search strategies..."})}

            queries_response = await asyncio.to_thread(llm.generate_search_queries, intent)

            if not queries_response.queries:
                yield {"event": "error", "data": json.dumps({"message": "Failed to generate search queries"})}
                return

            yield {
                "event": "queries",
                "data": json.dumps([
                    {"query": q.query, "rationale": q.rationale, "angle": q.angle}
                    for q in queries_response.queries
                ]),
            }

            # Step 3: Execute searches with progress updates via queue
            twitter = TwitterClient()
            await twitter.initialize()
            orchestrator = SearchOrchestrator(twitter)

            async def status_callback(msg: str):
                await queue.put(msg)

            query_strings = [q.query for q in queries_response.queries]

            search_task = asyncio.create_task(
                orchestrator.execute_searches(query_strings, status_callback, exclude_user_ids=exclude_user_ids or None)
            )

            # Drain progress messages while search runs
            while not search_task.done():
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=0.5)
                    yield {"event": "progress", "data": json.dumps({"message": msg})}
                except asyncio.TimeoutError:
                    continue

            accounts = search_task.result()

            # Drain any remaining messages
            while not queue.empty():
                msg = queue.get_nowait()
                yield {"event": "progress", "data": json.dumps({"message": msg})}

            if not accounts:
                yield {"event": "error", "data": json.dumps({"message": "No accounts found. Try broadening your search."})}
                return

            # Step 4: Rank accounts
            yield {
                "event": "progress",
                "data": json.dumps({"message": f"Found {len(accounts)} accounts, analyzing relevance..."}),
            }

            ranking = await llm.rank_accounts_parallel(intent, accounts)

            yield {
                "event": "results",
                "data": json.dumps({
                    "ranked": [_serialize_account(r) for r in ranking.ranked_accounts],
                    "quality": ranking.result_quality,
                    "refinement_questions": ranking.refinement_questions,
                }),
            }

        except Exception as e:
            traceback.print_exc()
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_stream())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
