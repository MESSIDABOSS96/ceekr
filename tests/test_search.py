#!/usr/bin/env python3
"""
Automated test suite for Twitter Account Finder search algorithm.

Nine layers:
  1. Classification tests (instant, no API calls)
  2. End-to-end name search tests (live API, ~3s each)
  3. Result quality tests (live API, ~3s each)
  4. Complex discovery queries (live API, ~20-30s each)
  5. Short & ambiguous queries (live API, ~5-10s each)
  6. Edge cases & stress tests (live API, ~5-10s each)
  7. User name discovery tests (live API, no LLM, ~2s each)
  8. Must-find name resolution tests (live API, no LLM, ~2s each)
  9. Must-find E2E tests (live API, full pipeline, ~30s each)

Usage:
    python3 tests/test_search.py              # all tests
    python3 tests/test_search.py classify      # classification only (instant)
    python3 tests/test_search.py names         # name search only (live API)
    python3 tests/test_search.py quality       # quality checks only (live API)
    python3 tests/test_search.py complex       # complex discovery queries (live API)
    python3 tests/test_search.py short         # short & ambiguous queries (live API)
    python3 tests/test_search.py edge          # edge cases & stress tests (live API)
    python3 tests/test_search.py discovery     # user name discovery only (live API, no LLM)
    python3 tests/test_search.py mustfind      # must-find name resolution (live API, no LLM)
    python3 tests/test_search.py mustfind-e2e  # must-find E2E (live API, full pipeline)
    python3 tests/test_search.py fast          # classify + discovery + mustfind + edge (no LLM pipeline)
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.fast_path import QueryType, classify_query


# ── Colors ──────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _pass(msg: str) -> str:
    return f"  {GREEN}PASS{RESET}  {msg}"


def _fail(msg: str) -> str:
    return f"  {RED}FAIL{RESET}  {msg}"


# ── Helpers ─────────────────────────────────────────


async def _run_search(client, query: str) -> list[dict]:
    """Run a search against local server and return ranked results."""
    results = []

    async with client.stream(
        "POST",
        "http://localhost:8000/api/search",
        json={"query": query},
        headers={"Content-Type": "application/json"},
    ) as response:
        buffer = ""
        current_event = None

        async for chunk in response.aiter_text():
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()

                if line.startswith("event:"):
                    current_event = line[6:].strip()
                elif line.startswith("data:") and current_event == "results":
                    data = line[5:].strip()
                    try:
                        parsed = json.loads(data)
                        results = parsed.get("ranked", [])
                    except Exception:
                        pass
                elif line.startswith("data:") and current_event == "error":
                    data = line[5:].strip()
                    try:
                        parsed = json.loads(data)
                        print(f"    {YELLOW}Server error: {parsed.get('message', data)}{RESET}")
                    except Exception:
                        pass
                elif line == "":
                    current_event = None

    return results


def _check_relevance(results: list[dict], terms: list[str], top_n: int = 10) -> tuple[int, int]:
    """Check how many of the top N results match any relevance term.

    Searches name + bio + why_relevant (case-insensitive).
    Returns (relevant_count, checked_count).
    """
    checked = results[:top_n]
    relevant = 0
    terms_lower = [t.lower() for t in terms]

    for r in checked:
        text = " ".join([
            r.get("name", ""),
            r.get("bio") or "",
            r.get("why_relevant") or "",
            r.get("handle", ""),
        ]).lower()
        if any(t in text for t in terms_lower):
            relevant += 1

    return relevant, len(checked)


# ══════════════════════════════════════════════════════
# 1. Classification tests (instant, no API)
# ══════════════════════════════════════════════════════

CLASSIFY_TESTS = [
    # (query, expected QueryType)
    # Standard handles
    ("@elonmusk", QueryType.HANDLE_LOOKUP),
    ("@sama", QueryType.HANDLE_LOOKUP),
    ("@naval", QueryType.HANDLE_LOOKUP),
    ("@user_name", QueryType.HANDLE_LOOKUP),
    ("@a", QueryType.HANDLE_LOOKUP),

    # Names and topics → full search
    ("elon musk", QueryType.FULL_SEARCH),
    ("sam altman", QueryType.FULL_SEARCH),
    ("paul graham", QueryType.FULL_SEARCH),
    ("YC", QueryType.FULL_SEARCH),
    ("machine learning", QueryType.FULL_SEARCH),
    ("ML engineers discussing LLMs", QueryType.FULL_SEARCH),
    ("founders building AI startups", QueryType.FULL_SEARCH),
    ("looking for React developers", QueryType.FULL_SEARCH),
    ("people who write about crypto", QueryType.FULL_SEARCH),

    # Edge cases for classification
    ("@ elonmusk", QueryType.HANDLE_LOOKUP),   # space after @ gets stripped → handle
    ("elon", QueryType.FULL_SEARCH),            # single word, not @
    ("#buildinpublic", QueryType.FULL_SEARCH),  # hashtag
    ("", QueryType.FULL_SEARCH),                # empty
]


def run_classification_tests() -> tuple[int, int]:
    """Run classification tests. Returns (passed, total)."""
    print(f"\n{BOLD}Classification (instant):{RESET}")

    passed = 0
    total = len(CLASSIFY_TESTS)

    for query, expected_type in CLASSIFY_TESTS:
        result = classify_query(query)
        if result.query_type == expected_type:
            print(_pass(f'"{query}" -> {expected_type.value}'))
            passed += 1
        else:
            print(_fail(f'"{query}" -> {result.query_type.value} (expected {expected_type.value})'))

    print(f"  Classification: {passed}/{total} passed")
    return passed, total


# ══════════════════════════════════════════════════════
# 2. End-to-end name search tests (live API)
# ══════════════════════════════════════════════════════

NAME_TESTS = [
    # (query, expected_handle, must_be_in_top_N)
    ("elon musk", "elonmusk", 1),
    ("sam altman", "sama", 3),
    ("paul graham", "paulg", 1),
    ("naval ravikant", "naval", 3),
    ("janak sunil", "janaksunil", 1),
    ("bill gates", "BillGates", 1),
    ("@elonmusk", "elonmusk", 1),
    ("@sama", "sama", 1),
    ("YC", "ycombinator", 3),

    # Additional diverse names
    ("jeff bezos", "JeffBezos", 1),
    ("mark zuckerberg", "faboroficial", 3),
    ("sundar pichai", "sundarpichai", 1),
    ("satya nadella", "satabordelon", 3),
    ("jensen huang", "nvidia", 5),
    ("Andrej Karpathy", "karpathy", 1),
    ("Pieter Levels", "levelsio", 1),
    ("George Hotz", "realGeorgeHotz", 3),
]


async def run_name_search_tests() -> tuple[int, int]:
    """Run name search tests against live API. Returns (passed, total)."""
    import httpx

    print(f"\n{BOLD}Name Search (live API):{RESET}")

    passed = 0
    total = len(NAME_TESTS)

    async with httpx.AsyncClient(timeout=60.0) as client:
        for query, expected_handle, top_n in NAME_TESTS:
            start = time.time()
            try:
                # POST to search endpoint and collect SSE events
                results = await _run_search(client, query)
                elapsed = time.time() - start

                if not results:
                    print(_fail(f'"{query}" -> no results [{elapsed:.1f}s]'))
                    continue

                # Find position of expected handle (case-insensitive)
                position = None
                for i, r in enumerate(results):
                    if r["handle"].lower() == expected_handle.lower():
                        position = i + 1
                        break

                if position is not None and position <= top_n:
                    print(_pass(f'"{query}" -> @{expected_handle} at #{position} (expected top {top_n}) [{elapsed:.1f}s]'))
                    passed += 1
                elif position is not None:
                    print(_fail(f'"{query}" -> @{expected_handle} at #{position} (expected top {top_n}) [{elapsed:.1f}s]'))
                else:
                    top_handles = [f"@{r['handle']}" for r in results[:5]]
                    print(_fail(f'"{query}" -> @{expected_handle} not found. Top 5: {", ".join(top_handles)} [{elapsed:.1f}s]'))

            except Exception as e:
                elapsed = time.time() - start
                print(_fail(f'"{query}" -> ERROR: {e} [{elapsed:.1f}s]'))

    print(f"  Name Search: {passed}/{total} passed")
    return passed, total


# ══════════════════════════════════════════════════════
# 3. Result quality tests (live API)
# ══════════════════════════════════════════════════════

async def run_quality_tests() -> tuple[int, int]:
    """Run result quality tests. Returns (passed, total)."""
    import httpx

    print(f"\n{BOLD}Result Quality (live API):{RESET}")

    passed = 0
    total = 0

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test: "elon musk" top result should have >1M followers
        total += 1
        results = await _run_search(client, "elon musk")
        if results and results[0]["followers_count"] > 1_000_000:
            print(_pass(f'"elon musk" top result has {results[0]["followers_count"]:,} followers (>1M)'))
            passed += 1
        else:
            count = results[0]["followers_count"] if results else 0
            print(_fail(f'"elon musk" top result has {count:,} followers (expected >1M)'))

        # Test: "paul graham" no accounts with <50 followers in top 3
        total += 1
        results = await _run_search(client, "paul graham")
        low_follower = [r for r in results[:3] if r["followers_count"] < 50]
        if not low_follower:
            print(_pass('"paul graham" no low-follower accounts in top 3'))
            passed += 1
        else:
            handles = [f"@{r['handle']}({r['followers_count']})" for r in low_follower]
            print(_fail(f'"paul graham" low-follower in top 3: {", ".join(handles)}'))

        # Test: "YC" at least 2 results with "YC" or "Y Combinator" in name/bio
        total += 1
        results = await _run_search(client, "YC")
        yc_related = 0
        for r in results[:10]:
            name_bio = (r.get("name", "") + " " + (r.get("bio") or "")).lower()
            if "yc" in name_bio or "y combinator" in name_bio or "ycombinator" in name_bio:
                yc_related += 1
        if yc_related >= 2:
            print(_pass(f'"YC" found {yc_related} YC-related accounts in top 10'))
            passed += 1
        else:
            print(_fail(f'"YC" only {yc_related} YC-related accounts in top 10 (expected >=2)'))

        # Test: Spam filter — no "giveaway" accounts in top 5 for "elon musk"
        total += 1
        results = await _run_search(client, "elon musk")
        spam_in_top5 = []
        for r in results[:5]:
            bio = (r.get("bio") or "").lower()
            if "giveaway" in bio or "airdrop" in bio or "free followers" in bio:
                spam_in_top5.append(r["handle"])
        if not spam_in_top5:
            print(_pass('"elon musk" no spam accounts in top 5'))
            passed += 1
        else:
            print(_fail(f'"elon musk" spam in top 5: {", ".join(spam_in_top5)}'))

        # Test: "AI researchers" should return accounts with diverse content
        total += 1
        results = await _run_search(client, "AI researchers")
        if results and len(results) >= 3:
            relevant, checked = _check_relevance(results, ["ai", "research", "ml", "machine learning", "deep learning"])
            if relevant >= 2:
                print(_pass(f'"AI researchers" {relevant}/{checked} relevant in top results'))
                passed += 1
            else:
                print(_fail(f'"AI researchers" only {relevant}/{checked} relevant in top results'))
        else:
            count = len(results) if results else 0
            print(_fail(f'"AI researchers" only {count} results (expected >=3)'))

        # Test: Score distribution — broad query shouldn't have all 10s
        total += 1
        results = await _run_search(client, "tech people")
        if results and len(results) >= 5:
            # Check scores aren't all identical
            scores = set()
            for r in results[:10]:
                scores.add(r.get("relevance_score") or r.get("score", 0))
            if len(scores) >= 2:
                print(_pass(f'"tech people" has {len(scores)} distinct scores in top 10 (not all identical)'))
                passed += 1
            else:
                print(_fail(f'"tech people" all scores identical: {scores}'))
        else:
            count = len(results) if results else 0
            print(_fail(f'"tech people" only {count} results (expected >=5)'))

    print(f"  Result Quality: {passed}/{total} passed")
    return passed, total


# ══════════════════════════════════════════════════════
# 4. Complex discovery queries (live API, LLM pipeline)
# ══════════════════════════════════════════════════════

# (query, min_results, relevance_terms, min_relevant_ratio)
COMPLEX_TESTS = [
    # ── Role + topic (medium specificity) ──
    ("AI researchers working on LLMs",
     3, ["ai", "llm", "machine learning", "nlp", "language model", "gpt", "researcher"], 0.3),
    ("venture capitalists investing in AI",
     3, ["vc", "venture", "investor", "capital", "ai", "fund", "partner"], 0.3),
    ("machine learning engineers at startups",
     3, ["ml", "machine learning", "engineer", "startup", "ai", "deep learning"], 0.3),
    ("journalists covering tech policy",
     3, ["journalist", "reporter", "writer", "tech", "policy", "regulation", "media"], 0.3),
    ("designers who tweet about UX research",
     3, ["design", "ux", "research", "user", "product", "designer"], 0.3),
    ("founders in the climate tech space",
     3, ["climate", "cleantech", "sustainability", "carbon", "energy", "founder"], 0.3),

    # ── Activity-based (what they do/tweet about) ──
    ("people tweeting about Rust programming",
     3, ["rust", "rustlang", "programming", "developer", "engineer", "code"], 0.3),
    ("people writing about personal finance",
     3, ["finance", "investing", "money", "budget", "wealth", "financial"], 0.3),
    ("accounts sharing startup advice",
     3, ["startup", "founder", "entrepreneur", "advice", "build", "growth"], 0.3),

    # ── Very broad (should return many results) ──
    ("tech Twitter",
     5, ["tech", "software", "engineer", "developer", "startup", "ai", "product"], 0.2),
    ("crypto Twitter",
     5, ["crypto", "bitcoin", "ethereum", "web3", "blockchain", "defi", "nft"], 0.3),

    # ── Very specific/niche (few but highly relevant results) ──
    ("people building dev tools for Kubernetes",
     2, ["kubernetes", "k8s", "devops", "cloud", "container", "infrastructure"], 0.3),
    ("biotech founders working on gene therapy",
     2, ["biotech", "gene", "therapy", "genomic", "crispr", "pharma", "bio"], 0.2),
    ("indie game developers using Godot engine",
     2, ["godot", "gamedev", "indie", "game", "developer"], 0.2),

    # ── Long, sentence-style queries ──
    ("I'm looking for people who are building open source alternatives to popular SaaS tools",
     3, ["open source", "oss", "saas", "developer", "build", "alternative", "software"], 0.2),
    ("can you find Twitter accounts that discuss the intersection of AI and healthcare",
     3, ["ai", "health", "medical", "healthcare", "clinical", "doctor", "patient"], 0.2),
    ("who are the most active people discussing TypeScript and frontend architecture",
     3, ["typescript", "frontend", "react", "javascript", "architect", "web", "developer"], 0.3),
]


async def run_complex_tests() -> tuple[int, int]:
    """Run complex discovery query tests. Returns (passed, total)."""
    import httpx

    print(f"\n{BOLD}Complex Discovery Queries (live API):{RESET}")

    passed = 0
    total = 0

    async with httpx.AsyncClient(timeout=120.0) as client:
        for query, min_results, relevance_terms, min_ratio in COMPLEX_TESTS:
            start = time.time()
            sub_passed = 0
            sub_total = 4
            total += 4
            failures = []

            try:
                results = await _run_search(client, query)
                elapsed = time.time() - start

                # Sub-check 1: minimum result count
                if results and len(results) >= min_results:
                    sub_passed += 1
                else:
                    count = len(results) if results else 0
                    failures.append(f"only {count} results (need >={min_results})")

                # Sub-check 2: relevance ratio in top 10
                if results:
                    relevant, checked = _check_relevance(results, relevance_terms, top_n=10)
                    ratio = relevant / checked if checked > 0 else 0
                    if ratio >= min_ratio:
                        sub_passed += 1
                    else:
                        failures.append(f"relevance {relevant}/{checked}={ratio:.0%} (need >={min_ratio:.0%})")
                else:
                    failures.append("no results for relevance check")

                # Sub-check 3: top result score >= 5
                if results:
                    top_score = results[0].get("relevance_score") or results[0].get("score", 0)
                    if top_score >= 5:
                        sub_passed += 1
                    else:
                        failures.append(f"top score {top_score} (need >=5)")
                else:
                    failures.append("no results for score check")

                # Sub-check 4: no 0-follower accounts in top 5
                if results:
                    zero_followers = [r["handle"] for r in results[:5] if r.get("followers_count", 0) == 0]
                    if not zero_followers:
                        sub_passed += 1
                    else:
                        failures.append(f"0-follower in top 5: @{', @'.join(zero_followers)}")
                else:
                    failures.append("no results for follower check")

                passed += sub_passed

                if sub_passed == sub_total:
                    print(_pass(f'"{query}" {sub_passed}/{sub_total} checks [{elapsed:.1f}s]'))
                else:
                    detail = "; ".join(failures)
                    print(_fail(f'"{query}" {sub_passed}/{sub_total} checks — {detail} [{elapsed:.1f}s]'))

            except Exception as e:
                elapsed = time.time() - start
                print(_fail(f'"{query}" -> ERROR: {e} [{elapsed:.1f}s]'))

    print(f"  Complex: {passed}/{total} passed")
    return passed, total


# ══════════════════════════════════════════════════════
# 5. Short & ambiguous queries (live API)
# ══════════════════════════════════════════════════════

# (query, min_results, expected_handle_or_none, top_n, relevance_terms)
SHORT_TESTS = [
    # Single-word — could be person or topic
    ("Tesla",     3, None, None, ["tesla", "ev", "electric", "elon"]),
    ("Bitcoin",   3, None, None, ["bitcoin", "btc", "crypto", "blockchain"]),
    ("Figma",     3, None, None, ["figma", "design", "ui", "ux"]),
    ("Stripe",    3, None, None, ["stripe", "payments", "fintech"]),
    ("OpenAI",    3, "OpenAI", 3, ["openai", "ai", "gpt", "chatgpt"]),
    ("Anthropic", 3, "AnthropicAI", 3, ["anthropic", "claude", "ai"]),
    ("NASA",      3, "NASA", 3, ["nasa", "space", "rocket", "aerospace"]),

    # Two-word — companies/orgs
    ("Y Combinator", 3, "ycombinator", 3, ["yc", "y combinator", "startup", "ycombinator"]),
    ("Google DeepMind", 3, None, None, ["deepmind", "google", "ai", "research"]),
    ("a16z",      3, None, None, ["a16z", "andreessen", "venture", "crypto"]),

    # Two-word — could be ambiguous
    ("linear app", 3, None, None, ["linear", "project", "issue", "tool"]),
    ("vercel next", 3, None, None, ["vercel", "next", "nextjs", "deploy", "frontend"]),

    # Single word — very short
    ("AI",        3, None, None, ["ai", "artificial", "machine learning", "ml"]),
    ("crypto",    3, None, None, ["crypto", "bitcoin", "blockchain", "web3"]),
    ("design",    3, None, None, ["design", "designer", "ux", "ui", "creative"]),
]


async def run_short_tests() -> tuple[int, int]:
    """Run short & ambiguous query tests. Returns (passed, total)."""
    import httpx

    print(f"\n{BOLD}Short & Ambiguous Queries (live API):{RESET}")

    passed = 0
    total = 0

    async with httpx.AsyncClient(timeout=120.0) as client:
        for query, min_results, expected_handle, top_n, relevance_terms in SHORT_TESTS:
            start = time.time()
            failures = []
            sub_passed = 0
            # Sub-checks: min results + optional handle check + relevance
            sub_total = 2 + (1 if expected_handle else 0)
            total += sub_total

            try:
                results = await _run_search(client, query)
                elapsed = time.time() - start

                # Sub-check 1: minimum result count
                if results and len(results) >= min_results:
                    sub_passed += 1
                else:
                    count = len(results) if results else 0
                    failures.append(f"only {count} results (need >={min_results})")

                # Sub-check 2 (optional): expected handle in top N
                if expected_handle:
                    found_pos = None
                    for i, r in enumerate(results or []):
                        if r["handle"].lower() == expected_handle.lower():
                            found_pos = i + 1
                            break
                    if found_pos is not None and found_pos <= top_n:
                        sub_passed += 1
                    elif found_pos is not None:
                        failures.append(f"@{expected_handle} at #{found_pos} (need top {top_n})")
                    else:
                        top_handles = [f"@{r['handle']}" for r in (results or [])[:5]]
                        failures.append(f"@{expected_handle} not found in {', '.join(top_handles)}")

                # Sub-check 3: at least 30% relevance in top 10
                if results:
                    relevant, checked = _check_relevance(results, relevance_terms, top_n=10)
                    ratio = relevant / checked if checked > 0 else 0
                    if ratio >= 0.3:
                        sub_passed += 1
                    else:
                        failures.append(f"relevance {relevant}/{checked}={ratio:.0%} (need >=30%)")
                else:
                    failures.append("no results for relevance check")

                passed += sub_passed

                if sub_passed == sub_total:
                    print(_pass(f'"{query}" {sub_passed}/{sub_total} checks [{elapsed:.1f}s]'))
                else:
                    detail = "; ".join(failures)
                    print(_fail(f'"{query}" {sub_passed}/{sub_total} checks — {detail} [{elapsed:.1f}s]'))

            except Exception as e:
                elapsed = time.time() - start
                print(_fail(f'"{query}" -> ERROR: {e} [{elapsed:.1f}s]'))

    print(f"  Short & Ambiguous: {passed}/{total} passed")
    return passed, total


# ══════════════════════════════════════════════════════
# 6. Edge cases & stress tests (live API)
# ══════════════════════════════════════════════════════

# (query, expectation)
# "should_return_results" = at least 1 result, no server error
# "should_return_results_or_empty" = no server error (0 results OK)
EDGE_TESTS = [
    # Formatting edge cases
    ("  elon musk  ",           "should_return_results"),
    ("ELON MUSK",               "should_return_results"),
    ("eLoN mUsK",               "should_return_results"),
    ("@ElOnMuSk",               "should_return_results"),

    # Partial/typo names — should still return something
    ("elonmusk",                "should_return_results"),
    ("samaltman",               "should_return_results"),

    # Special characters
    ("c++",                     "should_return_results"),
    ("node.js developers",     "should_return_results"),
    ("AI/ML engineers",        "should_return_results"),

    # Very long query
    ("I am looking for people who are experts in artificial intelligence and machine learning, "
     "particularly those who work on large language models and have published research papers "
     "on transformer architectures and attention mechanisms",
     "should_return_results"),

    # Single character (probably should still work)
    ("a",                       "should_return_results_or_empty"),

    # Numbers
    ("web3",                    "should_return_results"),
    ("gpt4",                    "should_return_results"),

    # Hashtag style
    ("#buildinpublic",         "should_return_results"),
    ("#indiedev",              "should_return_results"),
]


async def run_edge_tests() -> tuple[int, int]:
    """Run edge case & stress tests. Returns (passed, total)."""
    import httpx

    print(f"\n{BOLD}Edge Cases & Stress Tests (live API):{RESET}")

    passed = 0
    total = len(EDGE_TESTS)

    async with httpx.AsyncClient(timeout=120.0) as client:
        for query, expectation in EDGE_TESTS:
            start = time.time()
            try:
                results = await _run_search(client, query)
                elapsed = time.time() - start

                if expectation == "should_return_results":
                    if results and len(results) >= 1:
                        print(_pass(f'"{query}" -> {len(results)} results [{elapsed:.1f}s]'))
                        passed += 1
                    else:
                        print(_fail(f'"{query}" -> 0 results (expected >=1) [{elapsed:.1f}s]'))
                elif expectation == "should_return_results_or_empty":
                    # No crash = pass (even 0 results is OK)
                    count = len(results) if results else 0
                    print(_pass(f'"{query}" -> {count} results (no crash) [{elapsed:.1f}s]'))
                    passed += 1

            except Exception as e:
                elapsed = time.time() - start
                print(_fail(f'"{query}" -> ERROR: {e} [{elapsed:.1f}s]'))

    print(f"  Edge Cases: {passed}/{total} passed")
    return passed, total


# ══════════════════════════════════════════════════════
# 7. Discovery tests (live API, no LLM)
# ══════════════════════════════════════════════════════

DISCOVERY_TESTS = [
    # (query, min_results)
    ("janak sunil", 1),
    ("elon musk", 1),
    ("sam altman", 1),
]


async def run_discovery_tests() -> tuple[int, int]:
    """Run user name discovery tests (SocialData API only, no LLM). Returns (passed, total)."""
    from core.twitter import TwitterClient

    print(f"\n{BOLD}User Name Discovery (live API, no LLM):{RESET}")

    passed = 0
    total = len(DISCOVERY_TESTS)

    twitter = TwitterClient()

    for query, min_results in DISCOVERY_TESTS:
        start = time.time()
        try:
            # Call search_users + enrich (same pattern as V2's _discover_users_by_name)
            user_results = await twitter.search_users(query, max_results=10)

            enriched = []
            if user_results:
                async def enrich(user_data: dict) -> dict | None:
                    handle = user_data.get("screen_name", "")
                    if not handle:
                        return None
                    full = await twitter.lookup_user(handle)
                    return full if full else user_data

                enriched_raw = await asyncio.gather(*[enrich(u) for u in user_results])
                enriched = [u for u in enriched_raw if u is not None]

            elapsed = time.time() - start

            if len(enriched) >= min_results:
                # Verify enriched data has required fields
                sample = enriched[0]
                has_fields = all(
                    sample.get(f) is not None
                    for f in ("id_str", "screen_name", "description", "followers_count")
                )
                if has_fields:
                    handles = [u.get("screen_name", "?") for u in enriched[:5]]
                    print(_pass(f'"{query}" -> {len(enriched)} enriched users: @{", @".join(handles)} [{elapsed:.1f}s]'))
                    passed += 1
                else:
                    missing = [f for f in ("id_str", "screen_name", "description", "followers_count") if sample.get(f) is None]
                    print(_fail(f'"{query}" -> enriched but missing fields: {missing} [{elapsed:.1f}s]'))
            else:
                print(_fail(f'"{query}" -> {len(enriched)} enriched (need >={min_results}) [{elapsed:.1f}s]'))

        except Exception as e:
            elapsed = time.time() - start
            print(_fail(f'"{query}" -> ERROR: {e} [{elapsed:.1f}s]'))

    print(f"  Discovery: {passed}/{total} passed")
    return passed, total


# ══════════════════════════════════════════════════════
# 8. Must-find name resolution tests (live API, no LLM)
# ══════════════════════════════════════════════════════

MUST_FIND_TESTS = [
    # (names, expected_min_resolved)
    (["Sequoia Capital", "Y Combinator"], 2),
    (["Andreessen Horowitz", "OpenAI"], 2),
]


async def run_must_find_tests() -> tuple[int, int]:
    """Run must-find name resolution tests (SocialData API only, no LLM). Returns (passed, total)."""
    from algorithms.v2 import AlgorithmV2
    from core.twitter import TwitterClient

    print(f"\n{BOLD}Must-Find Name Resolution (live API, no LLM):{RESET}")

    passed = 0
    total = len(MUST_FIND_TESTS)

    twitter = TwitterClient()
    algo = AlgorithmV2()

    for names, min_resolved in MUST_FIND_TESTS:
        start = time.time()
        try:
            results = await algo._resolve_must_find_names(twitter, names, None)
            elapsed = time.time() - start

            if len(results) >= min_resolved:
                # Verify enriched data has required fields
                all_valid = True
                for source, user_data in results:
                    has_fields = all(
                        user_data.get(f) is not None
                        for f in ("id_str", "screen_name", "description", "followers_count")
                    )
                    if not has_fields:
                        all_valid = False
                        break

                if all_valid:
                    handles = [u.get("screen_name", "?") for _, u in results]
                    print(_pass(f'{names} -> {len(results)} resolved: @{", @".join(handles)} [{elapsed:.1f}s]'))
                    passed += 1
                else:
                    print(_fail(f'{names} -> resolved but missing fields [{elapsed:.1f}s]'))
            else:
                print(_fail(f'{names} -> {len(results)} resolved (need >={min_resolved}) [{elapsed:.1f}s]'))

        except Exception as e:
            elapsed = time.time() - start
            print(_fail(f'{names} -> ERROR: {e} [{elapsed:.1f}s]'))

    print(f"  Must-Find: {passed}/{total} passed")
    return passed, total


# ══════════════════════════════════════════════════════
# 9. Must-find E2E tests (live API, full pipeline)
# ══════════════════════════════════════════════════════

MUST_FIND_E2E_TESTS = [
    # (query, expected_handles_any_of, min_expected)
    ("top vc firms", ["sequoia", "ycombinator", "a16z", "benchmark"], 1),
]


async def run_must_find_e2e_tests() -> tuple[int, int]:
    """Run must-find E2E tests (full pipeline via server). Returns (passed, total)."""
    import httpx

    print(f"\n{BOLD}Must-Find E2E (live API, full pipeline):{RESET}")

    passed = 0
    total = len(MUST_FIND_E2E_TESTS)

    async with httpx.AsyncClient(timeout=120.0) as client:
        for query, expected_handles, min_expected in MUST_FIND_E2E_TESTS:
            start = time.time()
            try:
                results = await _run_search(client, query)
                elapsed = time.time() - start

                if not results:
                    print(_fail(f'"{query}" -> no results [{elapsed:.1f}s]'))
                    continue

                result_handles = [r["handle"].lower() for r in results]
                found = [h for h in expected_handles if h.lower() in result_handles]

                if len(found) >= min_expected:
                    print(_pass(f'"{query}" -> found {found} in results ({len(results)} total) [{elapsed:.1f}s]'))
                    passed += 1
                else:
                    top_handles = [f"@{r['handle']}" for r in results[:10]]
                    print(_fail(f'"{query}" -> found {found} of {expected_handles} (need >={min_expected}). Top 10: {", ".join(top_handles)} [{elapsed:.1f}s]'))

            except Exception as e:
                elapsed = time.time() - start
                print(_fail(f'"{query}" -> ERROR: {e} [{elapsed:.1f}s]'))

    print(f"  Must-Find E2E: {passed}/{total} passed")
    return passed, total


# ── Main ────────────────────────────────────────────


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    valid_modes = {"all", "classify", "names", "quality", "complex", "short", "edge", "discovery", "fast", "mustfind", "mustfind-e2e"}
    if mode not in valid_modes:
        print(f"Unknown mode: {mode}")
        print(f"Valid modes: {', '.join(sorted(valid_modes))}")
        return 1

    print(f"\n{BOLD}=== Search Algorithm Test Suite ==={RESET}")
    if mode != "all":
        print(f"  Mode: {mode}")

    total_passed = 0
    total_tests = 0

    if mode in ("all", "classify", "fast"):
        p, t = run_classification_tests()
        total_passed += p
        total_tests += t

    if mode in ("all", "names"):
        p, t = await run_name_search_tests()
        total_passed += p
        total_tests += t

    if mode in ("all", "quality"):
        p, t = await run_quality_tests()
        total_passed += p
        total_tests += t

    if mode in ("all", "complex"):
        p, t = await run_complex_tests()
        total_passed += p
        total_tests += t

    if mode in ("all", "short"):
        p, t = await run_short_tests()
        total_passed += p
        total_tests += t

    if mode in ("all", "discovery", "fast"):
        p, t = await run_discovery_tests()
        total_passed += p
        total_tests += t

    if mode in ("all", "mustfind", "fast"):
        p, t = await run_must_find_tests()
        total_passed += p
        total_tests += t

    if mode in ("all", "mustfind-e2e"):
        p, t = await run_must_find_e2e_tests()
        total_passed += p
        total_tests += t

    if mode in ("all", "edge", "fast"):
        p, t = await run_edge_tests()
        total_passed += p
        total_tests += t

    pct = (total_passed / total_tests * 100) if total_tests > 0 else 0
    color = GREEN if pct >= 80 else YELLOW if pct >= 50 else RED
    print(f"\n{BOLD}Overall: {color}{total_passed}/{total_tests} passed ({pct:.0f}%){RESET}\n")

    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
