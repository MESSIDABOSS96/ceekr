"""Prompt for ranking Twitter accounts by relevance."""

from typing import Optional

RANKING_PROMPT = """You are an expert at evaluating whether Twitter accounts are relevant for a specific purpose. Analyze the provided accounts and rank them by relevance.

## User's Goal
Who they want to find: {who}
{why_section}

## Scoring System

### Base Score: Content Relevance (1-10)
Evaluate how well the account matches what the user is looking for:
- 9-10: Perfect match - exactly the persona described, actively discussing the topic
- 7-8: Strong match - right persona, has discussed related topics
- 5-6: Moderate match - somewhat relevant, tangentially connected
- 3-4: Weak match - only loosely related
- 1-2: Poor match - barely relevant

### Score Boosters (add to base score)
- Account is followed by the searcher: +1.5
- Account follows the searcher: +2.0
- Has mutual connections: +0.5
- Tweeted about topic in last 30 days: +1.0
- Tweeted about topic in last 90 days: +0.5

### Score Penalties (subtract from base score)
- >500K followers (hard to reach): -0.5
- >100K followers: -0.25
- <100 followers (might be inactive/bot): -0.5
- <500 followers: -0.1
- Last relevant tweet >1 year ago: -1.0

## Your Task
For each account:
1. Assess base content relevance (1-10)
2. Apply boosters and penalties
3. Calculate final score
4. Write a brief "why relevant" explanation (1-2 sentences)
5. Optionally suggest an approach for engaging with them

Return accounts sorted by final score (highest first).

## Accounts to Rank
{accounts_json}
"""


def format_ranking_prompt(who: str, why: Optional[str], accounts_json: str) -> str:
    """Format the ranking prompt with user input and accounts."""
    why_section = f"Why (context): {why}" if why else "Why (context): Not provided"
    return RANKING_PROMPT.format(
        who=who,
        why_section=why_section,
        accounts_json=accounts_json,
    )
