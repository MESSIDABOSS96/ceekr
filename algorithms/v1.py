"""V1 algorithm — the original LLM pipeline + user search, extracted from server.py."""

from __future__ import annotations

import asyncio
import json
import traceback
from typing import TYPE_CHECKING, Optional

from algorithms import AlgorithmResult, SearchAlgorithm
from config import MIN_ACCOUNTS_BEFORE_FALLBACK
from core.fast_path import (
    light_filter,
    merge_ranked_results,
    score_user_search_results,
)
from core.llm import LLMClient
from core.models import BUCKET_SORT_ORDER
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
        await queue.put("Scanning Twitter...")

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
            await queue.put("Understanding your search...")
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
            bio_terms = intent.bio_search_terms
            if intent.mandatory_terms:
                bio_terms = [
                    t for t in bio_terms
                    if any(mt.lower() in t.lower() for mt in intent.mandatory_terms)
                ]
                seen = set()
                bio_terms = [t for t in bio_terms if not (t.lower() in seen or seen.add(t.lower()))]
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
                await queue.put(msg)

            query_strings = [q.query for q in queries]
            accounts = await orchestrator.execute_searches(
                query_strings, search_status, user_network=user_network,
            )

            # Step 2b: Fallback queries if too few accounts
            if len(accounts) < MIN_ACCOUNTS_BEFORE_FALLBACK:
                await queue.put(f"Only {len(accounts)} accounts found, broadening search...")
                fallback_queries = await llm.generate_fallback_queries(
                    intent, query_strings, len(accounts),
                )
                if fallback_queries:
                    fallback_strings = [q.query for q in fallback_queries]
                    fallback_accounts = await orchestrator.execute_searches(
                        fallback_strings, search_status, user_network=user_network,
                    )
                    existing_ids = {a.user_id for a in accounts}
                    for acc in fallback_accounts:
                        if acc.user_id not in existing_ids:
                            accounts.append(acc)
                            existing_ids.add(acc.user_id)

            if not accounts:
                return []

            # Step 3: Pre-filter
            await queue.put(f"Sifting through {len(accounts)} accounts...")
            filtered, removed = SearchOrchestrator.pre_filter_accounts(accounts, intent)
            if not filtered:
                return []

            await queue.put(f"Narrowed to {len(filtered)} promising matches")

            # Step 4: Rank with LLM
            await queue.put(f"Ranking {len(filtered)} accounts by relevance...")
            ranking = await llm.rank_accounts(intent, filtered, user_network=user_network)

            return ranking.ranked_accounts if ranking.ranked_accounts else []

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
        user_search_results = []
        llm_results = []

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
            llm_results = llm_pipeline_task.result()
        except Exception as e:
            print(f"LLM pipeline failed: {e}")
            traceback.print_exc()

        # --- Merge results ---
        merged = merge_ranked_results(user_search_results, llm_results)

        # For specific queries, drop good_match
        intent = shared_intent.get("intent")
        if intent and intent.specificity >= 4:
            merged = [r for r in merged if r.bucket in ("top_match", "strong_match")]

        if not merged:
            return AlgorithmResult(
                ranked_accounts=[],
                quality="weak",
                refinement_questions=["Try broadening your search."],
            )

        # Compute quality using bucket counts
        top_count = sum(1 for r in merged if r.bucket == "top_match")
        strong_count = sum(1 for r in merged if r.bucket == "strong_match")
        good_count = sum(1 for r in merged if r.bucket == "good_match")
        if top_count >= 3 and (top_count + strong_count) >= 5:
            quality = "strong"
        elif top_count >= 1 or (strong_count + good_count) >= 5:
            quality = "moderate"
        else:
            quality = "weak"

        return AlgorithmResult(
            ranked_accounts=merged,
            quality=quality,
            refinement_questions=[],
        )
