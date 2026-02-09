"""Prompt for generating Twitter search queries."""

from typing import Optional

QUERY_GENERATION_PROMPT = """You are an expert at finding relevant people on Twitter. Given a user's description of who they want to find, generate 3-5 Twitter search queries that will surface the most relevant accounts.

## Twitter Search Tips
- Use quotes for exact phrases: "user interviews"
- Use OR for alternatives: pain OR frustrating OR difficult
- Use - to exclude: tools -job -hiring
- Combine operators: "customer discovery" founder OR startup
- Think about different ways people phrase the same concept
- Consider different communities that might discuss the topic

## Your Task
Generate search queries from different angles:
1. Direct pain point expressions (people complaining/struggling)
2. Topic + persona combinations (founders discussing X, researchers on Y)
3. Tool/solution discussions (people discussing alternatives)
4. Process/methodology mentions (how people approach the problem)
5. Outcome-focused (people celebrating success or analyzing failure)

Each query should:
- Target a different angle/phrasing
- Be specific enough to find relevant tweets
- Not be so narrow it returns nothing
- Avoid common spam triggers (giveaway, follow4follow, etc.)

## User's Request
Who they want to find: {who}
{why_section}

Generate 3-5 search queries that will find these people through their tweets."""


def format_query_prompt(who: str, why: Optional[str] = None) -> str:
    """Format the query generation prompt with user input."""
    why_section = f"Why (context): {why}" if why else "Why (context): Not provided"
    return QUERY_GENERATION_PROMPT.format(who=who, why_section=why_section)
