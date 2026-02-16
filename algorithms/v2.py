"""V2 algorithm — Seed & Expand.

Find a small number of high-quality seed accounts, then expand outward
via similar profiles, lists, and broader queries to build a comprehensive
candidate pool.
"""

from __future__ import annotations

import asyncio
import json
import re
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from algorithms import AlgorithmResult, SearchAlgorithm
from config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_FAST_MODEL,
    MAX_BIO_LENGTH,
    MAX_TWEET_LENGTH,
    MAX_TWEETS_FOR_RANKING,
    RANKING_BATCH_SIZE,
    RECENCY_BONUS_WINDOW_DAYS,
    STALE_ACCOUNT_DAYS,
)
from core.models import (
    BUCKET_SCORE_MAP,
    BUCKET_SORT_ORDER,
    NetworkInfo,
    RankedAccount,
    SearchIntent,
    SearchQuery,
    Tweet,
    TwitterAccount,
)
from core.twitter import SearchOrchestrator, _tweet_recency_score

from .v2_prompts import (
    format_v2_fallback_prompt,
    format_v2_ranking_prompt,
    format_v2_search_plan_prompt,
)

if TYPE_CHECKING:
    from core.auth import UserNetwork
    from core.twitter import TwitterClient


# ── Internal dataclasses ──────────────────────────────────────


@dataclass
class V2SearchPlan:
    """Output of the seed planning step."""

    intent: SearchIntent
    seed_queries: list[SearchQuery] = field(default_factory=list)
    seed_accounts: list[str] = field(default_factory=list)  # known handles
    expansion_queries: list[SearchQuery] = field(default_factory=list)
    list_keywords: list[str] = field(default_factory=list)


@dataclass
class V2Candidate:
    """A candidate account in the v2 pipeline, accumulating signals."""

    user_id: str
    handle: str
    user_data: dict  # raw SocialData user dict
    tweets: list[Tweet] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)  # how they were discovered
    is_seed: bool = False
    bio_score: float = 0.0
    tweet_score: float = 0.0
    graph_score: float = 0.0
    list_score: float = 0.0
    heuristic_score: float = 0.0  # combined


# ── Constants ─────────────────────────────────────────────────

_MAX_SEEDS = 8
_MIN_SEEDS = 3
_MAX_EXPANSION_PER_SEED = 30
_MAX_LIST_MEMBERS = 50
_TIMELINE_ENRICHMENT_COUNT = 15
_TOP_N_FOR_ENRICHMENT = 30
_MIN_RESULTS_BEFORE_FALLBACK = 10


class AlgorithmV2(SearchAlgorithm):
    """Seed & Expand algorithm."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        self.fast_model = ANTHROPIC_FAST_MODEL

    async def run(
        self,
        query: str,
        twitter: TwitterClient,
        queue: asyncio.Queue,
        user_network: Optional[UserNetwork] = None,
    ) -> AlgorithmResult:
        # Step 1: Intent + seed plan
        await queue.put("Reading your mind...")
        plan = await self._plan_search(query)

        intent = plan.intent
        await queue.put(json.dumps({
            "_event": "intent",
            "persona": intent.persona,
            "topic": intent.topic,
            "goal": intent.goal,
            "specificity": intent.specificity,
            "key_signals": intent.key_signals,
            "anti_signals": intent.anti_signals,
        }))

        # Emit queries event (seed + expansion combined)
        all_queries = plan.seed_queries + plan.expansion_queries
        if all_queries:
            await queue.put(json.dumps({
                "_event": "queries",
                "queries": [
                    {"query": q.query, "rationale": q.rationale, "angle": q.angle}
                    for q in all_queries
                ],
            }))

        # Step 2: Find seeds (parallel)
        await queue.put("Casting a wide net...")
        candidates: dict[str, V2Candidate] = {}  # user_id → candidate

        seed_tasks = []

        # 2a: Seed tweet searches
        orchestrator = SearchOrchestrator(twitter)
        if plan.seed_queries:
            seed_query_strings = [q.query for q in plan.seed_queries]

            async def run_seed_tweet_search():
                accounts = await orchestrator.execute_searches(
                    seed_query_strings, None, user_network=user_network,
                )
                return ("seed_tweet_search", accounts)

            seed_tasks.append(asyncio.create_task(run_seed_tweet_search()))

        # 2b: Bio/profile searches
        if intent.bio_search_terms:
            async def run_bio_searches():
                all_accounts = []
                for term in intent.bio_search_terms[:4]:
                    try:
                        users = await twitter.search_users(term, max_results=10)
                        for u in users:
                            all_accounts.append(("bio_search", u))
                    except Exception as e:
                        print(f"Bio search failed for '{term}': {e}")
                return all_accounts

            seed_tasks.append(asyncio.create_task(run_bio_searches()))

        # 2c: Known account lookups
        if plan.seed_accounts:
            async def run_known_lookups():
                results = []
                lookup_tasks = []
                for handle in plan.seed_accounts[:5]:
                    lookup_tasks.append(twitter.lookup_user(handle))
                lookups = await asyncio.gather(*lookup_tasks, return_exceptions=True)
                for handle, result in zip(plan.seed_accounts[:5], lookups):
                    if isinstance(result, Exception) or result is None:
                        continue
                    results.append(("known_account", result))
                return results

            seed_tasks.append(asyncio.create_task(run_known_lookups()))

        # Gather all seed results
        seed_results = await asyncio.gather(*seed_tasks, return_exceptions=True)

        for result in seed_results:
            if isinstance(result, Exception):
                print(f"Seed task failed: {result}")
                continue

            if isinstance(result, tuple) and result[0] in ("seed_tweet_search",):
                # From tweet search — result is (label, list[TwitterAccount])
                label, accounts = result
                for acc in accounts:
                    self._add_or_merge_account(candidates, acc, "seed_tweet_search", user_network)
            elif isinstance(result, list):
                # From bio search or known lookups — list of (source, user_data)
                for source, user_data in result:
                    self._add_or_merge_user_data(candidates, user_data, source, user_network)

        print(f"[v2] {len(candidates)} seed candidates")
        await queue.put("Spotted some interesting people...")

        # Score seeds with heuristics and select top seeds
        self._score_candidates(candidates, intent)
        seeds = self._select_seeds(candidates)
        seed_ids = {c.user_id for c in seeds}

        await queue.put("Pulling on a few threads...")

        # Step 3: Graph expansion (parallel, starting from seeds)
        expansion_tasks = []

        for seed in seeds:
            # 3a: Similar profiles
            async def expand_similar(uid=seed.user_id):
                try:
                    profiles = await twitter.fetch_similar_profiles(uid)
                    return ("similar_profiles", profiles)
                except Exception as e:
                    print(f"Similar profiles failed for {uid}: {e}")
                    return ("similar_profiles", [])

            expansion_tasks.append(asyncio.create_task(expand_similar()))

            # 3b: User lists → list members
            async def expand_lists(uid=seed.user_id):
                try:
                    lists = await twitter.fetch_user_lists(uid)
                    all_members = []
                    # Take up to 3 lists per seed
                    member_tasks = []
                    for lst in lists[:3]:
                        list_id = str(lst.get("id_str", lst.get("id", "")))
                        if list_id:
                            member_tasks.append(twitter.fetch_list_members(list_id, max_results=_MAX_LIST_MEMBERS))
                    if member_tasks:
                        results = await asyncio.gather(*member_tasks, return_exceptions=True)
                        for r in results:
                            if not isinstance(r, Exception):
                                all_members.extend(r)
                    return ("list_members", all_members)
                except Exception as e:
                    print(f"List expansion failed for {uid}: {e}")
                    return ("list_members", [])

            expansion_tasks.append(asyncio.create_task(expand_lists()))

        # 3c: Expansion tweet searches
        if plan.expansion_queries:
            expansion_query_strings = [q.query for q in plan.expansion_queries]

            async def run_expansion_tweet_search():
                accounts = await orchestrator.execute_searches(
                    expansion_query_strings, None, user_network=user_network,
                )
                return ("expansion_tweet_search", accounts)

            expansion_tasks.append(asyncio.create_task(run_expansion_tweet_search()))

        # 3d: Verified followers of top seeds
        for seed in seeds[:3]:
            async def expand_verified(uid=seed.user_id):
                try:
                    followers = await twitter.fetch_verified_followers(uid, max_results=30)
                    return ("verified_followers", followers)
                except Exception as e:
                    print(f"Verified followers failed for {uid}: {e}")
                    return ("verified_followers", [])

            expansion_tasks.append(asyncio.create_task(expand_verified()))

        # Gather expansion results
        expansion_results = await asyncio.gather(*expansion_tasks, return_exceptions=True)

        for result in expansion_results:
            if isinstance(result, Exception):
                print(f"Expansion task failed: {result}")
                continue

            if isinstance(result, tuple):
                source, data = result
                if source == "expansion_tweet_search":
                    for acc in data:
                        self._add_or_merge_account(candidates, acc, source, user_network)
                else:
                    # similar_profiles, list_members, verified_followers
                    for user_data in data:
                        self._add_or_merge_user_data(candidates, user_data, source, user_network)

        print(f"[v2] {len(candidates)} total candidates after expansion")
        await queue.put("The plot thickens...")

        # Step 4: Timeline enrichment for candidates lacking tweets
        candidates_without_tweets = [
            c for c in candidates.values() if len(c.tweets) == 0
        ]
        if candidates_without_tweets:
            await queue.put("Reading what they've been saying...")
            # Convert to TwitterAccount objects for enrichment
            accounts_to_enrich = [
                self._candidate_to_account(c, user_network)
                for c in candidates_without_tweets
            ]
            # Batch in groups of 50 to avoid overwhelming the API
            for i in range(0, len(accounts_to_enrich), 50):
                batch = accounts_to_enrich[i:i + 50]
                await orchestrator.enrich_with_timelines(batch)
            # Copy fetched tweets back into candidates
            enriched_count = 0
            for acc in accounts_to_enrich:
                if acc.recent_tweets:
                    c = candidates.get(acc.user_id)
                    if c is not None:
                        existing_ids = {t.id for t in c.tweets}
                        for t in acc.recent_tweets:
                            if t.id not in existing_ids:
                                c.tweets.append(t)
                                existing_ids.add(t.id)
                        if c.tweets:
                            enriched_count += 1
            print(f"[v2] enriched {enriched_count} candidates with timelines")

        # Step 5: Pre-filter
        await queue.put("Separating the wheat from the chaff...")
        accounts_list = self._candidates_to_accounts(candidates, user_network)
        filtered, removed = SearchOrchestrator.pre_filter_accounts(accounts_list, intent)

        print(f"[v2] {len(filtered)} passed pre-filter ({removed} removed)")

        if not filtered:
            await queue.put("Couldn't find the right people this time")
            return AlgorithmResult(ranked_accounts=[], quality="weak")

        await queue.put("Getting warmer...")

        # Step 5: Heuristic scoring (update candidates with new data)
        self._score_candidates(candidates, intent)

        # Step 7: LLM ranking
        await queue.put("Picking the best of the bunch...")

        # Build discovery sources summary
        source_counts: dict[str, int] = {}
        for c in candidates.values():
            for s in c.sources:
                source_counts[s] = source_counts.get(s, 0) + 1
        discovery_sources = ", ".join(
            f"{source} ({count})" for source, count in sorted(source_counts.items(), key=lambda x: -x[1])
        )

        ranked = await self._rank_accounts(
            intent, filtered, candidates, len(seeds), discovery_sources, user_network,
        )

        # Step 8: Post-ranking — filter excludes, sort
        excluded_count = sum(1 for r in ranked if r.bucket == "exclude")
        ranked = [r for r in ranked if r.bucket != "exclude"]
        print(f"[v2] {len(ranked)} ranked ({excluded_count} excluded)")
        ranked.sort(
            key=lambda r: (BUCKET_SORT_ORDER.get(r.bucket, 3), -r.account.followers_count),
        )

        # Step 9: Quality assessment
        top_count = sum(1 for r in ranked if r.bucket == "top_match")
        strong_count = sum(1 for r in ranked if r.bucket == "strong_match")
        good_count = sum(1 for r in ranked if r.bucket == "good_match")

        if top_count >= 3 and (top_count + strong_count) >= 5:
            quality = "strong"
        elif top_count >= 1 or (strong_count + good_count) >= 5:
            quality = "moderate"
        else:
            quality = "weak"

        # Step 10: Fallback if too few results
        if len(ranked) < _MIN_RESULTS_BEFORE_FALLBACK and quality == "weak":
            await queue.put("Casting a wider net...")
            fallback_ranked = await self._run_fallback(
                intent, twitter, orchestrator, candidates, seeds, user_network, queue,
            )
            if fallback_ranked:
                existing_ids = {r.account.user_id for r in ranked}
                for r in fallback_ranked:
                    if r.account.user_id not in existing_ids:
                        ranked.append(r)
                        existing_ids.add(r.account.user_id)
                ranked.sort(
                    key=lambda r: (BUCKET_SORT_ORDER.get(r.bucket, 3), -r.account.followers_count),
                )
                # Re-assess quality
                top_count = sum(1 for r in ranked if r.bucket == "top_match")
                strong_count = sum(1 for r in ranked if r.bucket == "strong_match")
                good_count = sum(1 for r in ranked if r.bucket == "good_match")
                if top_count >= 3 and (top_count + strong_count) >= 5:
                    quality = "strong"
                elif top_count >= 1 or (strong_count + good_count) >= 5:
                    quality = "moderate"

        if not ranked:
            print("[v2] 0 final results, quality=weak")
            return AlgorithmResult(ranked_accounts=[], quality="weak")

        print(f"[v2] {len(ranked)} final results, quality={quality}")
        return AlgorithmResult(
            ranked_accounts=ranked,
            quality=quality,
            refinement_questions=[],
        )

    # ── Step 1: LLM planning ─────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _plan_search(self, query: str) -> V2SearchPlan:
        """Single LLM call to extract intent and generate seed plan."""
        tools = [
            {
                "name": "v2_search_plan",
                "description": "Analyze the search request and create a seed-based search plan",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "persona": {"type": "string"},
                        "topic": {"type": "string"},
                        "goal": {"type": "string"},
                        "specificity": {"type": "integer", "minimum": 1, "maximum": 5},
                        "key_signals": {"type": "array", "items": {"type": "string"}},
                        "anti_signals": {"type": "array", "items": {"type": "string"}},
                        "bio_search_terms": {"type": "array", "items": {"type": "string"}},
                        "mandatory_terms": {"type": "array", "items": {"type": "string"}},
                        "seed_queries": {
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
                        "seed_accounts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Known Twitter handles (without @) who are central to this topic",
                        },
                        "expansion_queries": {
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
                        "list_keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "persona", "topic", "goal", "specificity",
                        "key_signals", "anti_signals", "bio_search_terms", "mandatory_terms",
                        "seed_queries", "seed_accounts", "expansion_queries", "list_keywords",
                    ],
                },
            }
        ]

        prompt = format_v2_search_plan_prompt(query)

        response = await self.client.messages.create(
            model=self.fast_model,
            max_tokens=2048,
            tools=tools,
            tool_choice={"type": "tool", "name": "v2_search_plan"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if block.type == "tool_use":
                r = block.input

                intent = SearchIntent(
                    persona=r.get("persona", ""),
                    topic=r.get("topic", ""),
                    goal=r.get("goal", ""),
                    specificity=r.get("specificity", 3),
                    suggested_query_count=len(r.get("seed_queries", [])),
                    bio_search_terms=r.get("bio_search_terms", []),
                    key_signals=r.get("key_signals", []),
                    anti_signals=r.get("anti_signals", []),
                    mandatory_terms=r.get("mandatory_terms", []),
                )

                return V2SearchPlan(
                    intent=intent,
                    seed_queries=[
                        SearchQuery(query=q["query"], rationale=q["rationale"], angle=q["angle"])
                        for q in r.get("seed_queries", [])
                    ],
                    seed_accounts=r.get("seed_accounts", []),
                    expansion_queries=[
                        SearchQuery(query=q["query"], rationale=q["rationale"], angle=q["angle"])
                        for q in r.get("expansion_queries", [])
                    ],
                    list_keywords=r.get("list_keywords", []),
                )

        # Fallback
        return V2SearchPlan(intent=SearchIntent())

    # ── Candidate management ──────────────────────────────────

    def _add_or_merge_account(
        self,
        candidates: dict[str, V2Candidate],
        account: TwitterAccount,
        source: str,
        user_network: Optional[UserNetwork],
    ) -> None:
        """Add a TwitterAccount to the candidate pool, merging if already seen."""
        uid = account.user_id
        if uid in candidates:
            c = candidates[uid]
            if source not in c.sources:
                c.sources.append(source)
            # Merge tweets (deduplicate by ID)
            existing_ids = {t.id for t in c.tweets}
            for t in account.recent_tweets:
                if t.id not in existing_ids:
                    c.tweets.append(t)
                    existing_ids.add(t.id)
        else:
            candidates[uid] = V2Candidate(
                user_id=uid,
                handle=account.handle,
                user_data={
                    "id_str": account.user_id,
                    "screen_name": account.handle,
                    "name": account.name,
                    "description": account.bio or "",
                    "followers_count": account.followers_count,
                    "friends_count": account.following_count,
                    "statuses_count": account.tweet_count,
                    "profile_image_url_https": account.profile_image_url or "",
                    "location": account.location or "",
                    "verified": account.verified,
                    "created_at": account.created_at.isoformat() if account.created_at else None,
                },
                tweets=list(account.recent_tweets),
                sources=[source],
            )

    def _add_or_merge_user_data(
        self,
        candidates: dict[str, V2Candidate],
        user_data: dict,
        source: str,
        user_network: Optional[UserNetwork],
    ) -> None:
        """Add raw user data to the candidate pool."""
        uid = str(user_data.get("id_str", user_data.get("id", "")))
        if not uid:
            return

        if uid in candidates:
            c = candidates[uid]
            if source not in c.sources:
                c.sources.append(source)
        else:
            candidates[uid] = V2Candidate(
                user_id=uid,
                handle=user_data.get("screen_name", ""),
                user_data=user_data,
                sources=[source],
            )

    # ── Step 5: Heuristic scoring ─────────────────────────────

    def _score_candidates(
        self,
        candidates: dict[str, V2Candidate],
        intent: SearchIntent,
    ) -> None:
        """Score all candidates using Python heuristics."""
        mandatory_lower = [t.lower() for t in intent.mandatory_terms] if intent.mandatory_terms else []
        key_signals_lower = [s.lower() for s in intent.key_signals] if intent.key_signals else []

        for c in candidates.values():
            bio = (c.user_data.get("description") or "").lower()
            handle = c.handle.lower()

            # Bio match (0-30)
            bio_score = 0.0
            if mandatory_lower:
                for term in mandatory_lower:
                    if term in bio or term in handle:
                        bio_score += 15
            for signal in key_signals_lower:
                if signal in bio:
                    bio_score += 5
            c.bio_score = min(30, bio_score)

            # Tweet match (0-30)
            tweet_score = 0.0
            for tweet in c.tweets[:5]:
                text_lower = tweet.text.lower()
                if mandatory_lower and any(t in text_lower for t in mandatory_lower):
                    tweet_score += 10
                if any(s in text_lower for s in key_signals_lower):
                    tweet_score += 5
            c.tweet_score = min(30, tweet_score)

            # Graph signal (0-20)
            source_set = set(c.sources)
            graph_score = 0.0
            if "similar_profiles" in source_set:
                graph_score += 10
            if "verified_followers" in source_set:
                graph_score += 5
            if len(c.sources) > 1:
                graph_score += 5
            c.graph_score = min(20, graph_score)

            # List signal (0-20)
            list_score = 0.0
            if "list_members" in source_set:
                list_score += 15
            c.list_score = min(20, list_score)

            # Combined
            c.heuristic_score = c.bio_score + c.tweet_score + c.graph_score + c.list_score

    def _select_seeds(self, candidates: dict[str, V2Candidate]) -> list[V2Candidate]:
        """Select the top seeds from candidates."""
        sorted_candidates = sorted(
            candidates.values(),
            key=lambda c: c.heuristic_score,
            reverse=True,
        )
        seeds = sorted_candidates[:_MAX_SEEDS]
        for s in seeds:
            s.is_seed = True
        return seeds

    # ── Candidate → TwitterAccount conversion ─────────────────

    def _candidate_to_account(
        self, c: V2Candidate, user_network: Optional[UserNetwork],
    ) -> TwitterAccount:
        """Convert a V2Candidate to a TwitterAccount."""
        ud = c.user_data

        if user_network:
            network = NetworkInfo(
                you_follow=c.user_id in user_network.following_ids,
                follows_you=c.user_id in user_network.follower_ids,
            )
        else:
            network = NetworkInfo()

        return TwitterAccount(
            user_id=c.user_id,
            handle=c.handle,
            name=ud.get("name", c.handle),
            bio=ud.get("description"),
            followers_count=ud.get("followers_count", 0),
            following_count=ud.get("friends_count", 0),
            tweet_count=ud.get("statuses_count", 0),
            profile_url=f"https://twitter.com/{c.handle}",
            profile_image_url=ud.get("profile_image_url_https"),
            location=ud.get("location") or None,
            verified=ud.get("verified", False) or ud.get("is_blue_verified", False),
            created_at=ud.get("created_at"),
            recent_tweets=sorted(c.tweets, key=_tweet_recency_score, reverse=True)[:10],
            matched_queries=c.sources[:5],
            network=network,
        )

    def _candidates_to_accounts(
        self, candidates: dict[str, V2Candidate], user_network: Optional[UserNetwork],
    ) -> list[TwitterAccount]:
        """Convert all candidates to TwitterAccount list."""
        return [self._candidate_to_account(c, user_network) for c in candidates.values()]

    # ── Step 7: LLM ranking ───────────────────────────────────

    async def _rank_accounts(
        self,
        intent: SearchIntent,
        accounts: list[TwitterAccount],
        candidates: dict[str, V2Candidate],
        seed_count: int,
        discovery_sources: str,
        user_network: Optional[UserNetwork],
    ) -> list[RankedAccount]:
        """Rank accounts using batched LLM calls with v2 prompt."""
        # Split into batches
        batches = []
        for i in range(0, len(accounts), RANKING_BATCH_SIZE):
            batches.append(accounts[i:i + RANKING_BATCH_SIZE])

        tasks = [
            self._rank_batch(intent, batch, candidates, seed_count, discovery_sources, user_network)
            for batch in batches
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        accounts_by_handle = {acc.handle.lower(): acc for acc in accounts}
        all_ranked: list[RankedAccount] = []

        for result in batch_results:
            if isinstance(result, Exception):
                print(f"V2 ranking batch failed: {result}")
                traceback.print_exc()
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

        return all_ranked

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _rank_batch(
        self,
        intent: SearchIntent,
        accounts: list[TwitterAccount],
        candidates: dict[str, V2Candidate],
        seed_count: int,
        discovery_sources: str,
        user_network: Optional[UserNetwork],
    ) -> list[dict]:
        """Rank a single batch of accounts."""
        accounts_data = []
        for acc in accounts:
            # Get candidate data for source info
            candidate = candidates.get(acc.user_id)
            source_count = len(candidate.sources) if candidate else 1

            # Network match
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

            # Sort tweets by recency+engagement
            sorted_tweets = sorted(acc.recent_tweets, key=_tweet_recency_score, reverse=True)

            # Compute recency metadata
            now = datetime.now(timezone.utc)
            days_since_newest = None
            activity_status = "stale"
            for t in sorted_tweets:
                if t.created_at is not None:
                    created = t.created_at if t.created_at.tzinfo else t.created_at.replace(tzinfo=timezone.utc)
                    days = max(0, (now - created).total_seconds() / 86400)
                    if days_since_newest is None or days < days_since_newest:
                        days_since_newest = days
            if days_since_newest is not None:
                if days_since_newest <= RECENCY_BONUS_WINDOW_DAYS:
                    activity_status = "active"
                elif days_since_newest <= STALE_ACCOUNT_DAYS:
                    activity_status = "somewhat_active"

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
                "source_count": source_count,
                "sources": candidate.sources[:3] if candidate else [],
                "recent_tweets": [
                    {
                        "text": t.text[:MAX_TWEET_LENGTH],
                        "date": t.created_at.isoformat() if t.created_at else None,
                        "likes": t.like_count,
                        "retweets": t.retweet_count,
                    }
                    for t in sorted_tweets[:MAX_TWEETS_FOR_RANKING]
                ],
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
                            "items": {
                                "type": "object",
                                "properties": {
                                    "handle": {"type": "string"},
                                    "bucket": {
                                        "type": "string",
                                        "enum": ["top_match", "strong_match", "good_match", "exclude"],
                                    },
                                    "summary": {"type": "string"},
                                    "highlight_tweet_indices": {
                                        "type": "array",
                                        "items": {"type": "integer"},
                                    },
                                },
                                "required": ["handle", "bucket", "summary", "highlight_tweet_indices"],
                            },
                        },
                    },
                    "required": ["ranked_accounts"],
                },
            }
        ]

        prompt = format_v2_ranking_prompt(intent, accounts_json, seed_count, discovery_sources)

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

    # ── Step 10: Fallback ─────────────────────────────────────

    async def _run_fallback(
        self,
        intent: SearchIntent,
        twitter: TwitterClient,
        orchestrator: SearchOrchestrator,
        candidates: dict[str, V2Candidate],
        seeds: list[V2Candidate],
        user_network: Optional[UserNetwork],
        queue: asyncio.Queue,
    ) -> list[RankedAccount]:
        """Generate fallback queries and run them when we have too few results."""
        tools = [
            {
                "name": "fallback_queries",
                "description": "Generate broader fallback search queries",
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
            }
        ]

        prompt = format_v2_fallback_prompt(
            intent,
            seeds_found=len(seeds),
            expansion_count=len(candidates),
            filtered_count=0,
        )

        try:
            response = await self.client.messages.create(
                model=self.fast_model,
                max_tokens=1024,
                tools=tools,
                tool_choice={"type": "tool", "name": "fallback_queries"},
                messages=[{"role": "user", "content": prompt}],
            )

            fallback_queries = []
            for block in response.content:
                if block.type == "tool_use":
                    fallback_queries = [q["query"] for q in block.input.get("queries", [])]

            if not fallback_queries:
                return []

            # Execute fallback searches
            accounts = await orchestrator.execute_searches(
                fallback_queries, None, user_network=user_network,
            )

            if not accounts:
                return []

            # Pre-filter
            filtered, _ = SearchOrchestrator.pre_filter_accounts(accounts, intent)
            if not filtered:
                return []

            # Quick LLM rank of fallback results
            source_summary = "fallback_search"
            ranked = await self._rank_accounts(
                intent, filtered, candidates, len(seeds), source_summary, user_network,
            )
            return [r for r in ranked if r.bucket != "exclude"]

        except Exception as e:
            print(f"Fallback search failed: {e}")
            traceback.print_exc()
            return []
