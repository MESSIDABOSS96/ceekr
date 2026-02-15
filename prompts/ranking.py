"""Prompt for ranking Twitter accounts by relevance using bucket tiers."""

from core.models import SearchIntent

RANKING_PROMPT = """You are an expert at evaluating whether Twitter accounts are relevant for a specific purpose. Categorize each account into a bucket tier.

## User's Goal (Structured)
Looking for: {persona}
Who discuss: {topic}
Purpose: {goal}

## Key Signals (things that CONFIRM this is the right person)
{key_signals}

## Anti-Signals (things that DISQUALIFY)
{anti_signals}

## Bucket Tiers

Assign each account to exactly ONE bucket:

### top_match
The ideal result. This person IS the persona described, ACTIVELY discusses the exact topic, and has recent evidence (within last 30 days). Bio, tweets, and focus are a clear match. Reserve for the best ~10-15% of accounts.

### strong_match
Right persona and discusses related topics. May be slightly less recent (1-3 months) or slightly adjacent to the exact topic requested. Someone the user would want to connect with.

### good_match
Right general area but weaker evidence. Topic discussion may be older (3-6 months), or right topic but different persona, or limited tweet evidence. Still worth showing.

### exclude
Irrelevant, spam, stale (>6 months without relevant activity), or anti-signals match. Do NOT show to the user.

## Evaluation Criteria

For each account, evaluate:

**1. Topic Relevance** (most important)
- Are they actively discussing the topic? Not just mentioning a keyword once.
- Check key signals — how many match?
- Check anti-signals — if any match, lean toward exclude.

**2. Recency of Activity**
- Each account has `days_since_newest_tweet` and `activity_status` fields.
- "stale" accounts (>6 months) should be good_match at best, never top_match or strong_match.
- "active" accounts (within 30 days) are significantly more valuable.

**3. Evidence Quality**
- Multiple relevant tweets > one tweet
- Original thoughts > retweets
- High engagement relative to follower count = genuine influence

**4. Network Match** (if present)
- "mutual" connection: slight boost
- "you_follow" or "follows_you": minor boost

## Output Requirements

For EACH account provide:

**handle**: Twitter handle (without @)

**bucket**: One of: top_match, strong_match, good_match, exclude

**summary**: User-facing explanation. Tailor verbosity to bucket:
- top_match / strong_match: 2-3 sentences with SPECIFIC evidence. Reference tweets, bio, engagement. Mention recency.
  GOOD: "ML engineer at Google who 3 days ago shared results from fine-tuning Llama 3. Their tweets show deep technical knowledge with posts about LoRA training getting 200+ likes."
- good_match: 1 sentence explaining the connection.
  GOOD: "Discusses AI topics occasionally, bio mentions working in ML."
- exclude: Leave empty string.

**highlight_tweet_indices**: Indices (0-based) of the most relevant tweets from their recent_tweets array. Up to 3 for top/strong, 1 for good, empty for exclude.

Return accounts with top_match first, then strong_match, then good_match, then exclude.

## Accounts to Evaluate
{accounts_json}
"""


def format_ranking_prompt(intent: SearchIntent, accounts_json: str) -> str:
    """Format the ranking prompt with structured intent and accounts."""
    key_signals = "\n".join(f"- {s}" for s in intent.key_signals) if intent.key_signals else "- (none specified)"
    anti_signals = "\n".join(f"- {s}" for s in intent.anti_signals) if intent.anti_signals else "- (none specified)"

    return RANKING_PROMPT.format(
        persona=intent.persona,
        topic=intent.topic,
        goal=intent.goal,
        key_signals=key_signals,
        anti_signals=anti_signals,
        accounts_json=accounts_json,
    )
