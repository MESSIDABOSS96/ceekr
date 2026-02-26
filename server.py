"""FastAPI backend for Twitter Account Finder."""

import asyncio
import json
import traceback

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sse_starlette.sse import EventSourceResponse

from algorithms import get_algorithm
from config import (
    DATABASE_PATH,
    FRONTEND_URLS,
    PORT,
    TWITTER_CLIENT_ID,
    TWITTER_CLIENT_SECRET,
    TWITTER_REDIRECT_URI,
    is_oauth_configured,
    validate_config,
)
from core.auth import (
    create_auth_url,
    create_session,
    delete_session,
    exchange_code,
    fetch_twitter_user,
    get_session,
)
from core.database import WorkspaceDB
from core.fast_path import QueryType, classify_query, execute_handle_lookup
from core.llm import LLMClient
from core.twitter import TwitterClient
from core.workspace import WorkspaceOrchestrator


app = FastAPI(title="Twitter Account Finder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_URLS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    db = WorkspaceDB(DATABASE_PATH)
    await db.initialize()
    app.state.db = db


@app.on_event("shutdown")
async def shutdown():
    if hasattr(app.state, "db"):
        await app.state.db.close()


@app.get("/api/health")
async def health():
    errors = validate_config()
    return {"ok": len(errors) == 0, "errors": errors}


# ── Auth endpoints ──────────────────────────────────────────


@app.get("/api/auth/config")
async def auth_config():
    return {"oauth_enabled": is_oauth_configured()}


@app.get("/api/auth/twitter")
async def auth_twitter():
    if not is_oauth_configured():
        return {"error": "OAuth not configured"}
    url, _state = create_auth_url(TWITTER_CLIENT_ID, TWITTER_REDIRECT_URI)
    return RedirectResponse(url)


@app.get("/api/auth/twitter/callback")
async def auth_twitter_callback(code: str, state: str):
    try:
        token_data = await exchange_code(
            code=code,
            state=state,
            client_id=TWITTER_CLIENT_ID,
            client_secret=TWITTER_CLIENT_SECRET,
            redirect_uri=TWITTER_REDIRECT_URI,
        )
        access_token = token_data["access_token"]
        user = await fetch_twitter_user(access_token)
        session_token = create_session(user, access_token)

        # Start background network fetch
        asyncio.create_task(_fetch_network_background(session_token, user.user_id))

        return RedirectResponse(f"{FRONTEND_URLS[0]}?auth_token={session_token}")
    except Exception as e:
        traceback.print_exc()
        return RedirectResponse(f"{FRONTEND_URLS[0]}?auth_error={e}")


@app.get("/api/auth/me")
async def auth_me(request: Request):
    token = request.headers.get("x-session-token")
    if not token:
        return {"authenticated": False}
    session = get_session(token)
    if not session:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "user": {
            "user_id": session.user.user_id,
            "handle": session.user.handle,
            "name": session.user.name,
            "profile_image_url": session.user.profile_image_url,
        },
        "network_loaded": session.network.loaded,
        "network_loading": session.network.loading,
    }


@app.post("/api/auth/logout")
async def auth_logout(request: Request):
    token = request.headers.get("x-session-token")
    if token:
        delete_session(token)
    return {"ok": True}


async def _fetch_network_background(session_token: str, user_id: str):
    """Background task to fetch the user's follow lists."""
    session = get_session(session_token)
    if not session:
        return

    session.network.loading = True
    try:
        twitter = TwitterClient()
        await twitter.initialize()

        following, followers = await asyncio.gather(
            twitter.fetch_follow_list(user_id, "following", max_count=1000),
            twitter.fetch_follow_list(user_id, "followers", max_count=1000),
        )
        session.network.following_ids = following
        session.network.follower_ids = followers
        session.network.loaded = True
        print(f"Network loaded for @{session.user.handle}: {len(following)} following, {len(followers)} followers")
    except Exception as e:
        print(f"Error fetching network for @{session.user.handle}: {e}")
        traceback.print_exc()
    finally:
        session.network.loading = False


def require_auth(request: Request):
    """Require a valid session token. Returns the session or raises 401."""
    token = request.headers.get("x-session-token")
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session


def _serialize_account(ranked):
    """Serialize a RankedAccount to a JSON-safe dict."""
    acc = ranked.account
    result = {
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
                "media_urls": t.media_urls,
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
        "why_relevant": ranked.why_relevant,
        "bucket": ranked.bucket,
        "summary": ranked.summary,
        "highlight_tweet_indices": ranked.highlight_tweet_indices,
        "suggested_approach": ranked.suggested_approach,
        "evidence_highlights": ranked.evidence_highlights,
        "confidence": ranked.confidence,
        "enrichment": None,
    }
    if ranked.enrichment:
        result["enrichment"] = {
            "external_link": ranked.enrichment.external_link,
            "link_label": ranked.enrichment.link_label,
            "context_note": ranked.enrichment.context_note,
        }
    return result


@app.post("/api/chat")
async def chat(request: Request):
    require_auth(request)
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
        result = await llm.chat_respond(messages, filters_summary, results_summary)
        return result
    except Exception as e:
        traceback.print_exc()
        return {"response": f"Sorry, something went wrong: {e}", "action": None}


@app.post("/api/search")
async def search(request: Request):
    # Auth is optional — enables network matching when logged in
    token = request.headers.get("x-session-token")
    session = get_session(token) if token else None

    body = await request.json()
    query = body.get("query", "").strip()

    if not query:
        async def error_stream():
            yield {"event": "error", "data": json.dumps({"message": "Query is required"})}
        return EventSourceResponse(error_stream())

    user_network = session.network if session and session.network.loaded else None

    async def event_stream():
        try:
            classification = classify_query(query)

            # ── @handle → fast path only ──
            if classification.query_type == QueryType.HANDLE_LOOKUP:
                yield {"event": "progress", "data": json.dumps({"message": "Looking up profile..."})}

                twitter = TwitterClient()
                await twitter.initialize()

                ranked = await execute_handle_lookup(
                    twitter, classification.raw_query, user_network=user_network,
                )

                if not ranked:
                    yield {"event": "error", "data": json.dumps({"message": "Account not found."})}
                    return

                yield {
                    "event": "results",
                    "data": json.dumps({
                        "ranked": [_serialize_account(r) for r in ranked],
                        "quality": "strong",
                        "refinement_questions": [],
                    }),
                }
                return

            # ── Everything else: run selected algorithm ──
            twitter = TwitterClient()
            await twitter.initialize()
            queue: asyncio.Queue = asyncio.Queue()

            algorithm = get_algorithm()
            algorithm_task = asyncio.create_task(
                algorithm.run(query, twitter, queue, user_network)
            )

            # --- Drain progress / structured events while algorithm runs ---
            while not algorithm_task.done():
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=0.5)
                    if isinstance(msg, str) and msg.startswith("{"):
                        try:
                            parsed = json.loads(msg)
                            event_type = parsed.pop("_event", None)
                            if event_type == "intent":
                                yield {"event": "intent", "data": json.dumps(parsed)}
                                continue
                            elif event_type == "queries":
                                yield {"event": "queries", "data": json.dumps(parsed["queries"])}
                                continue
                        except (json.JSONDecodeError, KeyError):
                            pass
                    yield {"event": "progress", "data": json.dumps({"message": msg})}
                except asyncio.TimeoutError:
                    continue

            # Drain remaining queue messages
            while not queue.empty():
                msg = queue.get_nowait()
                if isinstance(msg, str) and msg.startswith("{"):
                    try:
                        parsed = json.loads(msg)
                        event_type = parsed.pop("_event", None)
                        if event_type == "intent":
                            yield {"event": "intent", "data": json.dumps(parsed)}
                            continue
                        elif event_type == "queries":
                            yield {"event": "queries", "data": json.dumps(parsed["queries"])}
                            continue
                    except (json.JSONDecodeError, KeyError):
                        pass
                yield {"event": "progress", "data": json.dumps({"message": msg})}

            # --- Collect algorithm result ---
            result = algorithm_task.result()

            if not result.ranked_accounts:
                yield {"event": "error", "data": json.dumps({"message": "No accounts found. Try broadening your search."})}
                return

            yield {
                "event": "results",
                "data": json.dumps({
                    "ranked": [_serialize_account(r) for r in result.ranked_accounts],
                    "quality": result.quality,
                    "refinement_questions": result.refinement_questions,
                }),
            }

        except Exception as e:
            traceback.print_exc()
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_stream(), ping=15)


# ── Workspace endpoints ───────────────────────────────────────


@app.post("/api/workspace")
async def create_workspace(request: Request):
    """Create a workspace from a query — SSE stream."""
    token = request.headers.get("x-session-token")
    session = get_session(token) if token else None

    body = await request.json()
    query = body.get("query", "").strip()

    if not query:
        async def error_stream():
            yield {"event": "error", "data": json.dumps({"message": "Query is required"})}
        return EventSourceResponse(error_stream())

    user_network = session.network if session and session.network.loaded else None
    db: WorkspaceDB = app.state.db

    async def event_stream():
        try:
            twitter = TwitterClient()
            await twitter.initialize()
            queue: asyncio.Queue = asyncio.Queue()

            orchestrator = WorkspaceOrchestrator(db)
            orchestrator_task = asyncio.create_task(
                orchestrator.create_workspace(query, twitter, queue, user_network)
            )

            # Drain progress events while orchestrator runs
            while not orchestrator_task.done():
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=0.5)
                    if isinstance(msg, str) and msg.startswith("{"):
                        try:
                            parsed = json.loads(msg)
                            event_type = parsed.pop("_event", None)
                            if event_type == "intent":
                                yield {"event": "intent", "data": json.dumps(parsed)}
                                continue
                            elif event_type == "queries":
                                yield {"event": "queries", "data": json.dumps(parsed["queries"])}
                                continue
                        except (json.JSONDecodeError, KeyError):
                            pass
                    yield {"event": "progress", "data": json.dumps({"message": msg})}
                except asyncio.TimeoutError:
                    continue

            # Drain remaining
            while not queue.empty():
                msg = queue.get_nowait()
                if isinstance(msg, str) and msg.startswith("{"):
                    try:
                        parsed = json.loads(msg)
                        event_type = parsed.pop("_event", None)
                        if event_type == "intent":
                            yield {"event": "intent", "data": json.dumps(parsed)}
                            continue
                        elif event_type == "queries":
                            yield {"event": "queries", "data": json.dumps(parsed["queries"])}
                            continue
                    except (json.JSONDecodeError, KeyError):
                        pass
                yield {"event": "progress", "data": json.dumps({"message": msg})}

            workspace_data = orchestrator_task.result()
            yield {"event": "workspace", "data": json.dumps(workspace_data)}

        except Exception as e:
            traceback.print_exc()
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_stream(), ping=15)


@app.get("/api/workspace/{workspace_id}")
async def get_workspace(workspace_id: str):
    """Load workspace state with journals, axes, and metadata."""
    db: WorkspaceDB = app.state.db
    ws = await db.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    journals = await db.get_journals(workspace_id)
    total_people = await db.get_workspace_people_count(workspace_id)
    axes = await db.get_axes(workspace_id)

    # Add people_count to each journal
    journal_dicts = []
    for j in journals:
        people_count = await db.get_journal_people_count(j["id"])
        journal_dicts.append({
            "id": j["id"],
            "label": j["label"],
            "description": j["description"],
            "color": j["color"],
            "people_count": people_count,
            "canvas_x": j["canvas_x"],
            "canvas_y": j["canvas_y"],
            "enrichment_status": j["enrichment_status"],
        })

    refinement_questions = []
    if ws.get("refinement_questions_json"):
        refinement_questions = json.loads(ws["refinement_questions_json"])

    intent = None
    if ws.get("intent_json"):
        intent = json.loads(ws["intent_json"])

    axes_dicts = [
        {
            "id": a["id"],
            "axis_key": a["axis_key"],
            "axis_label": a["axis_label"],
            "example_groups": a["example_groups"],
        }
        for a in axes
    ]

    return {
        "workspace_id": ws["id"],
        "query": ws["query"],
        "status": ws["status"],
        "summary": ws["summary"],
        "quality": ws["quality"],
        "intent": intent,
        "journals": journal_dicts,
        "axes": axes_dicts,
        "active_axis_id": ws.get("active_axis_id"),
        "recommendation_reason": ws.get("recommendation_reason", ""),
        "total_people": total_people,
        "refinement_questions": refinement_questions,
        "created_at": ws["created_at"],
        "updated_at": ws["updated_at"],
    }


@app.get("/api/workspace/{workspace_id}/journal/{journal_id}")
async def get_journal_people(workspace_id: str, journal_id: str):
    """Load full people data for a journal."""
    db: WorkspaceDB = app.state.db

    # Verify workspace exists
    ws = await db.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    people = await db.get_journal_people(journal_id)
    return {"journal_id": journal_id, "people": people}


@app.post("/api/workspace/{workspace_id}/regroup")
async def regroup_workspace(workspace_id: str, request: Request):
    """Re-group a workspace along a different axis."""
    db: WorkspaceDB = app.state.db

    ws = await db.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    body = await request.json()
    axis_id = body.get("axis_id")
    if not axis_id:
        raise HTTPException(status_code=400, detail="axis_id is required")

    try:
        orchestrator = WorkspaceOrchestrator(db)
        result = await orchestrator.regroup_workspace(workspace_id, axis_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/workspace/{workspace_id}/layout")
async def update_layout(workspace_id: str, request: Request):
    """Update canvas positions for journals."""
    db: WorkspaceDB = app.state.db

    ws = await db.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    body = await request.json()
    positions = body.get("positions", [])

    for pos in positions:
        journal_id = pos.get("journal_id")
        canvas_x = pos.get("canvas_x")
        canvas_y = pos.get("canvas_y")
        if journal_id is not None and canvas_x is not None and canvas_y is not None:
            await db.update_journal_layout(journal_id, canvas_x, canvas_y)

    return {"ok": True}


@app.get("/api/workspaces")
async def list_workspaces():
    """List all workspaces."""
    db: WorkspaceDB = app.state.db
    workspaces = await db.list_workspaces()
    return {"workspaces": workspaces}


@app.delete("/api/workspace/{workspace_id}")
async def delete_workspace(workspace_id: str):
    """Delete a workspace."""
    db: WorkspaceDB = app.state.db
    deleted = await db.delete_workspace(workspace_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
