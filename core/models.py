"""Pydantic models for Twitter Account Finder."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserInput(BaseModel):
    """User's search request."""

    who: str = Field(
        ...,
        description="Who they want to find - type of person and what they should have talked about",
    )
    why: Optional[str] = Field(
        None,
        description="Why they want to find them - context that helps determine relevance",
    )


class ClarificationQuestion(BaseModel):
    """A clarifying question to ask the user."""

    question: str = Field(..., description="The question to ask")
    reason: str = Field(..., description="Why this clarification is needed")


class ClarificationResponse(BaseModel):
    """Response from clarity check - either clear or needs clarification."""

    is_clear: bool = Field(..., description="Whether the input is clear enough to proceed")
    questions: list[ClarificationQuestion] = Field(
        default_factory=list,
        description="Questions to ask if input is not clear (empty if clear)",
    )


class SearchQuery(BaseModel):
    """A Twitter search query with rationale."""

    query: str = Field(..., description="The Twitter search query string")
    rationale: str = Field(..., description="Why this query helps find relevant people")
    angle: str = Field(..., description="What angle/approach this query takes")


class SearchQueriesResponse(BaseModel):
    """Response containing generated search queries."""

    queries: list[SearchQuery] = Field(
        ..., description="List of 3-5 search queries from different angles"
    )


class Tweet(BaseModel):
    """A tweet from a user."""

    id: str = Field(..., description="Tweet ID")
    text: str = Field(..., description="Tweet content")
    created_at: Optional[datetime] = Field(None, description="When the tweet was posted")
    like_count: int = Field(0, description="Number of likes")
    retweet_count: int = Field(0, description="Number of retweets")
    reply_count: int = Field(0, description="Number of replies")


class NetworkInfo(BaseModel):
    """Network relationship information."""

    you_follow: bool = Field(False, description="Whether you follow this account")
    follows_you: bool = Field(False, description="Whether this account follows you")
    mutual_followers: list[str] = Field(
        default_factory=list,
        description="Handles of mutual followers (limited to a few)",
    )


class TwitterAccount(BaseModel):
    """A Twitter account with profile and activity data."""

    user_id: str = Field(..., description="Twitter user ID")
    handle: str = Field(..., description="Twitter handle (without @)")
    name: str = Field(..., description="Display name")
    bio: Optional[str] = Field(None, description="Profile bio/description")
    followers_count: int = Field(0, description="Number of followers")
    following_count: int = Field(0, description="Number of accounts they follow")
    tweet_count: int = Field(0, description="Total number of tweets")
    profile_url: str = Field(..., description="URL to their Twitter profile")
    profile_image_url: Optional[str] = Field(None, description="URL to profile image")

    # Activity data
    recent_tweets: list[Tweet] = Field(
        default_factory=list, description="Recent tweets from this user"
    )
    matched_queries: list[str] = Field(
        default_factory=list,
        description="Which search queries this account appeared in",
    )

    # Network info
    network: NetworkInfo = Field(
        default_factory=NetworkInfo, description="Network relationship info"
    )


class RankedAccount(BaseModel):
    """A ranked Twitter account with relevance analysis."""

    account: TwitterAccount = Field(..., description="The Twitter account")
    relevance_score: float = Field(
        ..., ge=0, le=15, description="Overall relevance score (0-15)"
    )
    base_score: float = Field(
        ..., ge=0, le=10, description="Base content relevance score (0-10)"
    )
    why_relevant: str = Field(
        ..., description="1-2 sentence explanation of why this person is relevant"
    )
    suggested_approach: Optional[str] = Field(
        None, description="Optional suggestion for how to engage with this person"
    )


class RankingResponse(BaseModel):
    """Response from the ranking LLM call."""

    ranked_accounts: list[RankedAccount] = Field(
        ..., description="Accounts sorted by relevance score (highest first)"
    )
