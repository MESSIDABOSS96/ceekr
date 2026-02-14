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


class SearchIntent(BaseModel):
    """Structured decomposition of the user's search request."""

    persona: str = Field("", description="e.g. 'early-stage SaaS founders'")
    topic: str = Field("", description="e.g. 'customer discovery challenges'")
    goal: str = Field("", description="e.g. 'find people to validate product idea with'")
    specificity: int = Field(3, ge=1, le=5, description="1=very broad, 5=very specific")
    suggested_query_count: int = Field(5, ge=3, le=12, description="3-12 based on specificity")
    min_score_threshold: int = Field(5, ge=3, le=8, description="Minimum score to show")
    key_signals: list[str] = Field(
        default_factory=list,
        description="3-5 specific things to look for in tweets/bios that confirm relevance",
    )
    anti_signals: list[str] = Field(
        default_factory=list,
        description="2-3 disqualifiers that indicate NOT the right person",
    )


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


class EnrichmentData(BaseModel):
    """Supplemental web enrichment data for a ranked account."""

    external_link: Optional[str] = None
    link_label: Optional[str] = None
    context_note: Optional[str] = None


class RankedAccount(BaseModel):
    """A ranked Twitter account with relevance analysis."""

    account: TwitterAccount = Field(..., description="The Twitter account")
    relevance_score: float = Field(
        ..., ge=1, le=10, description="Relevance score (1-10)"
    )
    why_relevant: str = Field(
        ..., description="2-3 sentence evidence-based explanation of why this person is relevant"
    )
    suggested_approach: Optional[str] = Field(
        None, description="Optional suggestion for how to engage with this person"
    )
    evidence_highlights: list[str] = Field(
        default_factory=list,
        description="1-3 direct quotes from tweets/bio proving relevance",
    )
    confidence: str = Field(
        "medium", description="Confidence level: high, medium, or low"
    )
    enrichment: Optional[EnrichmentData] = Field(
        None, description="Supplemental web enrichment data (only when directly relevant)"
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
