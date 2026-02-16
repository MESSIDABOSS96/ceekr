#!/usr/bin/env python3
"""Evaluation & regression testing for Twitter Account Finder.

Run real searches, save full results as snapshots, and compare across runs
to track improvement direction after algorithm changes.

Usage:
    python3 tests/eval.py run                            # Run all benchmark queries
    python3 tests/eval.py run --label "before X"         # Snapshot with descriptive label
    python3 tests/eval.py run --queries "q1" "q2"        # Run only specific ad-hoc queries
    python3 tests/eval.py compare                        # Compare 2 most recent snapshots
    python3 tests/eval.py compare --base snapshots/X.json
    python3 tests/eval.py list                           # List all saved snapshots
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"
BENCHMARK_FILE = Path(__file__).parent / "benchmark_queries.json"
DEFAULT_SERVER = "http://localhost:8000"
QUERY_TIMEOUT = 120.0


# ── SSE client ───────────────────────────────────────────────────────────────


def run_single_query(server_url: str, query: str, timeout: float = QUERY_TIMEOUT) -> dict:
    """Run a single search query via SSE and collect full results.

    Returns raw result dict with all account-level data, not just counts.
    """
    url = f"{server_url}/api/search"
    start = time.time()

    ranked = []
    quality = None
    error = None

    try:
        with httpx.Client(timeout=timeout) as client:
            with client.stream(
                "POST",
                url,
                json={"query": query},
                headers={"Content-Type": "application/json"},
            ) as response:
                current_event = ""
                current_data = ""

                for line in response.iter_lines():
                    if line.startswith("event:"):
                        current_event = line[6:].strip()
                    elif line.startswith("data:"):
                        current_data = line[5:].strip()
                    elif line == "":
                        if current_event and current_data:
                            try:
                                parsed = json.loads(current_data)
                                if current_event == "results":
                                    ranked = parsed.get("ranked", [])
                                    quality = parsed.get("quality")
                                elif current_event == "partial_results":
                                    if not ranked:
                                        ranked = parsed.get("ranked", [])
                                elif current_event == "error":
                                    error = parsed.get("message")
                            except json.JSONDecodeError:
                                pass
                        current_event = ""
                        current_data = ""

    except Exception as e:
        error = str(e)

    elapsed = time.time() - start

    # Bucket distribution
    buckets = {"top_match": 0, "strong_match": 0, "good_match": 0}
    for r in ranked:
        bucket = r.get("bucket", "good_match")
        if bucket in buckets:
            buckets[bucket] += 1

    # Top 15 accounts (summary data only)
    top_accounts = []
    for i, r in enumerate(ranked[:15]):
        top_accounts.append({
            "rank": i + 1,
            "handle": r.get("handle", ""),
            "bucket": r.get("bucket", ""),
            "followers_count": r.get("followers_count", 0),
            "summary": r.get("summary", "")[:200],
        })

    return {
        "ranked": ranked,
        "total_results": len(ranked),
        "buckets": buckets,
        "quality": quality,
        "elapsed_seconds": round(elapsed, 1),
        "top_accounts": top_accounts,
        "error": error,
    }


def check_expected_accounts(ranked: list[dict], expected: list[str]) -> dict:
    """Check how many expected accounts were found in results."""
    if not expected:
        return {"found": [], "missing": [], "hit_rate": 1.0}

    result_handles = {r.get("handle", "").lower() for r in ranked}
    found = [h for h in expected if h.lower() in result_handles]
    missing = [h for h in expected if h.lower() not in result_handles]
    hit_rate = len(found) / len(expected)

    return {"found": found, "missing": missing, "hit_rate": hit_rate}


# ── Git metadata ─────────────────────────────────────────────────────────────


def get_git_metadata() -> dict:
    """Capture current git state."""
    meta = {"git_commit": "", "git_branch": "", "git_message": ""}
    try:
        meta["git_commit"] = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        meta["git_branch"] = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        meta["git_message"] = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%s"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return meta


# ── Composite score ──────────────────────────────────────────────────────────


def compute_composite_score(query_results: list[dict]) -> float:
    """Compute composite score (0-100) from query results.

    Components:
    - Quality distribution (40%): strong_count / total * 40
    - Bucket quality (30%): avg((top + strong) / total_results) * 30
    - Result count (15%): queries_meeting_minimum / total * 15
    - Expected account hit rate (15%): avg(hit_rate) * 15
    """
    total = len(query_results)
    if total == 0:
        return 0.0

    # Quality distribution (40%)
    strong_count = sum(1 for q in query_results if q.get("quality") == "strong")
    quality_score = (strong_count / total) * 40

    # Bucket quality (30%)
    bucket_ratios = []
    for q in query_results:
        t = q.get("total_results", 0)
        if t > 0:
            b = q.get("buckets", {})
            top_strong = b.get("top_match", 0) + b.get("strong_match", 0)
            bucket_ratios.append(top_strong / t)
        else:
            bucket_ratios.append(0.0)
    bucket_score = (sum(bucket_ratios) / len(bucket_ratios)) * 30 if bucket_ratios else 0.0

    # Result count (15%)
    met_min = sum(1 for q in query_results if q.get("met_minimum", False))
    count_score = (met_min / total) * 15

    # Expected account hit rate (15%)
    hit_rates = [q["expected_accounts"]["hit_rate"] for q in query_results if "expected_accounts" in q]
    hit_score = (sum(hit_rates) / len(hit_rates)) * 15 if hit_rates else 15.0  # Full marks if no expected

    return round(quality_score + bucket_score + count_score + hit_score, 1)


# ── Run command ──────────────────────────────────────────────────────────────


def cmd_run(args):
    """Run benchmark queries and save a snapshot."""
    server = args.server

    # Health check
    try:
        health = httpx.get(f"{server}/api/health", timeout=5).json()
        if not health.get("ok"):
            print(f"Server health check failed: {health.get('errors')}")
            sys.exit(1)
    except Exception as e:
        print(f"Cannot reach server at {server}: {e}")
        sys.exit(1)

    # Load queries
    if args.queries:
        benchmarks = [
            {"query": q, "expected_accounts": [], "min_results": 1, "category": "ad_hoc"}
            for q in args.queries
        ]
    else:
        with open(BENCHMARK_FILE) as f:
            benchmarks = json.load(f)

    total = len(benchmarks)
    print(f"Running {total} queries against {server}\n")

    # Header
    print(
        f"{'#':<4} {'Query':<45} {'Results':<8} {'Top':<5} {'Strong':<7} "
        f"{'Quality':<9} {'Time':<7} {'Hits':<6}"
    )
    print("-" * 95)

    query_results = []
    for i, benchmark in enumerate(benchmarks):
        query_text = benchmark["query"]
        print(f"{i:<4} {query_text[:44]:<45}", end="", flush=True)

        result = run_single_query(server, query_text)

        # Expected accounts
        expected = benchmark.get("expected_accounts", [])
        hit_info = check_expected_accounts(result["ranked"], expected)

        # Build query result record
        qr = {
            "query": query_text,
            "category": benchmark.get("category", "unknown"),
            "elapsed_seconds": result["elapsed_seconds"],
            "total_results": result["total_results"],
            "buckets": result["buckets"],
            "quality": result["quality"],
            "met_minimum": result["total_results"] >= benchmark.get("min_results", 0),
            "expected_accounts": hit_info,
            "top_accounts": result["top_accounts"],
            "error": result.get("error"),
        }
        query_results.append(qr)

        # Print row
        b = result["buckets"]
        q = result.get("quality") or "?"
        hit_str = f"{hit_info['hit_rate']:.0%}" if expected else "-"
        print(
            f"{result['total_results']:<8} "
            f"{b['top_match']:<5} "
            f"{b['strong_match']:<7} "
            f"{q:<9} "
            f"{result['elapsed_seconds']:<7} "
            f"{hit_str:<6}"
        )

        if result.get("error"):
            print(f"     ERROR: {result['error']}")

    # Summary
    print("\n" + "=" * 95)

    quality_dist = {}
    for qr in query_results:
        q = qr.get("quality") or "unknown"
        quality_dist[q] = quality_dist.get(q, 0) + 1

    avg_results = sum(qr["total_results"] for qr in query_results) / total if total else 0
    avg_time = sum(qr["elapsed_seconds"] for qr in query_results) / total if total else 0
    error_count = sum(1 for qr in query_results if qr.get("error"))

    composite = compute_composite_score(query_results)

    print(f"Composite Score: {composite}/100")
    print(f"Quality: {quality_dist}")
    print(f"Avg results: {avg_results:.1f}  |  Avg time: {avg_time:.1f}s  |  Errors: {error_count}")

    # Build snapshot
    git = get_git_metadata()
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    snapshot = {
        "metadata": {
            "timestamp": timestamp,
            "label": args.label or "",
            "git_commit": git["git_commit"],
            "git_branch": git["git_branch"],
            "git_message": git["git_message"],
        },
        "query_results": query_results,
        "summary": {
            "composite_score": composite,
            "quality_distribution": quality_dist,
            "avg_results": round(avg_results, 1),
            "avg_time_seconds": round(avg_time, 1),
            "error_count": error_count,
        },
    }

    # Save snapshot
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
    snapshot_path = SNAPSHOTS_DIR / filename
    with open(snapshot_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    print(f"\nSnapshot saved: {snapshot_path}")


# ── Compare command ──────────────────────────────────────────────────────────


def load_snapshot(path: Path) -> dict:
    """Load and return a snapshot from disk."""
    with open(path) as f:
        return json.load(f)


def get_sorted_snapshots() -> list[Path]:
    """Return snapshot files sorted by name (newest last)."""
    if not SNAPSHOTS_DIR.exists():
        return []
    return sorted(SNAPSHOTS_DIR.glob("*.json"))


def cmd_compare(args):
    """Compare two snapshots and show deltas."""
    snapshots = get_sorted_snapshots()

    if args.base:
        base_path = Path(args.base)
        if not base_path.is_absolute():
            base_path = Path(__file__).parent / base_path
        if not base_path.exists():
            print(f"Base snapshot not found: {base_path}")
            sys.exit(1)
    else:
        if len(snapshots) < 2:
            print(f"Need at least 2 snapshots to compare (found {len(snapshots)}).")
            print("Run `python3 tests/eval.py run` to create snapshots.")
            sys.exit(1)
        base_path = snapshots[-2]

    if args.current:
        current_path = Path(args.current)
        if not current_path.is_absolute():
            current_path = Path(__file__).parent / current_path
        if not current_path.exists():
            print(f"Current snapshot not found: {current_path}")
            sys.exit(1)
    else:
        if not snapshots:
            print("No snapshots found.")
            sys.exit(1)
        current_path = snapshots[-1]

    if base_path == current_path:
        print("Base and current snapshot are the same file.")
        sys.exit(1)

    base = load_snapshot(base_path)
    current = load_snapshot(current_path)

    base_meta = base["metadata"]
    curr_meta = current["metadata"]

    # Header
    print()
    print("\u2550\u2550 Eval Comparison " + "\u2550" * 58)
    base_label = f' "{base_meta["label"]}"' if base_meta.get("label") else ""
    curr_label = f' "{curr_meta["label"]}"' if curr_meta.get("label") else ""
    print(f'Base:    {base_meta["timestamp"][:16]} ({base_meta["git_commit"]}){base_label}')
    print(f'Current: {curr_meta["timestamp"][:16]} ({curr_meta["git_commit"]}){curr_label}')
    print()

    # Composite score
    base_score = base["summary"]["composite_score"]
    curr_score = current["summary"]["composite_score"]
    delta = curr_score - base_score
    direction = "\u2191 IMPROVED" if delta > 0.5 else ("\u2193 REGRESSED" if delta < -0.5 else "  UNCHANGED")
    sign = "+" if delta > 0 else ""
    print(f"Composite Score: {base_score} \u2192 {curr_score} ({sign}{delta:.1f}) {direction}")
    print()

    # Build lookup for base queries
    base_by_query = {qr["query"]: qr for qr in base["query_results"]}
    curr_by_query = {qr["query"]: qr for qr in current["query_results"]}

    # All queries in order (current first, then any base-only)
    all_queries = list(curr_by_query.keys())
    for q in base_by_query:
        if q not in curr_by_query:
            all_queries.append(q)

    # Table header
    print(
        f"{'Query':<42} {'Results':<10} {'Top':<8} {'Strong':<9} "
        f"{'Quality':<14} {'Time':<10}"
    )
    print("\u2500" * 95)

    improvements = []
    regressions = []
    unchanged = []

    for query_text in all_queries:
        bq = base_by_query.get(query_text)
        cq = curr_by_query.get(query_text)

        if not bq or not cq:
            # Query only in one snapshot
            label = query_text[:41]
            if cq and not bq:
                print(f"{label:<42} {'(new)':<10}")
            elif bq and not cq:
                print(f"{label:<42} {'(removed)':<10}")
            continue

        # Compute deltas
        def fmt_delta(old, new, suffix="", invert=False):
            """Format a before→after with arrow. invert=True means lower is better."""
            d = new - old
            if abs(d) < 0.01:
                arrow = " "
            elif (d > 0) != invert:
                arrow = "\u2191"
            else:
                arrow = "\u2193"
            return f"{old}{suffix}\u2192{new}{suffix}{arrow}"

        results_str = fmt_delta(bq["total_results"], cq["total_results"])
        top_str = fmt_delta(
            bq["buckets"].get("top_match", 0), cq["buckets"].get("top_match", 0)
        )
        strong_str = fmt_delta(
            bq["buckets"].get("strong_match", 0), cq["buckets"].get("strong_match", 0)
        )

        bq_qual = bq.get("quality") or "?"
        cq_qual = cq.get("quality") or "?"
        if bq_qual == cq_qual:
            qual_str = bq_qual
        else:
            qual_order = {"strong": 3, "moderate": 2, "weak": 1, "?": 0}
            arrow = "\u2191" if qual_order.get(cq_qual, 0) > qual_order.get(bq_qual, 0) else "\u2193"
            qual_str = f"{bq_qual}\u2192{cq_qual}{arrow}"

        time_str = fmt_delta(bq["elapsed_seconds"], cq["elapsed_seconds"], "s", invert=True)

        label = query_text[:41]
        print(f"{label:<42} {results_str:<10} {top_str:<8} {strong_str:<9} {qual_str:<14} {time_str:<10}")

        # Classify
        signals = 0
        signals += (cq["total_results"] - bq["total_results"])
        signals += (cq["buckets"].get("top_match", 0) - bq["buckets"].get("top_match", 0)) * 3
        signals += (cq["buckets"].get("strong_match", 0) - bq["buckets"].get("strong_match", 0)) * 2

        qual_order = {"strong": 3, "moderate": 2, "weak": 1}
        signals += (qual_order.get(cq_qual, 0) - qual_order.get(bq_qual, 0)) * 5

        cq_hit = cq.get("expected_accounts", {}).get("hit_rate", 1.0)
        bq_hit = bq.get("expected_accounts", {}).get("hit_rate", 1.0)
        signals += int((cq_hit - bq_hit) * 10)

        if signals > 1:
            improvements.append(query_text)
        elif signals < -1:
            regressions.append(query_text)
        else:
            unchanged.append(query_text)

    # Summary
    print()
    if improvements:
        print(f"Improvements ({len(improvements)}): {', '.join(q[:30] for q in improvements)}")
    if regressions:
        print(f"Regressions ({len(regressions)}): {', '.join(q[:30] for q in regressions)}")
    if unchanged:
        print(f"Unchanged ({len(unchanged)}): {', '.join(q[:30] for q in unchanged)}")
    print()


# ── List command ─────────────────────────────────────────────────────────────


def cmd_list(args):
    """List all saved snapshots."""
    snapshots = get_sorted_snapshots()

    if not snapshots:
        print("No snapshots found. Run `python3 tests/eval.py run` to create one.")
        return

    print(f"\n{'#':<4} {'Timestamp':<20} {'Commit':<10} {'Score':<8} {'Queries':<9} {'Label'}")
    print("-" * 80)

    for i, path in enumerate(snapshots):
        snap = load_snapshot(path)
        meta = snap["metadata"]
        summary = snap["summary"]
        label = meta.get("label", "")
        num_queries = len(snap.get("query_results", []))
        print(
            f"{i:<4} {meta['timestamp'][:19]:<20} {meta['git_commit']:<10} "
            f"{summary['composite_score']:<8} {num_queries:<9} {label}"
        )

    print()


# ── CLI ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Evaluation & regression testing for Twitter Account Finder"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run
    run_parser = subparsers.add_parser("run", help="Run benchmark queries and save snapshot")
    run_parser.add_argument("--label", default="", help="Descriptive label for this snapshot")
    run_parser.add_argument("--queries", nargs="+", help="Ad-hoc queries (overrides benchmark file)")
    run_parser.add_argument("--server", default=DEFAULT_SERVER, help="Server URL")

    # compare
    compare_parser = subparsers.add_parser("compare", help="Compare two snapshots")
    compare_parser.add_argument("--base", help="Path to base snapshot (default: second most recent)")
    compare_parser.add_argument("--current", help="Path to current snapshot (default: most recent)")

    # list
    subparsers.add_parser("list", help="List all saved snapshots")

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "compare":
        cmd_compare(args)
    elif args.command == "list":
        cmd_list(args)


if __name__ == "__main__":
    main()
