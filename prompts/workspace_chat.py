"""Prompt and tool schemas for the workspace chat agent."""

from typing import Optional

WORKSPACE_CHAT_SYSTEM_PROMPT = """You are a research assistant for a Twitter people-finding workspace. The user ran a search and you're helping them analyze and refine the results.

## Workspace context
Original query: "{query}"
Total people found: {total_people}
Result quality: {quality}
Summary: {summary}

## Journals (groups of people)
{journals_context}

## What you can do
1. Analyze patterns, trends, and commonalities across results
2. Explain why specific people were included
3. Filter or remove results
4. Run targeted searches to find more specific people
5. Re-organize journals along different dimensions

## Efficiency rules
- For analysis questions: reason over existing data. Don't search.
- For "show me more like X": prefer filtering existing results first.
- Only use run_targeted_search when existing data genuinely can't answer the request.
- Keep responses concise (2-4 sentences unless analysis requires more).

## Tool usage
Use EXACTLY ONE tool in every response. Pick the most appropriate:
- `respond` for analysis, explanations, suggestions, or conversational replies
- `apply_filters` to filter current results by criteria (follower count, keywords, etc.)
- `remove_profiles` to remove specific people by handle
- `run_targeted_search` ONLY when the user wants people not already in the workspace
- `regroup_journals` to re-cluster people along a different dimension"""


WORKSPACE_CHAT_TOOLS = [
    {
        "name": "respond",
        "description": "Send a conversational response — for analysis, explanations, suggestions, or general replies",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The response message to show the user",
                },
            },
            "required": ["message"],
        },
    },
    {
        "name": "apply_filters",
        "description": "Filter current results by criteria like follower count, keywords in bio, location, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to show the user about what filters were applied",
                },
                "filters": {
                    "type": "object",
                    "description": "Partial filter object — only include fields to change",
                    "properties": {
                        "min_followers": {"type": "integer", "description": "Minimum follower count"},
                        "max_followers": {"type": "integer", "description": "Maximum follower count"},
                        "bio_keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Keywords that must appear in bio",
                        },
                        "location": {"type": "string", "description": "Location filter"},
                    },
                },
            },
            "required": ["message", "filters"],
        },
    },
    {
        "name": "remove_profiles",
        "description": "Remove specific people from the workspace by their Twitter handle",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to show the user",
                },
                "handles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Twitter handles to remove (without @)",
                },
            },
            "required": ["message", "handles"],
        },
    },
    {
        "name": "run_targeted_search",
        "description": "Run 1-2 focused Twitter searches to find more people. Only use when existing data can't satisfy the request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to show the user about what you're searching for",
                },
                "search_description": {
                    "type": "string",
                    "description": "Description of who to find — will be used to generate targeted Twitter queries",
                },
            },
            "required": ["message", "search_description"],
        },
    },
    {
        "name": "regroup_journals",
        "description": "Re-organize people into new journal groups along a different dimension",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to show the user about the regrouping",
                },
                "new_axis_description": {
                    "type": "string",
                    "description": "How to regroup — e.g. 'by industry', 'by career stage', 'by geographic region'",
                },
            },
            "required": ["message", "new_axis_description"],
        },
    },
]


def format_workspace_chat_prompt(
    query: str,
    total_people: int,
    quality: str,
    summary: str,
    journals_context: str,
) -> str:
    """Format the workspace chat system prompt with workspace context."""
    return WORKSPACE_CHAT_SYSTEM_PROMPT.format(
        query=query,
        total_people=total_people,
        quality=quality,
        summary=summary,
        journals_context=journals_context,
    )


def build_journals_context(
    journals: list[dict],
    active_journal_id: Optional[str] = None,
    active_journal_people: Optional[list[dict]] = None,
) -> str:
    """Build the journals context string for the system prompt.

    For the active journal: includes enriched summaries of all people.
    For other journals: just label + count + description.
    """
    lines = []
    for j in journals:
        jid = j.get("id", "")
        label = j.get("label", "Untitled")
        desc = j.get("description", "")
        count = j.get("people_count", 0)

        if jid == active_journal_id and active_journal_people:
            lines.append(f'- "{label}" ({count} people, ACTIVE): {desc}')
            lines.append("  People in this journal:")
            for p in active_journal_people:
                handle = p.get("handle", "?")
                name = p.get("name", "")
                bio = (p.get("bio") or "")[:100]
                summary = (p.get("summary") or "")[:120]
                followers = p.get("followers_count", 0)
                parts = [f"  @{handle} ({name})"]
                if bio:
                    parts.append(f'bio: "{bio}"')
                if summary:
                    parts.append(f'summary: "{summary}"')
                parts.append(f"{followers:,} followers")
                lines.append(" | ".join(parts))
        else:
            lines.append(f'- "{label}" ({count} people): {desc}')

    return "\n".join(lines) if lines else "No journals yet."
