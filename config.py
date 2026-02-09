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

# Search settings
MAX_QUERIES = 5  # Maximum number of search queries to generate
TWEETS_PER_QUERY = 20  # Number of tweets to fetch per query
INITIAL_RESULTS = 15  # Number of results to show initially
LOAD_MORE_BATCH = 10  # Number of additional results per "load more"

# Rate limiting
REQUEST_DELAY = 0.5  # Seconds between Twitter requests

# Scoring weights
SCORE_WEIGHTS = {
    "you_follow": 1.5,
    "they_follow_you": 2.0,
    "mutual_followers": 0.5,
    "recent_30_days": 1.0,
    "recent_90_days": 0.5,
    "stale_1_year": -1.0,
    "huge_account_500k": -0.5,
    "large_account_100k": -0.25,
    "tiny_account_100": -0.5,
    "small_account_500": -0.1,
}


def validate_config() -> list[str]:
    """Validate configuration and return list of errors."""
    errors = []

    if not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")

    if not COOKIES_FILE.exists():
        errors.append(
            f"Twitter cookies not found at {COOKIES_FILE}. "
            "Export your Twitter cookies and convert to JSON format."
        )

    return errors
