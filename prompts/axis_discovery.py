"""Prompt for discovering grouping axes from search results."""

from core.models import SearchIntent


AXIS_DISCOVERY_TOOL = {
    "name": "discover_axes",
    "description": "Discover 2-4 meaningful axes for grouping these people. Each axis is a single dimension that slices ALL people into distinct groups.",
    "input_schema": {
        "type": "object",
        "properties": {
            "axes": {
                "type": "array",
                "description": "2-4 grouping axes, each a single dimension",
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
                "description": "axis_key of the best default axis",
            },
            "recommendation_reason": {
                "type": "string",
                "description": "1 sentence explaining why this axis is the best default",
            },
        },
        "required": ["axes", "recommended_axis_key", "recommendation_reason"],
    },
}


def format_axis_discovery_prompt(intent: SearchIntent, enriched_accounts: str) -> str:
    return f"""You are analyzing search results to find the best ways to group these people.

## Search Context
- **Looking for**: {intent.persona}
- **Topic**: {intent.topic}
- **Goal**: {intent.goal}

## People Found
{enriched_accounts}

## Task
Discover 2-4 meaningful **grouping axes**. Each axis is a SINGLE dimension that slices ALL people into distinct groups.

Rules:
- Each axis must be a single coherent dimension (e.g. "role", "topic focus", "geography") — never mix dimensions within one axis.
- Example groups within an axis must be mutually exclusive — every person fits in exactly one group per axis.
- Axes should be different from each other (don't propose "by role" and "by job title" — those are the same dimension).
- Choose axes that create balanced groups (avoid axes where 80% of people would land in one group).
- Prefer axes that are actionable and useful for the searcher's goal.

Pick the axis that creates the most balanced, distinct, and actionable grouping as the recommended default.

Use the discover_axes tool."""
