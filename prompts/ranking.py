"""Prompt for ranking Twitter accounts by relevance using bucket tiers."""

from core.models import SearchIntent

RANKING_PROMPT = """You are an expert at evaluating whether Twitter accounts are relevant for a specific purpose. Categorize each account into a bucket tier.

## User's Goal (Structured)
Looking for: {persona}
Who discuss: {topic}
Purpose: {goal}
Search specificity: {specificity}/5

## Key Signals (things that CONFIRM this is the right person)
{key_signals}

## Anti-Signals (things that DISQUALIFY)
{anti_signals}

{mandatory_terms_section}

## Bucket Tiers

Assign each account to exactly ONE bucket:

### top_match
The ideal result. This person IS the persona described, ACTIVELY discusses the exact topic, and has recent evidence (within last 30 days). Bio, tweets, and focus are a clear match. Reserve for the best ~10-15% of accounts.

### strong_match
Right persona and discusses related topics. May be slightly less recent (1-3 months) or slightly adjacent to the exact topic requested. Someone the user would want to connect with.

### good_match
Correct persona with weaker evidence. The account IS plausibly the type of person described, but evidence is older (3-6 months) or less direct. Must still be the right persona — wrong persona with topical overlap is exclude, not good_match.

### exclude
Irrelevant, spam, stale (>6 months without relevant activity), or anti-signals match. Do NOT show to the user.

## Evaluation Criteria

For each account, evaluate:

**0. Persona Gate** (HARD FILTER — evaluate first)
- Does this account match the described persona? Not adjacent — the ACTUAL persona.
- CRITICAL: "mentions X" ≠ "IS X":
  - "YC founders": YC partners, VCs investing in YC, journalists covering YC → all exclude. ONLY someone who founded a YC company qualifies.
  - "ML engineers": tech journalists writing about ML, PMs working with ML teams → exclude. ONLY someone who engineers ML systems qualifies.
  - "startup founders": VCs, accelerator staff, startup advisors → exclude unless they also founded a startup.
- The test: Is there DIRECT evidence in bio/tweets that they ARE the persona? Not that they interact with, invest in, cover, or advise the persona — that they ARE it.
- If persona doesn't match → ALWAYS exclude. No amount of topical overlap overrides this.
- High-specificity (4-5): be VERY strict. Low-specificity (1-2): more lenient on persona interpretation.

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

**summary**: Write like you're introducing someone at a party — who they are AND why they matter for this search. Be natural and conversational, not robotic.
- top_match / strong_match: 2-3 concise sentences. First: who they are. Second: why they're relevant to this search.
  GOOD: "Sarah builds payment infrastructure at Stripe and writes detailed threads on distributed systems. Her recent post on idempotency patterns sparked a great discussion."
  BAD: "Relevant for: payments infrastructure. Evidence: tweets about distributed systems."
- good_match: 1 natural sentence.
  GOOD: "Data engineer at Shopify who occasionally shares thoughts on ETL pipeline design."
- exclude: Leave empty string.

**highlight_tweet_indices**: Indices (0-based) of the best tweets from their recent_tweets array.
- ALWAYS include at least 1 tweet index for every non-exclude account. Never return an empty array for included accounts.
- For topic-specific searches (specificity >= 3): Choose tweets demonstrating direct engagement with the SPECIFIC topic. Prioritize topical relevance over raw engagement.
- For broad/general searches (specificity 1-2): Choose the most engaging or representative recent tweets.
- If no tweet is directly relevant to the query, pick the most popular or representative recent tweet instead.
- Count: 2-3 for top_match/strong_match, 1-2 for good_match, empty ONLY for exclude.

**evidence_highlights**: 1-2 direct quotes from their tweets or bio that prove relevance.
- For top_match/strong_match: Include the most compelling quote showing topic engagement.
- For good_match: 1 brief quote or bio excerpt.
- For exclude: Empty array.
- Quote format: "tweet: [exact quote]" or "bio: [exact quote]"

**suggested_approach**: For top_match/strong_match only — a 1-sentence specific suggestion for engaging.
- Reference a specific tweet or topic to reply to.
- Example: "Reply to their thread on distributed systems with your experience scaling payments."
- For good_match/exclude: Empty string.

Return accounts with top_match first, then strong_match, then good_match, then exclude.

## Accounts to Evaluate
{accounts_json}
"""


def format_ranking_prompt(intent: SearchIntent, accounts_json: str) -> str:
    """Format the ranking prompt with structured intent and accounts."""
    key_signals = "\n".join(f"- {s}" for s in intent.key_signals) if intent.key_signals else "- (none specified)"
    anti_signals = "\n".join(f"- {s}" for s in intent.anti_signals) if intent.anti_signals else "- (none specified)"

    if intent.mandatory_terms:
        terms_str = ", ".join(f'"{t}"' for t in intent.mandatory_terms)
        if intent.specificity >= 4:
            mandatory_terms_section = f"""## Mandatory Relevance Terms (HARD GATE)

Key terms for this search: {terms_str}

This is a specific search (specificity {intent.specificity}/5). These terms are NON-NEGOTIABLE:
- If an account does NOT mention at least one of these terms in their bio, tweets, or handle → EXCLUDE. No exceptions.
- Topical adjacency alone is NOT sufficient. Someone who talks about startups is not a YC founder unless they explicitly mention YC.
- Only accounts with clear, direct evidence of association with these terms can be non-exclude."""
        else:
            mandatory_terms_section = f"""## Key Relevance Terms

Key terms for this search: {terms_str}

Accounts that mention these terms in their bio, tweets, or handle are significantly more likely to be relevant — weight this heavily. Accounts without any mention can still qualify as good_match if they show clear topical connection through their content, but absence of these terms is a strong signal against relevance."""
    else:
        mandatory_terms_section = """## Search Scope

Broad category search — match on overall relevance. No mandatory term filtering required."""

    return RANKING_PROMPT.format(
        persona=intent.persona,
        topic=intent.topic,
        goal=intent.goal,
        specificity=intent.specificity,
        key_signals=key_signals,
        anti_signals=anti_signals,
        mandatory_terms_section=mandatory_terms_section,
        accounts_json=accounts_json,
    )
