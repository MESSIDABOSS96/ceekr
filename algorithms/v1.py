"""V1 algorithm — the original LLM pipeline + user search, extracted from server.py."""

from __future__ import annotations

import asyncio
import json
import traceback
from typing import TYPE_CHECKING, Optional

from algorithms import AlgorithmResult, SearchAlgorithm
from config import MIN_ACCOUNTS_BEFORE_FALLBACK, RANKING_BATCH_SIZE
from core.fast_path import score_user_search_results
from core.llm import LLMClient, validate_query
from core.models import TwitterAccount
from core.twitter import SearchOrchestrator

if TYPE_CHECKING:
    from core.auth import UserNetwork
    from core.twitter import TwitterClient


# Generic words that should NOT be treated as mandatory niche terms.
_GENERIC_QUERY_WORDS = frozenset({
    # Adjectives / qualifiers
    "top", "best", "popular", "famous", "leading", "prominent", "notable",
    "biggest", "largest", "major", "great", "good", "new", "recent", "active",
    # Roles / personas
    "researcher", "researchers", "developer", "developers", "engineer", "engineers",
    "founder", "founders", "creator", "creators", "builder", "builders",
    "contributor", "contributors", "maintainer", "maintainers",
    "scientist", "scientists", "expert", "experts", "professional", "professionals",
    "designer", "designers", "writer", "writers", "author", "authors",
    "analyst", "analysts", "consultant", "consultants", "advocate", "advocates",
    "influencer", "influencers", "leader", "leaders", "speaker", "speakers",
    "educator", "educators", "teacher", "teachers", "professor", "professors",
    "investor", "investors", "advisor", "advisors",
    # Common filler / stop words
    "find", "search", "looking", "who", "are", "the", "a", "an", "in", "on",
    "for", "with", "and", "or", "of", "to", "is", "that", "this", "about",
    "people", "person", "accounts", "users", "community", "working",
})


def _extract_niche_terms(query: str) -> list[str]:
    """Extract niche/specific terms from a query by filtering out generic words."""
    words = query.lower().split()
    niche = [w for w in words if w not in _GENERIC_QUERY_WORDS and len(w) > 2]
    return niche


class AlgorithmV1(SearchAlgorithm):
    """Original search algorithm: user search + LLM pipeline in parallel."""

    async def run(
        self,
        query: str,
        twitter: TwitterClient,
        queue: asyncio.Queue,
        user_network: Optional[UserNetwork] = None,
    ) -> AlgorithmResult:
        await queue.put(json.dumps({"message": "Scanning Twitter...", "step": "init"}))

        llm = LLMClient()

        # --- Leg A: User search API (fast, ~1-2s) ---
        user_search_task = asyncio.create_task(
            score_user_search_results(twitter, query, user_network=user_network)
        )

        # Bio search tasks will be populated after plan_search completes
        bio_search_tasks: list[asyncio.Task] = []
        shared_intent: dict = {}

        # --- Leg B: Full LLM pipeline (slow, ~15-30s) ---
        async def run_llm_pipeline() -> list:
            """Run the full LLM pipeline: intent → queries → tweet search → rank."""
            # Step 1: Analyze intent + generate queries
            await queue.put(json.dumps({"message": "Understanding your search...", "step": "intent_analysis"}))
            intent, queries = await llm.plan_search(query, None)

            # Fallback: if LLM didn't extract mandatory_terms, derive from query
            if not intent.mandatory_terms:
                niche = _extract_niche_terms(query)
                if niche:
                    intent.mandatory_terms = niche
                    print(f"[mandatory_terms] LLM returned [], fallback extracted: {niche}")
                else:
                    print(f"[mandatory_terms] Broad query, no mandatory terms")
            else:
                print(f"[mandatory_terms] LLM extracted: {intent.mandatory_terms}")

            shared_intent["intent"] = intent

            await queue.put(json.dumps({
                "_event": "intent",
                "persona": intent.persona,
                "topic": intent.topic,
                "goal": intent.goal,
                "specificity": intent.specificity,
                "key_signals": intent.key_signals,
                "anti_signals": intent.anti_signals,
            }))

            # Launch bio keyword searches in parallel (Leg A extension)
            # Use all bio_search_terms as-is (LLM generated them for relevance)
            # Deduplicate only
            seen = set()
            bio_terms = [t for t in intent.bio_search_terms if not (t.lower() in seen or seen.add(t.lower()))]
            for term in bio_terms:
                task = asyncio.create_task(
                    score_user_search_results(twitter, term, user_network=user_network)
                )
                bio_search_tasks.append(task)

            if not queries:
                return []

            await queue.put(json.dumps({
                "_event": "queries",
                "queries": [
                    {"query": q.query, "rationale": q.rationale, "angle": q.angle}
                    for q in queries
                ],
            }))

            # Step 2: Execute tweet searches
            orchestrator = SearchOrchestrator(twitter)

            async def search_status(msg: str):
                await queue.put(json.dumps({"message": msg, "step": "searching"}))

            query_strings = [validate_query(q.query) for q in queries]
            accounts = await orchestrator.execute_searches(
                query_strings, search_status, user_network=user_network,
            )

            # Step 2b: Fallback queries if too few accounts
            if len(accounts) < MIN_ACCOUNTS_BEFORE_FALLBACK:
                await queue.put(json.dumps({"message": f"Only {len(accounts)} accounts found, broadening search...", "step": "fallback", "counts": {"found": len(accounts)}}))
                fallback_queries = await llm.generate_fallback_queries(
                    intent, query_strings, len(accounts),
                )
                if fallback_queries:
                    fallback_strings = [validate_query(q.query) for q in fallback_queries]
                    fallback_accounts = await orchestrator.execute_searches(
                        fallback_strings, search_status, user_network=user_network,
                    )
                    existing_ids = {a.user_id for a in accounts}
                    for acc in fallback_accounts:
                        if acc.user_id not in existing_ids:
                            accounts.append(acc)
                            existing_ids.add(acc.user_id)

            if not accounts:
                return [], []

            return accounts, []

        llm_pipeline_task = asyncio.create_task(run_llm_pipeline())

        # --- Wait for all tasks to complete ---
        # We drain the queue in server.py, so just await completion here
        all_done = False
        while not all_done:
            all_tasks = [user_search_task, llm_pipeline_task] + bio_search_tasks
            done_tasks = {t for t in all_tasks if t.done()}
            all_done = len(done_tasks) == len(all_tasks)
            if not all_done:
                await asyncio.sleep(0.1)

        # --- Collect results from all legs ---
        user_search_results: list = []  # RankedAccount from user/bio search
        tweet_search_accounts: list[TwitterAccount] = []  # Raw accounts from tweet search

        try:
            user_search_results = user_search_task.result()
        except Exception as e:
            print(f"User search failed: {e}")
            traceback.print_exc()

        for task in bio_search_tasks:
            try:
                bio_results = task.result()
                user_search_results.extend(bio_results)
            except Exception as e:
                print(f"Bio search failed: {e}")

        try:
            pipeline_result = llm_pipeline_task.result()
            if isinstance(pipeline_result, tuple):
                tweet_search_accounts = pipeline_result[0]
            else:
                tweet_search_accounts = pipeline_result if pipeline_result else []
        except Exception as e:
            print(f"LLM pipeline failed: {e}")
            traceback.print_exc()

        intent = shared_intent.get("intent")

        # --- Merge user-search accounts into tweet-search pool for unified LLM ranking ---
        # Extract TwitterAccount objects from user-search RankedAccounts
        existing_ids = {a.user_id for a in tweet_search_accounts}
        user_search_accounts: list[TwitterAccount] = []
        for r in user_search_results:
            if r.account.user_id not in existing_ids:
                user_search_accounts.append(r.account)
                existing_ids.add(r.account.user_id)

        # Filter user search accounts by mandatory terms before adding to pool
        if intent and intent.mandatory_terms:
            terms_lower = [t.lower() for t in intent.mandatory_terms]

            def _has_mandatory_term(acc: TwitterAccount) -> bool:
                text = f"{acc.name} {acc.handle} {acc.bio or ''}".lower()
                return any(t in text for t in terms_lower)

            before = len(user_search_accounts)
            user_search_accounts = [a for a in user_search_accounts if _has_mandatory_term(a)]
            if before != len(user_search_accounts):
                print(f"[mandatory_terms] Filtered user search accounts: {before} → {len(user_search_accounts)}")

        # Combine all accounts into unified pool
        all_accounts = tweet_search_accounts + user_search_accounts
        print(f"[v1] Combined pool: {len(tweet_search_accounts)} tweet-search + {len(user_search_accounts)} user-search = {len(all_accounts)}")

        if all_accounts and intent:
            # Pre-filter the combined pool
            await queue.put(json.dumps({"message": f"Sifting through {len(all_accounts)} accounts...", "step": "filtering", "counts": {"total": len(all_accounts)}}))
            filtered, removed = SearchOrchestrator.pre_filter_accounts(all_accounts, intent)

            if filtered:
                await queue.put(json.dumps({"message": f"Narrowed to {len(filtered)} promising matches", "step": "filtering_done", "counts": {"passed": len(filtered)}}))

                # Triage large sets before expensive LLM ranking
                if len(filtered) > RANKING_BATCH_SIZE:
                    await queue.put(json.dumps({"message": "Quick-screening candidates...", "step": "triage"}))
                    filtered = await llm.triage_accounts(intent, filtered)
                    print(f"[triage] {len(filtered)} accounts passed triage")

                # LLM rank the unified pool
                await queue.put(json.dumps({"message": f"Ranking {len(filtered)} accounts by relevance...", "step": "ranking", "counts": {"accounts": len(filtered)}}))
                ranking = await llm.rank_accounts(intent, filtered, user_network=user_network)
                merged = ranking.ranked_accounts if ranking.ranked_accounts else []
            else:
                merged = []
        else:
            merged = []

        # For specific queries, drop good_match
        # Post-ranking mandatory_terms enforcement for high-specificity searches
        if intent and intent.specificity >= 4 and intent.mandatory_terms:
            terms_lower = [t.lower() for t in intent.mandatory_terms]
            before = len(merged)
            enforced = []
            for r in merged:
                text = f"{r.account.name} {r.account.handle} {r.account.bio or ''}"
                for t in r.account.recent_tweets:
                    text += f" {t.text}"
                text = text.lower()
                if any(t in text for t in terms_lower):
                    enforced.append(r)
                else:
                    print(f"[mandatory_enforce] Excluded @{r.account.handle}: no mandatory term in bio/tweets")
            merged = enforced
            if before != len(merged):
                print(f"[mandatory_enforce] {before} → {len(merged)}")

        # For ultra-specific queries, drop good_match
        if intent and intent.specificity >= 5:
            merged = [r for r in merged if r.bucket in ("top_match", "strong_match")]

        if not merged:
            return AlgorithmResult(
                ranked_accounts=[],
                quality="weak",
                refinement_questions=["Try broadening your search."],
                intent=intent,
            )

        # Compute quality using bucket counts, scaled by specificity
        top_count = sum(1 for r in merged if r.bucket == "top_match")
        strong_count = sum(1 for r in merged if r.bucket == "strong_match")
        good_count = sum(1 for r in merged if r.bucket == "good_match")
        spec = intent.specificity if intent else 3
        top_threshold = max(1, 4 - spec)       # spec 5 → 1, spec 1 → 3
        combined_threshold = max(2, 6 - spec)   # spec 5 → 2, spec 1 → 5
        if top_count >= top_threshold and (top_count + strong_count) >= combined_threshold:
            quality = "strong"
        elif top_count >= 1 or (strong_count + good_count) >= combined_threshold:
            quality = "moderate"
        else:
            quality = "weak"

        return AlgorithmResult(
            ranked_accounts=merged,
            quality=quality,
            refinement_questions=[],
            intent=intent,
        )
