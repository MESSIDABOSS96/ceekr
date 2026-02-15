"""Combined prompt for intent analysis + query generation in a single LLM call."""

from typing import Optional

SEARCH_PLAN_PROMPT = """Analyze this search request and create a complete search plan: both understanding the intent AND generating Twitter search queries.

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
Examples:
- If looking for practitioners: ["only retweets news articles without commentary", "bio is purely promotional/marketing", "tweets are all job postings or hiring"]
- If looking for founders: ["works at large corporation in non-founder role", "only shares motivational quotes", "account is a news aggregator or bot"]

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

## Part 2: Generate 8 Twitter Search Queries

Always generate exactly 8 search queries.

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

### Diversity Angles
Spread your 8 queries across these categories for maximum coverage:
1. **Pain points**: People complaining, struggling, or asking for help with the topic
2. **Identity/role**: Queries that target the persona directly (role + topic)
3. **Tool/methodology**: People discussing specific tools, frameworks, or methods related to the topic
4. **Achievement/sharing**: People celebrating wins, sharing results, or posting learnings
5. **Community/debate**: Hot takes, disagreements, conference mentions, or community discussions
6. **Help/advice**: People seeking or giving advice, recommendations, or guidance on the topic
7. **Contrarian/critical**: Skeptical takes, criticisms, "unpopular opinion" style tweets about the topic
8. **Building/shipping**: People announcing launches, demos, side projects, or work-in-progress related to the topic

Each query should:
- Be a quoted phrase ALONE, or a quoted phrase + ONE extra keyword. Nothing more.
- Target a different angle/phrasing to maximize coverage
- NEVER use parentheses, NEVER combine more than 3 total terms
- Avoid common spam triggers (giveaway, follow4follow, etc.)

Remember: these queries cast a wide net. A separate ranking step will filter for relevance, so strongly favor recall over precision.

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
    return SEARCH_PLAN_PROMPT.format(who=who, why_section=why_section)


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
