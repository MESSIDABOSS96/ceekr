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
    return f"""You are organizing Twitter search results for a user. Do TWO things in one pass:

**Part 1 — Discover grouping axes:** Find 2-4 meaningful dimensions that could slice these people into groups.
**Part 2 — Generate journals:** Pick the BEST axis and actually cluster people into journals along it.

## Search Context
- **Looking for**: {intent.persona}
- **Topic**: {intent.topic}
- **Goal**: {intent.goal}
- **Specificity**: {intent.specificity}/5
- **Key signals**: {key_signals_str}

## People Found
{enriched_accounts}

## Axis Discovery Rules
- Each axis is a SINGLE coherent dimension (e.g. "role", "topic focus", "geography").
- Axes must be different from each other.
- Choose axes that create balanced groups (avoid 80% in one group).
- Prefer axes that are actionable and useful for the searcher's goal.
- CRITICAL: Axes and journal labels must directly relate to "{intent.topic}" and "{intent.goal}". Do NOT generate abstract/generic labels like "Strategic Thought Leaders" — use concrete, intent-grounded labels like "YC W24 Batch" or "AI/ML Founders".

## Journal Generation Rules (apply to the recommended axis)
- Every person in AT MOST one journal. No duplicates. You MAY omit people who don't clearly match the search persona "{intent.persona}".
- Do NOT create catch-all journals like "Other", "Miscellaneous", or "Observers & Adjacent". If someone doesn't fit a meaningful group, leave them out.
- Labels should be specific and descriptive.
- For small result sets (<8 people), prefer fewer journals (2-3).
- For larger sets (15+), use more journals (4-7).
- Each journal needs at least 2 people (singleton OK as last resort).

Use the group_results tool."""
