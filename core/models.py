"""Pydantic models for Twitter Account Finder."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class BucketTier(str, Enum):
    """Ranking bucket tiers."""
    TOP_MATCH = "top_match"
    STRONG_MATCH = "strong_match"
    GOOD_MATCH = "good_match"
    EXCLUDE = "exclude"


# Sort order: lower = better
BUCKET_SORT_ORDER = {
    "top_match": 0,
    "strong_match": 1,
    "good_match": 2,
    "exclude": 3,
}

# Map bucket to synthetic relevance score for backward compat
BUCKET_SCORE_MAP = {
    "top_match": 9.0,
    "strong_match": 7.0,
    "good_match": 5.0,
    "exclude": 2.0,
}


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
    suggested_query_count: int = Field(8, ge=3, le=12, description="3-12 based on specificity")
    bio_search_terms: list[str] = Field(
        default_factory=list,
        description="3-4 short keyword phrases for bio/profile searches",
    )
    key_signals: list[str] = Field(
        default_factory=list,
        description="3-5 specific things to look for in tweets/bios that confirm relevance",
    )
    anti_signals: list[str] = Field(
        default_factory=list,
        description="2-3 disqualifiers that indicate NOT the right person",
    )
    mandatory_terms: list[str] = Field(
        default_factory=list,
        description="0-3 niche-specific terms that MUST appear in results. Empty for broad queries.",
    )
    time_constraint: Optional[str] = Field(
        None,
        description="ISO date YYYY-MM-DD for earliest relevant date, e.g. '2025-09-01'",
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
    media_urls: list[str] = Field(default_factory=list, description="Media URLs (photos/video thumbnails)")


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
    bucket: str = Field(
        "good_match", description="Bucket tier: top_match, strong_match, good_match, exclude"
    )
    summary: str = Field(
        "", description="User-facing summary of why this person matches"
    )
    highlight_tweet_indices: list[int] = Field(
        default_factory=list,
        description="Indices of highlighted tweets in recent_tweets",
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


# ── Workspace models ──────────────────────────────────────────


class GroupingAxis(BaseModel):
    """A discovered axis for grouping people in a workspace."""
    id: str = Field(default_factory=lambda: f"ax-{uuid4().hex[:8]}")
    axis_key: str = Field(..., description="e.g. 'contribution_area'")
    axis_label: str = Field(..., description="e.g. 'By contribution area'")
    example_groups: list[str] = Field(default_factory=list, description="Preview group labels")


class WorkspaceStatus(str, Enum):
    """Status of a workspace."""
    CREATING = "creating"
    READY = "ready"
    ENRICHING = "enriching"


class JournalPerson(BaseModel):
    """A person's membership in a journal."""
    user_id: str = Field(..., description="Twitter user ID")
    handle: str = Field(..., description="Twitter handle")
    journal_note: str = Field("", description="Why this person is in this journal")
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Journal(BaseModel):
    """A semantic group of people within a workspace."""
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    label: str = Field(..., description="Short label for this group")
    description: str = Field("", description="What this group represents")
    theme: str = Field("", description="Deprecated — use axis_id instead")
    axis_id: Optional[str] = Field(None, description="ID of the grouping axis this journal belongs to")
    color: str = Field("#6366f1", description="Display color hex")
    people: list[JournalPerson] = Field(default_factory=list)
    canvas_x: float = Field(0.0, description="X position on workspace canvas")
    canvas_y: float = Field(0.0, description="Y position on workspace canvas")
    enrichment_status: str = Field("pending", description="pending/enriching/done")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatMessage(BaseModel):
    """A message in the workspace chat history."""
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., description="Message content")
    action: Optional[dict] = Field(None, description="Optional action payload")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Workspace(BaseModel):
    """A research workspace created from a query."""
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    query: str = Field(..., description="Original search query")
    status: WorkspaceStatus = Field(WorkspaceStatus.CREATING)
    intent: Optional[SearchIntent] = None
    journals: list[Journal] = Field(default_factory=list)
    axes: list[GroupingAxis] = Field(default_factory=list, description="Available grouping axes")
    active_axis_id: Optional[str] = Field(None, description="Currently active axis ID")
    recommendation_reason: str = Field("", description="Why the default axis was chosen")
    quality: str = Field("moderate", description="strong/moderate/weak")
    summary: str = Field("", description="Executive summary of results")
    total_people: int = Field(0)
    refinement_questions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
