"""V2-specific LLM prompts for the Seed & Expand algorithm."""

from __future__ import annotations

from core.models import SearchIntent


V2_SEARCH_PLAN_PROMPT = """Analyze this search request and create a seed-based search plan. You need to identify the intent AND plan how to find seed accounts that we can then expand outward from.

## User's Request
Who they want to find: {who}
{why_section}

## Part 1: Analyze the Request

Decompose the request into structured fields:

**persona**: The type of person they're looking for (e.g., "early-stage SaaS founders", "ML researchers")
**topic**: What these people should be discussing/involved in (e.g., "customer discovery challenges", "LLM fine-tuning")
**goal**: Why the user wants to find them (infer if not stated)

**key_signals**: 3-5 SPECIFIC things to look for in tweets/bios that confirm this person matches.
**anti_signals**: 2-3 things that indicate this is NOT the right person.

**mandatory_terms**: 0-3 niche-specific terms that are the NON-NEGOTIABLE core of this search.
Rules:
- If the query has a SPECIFIC product/project/technology name → that IS a mandatory term
- If the query is inherently broad → mandatory_terms = []
- Use the NICHE SPECIFIER, not the role

**specificity** (1-5): How specific is this request?

**bio_search_terms**: 3-4 short keyword phrases for profile searches (1-3 words each).

## Part 2: Seed Discovery Plan

Generate strategies to find 5-8 high-quality seed accounts:

**seed_queries**: 3-5 Twitter search queries designed to find the MOST prominent/active people in this space. These should be highly targeted — we want quality seeds, not broad coverage.
- Use the same Twitter search rules (quoted phrase alone or + 1 keyword)
- Target people who are clearly central to this topic

**seed_accounts**: 0-5 known Twitter handles who are well-known in this space. Only include handles you are CONFIDENT exist and are relevant. Format: just the handle without @.

**must_find_names**: Up to 5 well-known entity names that users would EXPECT to see in results for this query. Use real-world names, NOT Twitter handles.
- Think: "top vc firms" → Sequoia Capital, Y Combinator, Andreessen Horowitz, Benchmark, etc.
- List the most famous/obvious people, companies, or organizations in this space.
- Use proper names (e.g., "Sequoia Capital" not "sequoia", "Marc Andreessen" not "pmarca").
- Leave empty for niche queries where no well-known entities exist.

**expansion_queries**: 2-3 broader queries to catch people in adjacent conversations. These run AFTER we have seeds and help fill gaps.

**list_keywords**: 1-3 keywords for finding relevant Twitter lists (e.g., "AI researchers", "web3 founders"). Lists are a great way to discover people curated by the community.

Use the v2_search_plan tool to respond."""


V2_RANKING_PROMPT = """You are an expert at evaluating whether Twitter accounts are relevant for a specific purpose. Categorize each account into a bucket tier.

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

## Discovery Context
These accounts were found through a seed & expand process:
- We started with {seed_count} seed accounts known to be central to this topic
- Candidates were discovered through: {discovery_sources}
- Source count per candidate is provided — higher means they appeared in multiple discovery channels

## Bucket Tiers

Assign each account to exactly ONE bucket:

### top_match
The ideal result. This person IS the persona described, ACTIVELY discusses the exact topic, and has recent evidence. Bio, tweets, and focus are a clear match. Reserve for the best ~10-15%.

### strong_match
Right persona and discusses related topics. May be slightly less recent or slightly adjacent. Someone the user would want to connect with.

### good_match
Correct persona with weaker evidence. Plausibly the right type but evidence is older or less direct. Must still be the right persona.

### exclude
Irrelevant, spam, stale, or anti-signals match. Do NOT show to the user.

## Evaluation Criteria

**0. Persona Gate** (HARD FILTER)
- Does this account match the described persona? If not → exclude.

**1. Topic Relevance** (most important)
- Active discussion of the topic, not just a keyword mention.

**2. Discovery Signal Strength**
- Found through multiple channels (similar profiles + lists + tweets) = stronger signal
- Found only through one broad query = weaker signal

**3. Evidence Quality**
- Multiple relevant tweets > one tweet
- Original thoughts > retweets

**4. Network Match** (if present)
- "mutual" connection: slight boost
- "you_follow" or "follows_you": minor boost

## Output Requirements

For EACH account provide:
- **handle**: Twitter handle (without @)
- **bucket**: One of: top_match, strong_match, good_match, exclude
- **summary**: A concise, natural explanation of why this person matters for this search. Focus ONLY on what makes them relevant — their expertise, what they talk about, and why the user should care.

  DO NOT mention: follower counts, verification status, account age, or that they're "relevant" or a "match" — the user can already see all of this.

  top_match / strong_match (2 short sentences): First sentence = who they are. Second = why they matter for this search.
    GOOD: "ML engineer at DeepMind who regularly shares practical tips on training large language models. Recently posted a detailed thread on RLHF techniques."
    BAD: "Highly relevant account with 50K followers, verified. Tweets about AI and machine learning topics related to your search."

  good_match (1 sentence):
    GOOD: "Data engineer at Shopify who occasionally shares thoughts on ETL pipeline design."
    BAD: "Relevant account that discusses data engineering. Has 12K followers."

  exclude: empty string.
- **highlight_tweet_indices**: 0-based indices of the 2-3 most relevant tweets (empty for exclude)

Return accounts with top_match first, then strong_match, then good_match, then exclude.

## Accounts to Evaluate
{accounts_json}
"""


V2_FALLBACK_PROMPT = """The seed & expand search for the following request didn't find enough accounts. Generate 3 broader queries to expand the search.

## Original Request
Persona: {persona}
Topic: {topic}
Goal: {goal}

## What We Tried
Seeds found: {seeds_found}
Expansion yielded: {expansion_count} candidates
After filtering: {filtered_count} results

## Instructions
Generate 3 BROADER queries that:
- Use more general terms
- Try adjacent communities or topics
- Still follow Twitter search rules (quoted phrase alone or + 1 keyword)

Use the fallback_queries tool to respond."""


def format_v2_search_plan_prompt(who: str, why: str | None = None) -> str:
    """Format the V2 search plan prompt."""
    why_section = f"Why (context): {why}" if why else "Why (context): Not provided"
    return V2_SEARCH_PLAN_PROMPT.format(who=who, why_section=why_section)


def format_v2_ranking_prompt(
    intent: SearchIntent,
    accounts_json: str,
    seed_count: int,
    discovery_sources: str,
) -> str:
    """Format the V2 ranking prompt with discovery context."""
    key_signals = "\n".join(f"- {s}" for s in intent.key_signals) if intent.key_signals else "- (none specified)"
    anti_signals = "\n".join(f"- {s}" for s in intent.anti_signals) if intent.anti_signals else "- (none specified)"

    if intent.mandatory_terms:
        terms_str = ", ".join(f'"{t}"' for t in intent.mandatory_terms)
        mandatory_terms_section = f"""## Key Relevance Terms

Key terms for this search: {terms_str}

Accounts that mention these terms in their bio, tweets, or handle are significantly more likely to be relevant."""
    else:
        mandatory_terms_section = """## Search Scope

Broad category search — match on overall relevance."""

    return V2_RANKING_PROMPT.format(
        persona=intent.persona,
        topic=intent.topic,
        goal=intent.goal,
        specificity=intent.specificity,
        key_signals=key_signals,
        anti_signals=anti_signals,
        mandatory_terms_section=mandatory_terms_section,
        seed_count=seed_count,
        discovery_sources=discovery_sources,
        accounts_json=accounts_json,
    )


def format_v2_fallback_prompt(
    intent: SearchIntent,
    seeds_found: int,
    expansion_count: int,
    filtered_count: int,
) -> str:
    """Format the V2 fallback prompt."""
    return V2_FALLBACK_PROMPT.format(
        persona=intent.persona,
        topic=intent.topic,
        goal=intent.goal,
        seeds_found=seeds_found,
        expansion_count=expansion_count,
        filtered_count=filtered_count,
    )
