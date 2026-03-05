"""Combined prompt for axis discovery + journal generation in a single LLM call."""

from core.models import SearchIntent


COMBINED_GROUPING_TOOL = {
    "name": "group_results",
    "description": "Discover the best grouping axis and organize people into journals along it — all in one step.",
    "input_schema": {
        "type": "object",
        "properties": {
            "axes": {
                "type": "array",
                "description": "2-4 candidate grouping axes (dimensions)",
                "items": {
                    "type": "object",
                    "properties": {
                        "axis_key": {
                            "type": "string",
                            "description": "Snake_case identifier, e.g. 'contribution_area', 'career_stage'",
                        },
                        "axis_label": {
                            "type": "string",
                            "description": "Human-readable label, e.g. 'By contribution area'",
                        },
                        "example_groups": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "2-5 preview group names if this axis were chosen",
                        },
                    },
                    "required": ["axis_key", "axis_label", "example_groups"],
                },
            },
            "recommended_axis_key": {
                "type": "string",
                "description": "axis_key of the best default axis (must match one of the axes above)",
            },
            "recommendation_reason": {
                "type": "string",
                "description": "1 sentence explaining why this axis is the best default",
            },
            "summary": {
                "type": "string",
                "description": "1-2 sentence executive summary of all results. What did we find?",
            },
            "journals": {
                "type": "array",
                "description": "2-7 groups along the RECOMMENDED axis. Each person in EXACTLY one group.",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string",
                            "description": "Short label (2-5 words), e.g. 'NLP at NYU/Columbia', 'Open Source Tool Builders'",
                        },
                        "description": {
                            "type": "string",
                            "description": "1 sentence explaining what unites this group",
                        },
                        "handles": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Twitter handles of people in this group (without @)",
                        },
                        "journal_notes": {
                            "type": "object",
                            "description": "Map of handle -> short note explaining why they belong in this journal",
                            "additionalProperties": {"type": "string"},
                        },
                    },
                    "required": ["label", "description", "handles", "journal_notes"],
                },
            },
        },
        "required": ["axes", "recommended_axis_key", "recommendation_reason", "summary", "journals"],
    },
}


def format_combined_grouping_prompt(intent: SearchIntent, enriched_accounts: str) -> str:
    key_signals_str = ", ".join(intent.key_signals) if intent.key_signals else "none"
    return f"""You are organizing Twitter search results to directly serve the user's goal. Do TWO things in one pass:

**Part 1 — Discover grouping axes:** Find 2-4 dimensions that would help the user achieve their goal.
**Part 2 — Generate journals:** Pick the BEST axis and cluster people into journals along it.

## Search Context
- **Looking for**: {intent.persona}
- **Topic**: {intent.topic}
- **Goal**: {intent.goal}
- **Specificity**: {intent.specificity}/5
- **Key signals**: {key_signals_str}

## People Found
{enriched_accounts}

## Axis Selection Priority
The user's GOAL determines the best axis. Ask: "What grouping would help this person achieve their goal?"
- Goal: "understand what types of companies YC is funding" → axis: "By company vertical" (AI, Fintech, DevTools)
- Goal: "find people to hire for my ML team" → axis: "By specialization" (NLP, Computer Vision, MLOps)
- Goal: "network with founders in my city" → axis: "By stage/focus" (Pre-seed, Series A, B2B SaaS)
The axis should answer the user's question, not just categorize people generically.

## Axis Discovery Rules
- Each axis is a SINGLE coherent dimension (e.g. "role", "topic focus", "geography").
- Axes must be different from each other.
- Choose axes that create balanced groups (avoid 80% in one group).
- CRITICAL: The axes and journal labels must help the user achieve their stated goal. Generic categorizations like role seniority or thought leadership are almost never useful. Use concrete, goal-grounded labels like "YC W24 Batch" or "AI/ML Founders", NOT abstract labels like "Strategic Thought Leaders" or "Community Builders".

## Examples (good vs bad)
Search: "YC founders" | Goal: "understand what YC is funding right now"
✓ "AI Infrastructure", "Fintech & Payments", "Developer Tools", "Health Tech"
✗ "Strategic Thought Leaders", "Early-Stage Innovators", "Community Builders"

Search: "ML engineers" | Goal: "hire for my NLP team"
✓ "NLP & Language Models", "Computer Vision", "MLOps & Infra"
✗ "Senior Practitioners", "Rising Stars", "Industry Veterans"

## Journal Generation Rules (apply to the recommended axis)
- Every person in AT MOST one journal. No duplicates. You MAY omit people who don't clearly match the search persona "{intent.persona}".
- Do NOT create catch-all journals like "Other", "Miscellaneous", or "Observers & Adjacent". If someone doesn't fit a meaningful group, leave them out.
- Labels should be specific and descriptive.
- For small result sets (<8 people), prefer fewer journals (2-3).
- For larger sets (15+), use more journals (4-7).
- Each journal needs at least 2 people (singleton OK as last resort).

Use the group_results tool."""
