"""LLM layer for Claude API calls."""

import json
from typing import Optional

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

from .models import (
    ClarificationQuestion,
    ClarificationResponse,
    RankedAccount,
    RankingResponse,
    SearchQueriesResponse,
    SearchQuery,
    TwitterAccount,
)
from prompts.query_generation import format_query_prompt
from prompts.ranking import format_ranking_prompt


class LLMClient:
    """Client for Claude API calls with structured output."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = ANTHROPIC_MODEL

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def check_input_clarity(self, who: str, why: Optional[str] = None) -> ClarificationResponse:
        """
        Check if user input is clear enough to search.

        Returns ClarificationResponse with is_clear=True if ready to search,
        or is_clear=False with questions if clarification is needed.
        """
        # Define the tool for structured output
        tools = [
            {
                "name": "assess_clarity",
                "description": "Assess whether the user input is clear enough to search or needs clarification",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "is_clear": {
                            "type": "boolean",
                            "description": "True if the input is clear enough to proceed with search",
                        },
                        "questions": {
                            "type": "array",
                            "description": "Questions to ask if clarification is needed (empty if clear)",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question": {
                                        "type": "string",
                                        "description": "The clarifying question to ask",
                                    },
                                    "reason": {
                                        "type": "string",
                                        "description": "Why this clarification helps",
                                    },
                                },
                                "required": ["question", "reason"],
                            },
                        },
                    },
                    "required": ["is_clear", "questions"],
                },
            }
        ]

        why_text = f"\nWhy/context: {why}" if why else ""
        prompt = f"""Evaluate if this search request is specific enough to find relevant Twitter accounts.

Who they want to find: {who}{why_text}

A request is CLEAR ENOUGH if it has:
1. A clear persona (type of person: founders, researchers, engineers, etc.)
2. A clear topic or keywords (what they should have tweeted about)

A request NEEDS CLARIFICATION if:
- No clear persona (just "people interested in X")
- No clear topic (just "startup founders" with no focus area)
- Extremely broad (just "AI" or "tech")

If clarification is needed, ask 1-2 focused questions. Don't over-ask - if you can make reasonable assumptions, do so.

Use the assess_clarity tool to respond."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            tools=tools,
            tool_choice={"type": "tool", "name": "assess_clarity"},
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract tool use result
        for block in response.content:
            if block.type == "tool_use":
                result = block.input
                return ClarificationResponse(
                    is_clear=result["is_clear"],
                    questions=[
                        ClarificationQuestion(question=q["question"], reason=q["reason"])
                        for q in result.get("questions", [])
                    ],
                )

        # Fallback: assume clear if no tool use
        return ClarificationResponse(is_clear=True, questions=[])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_search_queries(
        self, who: str, why: Optional[str] = None
    ) -> SearchQueriesResponse:
        """
        Generate Twitter search queries based on user input.

        Returns 3-5 search queries from different angles.
        """
        tools = [
            {
                "name": "generate_queries",
                "description": "Generate Twitter search queries to find relevant accounts",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "queries": {
                            "type": "array",
                            "description": "List of 3-5 search queries",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "The Twitter search query string",
                                    },
                                    "rationale": {
                                        "type": "string",
                                        "description": "Why this query helps find relevant people",
                                    },
                                    "angle": {
                                        "type": "string",
                                        "description": "What angle this query takes (e.g., 'pain points', 'tool discussions')",
                                    },
                                },
                                "required": ["query", "rationale", "angle"],
                            },
                            "minItems": 3,
                            "maxItems": 5,
                        },
                    },
                    "required": ["queries"],
                },
            }
        ]

        prompt = format_query_prompt(who, why)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            tools=tools,
            tool_choice={"type": "tool", "name": "generate_queries"},
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract tool use result
        for block in response.content:
            if block.type == "tool_use":
                result = block.input
                return SearchQueriesResponse(
                    queries=[
                        SearchQuery(
                            query=q["query"],
                            rationale=q["rationale"],
                            angle=q["angle"],
                        )
                        for q in result["queries"]
                    ]
                )

        # Fallback: return empty
        return SearchQueriesResponse(queries=[])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def rank_accounts(
        self,
        who: str,
        why: Optional[str],
        accounts: list[TwitterAccount],
    ) -> RankingResponse:
        """
        Rank accounts by relevance to the user's search.

        Returns accounts sorted by score with explanations.
        """
        # Prepare accounts data for the prompt
        accounts_data = []
        for acc in accounts:
            account_dict = {
                "handle": acc.handle,
                "name": acc.name,
                "bio": acc.bio,
                "followers_count": acc.followers_count,
                "recent_tweets": [t.text for t in acc.recent_tweets[:3]],
                "matched_queries": acc.matched_queries,
                "network": {
                    "you_follow": acc.network.you_follow,
                    "follows_you": acc.network.follows_you,
                },
            }
            accounts_data.append(account_dict)

        accounts_json = json.dumps(accounts_data, indent=2)

        tools = [
            {
                "name": "rank_accounts",
                "description": "Rank Twitter accounts by relevance",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ranked_accounts": {
                            "type": "array",
                            "description": "Accounts sorted by relevance (highest first)",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "handle": {
                                        "type": "string",
                                        "description": "Twitter handle",
                                    },
                                    "relevance_score": {
                                        "type": "number",
                                        "description": "Final relevance score (0-15)",
                                    },
                                    "base_score": {
                                        "type": "number",
                                        "description": "Base content relevance (0-10)",
                                    },
                                    "why_relevant": {
                                        "type": "string",
                                        "description": "1-2 sentence explanation",
                                    },
                                    "suggested_approach": {
                                        "type": "string",
                                        "description": "Optional engagement suggestion",
                                    },
                                },
                                "required": [
                                    "handle",
                                    "relevance_score",
                                    "base_score",
                                    "why_relevant",
                                ],
                            },
                        },
                    },
                    "required": ["ranked_accounts"],
                },
            }
        ]

        prompt = format_ranking_prompt(who, why, accounts_json)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            tools=tools,
            tool_choice={"type": "tool", "name": "rank_accounts"},
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract tool use result and map back to full account objects
        for block in response.content:
            if block.type == "tool_use":
                result = block.input

                # Create a lookup for accounts by handle
                accounts_by_handle = {acc.handle.lower(): acc for acc in accounts}

                ranked = []
                for item in result["ranked_accounts"]:
                    handle = item["handle"].lower().lstrip("@")
                    if handle in accounts_by_handle:
                        ranked.append(
                            RankedAccount(
                                account=accounts_by_handle[handle],
                                relevance_score=item["relevance_score"],
                                base_score=item["base_score"],
                                why_relevant=item["why_relevant"],
                                suggested_approach=item.get("suggested_approach"),
                            )
                        )

                return RankingResponse(ranked_accounts=ranked)

        # Fallback: return unranked
        return RankingResponse(ranked_accounts=[])
