"""Prompt for fast triage of accounts before full ranking."""

from core.models import SearchIntent

TRIAGE_PROMPT = """Quickly decide which Twitter accounts should advance to detailed evaluation.

## User is looking for
Persona: {persona}
Topic: {topic}
Goal: {goal}

## Key Signals
{key_signals}

## Anti-Signals
{anti_signals}

{mandatory_terms_section}

## Instructions
For each account, decide: "advance" (worth evaluating in detail) or "skip" (clearly irrelevant).

ERR ON THE SIDE OF ADVANCING. Only skip accounts that are obviously wrong:
- Completely unrelated to the topic (e.g., food blogger when looking for ML engineers)
- Clear spam/bot accounts
- Anti-signal matches
- Account shows NO connection to any mandatory term (if mandatory terms are specified)

If in doubt, advance. The next step will do careful ranking.

## Accounts
{accounts_json}
"""


def format_triage_prompt(intent: SearchIntent, accounts_json: str) -> str:
    """Format the triage prompt."""
    key_signals = "\n".join(f"- {s}" for s in intent.key_signals) if intent.key_signals else "- (none specified)"
    anti_signals = "\n".join(f"- {s}" for s in intent.anti_signals) if intent.anti_signals else "- (none specified)"

    if intent.mandatory_terms:
        terms_str = ", ".join(f'"{t}"' for t in intent.mandatory_terms)
        mandatory_terms_section = f"""## Mandatory Terms
Mandatory terms: {terms_str}
Skip accounts that show NO connection to any of these terms in their name, bio, or tweet."""
    else:
        mandatory_terms_section = ""

    return TRIAGE_PROMPT.format(
        persona=intent.persona,
        topic=intent.topic,
        goal=intent.goal,
        key_signals=key_signals,
        anti_signals=anti_signals,
        mandatory_terms_section=mandatory_terms_section,
        accounts_json=accounts_json,
    )
