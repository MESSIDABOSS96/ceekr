"""LLM layer for Claude API calls."""

import asyncio
import json
from typing import Optional

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

from .models import (
    ClarificationQuestion,
    RankedAccount,
    RankingResponse,
    SearchIntent,
    SearchQueriesResponse,
    SearchQuery,
    TwitterAccount,
)
from prompts.intent_extraction import format_intent_prompt
from prompts.query_generation import format_query_prompt
from prompts.ranking import format_ranking_prompt
from prompts.chat import format_chat_system_prompt


class LLMClient:
    """Client for Claude API calls with structured output."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = ANTHROPIC_MODEL

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def extract_intent(self, who: str, why: Optional[str] = None) -> SearchIntent:
        """
        Extract structured intent from user input.

        Returns SearchIntent with decomposed fields. If input is too broad
        (specificity=1), is_clear=False with clarifying questions.
        """
        tools = [
            {
                "name": "extract_intent",
                "description": "Extract structured search intent from the user's request",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "is_clear": {
                            "type": "boolean",
                            "description": "True if specificity >= 2 (can search). False only for specificity 1.",
                        },
                        "questions": {
                            "type": "array",
                            "description": "Clarifying questions if is_clear is False (empty if clear)",
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
                        "persona": {
                            "type": "string",
                            "description": "The type of person to find (e.g., 'early-stage SaaS founders')",
                        },
                        "topic": {
                            "type": "string",
                            "description": "What they should be discussing (e.g., 'customer discovery challenges')",
                        },
                        "goal": {
                            "type": "string",
                            "description": "Why the user wants to find them (e.g., 'validate product idea')",
                        },
                        "specificity": {
                            "type": "integer",
                            "description": "How specific the request is (1=very broad, 5=very specific)",
                            "minimum": 1,
                            "maximum": 5,
                        },
                        "suggested_query_count": {
                            "type": "integer",
                            "description": "Recommended number of search queries (3-7)",
                            "minimum": 3,
                            "maximum": 7,
                        },
                        "min_score_threshold": {
                            "type": "integer",
                            "description": "Minimum relevance score to show (1-7)",
                            "minimum": 1,
                            "maximum": 7,
                        },
                    },
                    "required": [
                        "is_clear",
                        "questions",
                        "persona",
                        "topic",
                        "goal",
                        "specificity",
                        "suggested_query_count",
                        "min_score_threshold",
                    ],
                },
            }
        ]

        prompt = format_intent_prompt(who, why)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            tools=tools,
            tool_choice={"type": "tool", "name": "extract_intent"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if block.type == "tool_use":
                result = block.input
                return SearchIntent(
                    is_clear=result["is_clear"],
                    questions=[
                        ClarificationQuestion(question=q["question"], reason=q["reason"])
                        for q in result.get("questions", [])
                    ],
                    persona=result.get("persona", ""),
                    topic=result.get("topic", ""),
                    goal=result.get("goal", ""),
                    specificity=result.get("specificity", 3),
                    suggested_query_count=result.get("suggested_query_count", 5),
                    min_score_threshold=result.get("min_score_threshold", 4),
                )

        # Fallback: assume clear with defaults
        return SearchIntent(is_clear=True, questions=[])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_search_queries(self, intent: SearchIntent) -> SearchQueriesResponse:
        """
        Generate Twitter search queries based on structured intent.

        Returns search queries from different angles.
        """
        query_count = intent.suggested_query_count

        tools = [
            {
                "name": "generate_queries",
                "description": "Generate Twitter search queries to find relevant accounts",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "queries": {
                            "type": "array",
                            "description": f"List of exactly {query_count} search queries",
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
                            "minItems": min(3, query_count),
                            "maxItems": query_count,
                        },
                    },
                    "required": ["queries"],
                },
            }
        ]

        prompt = format_query_prompt(intent)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            tools=tools,
            tool_choice={"type": "tool", "name": "generate_queries"},
            messages=[{"role": "user", "content": prompt}],
        )

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

        return SearchQueriesResponse(queries=[])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def rank_accounts(
        self,
        intent: SearchIntent,
        accounts: list[TwitterAccount],
    ) -> RankingResponse:
        """
        Rank accounts by relevance to the user's search intent.

        Returns accounts sorted by score with explanations and quality assessment.
        """
        accounts_data = []
        for acc in accounts:
            account_dict = {
                "handle": acc.handle,
                "name": acc.name,
                "bio": (acc.bio or "")[:200],
                "followers_count": acc.followers_count,
                "recent_tweets": [
                    {
                        "text": t.text[:200],
                        "date": t.created_at.isoformat() if t.created_at else None,
                    }
                    for t in acc.recent_tweets[:2]
                ],
                "matched_query_count": len(acc.matched_queries),
            }
            accounts_data.append(account_dict)

        accounts_json = json.dumps(accounts_data, indent=2)

        tools = [
            {
                "name": "rank_accounts",
                "description": "Rank Twitter accounts by relevance with quality assessment",
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
                                        "description": "Relevance score (1-10)",
                                    },
                                    "score_reasoning": {
                                        "type": "string",
                                        "description": "1 sentence explaining what drove this score",
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
                                    "score_reasoning",
                                    "why_relevant",
                                ],
                            },
                        },
                        "result_quality": {
                            "type": "string",
                            "enum": ["strong", "moderate", "weak"],
                            "description": "Overall quality: strong (3+ scored 7+), moderate (5+ scored 5+), weak (otherwise)",
                        },
                        "refinement_questions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "1-2 clarifying questions if quality is weak (empty otherwise)",
                        },
                    },
                    "required": ["ranked_accounts", "result_quality", "refinement_questions"],
                },
            }
        ]

        prompt = format_ranking_prompt(intent, accounts_json)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            tools=tools,
            tool_choice={"type": "tool", "name": "rank_accounts"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if block.type == "tool_use":
                result = block.input

                accounts_by_handle = {acc.handle.lower(): acc for acc in accounts}

                ranked = []
                for item in result["ranked_accounts"]:
                    handle = item["handle"].lower().lstrip("@")
                    if handle in accounts_by_handle:
                        ranked.append(
                            RankedAccount(
                                account=accounts_by_handle[handle],
                                relevance_score=item["relevance_score"],
                                score_reasoning=item["score_reasoning"],
                                why_relevant=item["why_relevant"],
                                suggested_approach=item.get("suggested_approach"),
                            )
                        )

                return RankingResponse(
                    ranked_accounts=ranked,
                    result_quality=result.get("result_quality", "moderate"),
                    refinement_questions=result.get("refinement_questions", []),
                )

        return RankingResponse(ranked_accounts=[])

    async def rank_accounts_parallel(
        self,
        intent: SearchIntent,
        accounts: list[TwitterAccount],
        batch_size: int = 20,
    ) -> RankingResponse:
        """Rank accounts in parallel batches for speed."""
        if len(accounts) <= batch_size:
            return await asyncio.to_thread(self.rank_accounts, intent, accounts)

        batches = [accounts[i : i + batch_size] for i in range(0, len(accounts), batch_size)]
        tasks = [asyncio.to_thread(self.rank_accounts, intent, batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks)

        all_ranked = []
        for result in batch_results:
            all_ranked.extend(result.ranked_accounts)
        all_ranked.sort(key=lambda r: r.relevance_score, reverse=True)

        high_scores = sum(1 for r in all_ranked if r.relevance_score >= 7)
        mid_scores = sum(1 for r in all_ranked if r.relevance_score >= 5)
        if high_scores >= 3:
            quality = "strong"
        elif mid_scores >= 5:
            quality = "moderate"
        else:
            quality = "weak"

        refinement_questions: list[str] = []
        if quality == "weak":
            for result in batch_results:
                refinement_questions.extend(result.refinement_questions)

        return RankingResponse(
            ranked_accounts=all_ranked,
            result_quality=quality,
            refinement_questions=refinement_questions[:2],
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def chat_respond(
        self,
        messages: list[dict],
        filters_summary: str,
        results_summary: str,
    ) -> dict:
        """
        Handle a chat message for search refinement.

        Returns dict with 'response' (str) and optional 'action' (dict).
        """
        tools = [
            {
                "name": "run_search",
                "description": "Run a new Twitter profile search with the given query",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message to show the user about what you're searching for",
                        },
                        "query": {
                            "type": "string",
                            "description": "The search query to run",
                        },
                    },
                    "required": ["message", "query"],
                },
            },
            {
                "name": "apply_filters",
                "description": "Adjust filters on the current results",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message to show the user about what filters were changed",
                        },
                        "filters": {
                            "type": "object",
                            "description": "Partial filter object — only include fields to change",
                            "properties": {
                                "keywords": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "followerMin": {"type": "number"},
                                "followerMax": {"type": "number"},
                                "location": {"type": "string"},
                                "verified": {"type": ["boolean", "null"]},
                                "postingFrequency": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "accountAge": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    },
                    "required": ["message", "filters"],
                },
            },
            {
                "name": "remove_profiles",
                "description": "Remove specific profiles from results by handle",
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
                "name": "respond",
                "description": "Send a conversational response (for explanations, suggestions, or declining off-topic requests)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The response message",
                        },
                    },
                    "required": ["message"],
                },
            },
        ]

        system_prompt = format_chat_system_prompt(filters_summary, results_summary)

        # Convert messages to Anthropic format
        api_messages = []
        for msg in messages:
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            messages=api_messages,
        )

        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                result = block.input

                if tool_name == "run_search":
                    return {
                        "response": result["message"],
                        "action": {"type": "search", "query": result["query"]},
                    }
                elif tool_name == "apply_filters":
                    return {
                        "response": result["message"],
                        "action": {"type": "filter", "filters": result["filters"]},
                    }
                elif tool_name == "remove_profiles":
                    return {
                        "response": result["message"],
                        "action": {
                            "type": "remove_profiles",
                            "removeHandles": result["handles"],
                        },
                    }
                else:  # respond
                    return {"response": result["message"]}

        # Fallback: extract text response
        text_parts = [b.text for b in response.content if hasattr(b, "text")]
        return {"response": " ".join(text_parts) if text_parts else "I'm not sure how to help with that. Want to refine your search?"}
