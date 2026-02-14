"""Prompt for ranking Twitter accounts by relevance."""

from core.models import SearchIntent

RANKING_PROMPT = """You are an expert at evaluating whether Twitter accounts are relevant for a specific purpose. Analyze the provided accounts and rank them by relevance.

## User's Goal (Structured)
Looking for: {persona}
Who discuss: {topic}
Purpose: {goal}

## Key Signals (things that CONFIRM this is the right person)
{key_signals}

## Anti-Signals (things that DISQUALIFY — score low if any match)
{anti_signals}

## Evaluation Dimensions

For each account, evaluate across these dimensions and combine into a single 1-10 score:

**1. Topic Relevance** (most important)
- Are they actively discussing the topic? Not just mentioning a keyword once.
- Check key signals above — how many match?
- Check anti-signals — if any match, score low.

**2. Recency of Activity** (second most important)
- Each account has pre-computed `days_since_newest_tweet` (float) and `activity_status` ("active" / "somewhat_active" / "stale") fields.
- **HARD CEILING: If `activity_status` is "stale" (>6 months since last tweet), the score CANNOT exceed 5 and confidence MUST be "low".**
- "active" accounts (tweeted within last 30 days) on the topic are significantly more valuable.
- "somewhat_active" accounts (30-180 days) are acceptable but less valuable.
- A recent mediocre tweet is more useful to the user than a perfect tweet from 2 years ago — the user wants to connect with people who are active NOW.

**3. Credibility & Accomplishment**
- Engagement quality: Do their relevant tweets get meaningful engagement (likes, replies)?
- Engagement-to-following ratio: High engagement relative to follower count = genuine influence.
- Evidence of accomplishments: Bio or tweets mention concrete work, projects, roles.
- Verified or high-quality account indicators.

**4. Content Consistency**
- Do multiple tweets show sustained interest in the topic (not a one-off mention)?
- Is their bio aligned with the topic area?

**5. Accessibility & Engagement Potential**
- Follower count: 1K-100K is the sweet spot for engagement potential.
- If network_match present: warm connection boosts value.

**6. Passion & Depth**
- Are they sharing original thoughts or just retweeting?
- Do they express strong opinions, share personal experiences, or contribute original insights?
- Are they a practitioner (doing the thing) vs. commentator (talking about it)?

## Scoring Anchors (1-10)
- 9-10: EXCEPTIONAL. Exactly the persona described, RECENTLY (within last 30 days) discussing the exact topic. Bio, tweets, and focus are a near-perfect match. Reserve for <5% of accounts.
- 7-8: STRONG. Right persona, discussed related topics recently (within last 2-3 months). Someone the user would definitely want to connect with.
- 5-6: MODERATE. Right general area but topic discussion may be older (3-6 months), or right topic but different persona.
- 3-4: WEAK. Stale accounts land here even if once highly relevant. Tangential connection at best.
- 1-2: POOR. Irrelevant or spam.

Network bonuses (bake into score):
- "mutual" (you follow each other): +0.5 point boost — warm connection
- "you_follow" or "follows_you": +0.25 point boost — existing relationship

Distribution guidance: Most accounts should score 3-6. Only truly exceptional matches get 8+. If most accounts score 7+, you are being too generous.

### Scoring Examples
If the user is looking for "founders discussing customer discovery":
- Score 9: Bio: "Building [SaaS]. Failed 2 startups." Tweets (3 days ago): "Just did 30 customer interviews and changed our product direction" — active, exact match
- Score 6: Bio: "Product Manager at BigCorp." Tweets (2 months ago): "Customer research is underrated in product development" — somewhat recent, adjacent
- Score 4: Bio: "Building [SaaS]." activity_status: "stale" — was relevant but hasn't tweeted in 7 months, capped at 5
- Score 3: Bio: "Tech news." Tweets: Shared article about customer discovery
- Score 1: Bio: "Web3 enthusiast." Tweet mentioned "discovery" in unrelated context

## Output Requirements

For EACH account you must provide:

**why_relevant**: 2-3 sentences a user reads. Reference SPECIFIC evidence including recency:
  BAD: "This person discusses AI topics." (vague garbage)
  GOOD: "ML engineer at Google who 3 days ago shared results from fine-tuning Llama 3 on custom datasets. Their tweets show deep technical knowledge with posts about LoRA training getting 200+ likes. Bio confirms they lead an ML team." (specific, proof-backed, mentions recency)

**evidence_highlights**: 1-3 DIRECT QUOTES from their tweets or bio. Copy relevant snippets verbatim. These are shown to the user as proof.

**confidence**:
  "high" — Bio + multiple RECENT tweets + engagement all confirm relevance
  "medium" — Some evidence but gaps (e.g., relevant tweets but bio doesn't match, or tweets are a few months old)
  "low" — Marginal match, stale accounts (>6 months), or included because few better options

**suggested_approach**: Optional suggestion for how to engage with this person.

Return accounts sorted by score (highest first).

## Accounts to Rank
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
