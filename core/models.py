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


class SearchIntent(BaseModel):
    """Structured decomposition of the user's search request."""

    is_clear: bool = Field(..., description="Can we meaningfully search? (False only for specificity=1)")
    questions: list[ClarificationQuestion] = Field(
        default_factory=list,
        description="If not clear, what to ask",
    )
    persona: str = Field("", description="e.g. 'early-stage SaaS founders'")
    topic: str = Field("", description="e.g. 'customer discovery challenges'")
    goal: str = Field("", description="e.g. 'find people to validate product idea with'")
    specificity: int = Field(3, ge=1, le=5, description="1=very broad, 5=very specific")
    suggested_query_count: int = Field(5, ge=3, le=7, description="3-7 based on specificity")
    min_score_threshold: int = Field(4, ge=1, le=7, description="Minimum score to show")


class SearchQuery(BaseModel):
    """A Twitter search query with rationale."""

    query: str = Field(..., description="The Twitter search query string")
    rationale: str = Field(..., description="Why this query helps find relevant people")
    angle: str = Field(..., description="What angle/approach this query takes")


class SearchQueriesResponse(BaseModel):
    """Response containing generated search queries."""

    queries: list[SearchQuery] = Field(
        ..., description="List of search queries from different angles"
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
    location: Optional[str] = Field(None, description="Profile location")
    verified: bool = Field(False, description="Whether the account is verified")
    created_at: Optional[datetime] = Field(None, description="When the account was created")

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
        ..., ge=1, le=10, description="Relevance score (1-10)"
    )
    score_reasoning: str = Field(
        ..., description="1 sentence explaining what drove this score"
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
    result_quality: str = Field(
        "moderate", description="Overall quality: 'strong', 'moderate', or 'weak'"
    )
    refinement_questions: list[str] = Field(
        default_factory=list,
        description="1-2 clarifying questions if quality is weak",
    )
