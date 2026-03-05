"""LLM layer for Claude API calls."""

import asyncio
import json
import math
import re
from datetime import datetime, timezone
from typing import Optional

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_FAST_MODEL,
    ANTHROPIC_MODEL,
    MAX_BIO_LENGTH,
    MAX_QUERIES,
    MAX_TWEET_LENGTH,
    MAX_TWEETS_FOR_RANKING,
    MIN_QUERIES,
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
from prompts.intent_check import INTENT_CHECK_TOOL, format_intent_check_prompt
from prompts.search_plan import format_search_plan_prompt, format_fallback_prompt
from prompts.axis_discovery import (
    AXIS_DISCOVERY_TOOL,
    format_axis_discovery_prompt,
)
from prompts.journal_generation import (
    JOURNAL_GENERATION_TOOL,
    format_journal_generation_prompt,
)
from prompts.combined_grouping import (
    COMBINED_GROUPING_TOOL,
    format_combined_grouping_prompt,
)
from prompts.workspace_chat import (
    WORKSPACE_CHAT_TOOLS,
    format_workspace_chat_prompt,
    build_journals_context,
)


def validate_query(q: str) -> str:
    """Repair queries that would return zero results on Twitter."""
    original = q
    # Extract and preserve date operators (since:/until:) before simplification
    date_ops = re.findall(r'\b(?:since|until):\d{4}-\d{2}-\d{2}\b', q)
    for op in date_ops:
        q = q.replace(op, "").strip()
    # Remove parentheses
    q = q.replace("(", "").replace(")", "")
    # Remove extra OR operators (keep at most 1)
    or_count = len(re.findall(r'\bOR\b', q))
    if or_count > 1:
        parts = re.split(r'\bOR\b', q)
        q = parts[0] + "OR" + parts[1]
        # Drop remaining OR parts
    # Count quoted phrases
    quoted = re.findall(r'"[^"]*"', q)
    if len(quoted) > 1:
        # Keep first quoted phrase + up to 1 extra word
        remaining = q
        for phrase in quoted[1:]:
            remaining = remaining.replace(phrase, "", 1)
        extra_words = remaining.split()
        # Remove the first quoted phrase from extra_words to avoid duplication
        extra_words = [w for w in extra_words if w not in quoted[0]]
        q = quoted[0] + (" " + extra_words[0] if extra_words else "")
    q = q.strip()
    # Re-append preserved date operators
    if date_ops:
        q = q + " " + " ".join(date_ops)
    if q != original:
        print(f"[validate_query] Repaired: {original!r} → {q!r}")
    return q


class LLMClient:
    """Client for Claude API calls with structured output."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        self.model = ANTHROPIC_MODEL
        self.fast_model = ANTHROPIC_FAST_MODEL

    async def extract_intent(self, query: str) -> dict:
        """
        Fast intent check using Haiku. Returns intent + clarification questions.

        Returns dict with: persona, topic, goal, specificity, needs_clarification,
        clarification_questions (list of {question, options}).
        """
        prompt = format_intent_check_prompt(query)

        response = await self.client.messages.create(
            model=self.fast_model,
            max_tokens=1024,
            tools=[INTENT_CHECK_TOOL],
            tool_choice={"type": "tool", "name": "check_intent"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if block.type == "tool_use":
                result = block.input
                specificity = result.get("specificity", 3)
                raw_questions = result.get("clarification_questions", [])
                # Normalize: if LLM returns old `options` format, join into placeholder
                questions = []
                for q in raw_questions:
                    if "placeholder" not in q and "options" in q:
                        q["placeholder"] = ", ".join(q.pop("options"))
                    questions.append(q)

                return {
                    "intent": {
                        "persona": result.get("persona", ""),
                        "topic": result.get("topic", ""),
                        "goal": result.get("goal", ""),
                        "specificity": specificity,
                    },
                    "needs_clarification": specificity < 4,
                    "clarification_questions": questions if specificity < 4 else [],
                }

        # Fallback — assume needs clarification
        return {
            "intent": {"persona": "", "topic": "", "goal": "", "specificity": 2},
            "needs_clarification": True,
            "clarification_questions": [],
        }

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
                        "time_constraint": {
                            "type": ["string", "null"],
                            "description": "ISO date YYYY-MM-DD for earliest relevant date, or null if no time constraint",
                        },
                        "queries": {
                            "type": "array",
                            "description": "3-7 Twitter search queries from different angles (count based on specificity)",
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

                specificity = result.get("specificity", 3)
                # Dynamic query count: broad → more queries, specific → fewer
                specificity_to_count = {1: 7, 2: 6, 3: 6, 4: 5, 5: 4}
                query_count = specificity_to_count.get(specificity, 5)

                time_constraint = result.get("time_constraint") or None

                intent = SearchIntent(
                    persona=result.get("persona", ""),
                    topic=result.get("topic", ""),
                    goal=result.get("goal", ""),
                    specificity=specificity,
                    suggested_query_count=query_count,
                    bio_search_terms=result.get("bio_search_terms", []),
                    key_signals=result.get("key_signals", []),
                    anti_signals=result.get("anti_signals", []),
                    mandatory_terms=result.get("mandatory_terms", []),
                    time_constraint=time_constraint,
                )

                queries = [
                    SearchQuery(
                        query=q["query"],
                        rationale=q["rationale"],
                        angle=q["angle"],
                    )
                    for q in result.get("queries", [])
                ]

                # Enforce query count bounds
                queries = queries[:max(query_count, MAX_QUERIES)]
                if len(queries) < MIN_QUERIES:
                    print(f"[queries] LLM returned {len(queries)}, expected {query_count}")

                # Safety net: if time_constraint is set, ensure every query has since:
                if intent.time_constraint:
                    since_op = f"since:{intent.time_constraint}"
                    for i, q in enumerate(queries):
                        if "since:" not in q.query:
                            queries[i] = SearchQuery(
                                query=f"{q.query} {since_op}",
                                rationale=q.rationale,
                                angle=q.angle,
                            )
                            print(f"[time_constraint] Appended {since_op} to query: {q.query}")

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
        anchors: Optional[list[dict]] = None,
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
                                    "evidence_highlights": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "1-2 direct quotes from tweets/bio proving relevance (for non-exclude accounts)",
                                    },
                                    "suggested_approach": {
                                        "type": "string",
                                        "description": "1-sentence suggestion for how to engage (for top_match/strong_match only, empty string otherwise)",
                                    },
                                },
                                "required": [
                                    "handle",
                                    "bucket",
                                    "summary",
                                    "highlight_tweet_indices",
                                    "evidence_highlights",
                                    "suggested_approach",
                                ],
                            },
                        },
                    },
                    "required": ["ranked_accounts"],
                },
            }
        ]

        prompt = format_ranking_prompt(intent, accounts_json)

        # Add anchor context for cross-batch consistency
        if anchors:
            anchor_text = json.dumps(anchors, indent=2)
            prompt += f"""

## Calibration Anchors
The following accounts have already been evaluated in a previous batch. Use them as reference points for consistent bucket assignment — do NOT re-score them, just use their buckets as calibration:
{anchor_text}
"""

        response = await self.client.messages.create(
            model=self.fast_model,
            max_tokens=12288,
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

        # Rank batches: first batch alone to extract anchors, rest in parallel
        batch_results: list = []
        anchor_accounts: list[dict] = []

        if batches:
            # First batch — no anchors
            first_result = await self._rank_batch(intent, batches[0], user_network)
            if isinstance(first_result, Exception):
                print(f"Ranking batch 0 failed: {first_result}")
                batch_results.append(first_result)
            else:
                batch_results.append(first_result)
                # Extract top 3 as anchors for subsequent batches
                anchor_accounts = [
                    {"handle": item["handle"], "bucket": item["bucket"], "summary": item.get("summary", "")}
                    for item in first_result
                    if item.get("bucket") == "top_match"
                ][:3]

            # Remaining batches in parallel with anchors
            if len(batches) > 1:
                tasks = [
                    self._rank_batch(intent, batch, user_network, anchors=anchor_accounts if anchor_accounts else None)
                    for batch in batches[1:]
                ]
                rest_results = await asyncio.gather(*tasks, return_exceptions=True)
                batch_results.extend(rest_results)

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
                    highlight_indices = item.get("highlight_tweet_indices", [])
                    acc = accounts_by_handle[handle]

                    # Ensure at least 1 tweet for non-exclude accounts
                    if not highlight_indices and bucket != "exclude" and acc.recent_tweets:
                        # Try to find tweets matching key signals or mandatory terms
                        search_terms = [s.lower() for s in (intent.key_signals + intent.mandatory_terms)]
                        for idx, tweet in enumerate(acc.recent_tweets):
                            if any(term in tweet.text.lower() for term in search_terms):
                                highlight_indices = [idx]
                                break
                        # Final fallback: most engaged tweet
                        if not highlight_indices:
                            best_idx = max(
                                range(len(acc.recent_tweets)),
                                key=lambda i: acc.recent_tweets[i].like_count + acc.recent_tweets[i].retweet_count,
                            )
                            highlight_indices = [best_idx]

                    all_ranked.append(
                        RankedAccount(
                            account=acc,
                            relevance_score=score,
                            bucket=bucket,
                            summary=summary,
                            highlight_tweet_indices=highlight_indices,
                            why_relevant=summary or f"Matched as {bucket.replace('_', ' ')}.",
                            evidence_highlights=item.get("evidence_highlights", []),
                            suggested_approach=item.get("suggested_approach") or None,
                            confidence="high" if bucket == "top_match" else "medium" if bucket == "strong_match" else "low",
                        )
                    )

        # Sort by bucket tier, then composite score within each bucket
        from core.models import BUCKET_SORT_ORDER

        def _within_bucket_sort_key(r: RankedAccount) -> tuple:
            query_signal = len(r.account.matched_queries) * 3
            # Average engagement across top tweets
            tweets = r.account.recent_tweets[:3]
            avg_engagement = sum(t.like_count + t.retweet_count for t in tweets) / max(len(tweets), 1)
            follower_log = math.log10(max(r.account.followers_count, 1))
            return (BUCKET_SORT_ORDER.get(r.bucket, 3), -(query_signal + avg_engagement * 0.1 + follower_log))

        all_ranked.sort(key=_within_bucket_sort_key)

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

    @staticmethod
    def _build_enriched_summaries(ranked_accounts: list[RankedAccount]) -> str:
        """Build enriched account summaries (~120 tokens/person) for axis discovery and journal generation."""
        lines = []
        for ra in ranked_accounts:
            acc = ra.account
            bio_snippet = (acc.bio or "")[:100]
            # Get a tweet snippet from evidence_highlights or first tweet
            tweet_snippet = ""
            if ra.evidence_highlights:
                tweet_snippet = ra.evidence_highlights[0][:120]
            elif acc.recent_tweets:
                tweet_snippet = acc.recent_tweets[0].text[:120]
            parts = [f"@{acc.handle}", acc.name, bio_snippet]
            if ra.summary:
                parts.append(f'summary: "{ra.summary[:150]}"')
            if tweet_snippet:
                parts.append(f'tweet: "{tweet_snippet}"')
            lines.append(" | ".join(parts))
        return "\n".join(lines)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def discover_axes(
        self,
        intent: SearchIntent,
        ranked_accounts: list[RankedAccount],
    ) -> tuple[list[dict], str, str]:
        """
        Discover 2-4 meaningful grouping axes for the result set.

        Returns (axes, recommended_key, recommendation_reason).
        Each axis dict has: axis_key, axis_label, example_groups.
        """
        enriched = self._build_enriched_summaries(ranked_accounts)
        prompt = format_axis_discovery_prompt(intent, enriched)

        response = await self.client.messages.create(
            model=self.fast_model,
            max_tokens=2048,
            tools=[AXIS_DISCOVERY_TOOL],
            tool_choice={"type": "tool", "name": "discover_axes"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if block.type == "tool_use":
                result = block.input
                axes = result.get("axes", [])
                recommended_key = result.get("recommended_axis_key", "")
                reason = result.get("recommendation_reason", "")
                return axes, recommended_key, reason

        return [], "", ""

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_journals(
        self,
        intent: SearchIntent,
        ranked_accounts: list[RankedAccount],
        axis_label: str,
        example_groups: list[str],
    ) -> tuple[str, list[dict]]:
        """
        Cluster ranked accounts into semantic journals along a single axis.

        Returns (summary, journals) where journals is a list of dicts with
        label, description, handles, journal_notes.
        """
        enriched = self._build_enriched_summaries(ranked_accounts)
        prompt = format_journal_generation_prompt(intent, enriched, axis_label, example_groups)

        response = await self.client.messages.create(
            model=self.fast_model,
            max_tokens=4096,
            tools=[JOURNAL_GENERATION_TOOL],
            tool_choice={"type": "tool", "name": "create_journals"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if block.type == "tool_use":
                result = block.input
                summary = result.get("summary", "")
                journals = result.get("journals", [])
                break
        else:
            return "", []

        # Post-LLM validation: deduplicate handles across journals
        all_handles = {ra.account.handle.lower() for ra in ranked_accounts}
        seen: set[str] = set()

        for journal in journals:
            unique_handles = []
            for h in journal.get("handles", []):
                h_lower = h.lower().lstrip("@")
                if h_lower not in seen:
                    seen.add(h_lower)
                    unique_handles.append(h_lower)
            journal["handles"] = unique_handles

        # Only force-assign unplaced handles if >30% are missing (likely LLM error)
        unplaced = all_handles - seen
        if unplaced and journals and len(unplaced) > len(all_handles) * 0.3:
            print(f"[grouping] {len(unplaced)}/{len(all_handles)} unplaced (>30%) — force-assigning")
            largest = max(journals, key=lambda j: len(j.get("handles", [])))
            largest["handles"].extend(sorted(unplaced))
            notes = largest.get("journal_notes", {})
            for h in unplaced:
                notes[h] = "Auto-assigned"
            largest["journal_notes"] = notes
        elif unplaced:
            print(f"[grouping] {len(unplaced)}/{len(all_handles)} unplaced — treating as intentional omission")

        return summary, journals

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def discover_and_generate_journals(
        self,
        intent: SearchIntent,
        ranked_accounts: list[RankedAccount],
    ) -> tuple[list[dict], str, str, str, list[dict]]:
        """
        Combined axis discovery + journal generation in a single LLM call.

        Returns (axes, recommended_key, recommendation_reason, summary, journals).
        """
        enriched = self._build_enriched_summaries(ranked_accounts)
        prompt = format_combined_grouping_prompt(intent, enriched)

        response = await self.client.messages.create(
            model=self.fast_model,
            max_tokens=4096,
            tools=[COMBINED_GROUPING_TOOL],
            tool_choice={"type": "tool", "name": "group_results"},
            messages=[{"role": "user", "content": prompt}],
        )

        axes = []
        recommended_key = ""
        recommendation_reason = ""
        summary = ""
        journals: list[dict] = []

        for block in response.content:
            if block.type == "tool_use":
                result = block.input
                axes = result.get("axes", [])
                recommended_key = result.get("recommended_axis_key", "")
                recommendation_reason = result.get("recommendation_reason", "")
                summary = result.get("summary", "")
                journals = result.get("journals", [])
                break

        # Post-LLM validation: deduplicate handles across journals
        all_handles = {ra.account.handle.lower() for ra in ranked_accounts}
        seen: set[str] = set()

        for journal in journals:
            unique_handles = []
            for h in journal.get("handles", []):
                h_lower = h.lower().lstrip("@")
                if h_lower not in seen:
                    seen.add(h_lower)
                    unique_handles.append(h_lower)
            journal["handles"] = unique_handles

        # Only force-assign unplaced handles if >30% are missing (likely LLM error)
        # Otherwise treat as intentional omission of marginal people
        unplaced = all_handles - seen
        if unplaced and journals and len(unplaced) > len(all_handles) * 0.3:
            print(f"[grouping] {len(unplaced)}/{len(all_handles)} unplaced (>30%) — force-assigning")
            largest = max(journals, key=lambda j: len(j.get("handles", [])))
            largest["handles"].extend(sorted(unplaced))
            notes = largest.get("journal_notes", {})
            for h in unplaced:
                notes[h] = "Auto-assigned"
            largest["journal_notes"] = notes
        elif unplaced:
            print(f"[grouping] {len(unplaced)}/{len(all_handles)} unplaced — treating as intentional omission")

        return axes, recommended_key, recommendation_reason, summary, journals

    async def workspace_chat_respond(
        self,
        messages: list[dict],
        workspace_context: dict,
        active_journal_id: Optional[str] = None,
        active_journal_people: Optional[list[dict]] = None,
    ):
        """
        Streaming workspace chat response with tool use.

        Yields dicts: {"type": "token", "text": "..."} or {"type": "tool", "name": ..., "input": ...}

        workspace_context keys: query, total_people, quality, summary, journals
        """
        journals_context = build_journals_context(
            workspace_context["journals"],
            active_journal_id,
            active_journal_people,
        )
        system_prompt = format_workspace_chat_prompt(
            query=workspace_context["query"],
            total_people=workspace_context["total_people"],
            quality=workspace_context["quality"],
            summary=workspace_context["summary"],
            journals_context=journals_context,
        )

        # Convert messages to Anthropic format
        api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

        # Manual retry loop — can't use @retry on async generators
        response = None
        last_error = None
        for attempt in range(3):
            try:
                async with self.client.messages.stream(
                    model=self.model,
                    max_tokens=1024,
                    system=system_prompt,
                    tools=WORKSPACE_CHAT_TOOLS,
                    messages=api_messages,
                ) as stream:
                    async for event in stream:
                        if event.type == "content_block_delta":
                            if hasattr(event.delta, "text"):
                                yield {"type": "token", "text": event.delta.text}

                    # Extract final message for tool use (must be inside async with)
                    response = await stream.get_final_message()
                last_error = None
                break
            except anthropic.APIStatusError as e:
                if e.status_code in (429, 529, 503) and attempt < 2:
                    last_error = e
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

        if last_error:
            raise last_error

        for block in response.content:
            if block.type == "tool_use":
                yield {"type": "tool", "name": block.name, "input": block.input}
                return

    async def generate_targeted_queries(
        self,
        search_description: str,
        existing_handles: list[str],
    ) -> list[SearchQuery]:
        """Generate 1-2 focused search queries for targeted workspace search."""
        existing_str = ", ".join(f"@{h}" for h in existing_handles[:20])
        prompt = f"""Generate 1-2 focused Twitter search queries to find: {search_description}

These people are already in the workspace (don't find them again): {existing_str}

Return short, focused queries that will find NEW people matching this description.
Each query should use a different angle."""

        tools = [{
            "name": "targeted_queries",
            "description": "Generate targeted search queries",
            "input_schema": {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "rationale": {"type": "string"},
                                "angle": {"type": "string"},
                            },
                            "required": ["query", "rationale", "angle"],
                        },
                    },
                },
                "required": ["queries"],
            },
        }]

        response = await self.client.messages.create(
            model=self.fast_model,
            max_tokens=512,
            tools=tools,
            tool_choice={"type": "tool", "name": "targeted_queries"},
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
                    for q in block.input.get("queries", [])[:2]
                ]

        return []
