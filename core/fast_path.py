"""Fast path for handle lookups and user search scoring."""

from __future__ import annotations

import asyncio
import math
import re
from difflib import SequenceMatcher
from enum import Enum
from typing import TYPE_CHECKING, Callable, Optional

from config import FAST_PATH_MAX_RESULTS

from .models import NetworkInfo, RankedAccount, Tweet, TwitterAccount

if TYPE_CHECKING:
    from .auth import UserNetwork
    from .twitter import TwitterClient


class QueryType(Enum):
    HANDLE_LOOKUP = "handle_lookup"
    FULL_SEARCH = "full_search"


class QueryClassification:
    def __init__(self, query_type: QueryType, raw_query: str):
        self.query_type = query_type
        self.raw_query = raw_query


_BOT_KEYWORDS_FAST = {"bot", "auto", "giveaway", "airdrop", "free followers", "follow back"}


def classify_query(raw_query: str) -> QueryClassification:
    """Classify a query: @handle → HANDLE_LOOKUP, everything else → FULL_SEARCH."""
    query = raw_query.strip()

    # Handle lookup: starts with @ and is a single token
    if query.startswith("@"):
        handle = query.lstrip("@").strip()
        if handle and " " not in handle:
            return QueryClassification(QueryType.HANDLE_LOOKUP, raw_query)

    return QueryClassification(QueryType.FULL_SEARCH, raw_query)


def _candidate_handles(query: str) -> list[str]:
    """Generate candidate Twitter handles from a name/keyword query."""
    words = query.lower().split()
    candidates = []
    if len(words) >= 2:
        # "elon musk" → elonmusk, elon_musk, muskelon
        candidates.append("".join(words))
        candidates.append("_".join(words))
        candidates.append("".join(reversed(words)))
        candidates.append("_".join(reversed(words)))
    elif len(words) == 1:
        candidates.append(words[0])
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


async def _build_account_from_user(
    twitter: TwitterClient,
    user_data: dict,
    matched_query: str,
    user_network: Optional[UserNetwork] = None,
    fetch_timeline: bool = True,
) -> TwitterAccount:
    """Build a TwitterAccount from raw SocialData user dict + optionally fetch timeline."""
    user_id = str(user_data.get("id_str", user_data.get("id", "")))
    handle = user_data.get("screen_name", "")

    tweets = []
    if fetch_timeline:
        timeline = await twitter.fetch_user_timeline(user_id, count=10)
        tweets = [
            Tweet(
                id=str(t.get("id_str", t.get("id", ""))),
                text=t.get("text", t.get("full_text", "")),
                created_at=t.get("created_at"),
                like_count=t.get("favorite_count", 0),
                retweet_count=t.get("retweet_count", 0),
                reply_count=t.get("reply_count", 0),
            )
            for t in timeline
        ]

    if user_network:
        network = NetworkInfo(
            you_follow=user_id in user_network.following_ids,
            follows_you=user_id in user_network.follower_ids,
        )
    else:
        network = NetworkInfo()

    return TwitterAccount(
        user_id=user_id,
        handle=handle,
        name=user_data.get("name", handle),
        bio=user_data.get("description"),
        followers_count=user_data.get("followers_count", 0),
        following_count=user_data.get("friends_count", 0),
        tweet_count=user_data.get("statuses_count", 0),
        profile_url=f"https://twitter.com/{handle}",
        profile_image_url=user_data.get("profile_image_url_https"),
        location=user_data.get("location") or None,
        verified=user_data.get("verified", False) or user_data.get("is_blue_verified", False),
        created_at=user_data.get("created_at"),
        recent_tweets=tweets,
        matched_queries=[matched_query],
        network=network,
    )


async def execute_handle_lookup(
    twitter: TwitterClient,
    handle: str,
    user_network: Optional[UserNetwork] = None,
    status_callback: Optional[Callable] = None,
) -> list[RankedAccount]:
    """Direct profile lookup for @handle queries."""
    clean_handle = handle.lstrip("@").strip()

    if status_callback:
        await status_callback(f"Looking up @{clean_handle}...")

    user_data = await twitter.lookup_user(clean_handle)
    if not user_data:
        return []

    account = await _build_account_from_user(twitter, user_data, f"@{clean_handle}", user_network)

    return [
        RankedAccount(
            account=account,
            relevance_score=10,
            why_relevant=f"Direct profile match for @{clean_handle}.",
            confidence="high",
            evidence_highlights=[f"Profile: {account.bio or 'No bio'}"],
        )
    ]


# ── User search scoring ──────────────────────────────────────


def _score_user_match(user_data: dict, query: str) -> float:
    """Score a user search result with weighted disambiguation (0-100 raw)."""
    query_lower = query.lower().strip()
    query_words = query_lower.split()

    name = (user_data.get("name") or "").lower()
    handle = (user_data.get("screen_name") or "").lower()
    bio = (user_data.get("description") or "").lower()
    followers = user_data.get("followers_count", 0)
    verified = user_data.get("verified", False) or user_data.get("is_blue_verified", False)
    tweet_count = user_data.get("statuses_count", 0)

    score = 0.0

    # --- Name match (0-40 pts) ---
    if query_lower == name:
        score += 40  # exact match
    elif query_lower in name:
        score += 35  # substring match
    elif all(w in name for w in query_words):
        score += 30  # all words present
    else:
        ratio = SequenceMatcher(None, query_lower, name).ratio()
        if ratio > 0.5:
            score += 40 * ratio

    # --- Follower signal (0-30 pts, log-scaled) ---
    if followers > 0:
        # log10(200M) ≈ 8.3 → 30 pts, log10(100K) ≈ 5 → ~18 pts, log10(1K) ≈ 3 → ~11 pts
        score += min(30, math.log10(max(followers, 1)) * 3.6)

    # --- Verified bonus (0-10 pts) ---
    if verified:
        score += 10

    # --- Activity signal (0-10 pts) ---
    if tweet_count > 100:
        score += 10
    elif tweet_count > 10:
        score += 5

    # --- Bio relevance (0-10 pts) ---
    if any(w in bio for w in query_words):
        score += 10

    return score


async def score_user_search_results(
    twitter: TwitterClient,
    query: str,
    user_network: Optional[UserNetwork] = None,
    status_callback: Optional[Callable] = None,
) -> list[RankedAccount]:
    """Run user search API and score results. Falls back to handle guessing if empty."""
    if status_callback:
        await status_callback(f'Searching user profiles for "{query}"...')

    # Run user search API
    user_results = await twitter.search_users(query, max_results=20)

    ranked: list[RankedAccount] = []

    if user_results:
        # search-users returns lightweight data (no followers, no bio).
        # Enrich each with a full profile lookup in parallel.
        async def enrich(user_data: dict) -> dict:
            handle = user_data.get("screen_name", "")
            if not handle:
                return user_data
            full = await twitter.lookup_user(handle)
            return full if full else user_data

        enriched = await asyncio.gather(*[enrich(u) for u in user_results])
        user_results = [u for u in enriched if u is not None]

        # Score and sort using enriched data
        scored_users = []
        for user_data in user_results:
            raw_score = _score_user_match(user_data, query)
            scored_users.append((user_data, raw_score))

        scored_users.sort(key=lambda x: x[1], reverse=True)

        # Take top 20 and build accounts (fetch timelines in parallel)
        top_users = scored_users[:20]

        async def build_one(user_data: dict, raw_score: float) -> RankedAccount | None:
            try:
                account = await _build_account_from_user(
                    twitter, user_data, query, user_network,
                )
                # Normalize raw score (0-100) to 1-10 scale
                normalized = max(1.0, min(10.0, round(raw_score / 10, 1)))
                return RankedAccount(
                    account=account,
                    relevance_score=normalized,
                    why_relevant=f"Profile match for \"{query}\". {account.name} (@{account.handle}).",
                    confidence="high" if normalized >= 7 else "medium" if normalized >= 4 else "low",
                    evidence_highlights=[f"Bio: {account.bio or 'No bio'}"],
                )
            except Exception as e:
                print(f"Error building account from user search: {e}")
                return None

        results = await asyncio.gather(*[build_one(ud, rs) for ud, rs in top_users])
        ranked = [r for r in results if r is not None]

    # Fallback: try handle guessing if user search returned nothing
    if not ranked:
        ranked = await _try_profile_lookups(twitter, query, user_network)

    return ranked


async def _try_profile_lookups(
    twitter: TwitterClient,
    query: str,
    user_network: Optional[UserNetwork] = None,
) -> list[RankedAccount]:
    """Try direct profile lookups by guessing handles from a name query."""
    candidates = _candidate_handles(query)
    if not candidates:
        return []

    async def try_one(handle: str) -> RankedAccount | None:
        user_data = await twitter.lookup_user(handle)
        if not user_data:
            return None
        account = await _build_account_from_user(twitter, user_data, query, user_network)
        # Score using the same weighted system instead of blanket 10
        raw_score = _score_user_match(user_data, query)
        normalized = max(1.0, min(10.0, round(raw_score / 10, 1)))
        return RankedAccount(
            account=account,
            relevance_score=normalized,
            why_relevant=f"Direct profile match for @{account.handle}.",
            confidence="high" if normalized >= 7 else "medium" if normalized >= 4 else "low",
            evidence_highlights=[f"Bio: {account.bio or 'No bio'}"],
        )

    results = await asyncio.gather(*[try_one(h) for h in candidates])
    # Deduplicate by user_id, keep first (highest priority candidate)
    seen_ids: set[str] = set()
    ranked: list[RankedAccount] = []
    for r in results:
        if r and r.account.user_id not in seen_ids:
            seen_ids.add(r.account.user_id)
            ranked.append(r)
    return ranked


# ── Tweet-search scoring (used by server.py for LLM pipeline fallback) ──


def light_filter(accounts: list[TwitterAccount]) -> list[TwitterAccount]:
    """Minimal filtering — only remove obvious bots/spam."""
    filtered = []
    for acc in accounts:
        bio_lower = (acc.bio or "").lower()

        # Bot keyword match
        if any(kw in bio_lower for kw in _BOT_KEYWORDS_FAST):
            continue

        # Extreme spam ratio (following 50x more than followers, with few followers)
        if acc.followers_count < 50 and acc.following_count > 50 * max(acc.followers_count, 1):
            continue

        filtered.append(acc)
    return filtered


def score_accounts_fast(
    accounts: list[TwitterAccount],
    query: str,
) -> list[RankedAccount]:
    """Score accounts found via tweet search using Python heuristics (no LLM)."""
    query_lower = query.lower().strip()
    query_no_spaces = re.sub(r"\s+", "", query_lower)
    query_words = query_lower.split()

    scored: list[RankedAccount] = []

    for acc in accounts:
        points = 0.0
        signals: list[str] = []

        name_lower = acc.name.lower()
        handle_lower = acc.handle.lower()
        bio_lower = (acc.bio or "").lower()

        # --- Display name match (0-50 pts, up from 40) ---
        name_ratio = SequenceMatcher(None, query_lower, name_lower).ratio()
        if query_lower in name_lower:
            points += 50
            signals.append(f'Name contains "{query}"')
        elif name_ratio > 0.6:
            points += 50 * name_ratio
            signals.append("Name closely matches query")

        # --- Handle match (0-35 pts) ---
        handle_clean = handle_lower.replace("_", "").replace(".", "")
        if query_no_spaces == handle_clean:
            points += 35
            signals.append(f"Handle @{acc.handle} is an exact match")
        elif query_no_spaces in handle_clean:
            points += 25
            signals.append(f"Handle @{acc.handle} contains query")
        else:
            handle_ratio = SequenceMatcher(None, query_no_spaces, handle_clean).ratio()
            if handle_ratio > 0.6:
                points += 35 * handle_ratio
                signals.append(f"Handle @{acc.handle} closely matches")

        # --- Follower signal (0-25 pts, up from 10 tiebreaker) ---
        if acc.followers_count > 0:
            follower_pts = min(25, math.log10(max(acc.followers_count, 1)) * 3.0)
            points += follower_pts
            if acc.followers_count >= 100_000:
                signals.append(f"{acc.followers_count:,} followers")

        # --- Bio mention (0-10 pts) ---
        if query_lower in bio_lower:
            points += 10
            signals.append("Bio mentions query")
        elif any(w in bio_lower for w in query_words):
            points += 5
            signals.append("Bio contains related terms")

        # Normalize to 1-10 scale (max raw ≈ 120)
        score = max(1.0, min(10.0, round(points / 12, 1)))

        # Build why_relevant
        if signals:
            why = ". ".join(signals[:3]) + "."
        else:
            why = f'Appeared in search results for "{query}".'

        # Build evidence highlights
        evidence = []
        if acc.bio:
            evidence.append(f"Bio: {acc.bio[:200]}")

        scored.append(RankedAccount(
            account=acc,
            relevance_score=score,
            why_relevant=why,
            confidence="high" if score >= 7 else "medium" if score >= 4 else "low",
            evidence_highlights=evidence,
        ))

    # Sort by score descending, then followers as tiebreaker
    scored.sort(key=lambda r: (r.relevance_score, r.account.followers_count), reverse=True)
    return scored


def merge_ranked_results(
    user_search_results: list[RankedAccount],
    llm_results: list[RankedAccount],
    max_results: int = FAST_PATH_MAX_RESULTS,
) -> list[RankedAccount]:
    """Merge user search and LLM pipeline results. Deduplicate by user_id, keep higher score."""
    by_user_id: dict[str, RankedAccount] = {}

    for r in user_search_results + llm_results:
        uid = r.account.user_id
        if uid not in by_user_id or r.relevance_score > by_user_id[uid].relevance_score:
            by_user_id[uid] = r

    merged = list(by_user_id.values())
    merged.sort(key=lambda r: (r.relevance_score, r.account.followers_count), reverse=True)
    return merged[:max_results]
