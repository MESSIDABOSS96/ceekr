"""Prompt for clustering search results into semantic journals along a single axis."""

from core.models import SearchIntent


JOURNAL_GENERATION_TOOL = {
    "name": "create_journals",
    "description": "Organize search results into exclusive groups (journals) along the specified axis",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "1-2 sentence executive summary of all results. What did we find?",
            },
            "journals": {
                "type": "array",
                "description": "2-7 groups along the specified axis. Each person in EXACTLY one group.",
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
        "required": ["summary", "journals"],
    },
}


def format_journal_generation_prompt(
    intent: SearchIntent,
    condensed_accounts: str,
    axis_label: str,
    example_groups: list[str],
) -> str:
    examples_str = ", ".join(f'"{g}"' for g in example_groups) if example_groups else "use your judgment"
    return f"""You are organizing Twitter search results into meaningful groups called "journals" to directly serve the user's goal.

## Search Context
- **Looking for**: {intent.persona}
- **Topic**: {intent.topic}
- **Goal**: {intent.goal}

## Goal-Driven Grouping
The user's GOAL determines how labels should read. Journal labels must help the user achieve their stated goal — not just categorize people generically. Generic labels like role seniority or thought leadership are almost never useful.

## Grouping Axis
Group ONLY along: **{axis_label}**
Example groups (for guidance, you may adjust labels): {examples_str}

## People Found
{condensed_accounts}

## Instructions
Create 2-7 journals along the specified axis. CRITICAL RULES:
- Every person must appear in EXACTLY ONE journal. No duplicates. No one left out.
- All journals must slice along the same dimension: {axis_label}
- If someone doesn't fit neatly, assign them to the closest matching journal
- Labels should be specific and descriptive (not generic like "Other" or "Miscellaneous")
- For small result sets (<8 people), prefer fewer journals (2-3)
- For larger sets (15+), use more journals (4-7) to add structure
- Each journal needs at least 2 people (if possible — a singleton is OK as a last resort)

Use the create_journals tool to output your groupings."""
