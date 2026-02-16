"""Algorithm interface and factory for Twitter Account Finder."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from core.models import RankedAccount

if TYPE_CHECKING:
    from core.auth import UserNetwork
    from core.twitter import TwitterClient


@dataclass
class AlgorithmResult:
    """Result returned by any search algorithm."""

    ranked_accounts: list[RankedAccount] = field(default_factory=list)
    quality: str = "moderate"  # "strong", "moderate", or "weak"
    refinement_questions: list[str] = field(default_factory=list)


class SearchAlgorithm(ABC):
    """Abstract base class for search algorithms."""

    @abstractmethod
    async def run(
        self,
        query: str,
        twitter: TwitterClient,
        queue: asyncio.Queue,
        user_network: Optional[UserNetwork] = None,
    ) -> AlgorithmResult:
        """Run the search algorithm and return results.

        Progress messages and structured events should be put onto `queue`
        (same format as the current server.py SSE drain loop expects).
        """
        ...


def get_algorithm() -> SearchAlgorithm:
    """Factory: return the algorithm selected by ALGORITHM_VERSION config."""
    from config import ALGORITHM_VERSION

    if ALGORITHM_VERSION == "v2":
        from algorithms.v2 import AlgorithmV2
        return AlgorithmV2()

    from algorithms.v1 import AlgorithmV1
    return AlgorithmV1()
