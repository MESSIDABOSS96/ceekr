"""LLM layer for Claude API calls."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_FAST_MODEL,
    ANTHROPIC_MODEL,
    MAX_BIO_LENGTH,
    MAX_TWEET_LENGTH,
    MAX_TWEETS_FOR_RANKING,
    RANKING_BATCH_SIZE,
    RECENCY_BONUS_WINDOW_DAYS,
    STALE_ACCOUNT_DAYS,
)
from core.twitter import _tweet_recency_score

from .models import (
    RankedAccount,
    RankingResponse,
    SearchIntent,
    SearchQuery,
    TwitterAccount,
)
from prompts.ranking import format_ranking_prompt
from prompts.chat import format_chat_system_prompt
from prompts.search_plan import format_search_plan_prompt, format_fallback_prompt


class LLMClient:
    """Client for Claude API calls with structured output."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        self.model = ANTHROPIC_MODEL
        self.fast_model = ANTHROPIC_FAST_MODEL

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def plan_search(
        self, who: str, why: Optional[str] = None
    ) -> tuple[SearchIntent, list[SearchQuery]]:
        """
        Combined intent extraction + query generation in a single Sonnet call.

        Always returns queries (may be empty on failure).
        """
        tools = [
            {
                "name": "search_plan",
                "description": "Analyze the search request and generate a search plan with queries",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "persona": {
                            "type": "string",
                            "description": "The type of person to find",
                        },
                        "topic": {
                            "type": "string",
                            "description": "What they should be discussing",
                        },
                        "goal": {
                            "type": "string",
                            "description": "Why the user wants to find them",
                        },
                        "specificity": {
                            "type": "integer",
                            "description": "How specific the request is (1-5)",
                            "minimum": 1,
                            "maximum": 5,
                        },
                        "key_signals": {
                            "type": "array",
                            "description": "3-5 specific things to look for in tweets/bios",
                            "items": {"type": "string"},
                        },
                        "anti_signals": {
                            "type": "array",
                            "description": "2-3 things that indicate NOT the right person",
                            "items": {"type": "string"},
                        },
                        "bio_search_terms": {
                            "type": "array",
                            "description": "3-4 short keyword phrases for bio/profile searches (1-3 words each)",
                            "items": {"type": "string"},
                        },
                        "mandatory_terms": {
                            "type": "array",
                            "description": "0-3 niche-specific terms that MUST appear in results. Empty for broad queries.",
                            "items": {"type": "string"},
                        },
                        "queries": {
                            "type": "array",
                            "description": "5 Twitter search queries from different angles",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "The Twitter search query string",
                                    },
                                    "rationale": {
                                        "type": "string",
                                        "description": "Why this query helps find relevant people",
                                    },
                                    "angle": {
                                        "type": "string",
                                        "description": "What angle this query takes",
                                    },
                                },
                                "required": ["query", "rationale", "angle"],
                            },
                        },
                    },
                    "required": [
                        "persona",
                        "topic",
                        "goal",
                        "specificity",
                        "key_signals",
                        "anti_signals",
                        "bio_search_terms",
                        "mandatory_terms",
                        "queries",
                    ],
                },
            }
        ]

        prompt = format_search_plan_prompt(who, why)

        response = await self.client.messages.create(
            model=self.fast_model,
            max_tokens=2048,
            tools=tools,
            tool_choice={"type": "tool", "name": "search_plan"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if block.type == "tool_use":
                result = block.input

                intent = SearchIntent(
                    persona=result.get("persona", ""),
                    topic=result.get("topic", ""),
                    goal=result.get("goal", ""),
                    specificity=result.get("specificity", 3),
                    suggested_query_count=5,
                    bio_search_terms=result.get("bio_search_terms", []),
                    key_signals=result.get("key_signals", []),
                    anti_signals=result.get("anti_signals", []),
                    mandatory_terms=result.get("mandatory_terms", []),
                )

                queries = [
                    SearchQuery(
                        query=q["query"],
                        rationale=q["rationale"],
                        angle=q["angle"],
                    )
                    for q in result.get("queries", [])
                ]

                return intent, queries

        # Fallback: defaults with no queries
        return SearchIntent(), []

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_fallback_queries(
        self,
        intent: SearchIntent,
        original_queries: list[str],
        accounts_found: int,
    ) -> list[SearchQuery]:
        """Generate 3 broader fallback queries when initial search found too few accounts."""
        tools = [
            {
                "name": "fallback_queries",
                "description": "Generate broader fallback search queries",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "queries": {
                            "type": "array",
                            "description": "3 broader Twitter search queries",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "The Twitter search query string",
                                    },
                                    "rationale": {
                                        "type": "string",
                                        "description": "Why this broader query helps",
                                    },
                                    "angle": {
                                        "type": "string",
                                        "description": "What angle this query takes",
                                    },
                                },
                                "required": ["query", "rationale", "angle"],
                            },
                        },
                    },
                    "required": ["queries"],
                },
            }
        ]

        prompt = format_fallback_prompt(intent, original_queries, accounts_found)

        response = await self.client.messages.create(
            model=self.fast_model,
            max_tokens=1024,
            tools=tools,
            tool_choice={"type": "tool", "name": "fallback_queries"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if block.type == "tool_use":
                return [
                    SearchQuery(
                        query=q["query"],
                        rationale=q["rationale"],
                        angle=q["angle"],
                    )
                    for q in block.input.get("queries", [])
                ]

        return []

    async def triage_accounts(
        self,
        intent: SearchIntent,
        accounts: list[TwitterAccount],
    ) -> list[TwitterAccount]:
        """Fast triage using Haiku — filter obviously irrelevant accounts before full ranking."""
        from prompts.triage import format_triage_prompt

        # Build minimal data for triage (less tokens = faster)
        accounts_data = []
        for acc in accounts:
            best_tweet = ""
            if acc.recent_tweets:
                best_tweet = acc.recent_tweets[0].text[:100]
            accounts_data.append({
                "handle": acc.handle,
                "name": acc.name,
                "bio": (acc.bio or "")[:100],
                "best_tweet": best_tweet,
            })

        accounts_json = json.dumps(accounts_data, indent=2)

        tools = [
            {
                "name": "triage",
                "description": "Triage accounts into advance or skip",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "decisions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "handle": {"type": "string"},
                                    "decision": {
                                        "type": "string",
                                        "enum": ["advance", "skip"],
                                    },
                                },
                                "required": ["handle", "decision"],
                            },
                        },
                    },
                    "required": ["decisions"],
                },
            }
        ]

        prompt = format_triage_prompt(intent, accounts_json)

        response = await self.client.messages.create(
            model=self.fast_model,
            max_tokens=4096,
            tools=tools,
            tool_choice={"type": "tool", "name": "triage"},
            messages=[{"role": "user", "content": prompt}],
        )

        advance_handles: set[str] = set()
        for block in response.content:
            if block.type == "tool_use":
                for d in block.input.get("decisions", []):
                    if d.get("decision") == "advance":
                        advance_handles.add(d["handle"].lower().lstrip("@"))

        if not advance_handles:
            # If triage returns nothing, don't filter (safety net)
            return accounts

        return [acc for acc in accounts if acc.handle.lower() in advance_handles]

    async def _rank_batch(
        self,
        intent: SearchIntent,
        accounts: list[TwitterAccount],
        user_network=None,
    ) -> list[dict]:
        """Rank a single batch of accounts. Returns raw ranked dicts."""
        accounts_data = []
        for acc in accounts:
            # Determine network match type
            network_match = None
            if user_network:
                you_follow = acc.user_id in user_network.following_ids
                follows_you = acc.user_id in user_network.follower_ids
                if you_follow and follows_you:
                    network_match = "mutual"
                elif you_follow:
                    network_match = "you_follow"
                elif follows_you:
                    network_match = "follows_you"

            # Sort tweets by blended recency+engagement
            sorted_tweets = sorted(
                acc.recent_tweets,
                key=_tweet_recency_score,
                reverse=True,
            )

            # Compute recency metadata for the LLM
            now = datetime.now(timezone.utc)
            days_since_newest = None
            activity_status = "stale"
            for t in sorted_tweets:
                if t.created_at is not None:
                    created = (
                        t.created_at
                        if t.created_at.tzinfo
                        else t.created_at.replace(tzinfo=timezone.utc)
                    )
                    days = max(0, (now - created).total_seconds() / 86400)
                    if days_since_newest is None or days < days_since_newest:
                        days_since_newest = days
            if days_since_newest is not None:
                if days_since_newest <= RECENCY_BONUS_WINDOW_DAYS:
                    activity_status = "active"
                elif days_since_newest <= STALE_ACCOUNT_DAYS:
                    activity_status = "somewhat_active"
                else:
                    activity_status = "stale"

            account_dict = {
                "handle": acc.handle,
                "name": acc.name,
                "bio": (acc.bio or "")[:MAX_BIO_LENGTH],
                "followers_count": acc.followers_count,
                "following_count": acc.following_count,
                "location": acc.location or "",
                "verified": acc.verified,
                "days_since_newest_tweet": round(days_since_newest, 1) if days_since_newest is not None else None,
                "activity_status": activity_status,
                "recent_tweets": [
                    {
                        "text": t.text[:MAX_TWEET_LENGTH],
                        "date": t.created_at.isoformat() if t.created_at else None,
                        "likes": t.like_count,
                        "retweets": t.retweet_count,
                    }
                    for t in sorted_tweets[:MAX_TWEETS_FOR_RANKING]
                ],
                "matched_query_count": len(acc.matched_queries),
                "matched_queries": acc.matched_queries[:3],
            }
            if network_match:
                account_dict["network_match"] = network_match
            accounts_data.append(account_dict)

        accounts_json = json.dumps(accounts_data, indent=2)

        tools = [
            {
                "name": "rank_accounts",
                "description": "Categorize Twitter accounts into bucket tiers by relevance",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ranked_accounts": {
                            "type": "array",
                            "description": "Accounts categorized by bucket tier (top_match first, then strong, good, exclude)",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "handle": {
                                        "type": "string",
                                        "description": "Twitter handle (without @)",
                                    },
                                    "bucket": {
                                        "type": "string",
                                        "enum": ["top_match", "strong_match", "good_match", "exclude"],
                                        "description": "Bucket tier for this account",
                                    },
                                    "summary": {
                                        "type": "string",
                                        "description": "User-facing summary (detailed for top/strong, brief for good, empty for exclude)",
                                    },
                                    "highlight_tweet_indices": {
                                        "type": "array",
                                        "description": "0-based indices of most relevant tweets",
                                        "items": {"type": "integer"},
                                    },
                                },
                                "required": [
                                    "handle",
                                    "bucket",
                                    "summary",
                                    "highlight_tweet_indices",
                                ],
                            },
                        },
                    },
                    "required": ["ranked_accounts"],
                },
            }
        ]

        prompt = format_ranking_prompt(intent, accounts_json)

        response = await self.client.messages.create(
            model=self.fast_model,
            max_tokens=8192,
            tools=tools,
            tool_choice={"type": "tool", "name": "rank_accounts"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if block.type == "tool_use":
                return block.input.get("ranked_accounts", [])

        return []

    async def rank_accounts(
        self,
        intent: SearchIntent,
        accounts: list[TwitterAccount],
        user_network=None,
    ) -> RankingResponse:
        """
        Rank accounts by relevance using batched parallel LLM calls.

        Applies score threshold from intent and computes quality assessment in Python.
        """
        # Split into batches
        batches = []
        for i in range(0, len(accounts), RANKING_BATCH_SIZE):
            batches.append(accounts[i : i + RANKING_BATCH_SIZE])

        # Rank all batches in parallel
        tasks = [
            self._rank_batch(intent, batch, user_network)
            for batch in batches
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge results from all batches
        from core.models import BUCKET_SCORE_MAP
        accounts_by_handle = {acc.handle.lower(): acc for acc in accounts}
        all_ranked: list[RankedAccount] = []

        for result in batch_results:
            if isinstance(result, Exception):
                print(f"Ranking batch failed: {result}")
                continue

            for item in result:
                handle = item["handle"].lower().lstrip("@")
                if handle in accounts_by_handle:
                    bucket = item.get("bucket", "good_match")
                    summary = item.get("summary", "")
                    score = BUCKET_SCORE_MAP.get(bucket, 5.0)
                    all_ranked.append(
                        RankedAccount(
                            account=accounts_by_handle[handle],
                            relevance_score=score,
                            bucket=bucket,
                            summary=summary,
                            highlight_tweet_indices=item.get("highlight_tweet_indices", []),
                            why_relevant=summary or f"Matched as {bucket.replace('_', ' ')}.",
                            evidence_highlights=[],
                            confidence="high" if bucket == "top_match" else "medium" if bucket == "strong_match" else "low",
                        )
                    )

        # Sort by bucket tier then followers
        from core.models import BUCKET_SORT_ORDER
        all_ranked.sort(
            key=lambda r: (BUCKET_SORT_ORDER.get(r.bucket, 3), -r.account.followers_count),
        )

        # Filter out excluded accounts
        filtered = [r for r in all_ranked if r.bucket != "exclude"]

        # Compute quality assessment using bucket counts
        top_count = sum(1 for r in filtered if r.bucket == "top_match")
        strong_count = sum(1 for r in filtered if r.bucket == "strong_match")
        good_count = sum(1 for r in filtered if r.bucket == "good_match")

        if top_count >= 3 and (top_count + strong_count) >= 5:
            quality = "strong"
        elif top_count >= 1 or (strong_count + good_count) >= 5:
            quality = "moderate"
        else:
            quality = "weak"

        # Generate refinement suggestions for weak results
        refinement_questions = []
        if quality == "weak":
            refinement_questions = [
                f"Could you be more specific about what aspect of '{intent.topic}' you're interested in?",
                f"Are you looking for {intent.persona} specifically, or would adjacent roles also work?",
            ]

        return RankingResponse(
            ranked_accounts=filtered,
            result_quality=quality,
            refinement_questions=refinement_questions,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def chat_respond(
        self,
        messages: list[dict],
        filters_summary: str,
        results_summary: str,
    ) -> dict:
        """
        Handle a chat message for search refinement.

        Returns dict with 'response' (str) and optional 'action' (dict).
        """
        tools = [
            {
                "name": "run_search",
                "description": "Run a new Twitter profile search with the given query",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message to show the user about what you're searching for",
                        },
                        "query": {
                            "type": "string",
                            "description": "The search query to run",
                        },
                    },
                    "required": ["message", "query"],
                },
            },
            {
                "name": "apply_filters",
                "description": "Adjust filters on the current results",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message to show the user about what filters were changed",
                        },
                        "filters": {
                            "type": "object",
                            "description": "Partial filter object — only include fields to change",
                            "properties": {
                                "keywords": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "followerMin": {"type": "number"},
                                "followerMax": {"type": "number"},
                                "location": {"type": "string"},
                                "verified": {"type": ["boolean", "null"]},
                                "postingFrequency": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "accountAge": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    },
                    "required": ["message", "filters"],
                },
            },
            {
                "name": "remove_profiles",
                "description": "Remove specific profiles from results by handle",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message to show the user",
                        },
                        "handles": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Twitter handles to remove (without @)",
                        },
                    },
                    "required": ["message", "handles"],
                },
            },
            {
                "name": "respond",
                "description": "Send a conversational response (for explanations, suggestions, or declining off-topic requests)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The response message",
                        },
                    },
                    "required": ["message"],
                },
            },
        ]

        system_prompt = format_chat_system_prompt(filters_summary, results_summary)

        # Convert messages to Anthropic format
        api_messages = []
        for msg in messages:
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            messages=api_messages,
        )

        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                result = block.input

                if tool_name == "run_search":
                    return {
                        "response": result["message"],
                        "action": {"type": "search", "query": result["query"]},
                    }
                elif tool_name == "apply_filters":
                    return {
                        "response": result["message"],
                        "action": {"type": "filter", "filters": result["filters"]},
                    }
                elif tool_name == "remove_profiles":
                    return {
                        "response": result["message"],
                        "action": {
                            "type": "remove_profiles",
                            "removeHandles": result["handles"],
                        },
                    }
                else:  # respond
                    return {"response": result["message"]}

        # Fallback: extract text response
        text_parts = [b.text for b in response.content if hasattr(b, "text")]
        return {"response": " ".join(text_parts) if text_parts else "I'm not sure how to help with that. Want to refine your search?"}
