# X (Twitter) API Access, Data Scraping Legality & Enrichment Options

**Research Date:** February 2026
**Purpose:** Commercial product that finds people on Twitter using search queries

---

## Table of Contents

1. [Official X API Tiers](#1-official-x-api-tiers)
2. [Third-Party Data Providers](#2-third-party-data-providers)
3. [Scraping Legality](#3-scraping-legality)
4. [Data Enrichment (Twitter Handle to Lead Data)](#4-data-enrichment)
5. [Cost Modeling](#5-cost-modeling)
6. [SocialData.tools vs. Official API](#6-socialdata-tools-vs-official-api)
7. [Risk Mitigation & Fallback Strategy](#7-risk-mitigation--fallback-strategy)

---

## 1. Official X API Tiers

As of early 2026, the X (Twitter) API has four tiers plus a new pay-per-use pilot.

### Tier Comparison

| Feature | Free | Basic | Pro | Enterprise |
|---|---|---|---|---|
| **Monthly Cost** | $0 | $200/mo | $5,000/mo ($4,500 annual) | $42,000+/mo (negotiable) |
| **Read Posts/mo** | ~1 req/day (very limited) | 15,000 | 1,000,000 | Custom (millions+) |
| **Write Posts/mo** | 500 | 50,000 | 300,000 | Custom |
| **App Environments** | 1 | 2 | 3 | Custom |
| **Search Type** | None | Recent (7 days) | Full Archive (since 2006) | Full Archive |
| **Search Rate Limit** | N/A | 60 req/15 min | 60 rpm | 120 rpm |
| **Streaming (Filtered)** | No | No | Yes (1 rule) | Yes (many rules) |
| **Full-Archive Search** | No | No | Yes | Yes |
| **Posts per Search Response** | N/A | 100 max | 500 max | 500 max |

### Key Details

- **Free tier** is essentially write-only. It is practically useless for a search product.
- **Basic tier** ($200/mo) gives you 15,000 post reads per month and search limited to the last 7 days. For a product that does 10,000 searches/month, you would quickly exhaust the read quota. No full-archive search.
- **Pro tier** ($5,000/mo) is the minimum viable tier for a search product. It provides 1M post reads, full-archive search back to March 2006, and real-time filtered streaming with 1 rule.
- **Enterprise tier** ($42,000+/mo) offers custom volumes, dedicated support, SLAs, and higher rate limits. Previously priced at $50,000/mo; X has reportedly adjusted pricing to attract developers back.
- **Pay-Per-Use Pilot** (closed beta, launched Nov 2025): Consumption-based pricing similar to AWS. Per-operation charges instead of flat monthly fees. Not broadly available yet. Worth monitoring via [@XDevelopers](https://x.com/XDevelopers).

### Search-Specific Limitations

- Basic: `GET /2/tweets/search/recent` only (7-day window), 10 req/15 min for app-only auth
- Pro: `GET /2/tweets/search/all` (full archive), 1 req/sec, 300 req/15 min
- Rate limits are per-app and per 15-minute window

**Sources:**
- [X API Rate Limits](https://docs.x.com/x-api/fundamentals/rate-limits)
- [X API Pricing (via getlate.dev)](https://getlate.dev/blog/twitter-api-pricing)
- [Elfsight X API Guide 2026](https://elfsight.com/blog/how-to-get-x-twitter-api-key-in-2026/)
- [TwitterAPI.io Official Tiers Analysis](https://twitterapi.io/blog/twitter-api-pricing-2025)
- [Social Media Today - X API Pay-Per-Use](https://www.socialmediatoday.com/news/x-formerly-twitter-launches-usage-based-api-access-charges/803315/)

---

## 2. Third-Party Data Providers

### Provider Comparison

| Provider | Pricing Model | Cost per 1K Tweets | Cost per 1K Profiles | Rate Limits | Full Archive? | Legal Standing |
|---|---|---|---|---|---|---|
| **SocialData.tools** | Pay-per-result | $0.20 | $0.20 | 120 req/min (raisable) | Yes (public data) | Complied with X legal (deprecated non-public endpoints) |
| **TwitterAPI.io** | Pay-per-result | $0.15 | $0.18 | 1,000+ req/sec | Yes | Unclear; newer entrant |
| **Bright Data** | Pay-per-record | $1.50 (scraped) / $2.50 (dataset) | Similar | High (managed infra) | Yes | Won lawsuit vs. X (May 2024) |
| **Apify** | Pay-per-result | $0.25-$0.40 | Varies | 30-80 tweets/sec | Yes | Marketplace model; actor-dependent |
| **RapidAPI (various)** | Subscription + per-req | Varies ($0.001-$0.01/req) | Varies | Provider-dependent | Varies | Wrapper APIs; quality inconsistent |

### Detailed Provider Profiles

#### SocialData.tools (Current Provider)
- **Pricing:** $0.0002/tweet or user ($0.20 per 1,000 items). No subscription. No minimum spend.
- **Rate Limits:** 120 req/min shared across endpoints. Higher limits available on request (free).
- **Endpoints:** Search tweets, get tweet details, user profile, user tweets/replies, followers/following, community tweets. Supports all Twitter search operators.
- **Legal:** Deprecated non-public data endpoints at X Legal Team's request. Now only serves publicly available data (no login required on X).
- **Reliability:** Maintains a [status page](https://status.socialdata.tools/). No documented major outages found.
- **Docs:** [docs.socialdata.tools](https://docs.socialdata.tools/)

#### TwitterAPI.io
- **Pricing:** $0.15/1K tweets, $0.18/1K profiles, $0.15/1K followers. Credits: $1 = 100,000 credits. Credits never expire.
- **Performance:** Sub-second latency (500-800ms). 99.99% uptime SLA. Global infrastructure (12+ regions).
- **Features:** REST API + WebSocket + Webhook. Full archive search. No Twitter auth required.
- **Docs:** [docs.twitterapi.io](https://docs.twitterapi.io/)
- **Note:** Claims 96% cheaper than official API. Relatively newer entrant; long-term reliability unproven.

#### Bright Data
- **Pricing:** $1.50/1K records (on-demand scraper), $2.50/1K records (pre-built datasets).
- **Approach:** Managed scraping infrastructure. Browser-level scraping with proxy networks.
- **Legal:** Won landmark case vs. X Corp (May 2024). Strong legal standing for public data scraping.
- **Latency:** Higher than API-based providers (scraping-based). Better for batch/bulk than real-time.
- **Free trial** available.

#### Apify
- **Pricing:** $0.25-$0.40/1K tweets depending on the Actor used. Multiple scrapers available.
- **Actors:** Tweet Scraper V2 ($0.40/1K), Cheapest Twitter Scraper ($0.25/1K), Scweet ($0.30/1K).
- **Speed:** 30-80 tweets/sec for bulk extraction.
- **Approach:** Cloud-hosted scraper marketplace. No API key needed.
- **Risk:** Individual actors are maintained by different developers. Quality and uptime varies.

#### RapidAPI Endpoints
- **Pricing:** Varies by provider. Some free tiers available.
- **Quality:** Highly inconsistent. Many endpoints are unreliable or slow.
- **Use case:** Prototyping only. Not recommended for production commercial use.

**Sources:**
- [SocialData Pricing](https://docs.socialdata.tools/getting-started/pricing/)
- [TwitterAPI.io Pricing](https://twitterapi.io/pricing)
- [Bright Data Twitter Scraper](https://brightdata.com/products/web-scraper/twitter)
- [Apify Tweet Scraper V2](https://apify.com/apidojo/tweet-scraper)
- [Netrows Provider Comparison 2026](https://www.netrows.com/blog/top-twitter-x-data-api-providers-2026)
- [Data365 API Comparison](https://data365.co/blog/twitter-apis-vs-private-api)

---

## 3. Scraping Legality

### Key Legal Precedents

#### X Corp v. Bright Data (2024) -- The Most Relevant Case

- **Court:** U.S. District Court, Northern District of California
- **Ruling (May 2024):** Judge dismissed X's breach of contract and tort claims against Bright Data for scraping public X data.
- **Key Holding:** X failed to allege a valid claim based on access to its **public site**. Claims that scraping breached X's Terms of Use were found to be **preempted by the Copyright Act** under the doctrine of "conflict preemption."
- **Meaning:** X (Twitter) does not own user-generated content and cannot unilaterally restrict access to publicly available information through ToS alone.
- **Caveat (Nov 2024):** X was allowed to amend some claims, arguing Bright Data's "sophisticated efforts" to access the platform caused harm. The case is still partially active.
- **Bright Data's counterclaims:** Accused X of monopolizing public data access.

#### hiQ Labs v. LinkedIn (Ninth Circuit, 2022)

- **Ruling:** Scraping publicly available data does not violate the CFAA. The Ninth Circuit held that accessing publicly available data on a computer system generally permitted public access is not "without authorization."
- **Supreme Court alignment:** Consistent with Van Buren v. United States (2021), which narrowed the CFAA's scope.
- **Settlement (Dec 2022):** Case settled, but the CFAA holding remains influential precedent.
- **Contract law caveat:** The district court found that contract law (LinkedIn ToS) could still restrict scraping, even if CFAA cannot.

#### Meta v. Bright Data (2024)

- **Ruling (Jan 2024):** Federal judge rejected Meta's claims against Bright Data for scraping public Facebook/Instagram data. Meta's ToS do not prohibit scraping of public data when accessed while **logged out**.

### Current Legal Framework Summary

| Legal Theory | Risk Level for Our Use Case | Notes |
|---|---|---|
| **CFAA (Computer Fraud & Abuse Act)** | LOW | Public data scraping is not "unauthorized access" per Van Buren, hiQ, and Bright Data rulings. |
| **Breach of Contract (ToS)** | MODERATE | X ToS prohibit scraping. Contract claims can still be viable even when CFAA fails. But X lost on this theory against Bright Data. |
| **Copyright** | LOW | User tweets are not X's copyrighted content. X cannot assert copyright over user-generated posts. |
| **State Unfair Competition** | LOW-MODERATE | Possible if scraping is characterized as "free-riding." Not yet successful against scrapers of public data. |
| **GDPR/CCPA (Privacy)** | MODERATE | Applies if processing personal data of EU/CA users. Public availability does not eliminate privacy obligations. |

### ToS Risks Specific to Our Product

1. **We don't scrape directly.** We use SocialData.tools, which handles data retrieval. This adds a layer of indirection, but does not eliminate risk.
2. **X's ToS (Section 4)** prohibit using automated means to access the service, and restrict commercial redistribution of X data.
3. **Practical risk is low** because:
   - X has not successfully sued a third-party data provider out of existence
   - The Bright Data ruling is strongly favorable
   - We access only public data (no login, no private tweets)
   - We don't redistribute raw data; we provide curated recommendations

**Sources:**
- [CNBC - X Loses Lawsuit Against Bright Data](https://www.cnbc.com/2024/05/10/elon-musks-x-loses-lawsuit-against-bright-data-over-data-scraping.html)
- [Proskauer - Dismissal of Scraping Claims](https://www.proskauer.com/release/proskauer-secures-dismissal-of-scraping-claims-against-bright-data)
- [Skadden - Copyright Preemption in Data Scraping](https://www.skadden.com/insights/publications/2024/05/district-court-adopts-broad-view)
- [Wikipedia - hiQ Labs v. LinkedIn](https://en.wikipedia.org/wiki/HiQ_Labs_v._LinkedIn)
- [EFF - hiQ v. LinkedIn Victory](https://www.eff.org/deeplinks/2019/09/victory-ruling-hiq-v-linkedin-protects-scraping-public-data)
- [Finnegan - Data Scraping Claims Analysis](https://www.finnegan.com/en/insights/blogs/incontestable/data-scraping-claims-cfaa-out-contract-and-copyright-in.html)
- [GroupBWT - Web Scraping Legal Issues 2025](https://groupbwt.com/blog/is-web-scraping-legal/)

---

## 4. Data Enrichment

### Can You Go From Twitter Handle to Full Lead Data?

**Short answer: Partially, with 30-70% success rates depending on the data field.**

Twitter profiles contain: name, bio, location, website URL, follower count, and sometimes email (if public). The challenge is bridging from a social handle to structured business data (email, company, job title).

### Enrichment Provider Comparison

| Provider | Input: Twitter Handle? | Email Accuracy | Company/Title? | Pricing | Notes |
|---|---|---|---|---|---|
| **Hunter.io** | No (email/domain input) | 95%+ for domain search | Company yes, title limited | $34-$299/mo (500-25K credits) | Best for domain-based email finding. Cannot take Twitter handle as input. |
| **Apollo.io** | Indirect (search by name) | 70-80% | Yes (275M+ contacts DB) | Free tier; Pro $1,000/mo for API | Large contact DB. Twitter handle not a direct input. Match by name + company. |
| **People Data Labs** | Yes (Twitter URL input) | Moderate | Yes (3B+ person profiles) | $0.004/record; Pro $98/mo (350 credits) | Supports Twitter URL as enrichment input. Best direct path from handle to data. |
| **Proxycurl** | Yes (Twitter URL input) | Good (via LinkedIn cross-ref) | Yes | ~$0.01/request | **Discontinued.** Founder moved to NinjaPear. Not viable. |
| **Clearbit (Breeze Intelligence)** | Indirect (email input) | High | Yes | HubSpot-bundled; ~$0.15-$1/enrichment | Now part of HubSpot. Requires email first. |
| **FullContact** | Yes (social profiles) | 91% match rate | Limited | Tiered; ~$0.01/match | Social profile resolution. Good for identity matching. |
| **Enricher.io** | Yes (social profiles) | Moderate | Yes | Pay-per-result | Social-first enrichment. |

### Realistic Pipeline: Twitter Handle to Lead Data

```
Twitter Handle (@username)
    │
    ├─ Step 1: Extract from Twitter profile
    │   └─ Name, bio, location, website URL, follower count
    │       (available via SocialData.tools for $0.0002)
    │
    ├─ Step 2: Enrich via People Data Labs
    │   └─ Input: Twitter URL + name
    │   └─ Output: email, company, title, LinkedIn URL
    │   └─ Success rate: ~30-50% match rate
    │   └─ Cost: $0.004/record
    │
    ├─ Step 3 (optional): If website URL found, use Hunter.io
    │   └─ Input: domain from website URL
    │   └─ Output: email addresses at that domain
    │   └─ Success rate: ~60-80% for companies with public emails
    │   └─ Cost: 1 credit per lookup ($0.01-$0.10)
    │
    └─ Step 4 (optional): Cross-reference via Apollo.io
        └─ Input: name + company (from step 2)
        └─ Output: verified email, phone, title
        └─ Success rate: 70-80% for business professionals
        └─ Cost: 1 credit per enrichment
```

### Key Insight

The Twitter-handle-to-email pipeline is inherently lossy. Expect 30-50% overall success rates for getting a verified work email from just a Twitter handle. Success rates are much higher (70%+) for business professionals and tech workers who maintain LinkedIn profiles, and much lower for casual Twitter users, pseudonymous accounts, or non-English-speaking users.

**Sources:**
- [Hunter.io Pricing](https://hunter.io/pricing)
- [Apollo.io People Enrichment API](https://docs.apollo.io/reference/people-enrichment)
- [People Data Labs Person Enrichment](https://docs.peopledatalabs.com/docs/input-parameters-person-enrichment-api)
- [People Data Labs Pricing](https://www.peopledatalabs.com/pricing/person)
- [Coefficient - Top 13 Data Enrichment APIs 2025](https://coefficient.io/top-data-enrichment-apis)
- [Dropcontact Email Finder Benchmark 2025](https://www.dropcontact.com/email-finder-benchmark)

---

## 5. Cost Modeling

### Assumptions

- 1,000 users
- 10 searches per user per month = **10,000 searches/month**
- 5 search queries per search = **50,000 queries/month**
- ~20 tweets per query = **1,000,000 tweets retrieved/month**
- ~200 unique accounts surfaced per search (after dedup) = ~2,000,000 profile lookups/month (upper bound, realistically much lower due to dedup across queries within a search)
- Realistic unique tweet volume after dedup: ~500,000-750,000 tweets/month

### Data Layer Cost Estimates

| Provider | Tweet Cost | Profile Cost | Total Monthly Estimate | Notes |
|---|---|---|---|---|
| **SocialData.tools** | $0.20/1K = $150-$200 | Included in tweet results | **$150-$200/mo** | Tweets include embedded user objects. No separate profile call needed for basic data. |
| **TwitterAPI.io** | $0.15/1K = $112-$150 | $0.18/1K for separate calls | **$112-$200/mo** | Slightly cheaper per tweet. Profile calls extra if needed. |
| **Bright Data** | $1.50/1K = $1,125 | Included | **$1,125-$1,500/mo** | Significantly more expensive. Better for bulk batch jobs. |
| **Apify** | $0.25-$0.40/1K = $188-$300 | Varies | **$200-$400/mo** | Quality varies by actor. Not ideal for production real-time use. |
| **X Official (Basic)** | $200/mo flat, 15K reads | Included in reads | **$200/mo BUT only 15K reads** | Would exhaust quota in ~1.5% of needed volume. Not viable. |
| **X Official (Pro)** | $5,000/mo flat, 1M reads | Included in reads | **$5,000/mo** | Could work at this scale but expensive. Hits 1M read limit. |
| **X Official (Enterprise)** | $42,000+/mo | Included | **$42,000+/mo** | Overkill for this volume. |

### Full Stack Cost (Data + LLM + Enrichment)

| Component | Monthly Cost | Notes |
|---|---|---|
| **Twitter Data (SocialData.tools)** | $150-$200 | 750K tweets/month |
| **Claude API (Sonnet)** | $200-$500 | ~10K search intents + 10K ranking calls. ~$0.003/1K input tokens, $0.015/1K output tokens. |
| **Data Enrichment (optional, People Data Labs)** | $400-$1,000 | If enriching top 5 results per search = 50K enrichments at $0.004/ea = $200. With Hunter.io supplement: +$200-$800. |
| **Infrastructure (hosting)** | $50-$200 | VPS or cloud hosting for backend. |
| **Total (without enrichment)** | **$400-$900/mo** | |
| **Total (with enrichment)** | **$800-$1,900/mo** | |

### Cost Per Search

| Scenario | Total Monthly | Cost Per Search |
|---|---|---|
| Data only (SocialData + Claude) | $400-$700 | $0.04-$0.07 |
| Data + basic enrichment | $800-$1,200 | $0.08-$0.12 |
| Data + full enrichment pipeline | $1,200-$1,900 | $0.12-$0.19 |
| Official X API Pro + Claude | $5,200-$5,500 | $0.52-$0.55 |

### Scaling Considerations

At 10x scale (10,000 users, 100,000 searches/month):

| Provider | Monthly Cost |
|---|---|
| SocialData.tools | ~$1,500-$2,000 |
| TwitterAPI.io | ~$1,100-$1,500 |
| X Official Pro | $5,000 (but would exceed 1M read limit) |
| X Official Enterprise | $42,000+ |

Third-party providers scale linearly with usage. The official API has hard caps that require tier upgrades.

---

## 6. SocialData.tools vs. Official API

### Feature-by-Feature Comparison

| Feature | SocialData.tools | X Official API (Pro Tier) |
|---|---|---|
| **Cost for 1M tweets** | $200 | $5,000/mo (included in tier) |
| **Search Operators** | All Twitter search operators supported | Full query syntax (same operators) |
| **Full Archive** | Yes (public data) | Yes (Pro and Enterprise only) |
| **Search Results per Page** | ~20 (matches Twitter web pagination) | Up to 500 per response |
| **Rate Limits** | 120 req/min (raisable on request) | 60 rpm (Pro), 120 rpm (Enterprise) |
| **User Profile Fields** | name, screen_name, bio, location, followers_count, friends_count, profile_image_url, verified, created_at | Same fields + additional expansions (pinned_tweet_id, public_metrics, withheld) |
| **Tweet Fields** | id_str, full_text, created_at, source, user object, entities, retweet_count, favorite_count, media | Same + context_annotations, conversation_id, reply_settings, geo, non_public_metrics (author only) |
| **Authentication** | API key only | OAuth 2.0 App-Only or User Context |
| **Streaming** | Not available (polling only) | Filtered stream (Pro: 1 rule, Enterprise: many rules) |
| **Pagination** | Cursor-based (next_cursor) | Pagination token (next_token) |
| **Monthly Read Cap** | No cap (pay per result) | 1M posts (Pro), custom (Enterprise) |
| **Write Access** | No | Yes (post tweets, manage lists, etc.) |
| **DM Access** | No | Yes (Pro+) |
| **Non-Public Data** | No (deprecated by X Legal request) | Yes (with user auth: private metrics, DMs) |
| **SLA/Support** | Email support, status page | Dedicated support (Enterprise only) |
| **TOS Compliance** | Operates in legal gray area; complied with X legal demands | Fully compliant |

### Data Quality Comparison

- **Search relevance:** SocialData mirrors Twitter's own search relevance (it returns what Twitter's web search returns). The official API uses the same underlying search but offers additional filtering parameters.
- **Data freshness:** SocialData has near-real-time data (minutes of delay). The official API offers true real-time via streaming.
- **Missing from SocialData:** Streaming/firehose, conversation threading (partial), some extended entities, non-public metrics, write operations.
- **What SocialData does better:** No monthly caps, simpler auth, dramatically lower cost, no per-app rate limits that throttle growth.

### For Our Use Case Specifically

SocialData.tools is the better choice because:
1. We only need search + user profiles (both available).
2. We don't need write access or streaming.
3. The cost difference is 25x ($200 vs $5,000/mo).
4. No monthly read caps means we can scale without tier upgrades.
5. Search operators are identical to the official API.

**Sources:**
- [SocialData API Overview](https://docs.socialdata.tools/getting-started/overview/)
- [SocialData Search Endpoint](https://docs.socialdata.tools/reference/get-search-results/)
- [SocialData Rate Limits](https://docs.socialdata.tools/getting-started/rate-limits/)
- [X API Data Dictionary](https://docs.x.com/x-api/fundamentals/data-dictionary)

---

## 7. Risk Mitigation & Fallback Strategy

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| SocialData.tools gets shut down by X legal action | Low-Medium | Critical | Multi-provider architecture |
| SocialData.tools raises prices significantly | Low | Moderate | Provider abstraction layer |
| SocialData.tools has extended outage | Low | High | Automatic failover |
| X blocks SocialData's data access methods | Medium | Critical | Diversified provider pool |
| Legal action against our product directly | Very Low | Critical | Only use public data, add ToS disclaimers |
| X API pricing changes make official tier viable | Low | Positive | Monitor pay-per-use pilot |

### Recommended Fallback Architecture

```
                    ┌─────────────────────┐
                    │   TwitterDataClient  │  ← Abstraction layer
                    │   (interface/ABC)    │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐ ┌──────▼────────┐ ┌─────▼──────────┐
    │ SocialData     │ │ TwitterAPI.io │ │ Bright Data    │
    │ (Primary)      │ │ (Secondary)   │ │ (Tertiary)     │
    │ $0.20/1K       │ │ $0.15/1K      │ │ $1.50/1K       │
    └────────────────┘ └───────────────┘ └────────────────┘
```

### Implementation Strategy

#### 1. Provider Abstraction Layer

Create a `TwitterDataProvider` interface/protocol in Python:

```python
from abc import ABC, abstractmethod
from typing import List
from core.models import TweetResult, UserProfile

class TwitterDataProvider(ABC):
    @abstractmethod
    async def search_tweets(self, query: str, count: int = 20) -> List[TweetResult]:
        ...

    @abstractmethod
    async def get_user_profile(self, username: str) -> UserProfile:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
```

#### 2. Automatic Failover

```python
class ResilientTwitterClient:
    def __init__(self):
        self.providers = [
            SocialDataProvider(),      # Primary
            TwitterAPIioProvider(),    # Secondary
            BrightDataProvider(),      # Tertiary
        ]

    async def search_tweets(self, query: str) -> List[TweetResult]:
        for provider in self.providers:
            try:
                if await provider.health_check():
                    return await provider.search_tweets(query)
            except Exception:
                continue
        raise AllProvidersFailedError()
```

#### 3. Response Normalization

All providers return slightly different JSON shapes. Normalize into a common `TweetResult` model at the adapter level so the rest of the codebase is provider-agnostic.

#### 4. Monitoring & Alerting

- Health-check each provider every 5 minutes.
- Track per-provider error rates, latency, and cost.
- Alert when primary provider error rate exceeds 5%.
- Auto-switch to secondary after 3 consecutive failures.

#### 5. Data Caching

- Cache search results for identical queries within a 15-minute window.
- Cache user profiles for 24 hours (profile data changes slowly).
- This reduces provider dependency AND costs.

#### 6. Legal Risk Mitigation

- Only access and display publicly available data.
- Include clear Terms of Service stating data is sourced from public social media.
- Do not store or redistribute raw tweet content long-term.
- Add rate limiting to prevent abuse of the product being used as a scraping proxy.
- Comply promptly with any takedown or legal requests.

### Provider Onboarding Priority

1. **Now:** Continue with SocialData.tools as primary (working, tested, integrated).
2. **Next (within 1 month):** Implement the abstraction layer and add TwitterAPI.io as secondary. It has the closest pricing and API shape.
3. **Later (within 3 months):** Add Bright Data as tertiary. Higher cost but strongest legal standing (won lawsuit against X).
4. **Monitor:** X's pay-per-use pilot. If it launches broadly at competitive pricing, consider adding the official API as the most legally safe option.

### What If All Third-Party Providers Fail?

Worst-case scenario (X successfully shuts down all third-party data access):

1. **Official API (Pro tier):** $5,000/mo. Fully legal. Would require product pricing changes.
2. **X's pay-per-use pilot:** If available, could be more cost-effective than Pro tier.
3. **Pivot to multi-platform:** Expand to LinkedIn, Bluesky, Mastodon, Threads search. Reduces X dependency.
4. **User-authenticated approach:** Users connect their own X accounts via OAuth. Product searches on their behalf using their own API access. Eliminates the need for third-party data access but limits scale and UX.

**Sources:**
- [SocialData Terms & Conditions](https://socialdata.tools/legal/terms-and-conditions)
- [SocialData Status Page](https://status.socialdata.tools/)
- [TwitterAPI.io Documentation](https://docs.twitterapi.io/)
- [Bright Data Twitter Scraper](https://brightdata.com/products/web-scraper/twitter)
- [TechCrunch - Twitter Bans Third-Party Clients](https://techcrunch.com/2023/01/19/twitter-officially-bans-third-party-clients-after-cutting-off-prominent-devs/)

---

## Summary & Recommendations

### For the Twitter Account Finder Product:

1. **Stay with SocialData.tools** as the primary data provider. At $0.20/1K tweets with no monthly caps, it is 25x cheaper than the official Pro tier and sufficient for our search use case.

2. **Build the provider abstraction layer now.** This is the single most important risk mitigation. It costs only engineering time and protects against any single provider going down.

3. **Add TwitterAPI.io as a secondary provider.** At $0.15/1K tweets, it is actually cheaper than SocialData and offers similar capabilities. Having two providers dramatically reduces downtime risk.

4. **Data enrichment is a separate product decision.** The Twitter-handle-to-email pipeline has 30-50% success rates and adds $0.04-$0.12 per search in cost. Consider it a premium/paid feature rather than a default.

5. **Legal risk is manageable.** The Bright Data v. X ruling establishes strong precedent for accessing public data. Our indirect usage (via SocialData) adds additional distance. The key is to only use public data and not circumvent any access controls.

6. **At 1,000 users doing 10 searches/month, total data costs are approximately $150-$200/month** with SocialData.tools, making unit economics very favorable even at low price points.

7. **Monitor X's pay-per-use API pilot.** If it launches at competitive rates, it could become the most legally safe option without the $5,000/mo Pro tier commitment.
