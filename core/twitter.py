"""Twitter data layer using SocialData.tools API."""

from __future__ import annotations

import asyncio
import re
import traceback
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import (
    BOT_KEYWORDS,
    MIN_FOLLOWERS_THRESHOLD,
    RECENCY_BONUS_WINDOW_DAYS,
    RECENCY_HALF_LIFE_DAYS,
    TIMELINE_TWEETS_COUNT,
    TWEETS_PER_QUERY,
)

from .models import NetworkInfo, SearchIntent, Tweet, TwitterAccount

if TYPE_CHECKING:
    from .auth import UserNetwork


def _tweet_recency_score(tweet: Tweet) -> float:
    """Blended score combining engagement with time decay.

    Engagement decays with a 90-day half-life and tweets within the last
    30 days get an additive bonus so that recent low-engagement tweets
    still outrank stale silence.
    """
    engagement = tweet.like_count + 2 * tweet.retweet_count
    if tweet.created_at is None:
        return engagement * 0.1  # no date = heavily penalized
    now = datetime.now(timezone.utc)
    created = (
        tweet.created_at
        if tweet.created_at.tzinfo
        else tweet.created_at.replace(tzinfo=timezone.utc)
    )
    days_old = max(0, (now - created).total_seconds() / 86400)
    decay = 0.5 ** (days_old / RECENCY_HALF_LIFE_DAYS)
    bonus = max(0, RECENCY_BONUS_WINDOW_DAYS - days_old)
    return engagement * decay + bonus


def _extract_media_urls(tweet_obj: dict) -> list[str]:
    """Extract media URLs from a tweet object, preferring extended_entities."""
    urls: list[str] = []
    # Prefer extended_entities (has all media), fall back to entities
    media_list = (
        tweet_obj.get("extended_entities", {}).get("media")
        or tweet_obj.get("entities", {}).get("media")
        or []
    )
    for m in media_list:
        url = m.get("media_url_https") or m.get("media_url")
        if url:
            urls.append(url)
    return urls


class TwitterClient:
    """Wrapper around SocialData.tools API for Twitter data access."""

    def __init__(self):
        """Initialize the Twitter client."""
        from config import SOCIALDATA_API_KEY
        self.api_key = SOCIALDATA_API_KEY
        self.base_url = "https://api.socialdata.tools"
        self._http_client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize the HTTP client."""
        if self._http_client is not None:
            return

        if not self.api_key:
            raise ValueError(
                "SOCIALDATA_API_KEY not set. "
                "Sign up at https://socialdata.tools and add your key to .env"
            )

        self._http_client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    async def _ensure_initialized(self) -> None:
        """Ensure the client is initialized."""
        if self._http_client is None:
            await self.initialize()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def search_tweets(
        self, query: str, count: int = TWEETS_PER_QUERY, search_type: str = "Top"
    ) -> list[dict]:
        """
        Search for tweets matching a query.

        Args:
            query: Twitter search query string
            count: Max tweets to return
            search_type: "Top" or "Latest"

        Returns list of tweet data with author info.
        """
        await self._ensure_initialized()

        try:
            response = await self._http_client.get(
                f"{self.base_url}/twitter/search",
                params={"query": query, "type": search_type},
            )
            response.raise_for_status()
            data = response.json()

            results = []
            tweets = data.get("tweets", [])

            for tweet_obj in tweets[:count]:
                user = tweet_obj.get("user", {})

                tweet_data = {
                    "tweet": {
                        "id": tweet_obj.get("id_str", ""),
                        "text": tweet_obj.get("full_text", ""),
                        "created_at": tweet_obj.get("created_at"),
                        "like_count": tweet_obj.get("favorite_count", 0),
                        "retweet_count": tweet_obj.get("retweet_count", 0),
                        "reply_count": tweet_obj.get("reply_count", 0),
                        "media_urls": _extract_media_urls(tweet_obj),
                    },
                    "user": {
                        "user_id": user.get("id_str", ""),
                        "handle": user.get("screen_name", ""),
                        "name": user.get("name", ""),
                        "bio": user.get("description", ""),
                        "followers_count": user.get("followers_count", 0),
                        "following_count": user.get("friends_count", 0),
                        "tweet_count": user.get("statuses_count", 0),
                        "profile_image_url": user.get("profile_image_url_https", ""),
                        "location": user.get("location", ""),
                        "verified": user.get("verified", False) or user.get("is_blue_verified", False),
                        "created_at": user.get("created_at"),
                    },
                }
                results.append(tweet_data)

            return results

        except httpx.HTTPStatusError as e:
            print(f"HTTP error searching tweets for query '{query}': {e.response.status_code} {e.response.text}")
            raise
        except Exception as e:
            print(f"Error searching tweets for query '{query}': {e}")
            raise

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def fetch_user_timeline(self, user_id: str, count: int = TIMELINE_TWEETS_COUNT) -> list[dict]:
        """
        Fetch recent tweets from a user's timeline.

        Args:
            user_id: Twitter user ID
            count: Max tweets to return

        Returns list of tweet dicts in same format as search results.
        """
        await self._ensure_initialized()

        try:
            response = await self._http_client.get(
                f"{self.base_url}/twitter/statuses/user_timeline",
                params={"user_id": user_id, "count": count},
            )
            response.raise_for_status()
            data = response.json()

            tweets = []
            for tweet_obj in data if isinstance(data, list) else data.get("tweets", data.get("statuses", [])):
                tweets.append({
                    "id": str(tweet_obj.get("id_str", tweet_obj.get("id", ""))),
                    "text": tweet_obj.get("full_text", tweet_obj.get("text", "")),
                    "created_at": tweet_obj.get("created_at"),
                    "like_count": tweet_obj.get("favorite_count", 0),
                    "retweet_count": tweet_obj.get("retweet_count", 0),
                    "reply_count": tweet_obj.get("reply_count", 0),
                    "media_urls": _extract_media_urls(tweet_obj),
                })

            return tweets[:count]

        except Exception as e:
            print(f"Error fetching timeline for user {user_id}: {e}")
            return []

    async def lookup_user(self, handle: str) -> dict | None:
        """Look up a single user by handle. Returns user dict or None if not found."""
        await self._ensure_initialized()
        try:
            response = await self._http_client.get(
                f"{self.base_url}/twitter/user/{handle}",
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError:
            return None
        except Exception as e:
            print(f"Error looking up user @{handle}: {e}")
            return None

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def search_users(self, query: str, max_results: int = 20) -> list[dict]:
        """Search users by display name / screenname via SocialData API."""
        await self._ensure_initialized()
        try:
            response = await self._http_client.get(
                f"{self.base_url}/twitter/search-users",
                params={"query": query},
            )
            response.raise_for_status()
            data = response.json()
            users = data if isinstance(data, list) else data.get("users", [])
            return users[:max_results]
        except httpx.HTTPStatusError as e:
            print(f"HTTP error searching users for '{query}': {e.response.status_code}")
            return []
        except Exception as e:
            print(f"Error searching users for '{query}': {e}")
            return []

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def fetch_similar_profiles(self, user_id: str) -> list[dict]:
        """Fetch profiles similar to a given user via SocialData API."""
        await self._ensure_initialized()
        try:
            response = await self._http_client.get(
                f"{self.base_url}/twitter/user/{user_id}/similar-profiles",
            )
            response.raise_for_status()
            data = response.json()
            users = data if isinstance(data, list) else data.get("users", data.get("similar_profiles", []))
            return users
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching similar profiles for {user_id}: {e.response.status_code}")
            return []
        except Exception as e:
            print(f"Error fetching similar profiles for {user_id}: {e}")
            return []

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def fetch_user_lists(self, user_id: str) -> list[dict]:
        """Fetch lists that a user is a member of via SocialData API."""
        await self._ensure_initialized()
        try:
            response = await self._http_client.get(
                f"{self.base_url}/twitter/user/{user_id}/lists",
            )
            response.raise_for_status()
            data = response.json()
            lists = data if isinstance(data, list) else data.get("lists", [])
            return lists
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching lists for {user_id}: {e.response.status_code}")
            return []
        except Exception as e:
            print(f"Error fetching lists for {user_id}: {e}")
            return []

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def fetch_list_members(self, list_id: str, max_results: int = 100) -> list[dict]:
        """Fetch members of a Twitter list via SocialData API."""
        await self._ensure_initialized()
        try:
            response = await self._http_client.get(
                f"{self.base_url}/twitter/list/{list_id}/members",
            )
            response.raise_for_status()
            data = response.json()
            members = data if isinstance(data, list) else data.get("members", data.get("users", []))
            return members[:max_results]
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching list members for {list_id}: {e.response.status_code}")
            return []
        except Exception as e:
            print(f"Error fetching list members for {list_id}: {e}")
            return []

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def fetch_verified_followers(self, user_id: str, max_results: int = 50) -> list[dict]:
        """Fetch verified followers of a user via SocialData API."""
        await self._ensure_initialized()
        try:
            response = await self._http_client.get(
                f"{self.base_url}/twitter/user/{user_id}/verified-followers",
            )
            response.raise_for_status()
            data = response.json()
            users = data if isinstance(data, list) else data.get("users", data.get("followers", []))
            return users[:max_results]
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching verified followers for {user_id}: {e.response.status_code}")
            return []
        except Exception as e:
            print(f"Error fetching verified followers for {user_id}: {e}")
            return []

    async def fetch_follow_list(
        self, user_id: str, list_type: str = "following", max_count: int = 1000,
    ) -> set[str]:
        """
        Fetch a user's following or followers list via SocialData API.

        Args:
            user_id: Twitter user ID
            list_type: "following" or "followers"
            max_count: Maximum IDs to collect (capped at 1000)

        Returns set of user ID strings.
        """
        await self._ensure_initialized()

        endpoint = "friends" if list_type == "following" else "followers"
        url = f"{self.base_url}/twitter/{endpoint}/list"
        ids: set[str] = set()
        cursor: str | None = None

        while len(ids) < max_count:
            params: dict[str, str] = {"user_id": user_id}
            if cursor:
                params["cursor"] = cursor

            try:
                response = await self._http_client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                users = data.get("users", [])
                if not users:
                    break

                for u in users:
                    ids.add(str(u.get("id_str", u.get("id", ""))))
                    if len(ids) >= max_count:
                        break

                cursor = data.get("next_cursor_str") or data.get("next_cursor")
                if not cursor or cursor == "0":
                    break

                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Error fetching {list_type} for {user_id}: {e}")
                break

        return ids


class SearchOrchestrator:
    """Orchestrates search queries and deduplicates results."""

    def __init__(self, twitter_client: TwitterClient):
        self.client = twitter_client

    async def _run_single_query(self, query, search_type, status_callback):
        """Execute a single search query and return raw results."""
        if status_callback:
            await status_callback(f"Searching for \"{query[:50]}\"...")
        try:
            results = await self.client.search_tweets(query, search_type=search_type)
            return query, results
        except Exception as e:
            print(f"Error executing query '{query}': {e}")
            traceback.print_exc()
            if status_callback:
                await status_callback(f"Query failed: {query[:40]}... ({e})")
            return query, []

    async def execute_searches(
        self, queries: list[str], status_callback=None, exclude_user_ids: set[str] | None = None,
        user_network=None,
    ) -> list[TwitterAccount]:
        """
        Execute multiple search queries in parallel and return deduplicated accounts.

        Queries are split 50/50 between "Top" and "Latest" search types.
        """
        # Build tasks — split 50/50 between Top and Latest
        tasks = []
        for i, query in enumerate(queries):
            search_type = "Latest" if i % 2 == 1 else "Top"
            tasks.append(self._run_single_query(query, search_type, status_callback))

        # Fire all queries in parallel
        results_list = await asyncio.gather(*tasks)

        # Merge results with dedup
        users_by_id: dict[str, dict] = {}
        tweets_by_user: dict[str, list[Tweet]] = {}
        queries_by_user: dict[str, list[str]] = {}

        for query, results in results_list:
            for result in results:
                user_data = result["user"]
                tweet_data = result["tweet"]
                user_id = user_data["user_id"]

                if exclude_user_ids and user_id in exclude_user_ids:
                    continue

                if user_id not in users_by_id:
                    users_by_id[user_id] = user_data
                    tweets_by_user[user_id] = []
                    queries_by_user[user_id] = []

                tweet = Tweet(
                    id=tweet_data["id"],
                    text=tweet_data["text"],
                    created_at=tweet_data.get("created_at"),
                    like_count=tweet_data.get("like_count", 0),
                    retweet_count=tweet_data.get("retweet_count", 0),
                    reply_count=tweet_data.get("reply_count", 0),
                    media_urls=tweet_data.get("media_urls", []),
                )
                tweets_by_user[user_id].append(tweet)

                if query not in queries_by_user[user_id]:
                    queries_by_user[user_id].append(query)

        if status_callback:
            await status_callback(f"Collecting tweets from {len(users_by_id)} accounts...")

        accounts = []
        for user_id, user_data in users_by_id.items():
            # Build network info from user_network if available, otherwise default
            if user_network:
                you_follow = user_id in user_network.following_ids
                follows_you = user_id in user_network.follower_ids
                network = NetworkInfo(
                    you_follow=you_follow,
                    follows_you=follows_you,
                    mutual_followers=[],
                )
            else:
                network = NetworkInfo()

            account = TwitterAccount(
                user_id=user_id,
                handle=user_data["handle"],
                name=user_data["name"],
                bio=user_data.get("bio"),
                followers_count=user_data.get("followers_count", 0),
                following_count=user_data.get("following_count", 0),
                tweet_count=user_data.get("tweet_count", 0),
                profile_url=f"https://twitter.com/{user_data['handle']}",
                profile_image_url=user_data.get("profile_image_url"),
                location=user_data.get("location") or None,
                verified=user_data.get("verified", False),
                created_at=user_data.get("created_at"),
                recent_tweets=sorted(
                    tweets_by_user[user_id],
                    key=_tweet_recency_score,
                    reverse=True,
                )[:10],
                matched_queries=queries_by_user[user_id],
                network=network,
            )
            accounts.append(account)

        return accounts

    @staticmethod
    def pre_filter_accounts(
        accounts: list[TwitterAccount], intent: Optional[SearchIntent] = None,
    ) -> tuple[list[TwitterAccount], int]:
        """
        Remove obvious noise before ranking.

        Returns (filtered_accounts, removed_count).
        """
        anti_signals = [s.lower() for s in intent.anti_signals] if intent and intent.anti_signals else []
        filtered = []
        removed = 0

        for acc in accounts:
            bio_lower = (acc.bio or "").lower()

            # Too few followers (bots/inactive)
            if acc.followers_count < MIN_FOLLOWERS_THRESHOLD:
                removed += 1
                continue

            # Bot keyword match in bio
            if any(kw in bio_lower for kw in BOT_KEYWORDS):
                removed += 1
                continue

            # Suspicious following/follower ratio
            if acc.following_count > 10 * acc.followers_count and acc.followers_count < 100:
                removed += 1
                continue

            # No collected tweets (exempt must_find accounts — they were explicitly sought)
            if not acc.recent_tweets and "must_find" not in (acc.matched_queries or []):
                removed += 1
                continue

            # Anti-signal match in bio (word-boundary so "bot" doesn't match "robot")
            if anti_signals and any(
                re.search(rf'\b{re.escape(signal)}\b', bio_lower) for signal in anti_signals
            ):
                removed += 1
                continue

            filtered.append(acc)

        return filtered, removed

    async def enrich_with_timelines(
        self, accounts: list[TwitterAccount], status_callback=None,
    ) -> None:
        """
        Fetch timelines for accounts and merge with existing tweets.

        Modifies accounts in-place. Fetches in batches of 20 concurrent requests.
        """
        batch_size = 20

        for i in range(0, len(accounts), batch_size):
            batch = accounts[i : i + batch_size]

            async def fetch_for_account(acc: TwitterAccount) -> tuple[TwitterAccount, list[dict]]:
                timeline = await self.client.fetch_user_timeline(acc.user_id)
                return acc, timeline

            tasks = [fetch_for_account(acc) for acc in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    continue
                acc, timeline_tweets = result

                # Deduplicate by tweet ID
                existing_ids = {t.id for t in acc.recent_tweets}
                for t_data in timeline_tweets:
                    t_id = str(t_data.get("id", ""))
                    if t_id and t_id not in existing_ids:
                        acc.recent_tweets.append(Tweet(
                            id=t_id,
                            text=t_data.get("text", ""),
                            created_at=t_data.get("created_at"),
                            like_count=t_data.get("like_count", 0),
                            retweet_count=t_data.get("retweet_count", 0),
                            reply_count=t_data.get("reply_count", 0),
                            media_urls=t_data.get("media_urls", []),
                        ))
                        existing_ids.add(t_id)

                # Sort by blended recency+engagement and keep top 10
                acc.recent_tweets.sort(
                    key=_tweet_recency_score,
                    reverse=True,
                )
                acc.recent_tweets = acc.recent_tweets[:10]

        if status_callback:
            await status_callback(f"Analyzing {len(accounts)} profiles...")
