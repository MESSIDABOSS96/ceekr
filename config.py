"""Configuration and environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent
COOKIES_FILE = PROJECT_ROOT / "cookies.json"

# Anthropic settings
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
ANTHROPIC_FAST_MODEL = os.getenv("ANTHROPIC_FAST_MODEL", "claude-haiku-4-5-20251001")

# SocialData settings
SOCIALDATA_API_KEY = os.getenv("SOCIALDATA_API_KEY")

# Twitter OAuth 2.0 settings (optional — enables network matching)
TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
TWITTER_REDIRECT_URI = os.getenv("TWITTER_REDIRECT_URI", "http://localhost:8000/api/auth/twitter/callback")


def is_oauth_configured() -> bool:
    """Check if Twitter OAuth credentials are set."""
    return bool(TWITTER_CLIENT_ID)


# Search settings
MIN_QUERIES = 8  # Number of search queries to generate (fixed)
MAX_QUERIES = 8  # Number of search queries to generate (fixed)
TWEETS_PER_QUERY = 50  # Number of tweets to fetch per query

# Pre-filter thresholds
MIN_FOLLOWERS_THRESHOLD = 10
BOT_KEYWORDS = ["bot", "auto", "giveaway", "airdrop", "free followers", "follow back"]

# Ranking
RANKING_BATCH_SIZE = 40
MAX_TWEETS_FOR_RANKING = 3  # tweets sent to LLM per account
MAX_TWEET_LENGTH = 250  # chars per tweet
MAX_BIO_LENGTH = 200  # chars for bio

# Fast path
FAST_PATH_MAX_RESULTS = 75

# Fallback queries
MIN_ACCOUNTS_BEFORE_FALLBACK = 30

# Recency scoring
RECENCY_HALF_LIFE_DAYS = 90        # engagement value halves every N days
RECENCY_BONUS_WINDOW_DAYS = 30     # additive bonus for tweets within this window
STALE_ACCOUNT_DAYS = 180           # days without tweets = "stale" signal to LLM

# Enrichment (post-ranking, supplemental only)
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")  # Optional — web enrichment for links
TIMELINE_TWEETS_COUNT = 15  # tweets to fetch from user timeline


def validate_config() -> list[str]:
    """Validate configuration and return list of errors."""
    errors = []

    if not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")

    if not SOCIALDATA_API_KEY:
        errors.append(
            "SOCIALDATA_API_KEY not set. Sign up at https://socialdata.tools and add your key to .env"
        )

    return errors
