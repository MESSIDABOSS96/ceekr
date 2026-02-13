"""Twitter data layer using SocialData.tools API."""

from __future__ import annotations

import asyncio
import traceback
from typing import TYPE_CHECKING, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import SOCIALDATA_API_KEY, TWEETS_PER_QUERY

from .models import NetworkInfo, Tweet, TwitterAccount

if TYPE_CHECKING:
    from .auth import UserNetwork


class TwitterClient:
    """Wrapper around SocialData.tools API for Twitter data access."""

    def __init__(self):
        """Initialize the Twitter client."""
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
            await status_callback(f"Searching: {query[:50]}...")
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

        Args:
            queries: List of Twitter search query strings
            status_callback: Optional async function to call with status updates
            exclude_user_ids: Optional set of user IDs to skip (for "Find More")

        Returns:
            List of unique TwitterAccount objects with network info
        """
        # Build tasks — last query uses "Latest"
        tasks = []
        for i, query in enumerate(queries):
            search_type = "Latest" if i == len(queries) - 1 else "Top"
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
                )
                tweets_by_user[user_id].append(tweet)

                if query not in queries_by_user[user_id]:
                    queries_by_user[user_id].append(query)

        if status_callback:
            await status_callback(f"Found {len(users_by_id)} unique accounts, enriching data...")

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
                recent_tweets=tweets_by_user[user_id][:5],
                matched_queries=queries_by_user[user_id],
                network=network,
            )
            accounts.append(account)

        return accounts
