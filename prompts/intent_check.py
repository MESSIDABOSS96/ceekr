"""Prompt template for fast intent extraction + clarification question generation."""


INTENT_CHECK_PROMPT = """Analyze this search request and determine if it's specific enough to produce high-quality Twitter search results.

## User's Request
"{query}"

## Specificity Scale
- 1: "people in tech" — too broad to search meaningfully
- 2: "AI researchers" — broad but has direction
- 3: "ML engineers discussing LLM fine-tuning" — moderate
- 4: "founders who've discussed customer discovery for B2B SaaS" — specific
- 5: "YC founders who pivoted from consumer to enterprise in 2024" — very specific

## Instructions

1. Extract the intent: who they want to find (persona), what topic, and why (infer if not stated).

2. Rate specificity 1-5 based on the scale above.

3. If specificity < 4, generate 2-3 clarification questions that would help narrow the search. Each question should:
   - Target what's MISSING or VAGUE in the query
   - Be short and direct (e.g. "What industry?" not "What industry are you interested in?")
   - Include a short placeholder hint showing the kind of answer expected (e.g. "fintech, climate tech, healthcare")

   Good questions target: role/persona type, specific sub-topic or focus area, goal/use case, time frame, geography, or experience level.

4. If specificity >= 4, return an empty list of clarification questions.

Use the check_intent tool to respond."""


INTENT_CHECK_TOOL = {
    "name": "check_intent",
    "description": "Extract search intent and generate clarification questions if needed",
    "input_schema": {
        "type": "object",
        "properties": {
            "persona": {
                "type": "string",
                "description": "The type of person to find",
            },
            "topic": {
                "type": "string",
                "description": "What they should be discussing or involved in",
            },
            "goal": {
                "type": "string",
                "description": "Why the user wants to find them (infer if not stated)",
            },
            "specificity": {
                "type": "integer",
                "description": "How specific the request is (1-5)",
                "minimum": 1,
                "maximum": 5,
            },
            "clarification_questions": {
                "type": "array",
                "description": "2-3 questions to help narrow a vague search (empty if specificity >= 4)",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "A short question targeting what's missing",
                        },
                        "placeholder": {
                            "type": "string",
                            "description": "Short hint showing example answers, e.g. 'fintech, climate tech, healthcare'",
                        },
                    },
                    "required": ["question", "placeholder"],
                },
            },
        },
        "required": [
            "persona",
            "topic",
            "goal",
            "specificity",
            "clarification_questions",
        ],
    },
}


def format_intent_check_prompt(query: str) -> str:
    """Format the intent check prompt with the user's query."""
    return INTENT_CHECK_PROMPT.format(query=query)
