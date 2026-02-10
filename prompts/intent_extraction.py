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

**specificity** (1-5): How specific is this request?
- 1: "people in tech" — too broad to search meaningfully
- 2: "AI researchers" — broad but has direction
- 3: "ML engineers discussing LLM fine-tuning" — moderate
- 4: "founders who've discussed customer discovery for B2B SaaS" — specific
- 5: "YC founders who pivoted from consumer to enterprise in 2024" — very specific

**is_clear**: Set to False ONLY if specificity=1. For specificity>=2, set to True.

If is_clear is False, provide 1-2 focused clarifying questions that would raise the specificity to at least 3.

**suggested_query_count**: How many Twitter search queries to generate.
- Specificity 1-2 (broad): 6-7 queries to cast a wide net
- Specificity 3 (moderate): 4-5 queries
- Specificity 4-5 (specific): 3 queries (focused is better)

Use the extract_intent tool to respond."""


def format_intent_prompt(who: str, why: Optional[str] = None) -> str:
    """Format the intent extraction prompt with user input."""
    why_section = f"Why (context): {why}" if why else "Why (context): Not provided"
    return INTENT_EXTRACTION_PROMPT.format(who=who, why_section=why_section)
