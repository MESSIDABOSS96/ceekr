"""Prompt for extracting structured intent from user search requests."""

from typing import Optional

INTENT_EXTRACTION_PROMPT = """Analyze this search request and extract structured intent for finding Twitter accounts.

## User's Request
Who they want to find: {who}
{why_section}

## Instructions

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

**is_clear**: Set to False ONLY if specificity=1. For specificity>=2, set to True.

If is_clear is False, provide 1-2 focused clarifying questions that would raise the specificity to at least 3.

**suggested_query_count**: How many Twitter search queries to generate (3-12).
- Specificity 1-2 (broad): 10-12 queries to cast a wide net
- Specificity 3 (moderate): 7-10 queries
- Specificity 4-5 (specific): 3-6 queries (focused is better)

**min_score_threshold**: Minimum relevance score (3-8) to include in results.
- Specificity 2: threshold 4 (broad search, lower bar)
- Specificity 3: threshold 5
- Specificity 4: threshold 6
- Specificity 5: threshold 7 (specific search, higher bar)

Use the extract_intent tool to respond."""


def format_intent_prompt(who: str, why: Optional[str] = None) -> str:
    """Format the intent extraction prompt with user input."""
    why_section = f"Why (context): {why}" if why else "Why (context): Not provided"
    return INTENT_EXTRACTION_PROMPT.format(who=who, why_section=why_section)
