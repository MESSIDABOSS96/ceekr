"""Post-ranking web enrichment via Brave Search API."""

from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from config import BRAVE_API_KEY
from .models import EnrichmentData, RankedAccount, SearchIntent


class WebEnricher:
    """Enriches ranked accounts with supplemental web data via Brave Search."""

    def __init__(self):
        self.api_key = BRAVE_API_KEY
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": self.api_key or "",
                },
                timeout=10.0,
            )
        return self._http_client

    async def _search_brave(self, query: str) -> list[dict]:
        """Run a single Brave Search query and return top results."""
        client = await self._ensure_client()
        try:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 5},
            )
            response.raise_for_status()
            data = response.json()
            results = []
            for item in data.get("web", {}).get("results", []):
                results.append({
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                })
            return results
        except Exception as e:
            print(f"Brave search error for '{query}': {e}")
            return []

    def _is_relevant_to_intent(self, url: str, title: str, description: str, intent: SearchIntent) -> bool:
        """Check if a search result is directly relevant to the search intent."""
        # Skip generic social profiles — these aren't useful as enrichment links
        generic_domains = [
            "twitter.com", "x.com", "linkedin.com/in/", "facebook.com",
            "instagram.com", "youtube.com/@", "medium.com/@",
        ]
        url_lower = url.lower()
        if any(domain in url_lower for domain in generic_domains):
            return False

        # Build relevance keywords from intent
        relevance_terms = set()
        for word in intent.topic.lower().split():
            if len(word) > 3:
                relevance_terms.add(word)
        for signal in intent.key_signals:
            for word in signal.lower().split():
                if len(word) > 3:
                    relevance_terms.add(word)

        # Check if title or description contain intent-related terms
        combined_text = f"{title} {description}".lower()
        matches = sum(1 for term in relevance_terms if term in combined_text)
        return matches >= 2

    def _make_link_label(self, url: str, title: str) -> str:
        """Create a concise label for an external link."""
        # Extract domain for prefix
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")

        if "github.com" in domain:
            # Extract repo name from path
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) >= 2:
                return f"GitHub: {path_parts[1]}"
            return f"GitHub: {title[:40]}"
        elif "arxiv.org" in domain:
            return f"Paper: {title[:50]}"
        elif "substack.com" in domain:
            return f"Substack: {title[:40]}"
        else:
            # Use domain + short title
            short_domain = domain.split(".")[0].title()
            return f"{short_domain}: {title[:40]}"

    async def _enrich_single_account(
        self, ranked: RankedAccount, intent: SearchIntent,
    ) -> None:
        """Enrich a single ranked account. Modifies in-place."""
        handle = ranked.account.handle
        name = ranked.account.name

        # Search for the person
        query = f'"{handle}" OR "{name}"'
        results = await self._search_brave(query)

        if not results:
            return

        # Check each result for direct relevance to the search intent
        for result in results:
            url = result["url"]
            title = result["title"]
            description = result["description"]

            if self._is_relevant_to_intent(url, title, description, intent):
                label = self._make_link_label(url, title)
                context = description[:150].strip()
                if context and not context.endswith("."):
                    context = context.rsplit(" ", 1)[0] + "..."

                ranked.enrichment = EnrichmentData(
                    external_link=url,
                    link_label=label,
                    context_note=context,
                )
                # Append context to why_relevant
                if context:
                    ranked.why_relevant = f"{ranked.why_relevant} {context}"
                return

        # No link-worthy result found — check if any result has useful context
        for result in results:
            description = result["description"]
            if description and len(description) > 50:
                # Check if description adds new info (not just a social profile bio)
                url_lower = result["url"].lower()
                if not any(d in url_lower for d in ["twitter.com", "x.com", "linkedin.com", "facebook.com"]):
                    context = description[:150].strip()
                    if context and not context.endswith("."):
                        context = context.rsplit(" ", 1)[0] + "..."
                    ranked.enrichment = EnrichmentData(context_note=context)
                    ranked.why_relevant = f"{ranked.why_relevant} {context}"
                    return

    async def enrich_accounts(
        self, ranked_accounts: list[RankedAccount], intent: SearchIntent,
    ) -> None:
        """
        Enrich ranked accounts with web search findings.

        Modifies RankedAccount objects in-place. Skips if BRAVE_API_KEY not set.
        """
        if not self.api_key:
            return

        batch_size = 20
        for i in range(0, len(ranked_accounts), batch_size):
            batch = ranked_accounts[i : i + batch_size]
            tasks = [self._enrich_single_account(r, intent) for r in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
