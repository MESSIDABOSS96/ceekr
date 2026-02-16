# Twitter Account Finder — Complete Algorithm Documentation

## Overview

This is a tool that finds relevant Twitter/X accounts based on a natural language description. The user describes who they want to find (e.g., "ML engineers working on LLM fine-tuning") and the system returns a ranked list of real Twitter accounts matching that description. It uses a combination of Twitter data APIs (SocialData.tools), Claude LLM calls for intent analysis and ranking, and heuristic scoring for fast-path results.

## Architecture

- **Frontend**: Next.js App Router + Tailwind CSS v4 + shadcn/ui
- **Backend**: FastAPI with Server-Sent Events (SSE) streaming
- **LLM**: Anthropic Claude API — Haiku 4.5 for most calls (intent, queries, triage, ranking), Sonnet for chat refinement
- **Twitter Data**: SocialData.tools REST API via httpx (searches tweets, user profiles, timelines, follow lists)
- **Auth**: Optional Twitter OAuth 2.0 for network matching (follow/follower data)

The frontend POSTs to `/api/search` and reads an SSE stream. Events streamed back: `progress`, `intent`, `queries`, `results`, `error`.

---

## Step-by-Step Algorithm

### Step 0: Query Classification

When a search query arrives, it's first classified:

- **Handle Lookup** (`@username`): If the query starts with `@` and is a single token, it's treated as a direct profile lookup. The system fetches that user's profile + 10 timeline tweets and returns them immediately as a `top_match` with score 10. No LLM calls needed.
- **Full Search** (everything else): Proceeds through the full pipeline described below.

### Step 1: Parallel Execution — Two Legs

The system runs two independent search strategies in parallel:

**Leg A — Fast Path (User Search API, ~1-2 seconds):**
Immediately fires a user/profile search against the SocialData `search-users` endpoint using the raw query string. This returns user profiles matching by name/handle. Results are scored with a Python heuristic (no LLM). Additional bio-keyword searches are launched once the intent is extracted (see Step 2).

**Leg B — Full LLM Pipeline (slow, ~15-30 seconds):**
The deep search pipeline that uses Claude for intent extraction, query generation, and ranking.

Both legs produce ranked results that are merged at the end.

---

### Step 2: Intent Extraction + Query Generation (Single LLM Call)

A single Claude Haiku 4.5 call does both intent analysis and query generation using forced tool use. The LLM is given the user's search request and must call the `search_plan` tool with structured output.

**Input to LLM:**
- Who the user wants to find
- Why (optional context)

**Output (structured via tool_use):**

| Field | Description |
|---|---|
| `persona` | Type of person to find (e.g., "early-stage SaaS founders") |
| `topic` | What they should be discussing (e.g., "customer discovery challenges") |
| `goal` | Why the user wants to find them (inferred if not stated) |
| `specificity` | 1-5 scale: 1=very broad ("people in tech"), 5=very specific ("YC founders who pivoted in 2024") |
| `key_signals` | 3-5 specific observable signals to look for in tweets/bios (e.g., "mentions LoRA, QLoRA, or PEFT") |
| `anti_signals` | 2-3 disqualifiers (e.g., "only retweets news articles without commentary") |
| `bio_search_terms` | 3-4 short keyword phrases for user/profile searches (1-3 words each) |
| `mandatory_terms` | 0-3 niche-specific terms that MUST appear in results. Empty for broad queries. E.g., "langchain" for "langchain contributors", empty for "AI researchers" |
| `queries` | Exactly 5 Twitter search queries, each with `query`, `rationale`, and `angle` |

**Query generation rules enforced in the prompt:**
- Twitter search is very restrictive — a quoted phrase alone OR a quoted phrase + one keyword is the maximum complexity
- Never use parentheses, never combine more than 3 words with a quoted phrase
- Each query targets a different angle (builders, self-identification, teaching, opinions, community, discovery, experience, professional context)
- If the topic has specific niche terms, every query must include at least one of those terms
- Exclusion operators like `-job -hiring -giveaway` are used to reduce spam

**Mandatory terms fallback:**
If the LLM returns empty `mandatory_terms`, the server extracts niche terms from the raw query by filtering out a hardcoded set of ~80 generic words (roles like "researcher", "developer", fillers like "find", "looking", "best", etc.). Any remaining words longer than 2 characters become mandatory terms.

**Bio search extension (Leg A continued):**
Once intent is extracted, the `bio_search_terms` are used to launch additional user-search API calls in parallel. Bio terms are filtered to only keep those containing a mandatory term (if mandatory terms exist), to avoid overly broad profile searches.

### Step 3: Tweet Search Execution

The 5 generated queries are executed against the SocialData tweet search API **all in parallel**.

**Search type alternation:** Queries alternate 50/50 between "Top" (most relevant/popular) and "Latest" (most recent) search types. Odd-indexed queries use "Latest", even-indexed use "Top".

**Per query:** Up to 50 tweets are fetched. Each tweet comes with its author's profile data (handle, name, bio, followers, following, location, verified status, profile image, etc.).

**Deduplication:** Results across all queries are merged by user ID. Each unique user accumulates:
- All their tweets found across different queries (deduped by tweet ID)
- A list of which queries they matched

**Network info:** If the user is authenticated via Twitter OAuth, each account gets tagged with whether they follow the user, the user follows them, or they're mutual.

**Tweet sorting:** Each user's tweets are sorted by a blended recency+engagement score:
```
engagement = likes + 2 * retweets
decay = 0.5 ^ (days_old / 90)    # 90-day half-life
bonus = max(0, 30 - days_old)     # additive bonus for tweets < 30 days old
score = engagement * decay + bonus
```
Top 10 tweets per user are kept.

### Step 4: Fallback Queries (if needed)

If fewer than 15 unique accounts were found, the system generates 3 broader fallback queries via another Claude Haiku call. The prompt includes the original queries (to avoid repetition) and instructs the LLM to use more general terms, remove niche jargon, and try different phrasings. Fallback results are merged with existing accounts (new accounts only, no duplicates).

### Step 5: Pre-filtering (Python heuristics, no LLM)

Before sending accounts to the LLM for ranking, obvious noise is removed:

| Filter | Threshold |
|---|---|
| Minimum followers | < 10 followers → removed |
| Bot keywords in bio | "bot", "auto", "giveaway", "airdrop", "free followers", "follow back" |
| Suspicious ratio | following > 10x followers AND followers < 100 |
| No tweets | Accounts with zero collected tweets |
| Anti-signal match | Word-boundary regex match of anti_signals in bio |

The removed count is tracked for progress messaging.

### Step 6: LLM Ranking (Bucket Tier System)

Surviving accounts are ranked by Claude Haiku 4.5 using a **bucket tier system** (not numeric scores).

**Batching:** Accounts are split into batches of 40. All batches are ranked in parallel via concurrent LLM calls.

**Data sent to LLM per account:**
- Handle, name, bio (truncated to 150 chars)
- Followers count, following count, location, verified status
- `days_since_newest_tweet` (float) and `activity_status` ("active" if ≤30 days, "somewhat_active" if ≤180 days, "stale" if >180 days)
- Top 3 tweets (sorted by recency+engagement score), each truncated to 150 chars, with date, likes, retweets
- `matched_query_count` and up to 3 `matched_queries`
- `network_match` if applicable ("mutual", "you_follow", "follows_you")

**Bucket tiers:**

| Bucket | Description | Synthetic Score |
|---|---|---|
| `top_match` | Ideal result. IS the persona, ACTIVELY discusses exact topic, recent evidence (≤30 days). Best ~10-15% | 9.0 |
| `strong_match` | Right persona, discusses related topics. Slightly less recent (1-3 months) or slightly adjacent | 7.0 |
| `good_match` | Correct persona, weaker evidence. Older activity (3-6 months) or less direct | 5.0 |
| `exclude` | Irrelevant, spam, stale (>6 months), or anti-signal match | 2.0 |

**Ranking prompt evaluation criteria (in order):**

1. **Persona Gate (HARD FILTER):** Does the account match the described persona? Not adjacent, not related — the actual persona. If looking for "YC founders", an indie hacker is NOT a YC founder → exclude. This is evaluated first and overrides everything. Strictness scales with specificity (4-5 = strict, 1-2 = lenient).

2. **Topic Relevance:** Active discussion of the topic (not just one keyword mention). Key signals are checked for matches. Anti-signals trigger exclusion.

3. **Recency of Activity:** Each account has `days_since_newest_tweet` and `activity_status` fields. "stale" accounts (>6 months) should be good_match at best, never top_match or strong_match. "active" accounts (within 30 days) are significantly more valuable.

4. **Evidence Quality:** Multiple relevant tweets > one tweet. Original thoughts > retweets. High engagement relative to follower count = genuine influence.

5. **Network Match (if present):** "mutual" connection = slight boost. "you_follow" or "follows_you" = minor boost.

**Mandatory terms in ranking prompt:**
If mandatory terms exist, the prompt includes a "Key Relevance Terms" section telling the LLM that accounts mentioning these terms are significantly more likely to be relevant, and absence is a strong signal against relevance. If no mandatory terms, it says "Broad category search — match on overall relevance."

**LLM output per account:**
- `handle`: Twitter handle (without @)
- `bucket`: One of the four tiers
- `summary`: Natural language description — "Sarah builds payment infrastructure at Stripe and writes detailed threads on distributed systems." Top/strong get 2-3 sentences, good gets 1, exclude gets empty string.
- `highlight_tweet_indices`: 0-based indices into the recent_tweets array for the most relevant tweets. 2-3 for top/strong, 1-2 for good, empty for exclude.

### Step 7: Post-ranking Processing

**Sorting:** Results are sorted by bucket tier (top_match first), then by follower count as tiebreaker within each tier.

**Filtering:** Excluded accounts are removed from results.

**Specificity gate:** For high-specificity queries (specificity ≥ 4), `good_match` accounts are also dropped — only `top_match` and `strong_match` are returned.

### Step 8: Result Merging (Fast Path + LLM Pipeline)

The two parallel legs are merged:

1. **LLM results are authoritative** — they go in first.
2. **Fast-path (user search) results:** Only included if the LLM also found the same account. In that case, if the fast-path scored a higher bucket, the bucket is upgraded. Fast-path-only results that the LLM didn't evaluate are **not included** (LLM judgment is the source of truth).
3. Excluded accounts are filtered out.
4. Final sort by bucket tier then followers.
5. Capped at 75 results max.

### Step 9: Quality Assessment

The final result set gets a quality label computed from bucket counts:

| Quality | Criteria |
|---|---|
| `strong` | ≥3 top_match AND (top + strong) ≥ 5 |
| `moderate` | ≥1 top_match OR (strong + good) ≥ 5 |
| `weak` | Everything else |

Weak results generate refinement suggestions like "Could you be more specific about what aspect of '{topic}' you're interested in?"

---

## Fast Path Scoring Details (Leg A)

The user search API returns lightweight profile data. Each result is enriched with a full profile lookup in parallel, then scored:

**Name match (0-40 pts):**
- Exact match: 40
- Query contained in name: 35
- All query words in name: 30
- Fuzzy match (SequenceMatcher ratio > 0.5): 40 * ratio

**Bio relevance (0-10 pts):**
- Any query word found in bio: 10

**Credibility (only if relevance > 0):**
- Followers: min(30, log10(followers) * 3.6)
- Verified: +10
- Tweet count > 100: +10; > 10: +5

Score is normalized to 1-10 scale (raw / 10), then bucketed: ≥8 = top_match, ≥6 = strong_match, else good_match.

**Handle guessing fallback:** If user search returns nothing, the system tries direct profile lookups by guessing handles from the query. For "elon musk" it tries: `elonmusk`, `elon_musk`, `muskelon`, `musk_elon`. Found profiles are scored with the same system.

---

## Tweet Recency Score (used for sorting tweets within an account)

```
engagement = likes + 2 * retweets
decay = 0.5 ^ (days_old / 90)       # 90-day half-life on engagement value
bonus = max(0, 30 - days_old)        # flat bonus for tweets < 30 days old
score = engagement * decay + bonus
```

Tweets with no date get `engagement * 0.1` (heavily penalized).

---

## Timeline Enrichment

After tweet-search deduplication, the system fetches each user's timeline (15 most recent tweets) via the user timeline API. Fetches run in batches of 20 concurrent requests. Timeline tweets are merged with search-found tweets (deduped by tweet ID), re-sorted by recency+engagement, and trimmed to top 10 per user.

---

## Chat Refinement (Post-Search)

After results are shown, users can chat to refine. This uses Claude Sonnet (not Haiku) with a system prompt scoped to only profile search operations.

Available tools the chat LLM can invoke:
- `run_search`: Run a new search with a different query
- `apply_filters`: Adjust filters (keywords, follower range, location, verified, posting frequency, account age)
- `remove_profiles`: Remove specific handles from results
- `respond`: Send a conversational response

The chat prompt includes current active filters and a summary of current results for context. Off-topic requests are declined.

---

## Configuration Constants

| Constant | Value | Purpose |
|---|---|---|
| `TWEETS_PER_QUERY` | 50 | Max tweets fetched per search query |
| `TIMELINE_TWEETS_COUNT` | 15 | Tweets fetched from user timeline |
| `MIN_FOLLOWERS_THRESHOLD` | 10 | Pre-filter minimum followers |
| `RANKING_BATCH_SIZE` | 40 | Accounts per LLM ranking batch |
| `MAX_TWEETS_FOR_RANKING` | 3 | Tweets sent to LLM per account |
| `MAX_TWEET_LENGTH` | 150 | Chars per tweet sent to LLM |
| `MAX_BIO_LENGTH` | 150 | Chars for bio sent to LLM |
| `FAST_PATH_MAX_RESULTS` | 75 | Maximum final results returned |
| `MIN_ACCOUNTS_BEFORE_FALLBACK` | 15 | Threshold to trigger fallback queries |
| `RECENCY_HALF_LIFE_DAYS` | 90 | Engagement decay half-life |
| `RECENCY_BONUS_WINDOW_DAYS` | 30 | Additive bonus window for recent tweets |
| `STALE_ACCOUNT_DAYS` | 180 | Days without tweets = "stale" signal |

---

## LLM Models Used

| Call | Model | Max Tokens |
|---|---|---|
| Search plan (intent + queries) | Haiku 4.5 | 2048 |
| Fallback query generation | Haiku 4.5 | 1024 |
| Triage (advance/skip) | Haiku 4.5 | 4096 |
| Ranking (bucket assignment) | Haiku 4.5 | 8192 |
| Chat refinement | Sonnet | 1024 |

All LLM calls use **forced tool choice** (`tool_choice: {"type": "tool", "name": "..."}`) to guarantee structured JSON output. Retries use exponential backoff (2-3 attempts depending on the call).

---

## End-to-End Flow Summary

```
User query
  │
  ├─ Classify: @handle? → Direct lookup → Return immediately
  │
  ├─ Leg A (fast, parallel):
  │    ├─ User search API → Enrich profiles → Score heuristically
  │    └─ (after intent) Bio keyword searches → Score heuristically
  │
  └─ Leg B (slow, sequential within):
       ├─ LLM: Extract intent + generate 5 queries (1 call)
       ├─ Execute 5 tweet searches (parallel, 50/50 Top/Latest)
       ├─ Fallback: if <15 accounts, generate 3 broader queries + search
       ├─ Pre-filter: remove bots, low-followers, anti-signals
       └─ LLM: Rank into buckets (batches of 40, parallel)
  │
  Merge Leg A + Leg B (LLM authoritative)
  │
  Drop good_match if specificity ≥ 4
  │
  Quality assessment (strong/moderate/weak)
  │
  Stream results to frontend via SSE
```
