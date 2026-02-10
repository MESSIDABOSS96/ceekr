"""Prompt for ranking Twitter accounts by relevance."""

from core.models import SearchIntent

RANKING_PROMPT = """You are an expert at evaluating whether Twitter accounts are relevant for a specific purpose. Analyze the provided accounts and rank them by relevance.

## User's Goal (Structured)
Looking for: {persona}
Who discuss: {topic}
Purpose: {goal}

## Relevance Score (1-10)
Score each account on a 1-10 scale. This is the ONLY score.

Scoring anchors:
- 9-10: EXCEPTIONAL. Exactly the persona described, actively and recently
  discussing the exact topic. Bio, tweets, and focus are a near-perfect match.
  Reserve for <5% of accounts.
- 7-8: STRONG. Right persona, clearly discussed related topics recently.
  Someone the user would definitely want to connect with.
- 5-6: MODERATE. Right general area but not a direct match. Right persona
  but wrong topic, or right topic but different persona.
- 3-4: WEAK. Tangential connection at best. Keyword matched but not truly
  the target audience.
- 1-2: POOR. Irrelevant or spam.

Factors to weigh (bake into your 1-10 score, do NOT add separate modifiers):
- Recency: actively discussing the topic recently (check tweet dates) -> score higher
- Accessibility: >500K followers are hard to engage -> slight penalty
- Activity: <100 followers may be inactive/bot -> slight penalty
- Query overlap: appeared in multiple search queries -> likely more relevant

Distribution guidance: most accounts should score 3-6. Only truly exceptional
matches get 8+. If most accounts score 7+, you are being too generous.

### Scoring Examples
If the user is looking for "founders discussing customer discovery":
- Score 9: Bio: "Building [SaaS]. Failed 2 startups." Tweets: "Just did 30
  customer interviews and changed our product direction"
- Score 6: Bio: "Product Manager at BigCorp." Tweets: "Customer research
  is underrated in product development"
- Score 3: Bio: "Tech news." Tweets: Shared article about customer discovery
- Score 1: Bio: "Web3 enthusiast." Tweet mentioned "discovery" in unrelated context

### Step by Step
For each account:
1. Read bio — does this person match the persona?
2. Read tweets — are they DISCUSSING the topic or just mentioning it?
3. Consider recency — recent active discussion vs. one mention long ago? (check tweet dates)
4. Assign score using the anchors above
5. Write score_reasoning explaining your judgment in 1 sentence
   (e.g., "Strong persona match and recent relevant tweets, mid-size accessible account")
6. Write why_relevant explaining their value to the user in 1-2 sentences
7. Optionally suggest an approach for engaging with them

Return accounts sorted by score (highest first).

## Quality Assessment
After scoring all accounts, assess the overall result quality:
- If 3+ accounts scored 7+: quality is "strong" — no clarification needed
- If fewer than 3 scored 7+ but 5+ scored 5+: quality is "moderate" — no clarification needed
- Otherwise: quality is "weak" — suggest 1-2 clarifying questions

If quality is "weak", your clarifying questions should be SPECIFIC and based on
what you actually found in the accounts. For example:
- "I found several AI researchers but most focus on NLP. Are you specifically
  looking for NLP researchers, or another subfield?"
- "Most accounts I found are large influencers (>100K followers). Would you
  prefer smaller, more accessible accounts?"

## Accounts to Rank
{accounts_json}
"""


def format_ranking_prompt(intent: SearchIntent, accounts_json: str) -> str:
    """Format the ranking prompt with structured intent and accounts."""
    return RANKING_PROMPT.format(
        persona=intent.persona,
        topic=intent.topic,
        goal=intent.goal,
        accounts_json=accounts_json,
    )
