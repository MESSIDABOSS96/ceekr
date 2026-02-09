"""Twitter data layer using twikit."""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential
from twikit import Client

from config import COOKIES_FILE, REQUEST_DELAY, TWEETS_PER_QUERY

from .models import NetworkInfo, Tweet, TwitterAccount


class TwitterClient:
    """Wrapper around twikit for Twitter data access."""

    def __init__(self, cookies_file: Path = COOKIES_FILE):
        """Initialize the Twitter client."""
        self.cookies_file = cookies_file
        self.client: Optional[Client] = None
        self._following_cache: Optional[set[str]] = None
        self._followers_cache: Optional[set[str]] = None
        self._my_user_id: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize and authenticate the client."""
        if self.client is not None:
            return

        self.client = Client("en-US")

        # Load cookies from file
        if not self.cookies_file.exists():
            raise FileNotFoundError(
                f"Cookies file not found at {self.cookies_file}. "
                "Please export your Twitter cookies using a browser extension."
            )

        # twikit expects cookies in Netscape format or JSON
        self.client.load_cookies(str(self.cookies_file))

    async def _ensure_initialized(self) -> None:
        """Ensure the client is initialized."""
        if self.client is None:
            await self.initialize()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def search_tweets(self, query: str, count: int = TWEETS_PER_QUERY) -> list[dict]:
        """
        Search for tweets matching a query.

        Returns list of tweet data with author info.
        """
        await self._ensure_initialized()

        # Add delay to avoid rate limiting
        await asyncio.sleep(REQUEST_DELAY)

        try:
            # Search for tweets (Top results, not Latest)
            tweets = await self.client.search_tweet(query, "Top", count=count)

            results = []
            for tweet in tweets:
                # Extract tweet and user data
                tweet_data = {
                    "tweet": {
                        "id": tweet.id,
                        "text": tweet.text,
                        "created_at": tweet.created_at,
                        "like_count": tweet.favorite_count or 0,
                        "retweet_count": tweet.retweet_count or 0,
                        "reply_count": tweet.reply_count or 0,
                    },
                    "user": {
                        "user_id": tweet.user.id,
                        "handle": tweet.user.screen_name,
                        "name": tweet.user.name,
                        "bio": tweet.user.description,
                        "followers_count": tweet.user.followers_count or 0,
                        "following_count": tweet.user.friends_count or 0,
                        "tweet_count": tweet.user.statuses_count or 0,
                        "profile_image_url": tweet.user.profile_image_url,
                    },
                }
                results.append(tweet_data)

            return results

        except Exception as e:
            print(f"Error searching tweets: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_user_tweets(self, user_id: str, count: int = 5) -> list[Tweet]:
        """Fetch recent tweets from a user."""
        await self._ensure_initialized()
        await asyncio.sleep(REQUEST_DELAY)

        try:
            user = await self.client.get_user_by_id(user_id)
            tweets = await user.get_tweets("Tweets", count=count)

            return [
                Tweet(
                    id=t.id,
                    text=t.text,
                    created_at=t.created_at,
                    like_count=t.favorite_count or 0,
                    retweet_count=t.retweet_count or 0,
                    reply_count=t.reply_count or 0,
                )
                for t in tweets
            ]
        except Exception as e:
            print(f"Error getting user tweets: {e}")
            return []

    async def get_my_following(self, force_refresh: bool = False) -> set[str]:
        """
        Get set of user IDs that I follow.

        Results are cached for the session.
        """
        if self._following_cache is not None and not force_refresh:
            return self._following_cache

        await self._ensure_initialized()

        try:
            # Get my user info first
            me = await self.client.user()
            self._my_user_id = me.id

            # Get following list
            following = set()
            cursor = None

            # Paginate through following list (limit to avoid rate limits)
            for _ in range(10):  # Max 10 pages (~2000 users)
                await asyncio.sleep(REQUEST_DELAY)
                result = await me.get_following(cursor=cursor)

                for user in result:
                    following.add(user.id)

                if not hasattr(result, "next_cursor") or not result.next_cursor:
                    break
                cursor = result.next_cursor

            self._following_cache = following
            return following

        except Exception as e:
            print(f"Error getting following list: {e}")
            return set()

    async def get_my_followers(self, force_refresh: bool = False) -> set[str]:
        """
        Get set of user IDs that follow me.

        Results are cached for the session.
        """
        if self._followers_cache is not None and not force_refresh:
            return self._followers_cache

        await self._ensure_initialized()

        try:
            me = await self.client.user()
            self._my_user_id = me.id

            # Get followers list
            followers = set()
            cursor = None

            for _ in range(10):  # Max 10 pages
                await asyncio.sleep(REQUEST_DELAY)
                result = await me.get_followers(cursor=cursor)

                for user in result:
                    followers.add(user.id)

                if not hasattr(result, "next_cursor") or not result.next_cursor:
                    break
                cursor = result.next_cursor

            self._followers_cache = followers
            return followers

        except Exception as e:
            print(f"Error getting followers list: {e}")
            return set()

    async def check_network_status(self, user_id: str) -> NetworkInfo:
        """Check network relationship with a user."""
        following = await self.get_my_following()
        followers = await self.get_my_followers()

        return NetworkInfo(
            you_follow=user_id in following,
            follows_you=user_id in followers,
            mutual_followers=[],  # Skip mutual detection for v1
        )


class SearchOrchestrator:
    """Orchestrates search queries and deduplicates results."""

    def __init__(self, twitter_client: TwitterClient):
        self.client = twitter_client

    async def execute_searches(
        self, queries: list[str], status_callback=None
    ) -> list[TwitterAccount]:
        """
        Execute multiple search queries and return deduplicated accounts.

        Args:
            queries: List of Twitter search query strings
            status_callback: Optional async function to call with status updates

        Returns:
            List of unique TwitterAccount objects with network info
        """
        # Track unique users by ID
        users_by_id: dict[str, dict] = {}
        tweets_by_user: dict[str, list[Tweet]] = {}
        queries_by_user: dict[str, list[str]] = {}

        # Execute all queries
        for i, query in enumerate(queries):
            if status_callback:
                await status_callback(f"Searching: {query[:50]}...")

            try:
                results = await self.client.search_tweets(query)

                for result in results:
                    user_data = result["user"]
                    tweet_data = result["tweet"]
                    user_id = user_data["user_id"]

                    # Store/update user data
                    if user_id not in users_by_id:
                        users_by_id[user_id] = user_data
                        tweets_by_user[user_id] = []
                        queries_by_user[user_id] = []

                    # Add tweet
                    tweet = Tweet(
                        id=tweet_data["id"],
                        text=tweet_data["text"],
                        created_at=tweet_data.get("created_at"),
                        like_count=tweet_data.get("like_count", 0),
                        retweet_count=tweet_data.get("retweet_count", 0),
                        reply_count=tweet_data.get("reply_count", 0),
                    )
                    tweets_by_user[user_id].append(tweet)

                    # Track which query found this user
                    if query not in queries_by_user[user_id]:
                        queries_by_user[user_id].append(query)

            except Exception as e:
                print(f"Error executing query '{query}': {e}")
                continue

        if status_callback:
            await status_callback(f"Found {len(users_by_id)} unique accounts, enriching data...")

        # Build TwitterAccount objects with network info
        accounts = []
        for user_id, user_data in users_by_id.items():
            # Get network status
            network = await self.client.check_network_status(user_id)

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
                recent_tweets=tweets_by_user[user_id][:5],  # Limit to 5 tweets
                matched_queries=queries_by_user[user_id],
                network=network,
            )
            accounts.append(account)

        return accounts
