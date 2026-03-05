"""Combined prompt for intent analysis + query generation in a single LLM call."""

from datetime import date
from typing import Optional

SEARCH_PLAN_PROMPT = """Analyze this search request and create a complete search plan: both understanding the intent AND generating Twitter search queries.

Today's date: {today}

## User's Request
Who they want to find: {who}
{why_section}

## Part 1: Analyze the Request

Decompose the request into structured fields:

**persona**: The type of person they're looking for (e.g., "early-stage SaaS founders", "ML researchers")
**topic**: What these people should be discussing/involved in (e.g., "customer discovery challenges", "LLM fine-tuning")
**goal**: Why the user wants to find them (infer if not stated)

**key_signals**: 3-5 SPECIFIC things to look for in tweets/bios that confirm this person matches.
These should be concrete, observable signals — not abstract qualities.
Examples:
- If looking for "ML engineers fine-tuning LLMs": ["mentions LoRA, QLoRA, or PEFT", "discusses training loss or evaluation metrics", "shares model benchmarks or comparisons", "bio mentions ML/AI engineering role", "tweets about GPU/compute costs"]
- If looking for "founders doing customer discovery": ["describes doing user interviews", "mentions pivoting based on feedback", "discusses problem-solution fit", "bio says founder/CEO/building", "shares learnings from talking to customers"]

**anti_signals**: 2-3 things that indicate this is NOT the right person.
IMPORTANT: Always include at least one signal for "adjacent but wrong persona" — people who interact with the target world but aren't the target persona themselves.
Examples:
- If looking for "YC founders": ["VC/investor who funds YC companies but didn't found one", "YC partner or staff member", "journalist covering YC startups"]
- If looking for practitioners: ["only retweets news articles without commentary", "bio is purely promotional/marketing", "tweets are all job postings or hiring"]
- If looking for founders: ["works at large corporation in non-founder role", "VC or investor (not a founder)", "account is a news aggregator or bot"]

**mandatory_terms**: 0-3 niche-specific terms that are the NON-NEGOTIABLE core of this search.

Rules:
- If the query has a SPECIFIC product/project/technology name → that IS a mandatory term
- If the query is inherently broad (e.g., "AI researchers", "founders") → mandatory_terms = []
- Use the NICHE SPECIFIER, not the role. "openclaw researchers" → ["openclaw"], NOT ["researchers"]
- Include reasonable variations (e.g., ["openclaw", "open-claw"])
- Maximum 3 terms

Examples:
- "openclaw researchers" → ["openclaw"]
- "langchain contributors" → ["langchain"]
- "AI researchers" → []
- "founders" → []

**time_constraint**: If the user mentions a time frame, convert to an ISO date (YYYY-MM-DD) for the earliest relevant date.
- "recent" with no qualifier → 6 months back from today
- "last 6 months" → 6 months back from today
- "2024" → "2024-01-01"
- "last year" → beginning of last year
- No time mention → null
Examples (assuming today is {today}):
- "recent YC founders" → 6 months back
- "people who discussed X in the last 6 months" → 6 months back
- "AI researchers" (no time mention) → null

**specificity** (1-5): How specific is this request?
- 1: "people in tech" — too broad to search meaningfully
- 2: "AI researchers" — broad but has direction
- 3: "ML engineers discussing LLM fine-tuning" — moderate
- 4: "founders who've discussed customer discovery for B2B SaaS" — specific
- 5: "YC founders who pivoted from consumer to enterprise in 2024" — very specific

**bio_search_terms**: 3-4 short keyword phrases that would appear in the Twitter bio of the target persona. These are used for direct user/profile searches (not tweet searches). Each should be 1-3 words max.
Examples:
- If looking for "ML engineers fine-tuning LLMs": ["ML engineer", "machine learning", "AI researcher", "deep learning"]
- If looking for "founders doing customer discovery": ["founder", "CEO", "building", "startup"]

## Part 2: Generate Twitter Search Queries

Generate a number of queries based on the specificity you determined above:
- Specificity 1 → 10 queries (broad search needs diverse angles)
- Specificity 2 → 9 queries
- Specificity 3 → 8 queries
- Specificity 4 → 6 queries
- Specificity 5 → 5 queries (specific search needs more angles to find niche people)

### Twitter Search Rules (CRITICAL - read carefully)
Twitter search is very restrictive. Complex queries return ZERO results. Follow these rules strictly:

- A quoted phrase alone OR a quoted phrase + ONE keyword is the max complexity that works.
- NEVER use parentheses. NEVER use more than one OR. NEVER combine more than 3 words total with a quoted phrase.
- Use - to exclude: -job -hiring -giveaway

Examples of queries that WORK:
- "customer discovery" founder        (quoted phrase + 1 keyword = GOOD)
- "user research"                      (just a quoted phrase = GOOD)
- user research                        (unquoted = GOOD, broad)
- "customer interviews" startup        (quoted phrase + 1 keyword = GOOD)

Examples of queries that return ZERO results (DO NOT USE):
- "user research" founder struggles OR challenges   (too many words!)
- "UX research" startup difficult expensive         (too many words!)
- founder "customer interviews" hard time           (too many words!)

### Query Strategy: Think Like a Searcher

For each query, ask yourself: "If I was manually searching Twitter to find this person, what would I type?" Think about how the target person would naturally surface:

1. **Builders/creators**: What they'd say when sharing work ("built with [topic]", "my [topic] project", "shipped" [topic])
2. **Self-identification**: How they describe themselves or their role ("[topic] contributor", "working on [topic]", "maintaining [topic]")
3. **Teaching/explaining**: How they'd share knowledge ("[topic] tutorial", "how to use [topic]", "here's how [topic] works")
4. **Opinions/enthusiasm**: How they'd express views ("love [topic]", "[topic] is", "why [topic]")
5. **Community/events**: How they'd engage with peers ("[topic] community", "[topic]" meetup, "[topic]" release)
6. **Discovery phrases**: How others would mention them ("check out" [topic], "best [topic]", "recommend" [topic])
7. **Experience/struggles**: Hands-on experience signals ("debugging [topic]", "learning [topic]", "migrating to [topic]")
8. **Professional context**: Work-related mentions ("using [topic] at", "[topic] integration", "[topic] in production")

The goal is maximum PRECISION — queries that almost exclusively surface the right people, not broad queries that need heavy filtering afterward.

Each query should:
- Be a quoted phrase ALONE, or a quoted phrase + ONE extra keyword. Nothing more.
- Target a different angle/phrasing to maximize coverage
- NEVER use parentheses, NEVER combine more than 3 total terms
- Avoid common spam triggers (giveaway, follow4follow, etc.)
- If time_constraint is set, append `since:YYYY-MM-DD` to EVERY query. The `since:` operator doesn't count toward the complexity limit. Example: `"YC founder" startup since:2025-09-01`

Remember: if the topic contains specific niche terms (e.g., "openclaw", "customer discovery"), every query MUST include at least one of those specific terms. Never generate queries that only use the generic category (e.g., just "researchers" without "openclaw"). However, if the topic is inherently broad (e.g., "AI researchers", "founders"), broad queries are fine. A separate ranking step will filter for relevance, but it cannot fix queries that are too broad to begin with.

Use the search_plan tool to respond."""


FALLBACK_QUERIES_PROMPT = """The initial search for the following request didn't find enough accounts. Generate 3 broader, more general queries to find more candidates.

## Original Request
Persona: {persona}
Topic: {topic}
Goal: {goal}

## Original Queries (already tried)
{original_queries}

## Current Results
Only found {accounts_found} accounts (need at least 30).

## Instructions
Generate 3 BROADER queries that:
- Use more general terms than the original queries
- Remove niche jargon in favor of common language
- Try different phrasings or adjacent topics
- Still follow Twitter search rules (quoted phrase alone or quoted phrase + 1 keyword)

Use the fallback_queries tool to respond."""


def format_search_plan_prompt(who: str, why: Optional[str] = None) -> str:
    """Format the combined search plan prompt with user input."""
    why_section = f"Why (context): {why}" if why else "Why (context): Not provided"
    return SEARCH_PLAN_PROMPT.format(who=who, why_section=why_section, today=date.today().isoformat())


def format_fallback_prompt(
    intent, original_queries: list[str], accounts_found: int
) -> str:
    """Format the fallback queries prompt."""
    queries_str = "\n".join(f"- {q}" for q in original_queries)
    return FALLBACK_QUERIES_PROMPT.format(
        persona=intent.persona,
        topic=intent.topic,
        goal=intent.goal,
        original_queries=queries_str,
        accounts_found=accounts_found,
    )
