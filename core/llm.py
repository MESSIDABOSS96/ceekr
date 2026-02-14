"""LLM layer for Claude API calls."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from config import (
    ABSOLUTE_MIN_THRESHOLD,
    ANTHROPIC_API_KEY,
    ANTHROPIC_FAST_MODEL,
    ANTHROPIC_MODEL,
    MAX_BIO_LENGTH,
    MAX_TWEET_LENGTH,
    MAX_TWEETS_FOR_RANKING,
    MIN_RESULTS_BEFORE_LOWERING,
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
from prompts.search_plan import format_search_plan_prompt


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
        Combined intent extraction + query generation in a single Haiku call.

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
                        "min_score_threshold": {
                            "type": "integer",
                            "description": "Minimum relevance score to show (3-8)",
                            "minimum": 3,
                            "maximum": 8,
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
                        "queries": {
                            "type": "array",
                            "description": "5 Twitter search queries",
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
                        "min_score_threshold",
                        "key_signals",
                        "anti_signals",
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
                    min_score_threshold=result.get("min_score_threshold", 5),
                    key_signals=result.get("key_signals", []),
                    anti_signals=result.get("anti_signals", []),
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
                "description": "Rank Twitter accounts by relevance with evidence-based explanations",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ranked_accounts": {
                            "type": "array",
                            "description": "Accounts sorted by relevance (highest first)",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "handle": {
                                        "type": "string",
                                        "description": "Twitter handle",
                                    },
                                    "relevance_score": {
                                        "type": "number",
                                        "description": "Relevance score (1-10)",
                                    },
                                    "why_relevant": {
                                        "type": "string",
                                        "description": "2-3 sentence evidence-based explanation",
                                    },
                                    "evidence_highlights": {
                                        "type": "array",
                                        "description": "1-3 direct quotes from tweets/bio proving relevance",
                                        "items": {"type": "string"},
                                        "minItems": 1,
                                        "maxItems": 3,
                                    },
                                    "confidence": {
                                        "type": "string",
                                        "enum": ["high", "medium", "low"],
                                        "description": "Confidence level based on evidence strength",
                                    },
                                    "suggested_approach": {
                                        "type": "string",
                                        "description": "Optional engagement suggestion",
                                    },
                                },
                                "required": [
                                    "handle",
                                    "relevance_score",
                                    "why_relevant",
                                    "evidence_highlights",
                                    "confidence",
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
            model=self.model,
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
        accounts_by_handle = {acc.handle.lower(): acc for acc in accounts}
        all_ranked: list[RankedAccount] = []

        for result in batch_results:
            if isinstance(result, Exception):
                print(f"Ranking batch failed: {result}")
                continue

            for item in result:
                handle = item["handle"].lower().lstrip("@")
                if handle in accounts_by_handle:
                    all_ranked.append(
                        RankedAccount(
                            account=accounts_by_handle[handle],
                            relevance_score=item["relevance_score"],
                            why_relevant=item["why_relevant"],
                            suggested_approach=item.get("suggested_approach"),
                            evidence_highlights=item.get("evidence_highlights", []),
                            confidence=item.get("confidence", "medium"),
                        )
                    )

        # Sort by score descending
        all_ranked.sort(key=lambda r: r.relevance_score, reverse=True)

        # Apply score threshold, progressively lowering if too few results
        threshold = intent.min_score_threshold
        filtered = [r for r in all_ranked if r.relevance_score >= threshold]

        while len(filtered) < MIN_RESULTS_BEFORE_LOWERING and threshold > ABSOLUTE_MIN_THRESHOLD:
            threshold = max(threshold - 1, ABSOLUTE_MIN_THRESHOLD)
            filtered = [r for r in all_ranked if r.relevance_score >= threshold]

        # Compute quality assessment in Python
        high_scores = sum(1 for r in filtered if r.relevance_score >= 7)
        mid_scores = sum(1 for r in filtered if r.relevance_score >= 5)

        if high_scores >= 5:
            quality = "strong"
        elif high_scores >= 2 or mid_scores >= 10:
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
