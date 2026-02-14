"""Prompt for generating Twitter search queries."""

from core.models import SearchIntent

QUERY_GENERATION_PROMPT = """You are an expert at finding relevant people on Twitter. Given a structured description of who the user wants to find, generate Twitter search queries that will surface the most relevant accounts.

## Twitter Search Rules (CRITICAL - read carefully)
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

## User's Request (Structured)
Persona: {persona}
Topic: {topic}
Goal: {goal}
Specificity: {specificity}/5

## Key Signals to Target
These are specific things that confirm someone is the right match. Design queries that surface tweets containing these signals:
{key_signals}

## Anti-Signals (Avoid)
These indicate NOT the right person. Avoid queries that mainly attract these:
{anti_signals}

## Your Task
Generate exactly {query_count} search queries covering these 6 diversity categories:

1. **Pain points**: People complaining, struggling, or asking for help with the topic
2. **Identity/role**: Queries that target the persona directly (role + topic)
3. **Tool/methodology**: People discussing specific tools, frameworks, or methods related to the topic
4. **Achievement/sharing**: People celebrating wins, sharing results, or posting learnings
5. **Community/events**: Conference mentions, community discussions, meetups
6. **Contrarian/debate**: Hot takes, disagreements, or strong opinions on the topic

Spread queries across these categories. Not every category needs a query, but aim for diversity — queries that all use the same phrasing will return the same results.
{niche_instruction}
Each query should:
- Be a quoted phrase ALONE, or a quoted phrase + ONE extra keyword. Nothing more.
- Target a different angle/phrasing to maximize coverage
- NEVER use parentheses, NEVER combine more than 3 total terms
- Avoid common spam triggers (giveaway, follow4follow, etc.)
- Include -job -hiring -giveaway as negative keywords when relevant

Remember: these queries cast a wide net. A separate ranking step will filter for relevance, so strongly favor recall over precision. A broad query that returns results is infinitely better than a precise query that returns nothing.

Generate exactly {query_count} search queries that will find these people through their tweets."""


def format_query_prompt(intent: SearchIntent) -> str:
    """Format the query generation prompt with structured intent."""
    niche_instruction = ""
    if intent.specificity <= 3:
        niche_instruction = (
            "\nIMPORTANT: Since this is a broad search, include at least one query "
            "targeting a specific subcommunity or niche within the broader area. "
            "This helps surface focused accounts that broad queries miss.\n"
        )

    key_signals = "\n".join(f"- {s}" for s in intent.key_signals) if intent.key_signals else "- (none provided)"
    anti_signals = "\n".join(f"- {s}" for s in intent.anti_signals) if intent.anti_signals else "- (none provided)"

    return QUERY_GENERATION_PROMPT.format(
        persona=intent.persona,
        topic=intent.topic,
        goal=intent.goal,
        specificity=intent.specificity,
        query_count=intent.suggested_query_count,
        niche_instruction=niche_instruction,
        key_signals=key_signals,
        anti_signals=anti_signals,
    )
