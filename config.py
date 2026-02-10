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

# SocialData settings
SOCIALDATA_API_KEY = os.getenv("SOCIALDATA_API_KEY")

# Search settings
MIN_QUERIES = 3  # Minimum number of search queries to generate
MAX_QUERIES = 7  # Maximum number of search queries to generate
TWEETS_PER_QUERY = 20  # Number of tweets to fetch per query


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
