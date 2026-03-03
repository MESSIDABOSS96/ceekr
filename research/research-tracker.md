# Research Tracker: Understanding How X Builds Businesses

**Date**: February 19, 2026
**Status**: All 7 topics researched. Ready for review.

---

## Table of Contents

1. [Topic 1: How X's Algorithm Works](#topic-1-how-xs-algorithm-works)
2. [Topic 2: How People Use X to Build Businesses](#topic-2-how-people-use-x-to-build-businesses)
3. [Topic 3: Sales Lead Generation Playbook on X](#topic-3-sales-lead-generation-playbook-on-x)
4. [Topic 4: X Chats and New Platform Features](#topic-4-x-chats-and-new-platform-features)
5. [Topic 5: Deep Competitive Analysis](#topic-5-deep-competitive-analysis)
6. [Topic 6: X API & Data Access](#topic-6-x-api--data-access)
7. [Topic 7: ICP Refinement & Positioning](#topic-7-icp-refinement--positioning)
8. [Cross-Topic Synthesis](#cross-topic-synthesis)

**Full research documents**: See `topic-*.md` files in this directory for complete findings with sources.

---

## Topic 1: How X's Algorithm Works

**Full document**: `topic-1-x-algorithm.md`

### Key Takeaways

**Search Ranking**
- Two modes: "Top" (engagement-weighted, favors established/Premium accounts) and "Latest" (chronological, no engagement threshold)
- Public engagement formula: `Likes x1 + Retweets x20 + Replies x13.5 + Profile Clicks x12 + Link Clicks x11 + Bookmarks x10`
- Reply-chains are the #1 signal: a reply that gets a reply from the author is worth **150x a like**
- Standard search only covers the **last 7 days**
- Premium accounts get priority in search results

**Recommendation Algorithm (For You)**
- 48M parameter neural network processing 500M daily tweets
- ~50% in-network, ~50% out-of-network content
- SimClusters: 145,000 virtual communities determine out-of-network content
- As of January 2026: replaced by Grok-powered transformer (Rust-based)

**Critical Numbers**
- **TweepCred**: Hidden 0-100 reputation score. Below 65 = only 3 tweets considered for distribution
- **Premium boost**: 4x in-network, 2x out-of-network visibility. ~10x total reach vs free accounts
- **Time decay**: Half-life of 6 hours. First 30 minutes are critical
- **Negative signals**: Report = -369x penalty, Block/mute = -74x penalty
- **Link penalty**: Since March 2026, non-Premium link posts get zero median engagement

**Implications for Our Tool**
- Our multi-query approach (3-7 queries) is well-aligned with how SimClusters work -- different phrasings catch different communities
- Using "Latest" for the last query is sound; consider 50/50 mix of Top/Latest
- Reply counts are better quality signals than likes (mirrors algorithm's 27:1 weighting)
- Premium accounts are over-represented in search results -- not necessarily a quality signal
- Link-sharers (researchers, journalists, curators) are systematically under-represented

---

## Topic 2: How People Use X to Build Businesses

**Full document**: `topic-2-x-business-use.md`

### Key Takeaways

**Business Use Cases (15+ identified)**
- Direct revenue: digital products via audience ($1M-$12.5M+/year), cohort courses ($100K-$500K+/year), social selling/DM outreach ($30K-$50K+/month)
- Discovery: sales prospecting, recruiting, PR/journalist outreach, investor relations, partnerships
- Intelligence: competitive monitoring, customer research, audience analysis
- Growth: build-in-public content marketing, community building, SEO/distribution

**The Business Builder Journey**
Canonical funnel: X (discovery) -> Newsletter (ownership) -> Low-ticket product -> High-ticket product -> Community/recurring revenue

**X vs LinkedIn vs Email**
- X wins on: speed, virality, accessibility, cultural relevance
- LinkedIn wins on: lead quality (85% ICP match vs 45% on X), B2B targeting, recruiting
- Email wins on: audience ownership, conversion rates
- Personal accounts get 100x more engagement than brand accounts

**Biggest Pain Points**
1. **Finding the right people is hard** -- X's native search is weak, no bio/profile search, poor signal-to-noise
2. Prospecting and lead identification is the #1 time sink (5-15 hrs/week)
3. API cost explosion (9,900% increase) killed many third-party tools
4. The automation gap: tools handle scheduling/analytics well, but **discovery is fragmented and manual**

**The Core Unmet Need**
"I know the kind of person I want to find, but I don't know how to find them on X." This applies across EVERY business use case.

---

## Topic 3: Sales Lead Generation Playbook on X

**Full document**: `topic-3-sales-lead-gen.md`

### Key Takeaways

**The Manual Outbound Process**
1. Define ICP + build keyword lists
2. Build prospect lists via Twitter Advanced Search (150-300 targets)
3. Research profiles one by one
4. Warm up for 1-2 weeks with likes/retweets/replies
5. Send personalized DMs from personal (not branded) accounts
6. Move off-platform to email/call

Key insight from La Growth Machine: the goal is NOT immediate sale -- it's building familiarity so prospects respond to email/phone later. This process is **entirely manual and does not scale**.

**Conversion Data**
- Twitter visitor-to-lead: 0.69% (vs LinkedIn's 2.74%)
- Twitter cold DM response rate: **22.5%** (Jake Peters across 537 DMs)
- Drippi.ai users: 1,000+ personalized DMs/day, 1,100+ sales calls since Aug 2024
- Social selling conversion: 1.4-8.2% (Breakcold data)
- 80% of sales require 5+ follow-ups

**Buying Intent Signals**
- Direct: "looking for a CRM", "can anyone recommend", "frustrated with [competitor]"
- Indirect: role changes, hiring signals, funding announcements
- Engagement: liking competitor content, following multiple accounts in a space
- Devi AI monitors 26 specific buyer-intent expressions

**Data Needs Per Lead**
Must-haves: Twitter handle, full name, bio, recent tweets, email, company, job title
Enrichment workflow: Scrape (PhantomBuster) -> Email (waterfall: Snov.io -> Hunter.io -> Apollo -> Clay) -> Company data -> CRM

**Best Niches for X Sales**
- Tier 1: SaaS founders (#1), marketing/growth agencies, coaches/consultants, dev tools
- Tier 2: Freelancers, e-commerce/DTC, recruiting, fintech
- Key filter: decision-makers personally active on X discussing tools/problems openly

**Smartest Practitioners Use Multichannel**
Warm up on Twitter -> Connect on LinkedIn -> Close via email. Multichannel campaigns deliver 40% higher response rates.

**Tool Ecosystem**
- DM automation: Drippi.ai ($76-144/mo), xAutoDM ($29-59/mo)
- Content/growth: Tweet Hunter, Hypefury
- Social CRM: Breakcold ($30-70/mo), folk.app
- Scraping: PhantomBuster ($59-399/mo)
- Enrichment: Clay ($149-800/mo), Apollo, Snov.io
- Intent monitoring: Devi AI ($29-79/mo), Trigify ($149-549/mo)

---

## Topic 4: X Chats and New Platform Features

**Full document**: `topic-4-x-chats-features.md`

### Key Takeaways

**X Chats: Dead End for Discovery**
- End-to-end encrypted, replaced DMs in November 2025
- Group chats up to 256 members, video/voice calls built in
- Cannot be searched, indexed, or accessed via API
- **Not useful for people discovery**

**X Communities: Now Gold**
- February 2026 change: Community posts are now **publicly visible to everyone**
- Posts appear in global search, For You feed, and member profiles
- Third-party APIs (Netrows, SociaVault) provide Community Tweets endpoints
- Posting in a Community = genuine engagement signal (only members can post)
- **Highly relevant for people discovery**

**X Spaces: Partially Accessible**
- API returns host and speaker IDs (strong expertise signals)
- Keyword search of Space titles enables topic-based discovery
- Cannot access individual listener identities
- 10% increase in Spaces conversations correlates with 3% sales rise

**Premium Tiers (Feb 2026)**
- Basic: $3/mo | Premium: $8/mo | Premium+: $40/mo | Verified Orgs: ~$1,000/mo
- Non-Premium link posts get ~0% engagement since March 2025
- Premium = near-mandatory for business use

**New Features Worth Noting**
- **Radar**: Real-time keyword analytics, now in Premium+ ($40/mo, was $1,000/mo)
- **X Money**: Visa-backed digital wallet, external beta in 1-2 months
- **Account Deep Dive**: Shows country of creation, username change history, VPN detection
- **Creator monetization**: $45M+ paid out, eligibility at 500 followers, 2-3x revenue increases in early 2026
- **1.5M+ job postings**: Positions X as LinkedIn competitor for hiring

---

## Topic 5: Deep Competitive Analysis

**Full document**: `topic-5-competitive-analysis.md`

### Key Takeaways

**Tweet Hunter ($0 -> $1M ARR in 12 months, ~$8M ARR at exit)**
- Viral tweet library (2M+ searchable tweets) + AI writing drove daily habits
- Breakthrough GTM: gave influencer JK Molina **10% equity** instead of affiliate commissions -- revenue tripled from $5K to $15K MRR in two weeks
- Founder Tibo left after stressful 2-year earnout under Lempire, says he "gave up on his baby" and will never do an earnout again
- Now building portfolio of small SaaS tools he owns outright

**Breakcold (~$44K revenue, early stage)**
- Social selling CRM: unified LinkedIn/Twitter feed for prospect engagement
- Users love the feed-based approach; dislike limited platform support
- Critical gap: manages known prospects but **does NOT help discover new ones**

**PhantomBuster**
- 150+ automation "Phantoms" across platforms
- Twitter capabilities severely limited (only 70 followers extractable per account)
- Scripts break when platforms update, documentation poor, $59-399/mo
- Swiss Army knife, not purpose-built for discovery

**SparkToro (~$330K revenue, 3 employees)**
- Audience intelligence: "where does my audience hang out?"
- Returns aggregate insights (demographics, followed accounts), not actionable individual lists
- Data can be weeks old
- Different paradigm: audience research vs. people discovery

**The February 2023 API Extinction Event**
- Twitter API price change killed many tools
- Zlappo: shut down entirely
- BlackMagic.so: sold for $128K despite $168K ARR
- Crowdfire: shut down after 15 years
- Survivors had acquisition backing or enough revenue to absorb costs

**Winning GTM Playbook**
1. Build in public on Twitter itself (natural flywheel)
2. Influencer equity partnerships (10x more effective than sponsorships)
3. Product Hunt launches
4. Indie Hackers / HN communities
5. Paid ads generally don't work for these niche tools

**The Gap We Fill**
No tool does **intent-driven people discovery**. Existing tools assume you already know who to target, which keywords to search, or which accounts to scrape. An LLM-powered tool can:
- Translate vague human intent into multi-angle search strategies
- Find people based on real-time conversation signals
- Rank with contextual understanding
- Explain WHY each person is relevant
- Solve the cold-start problem every other tool ignores

---

## Topic 6: X API & Data Access

**Full document**: `topic-6-api-data-access.md`

### Key Takeaways

**Official API Pricing (Unusable for Our Use Case)**
| Tier | Cost | Search | Reads/mo |
|------|------|--------|----------|
| Free | $0 | None (write-only) | ~500 posts |
| Basic | $200/mo | 7-day only | 15K |
| Pro | $5,000/mo | Full archive | 1M |
| Enterprise | $42,000+/mo | Custom | Custom |

**Third-Party Providers (Our Path)**
| Provider | Cost per 1K tweets | Legal Standing | Best For |
|----------|-------------------|----------------|----------|
| SocialData.tools | $0.20 | Gray area | Real-time search (current choice) |
| TwitterAPI.io | $0.15 | Gray area | Budget alternative |
| Bright Data | $1.50 | Strong (won lawsuit) | Enterprise fallback |
| Apify | $0.25-$0.40 | Gray area | Custom scrapers |

**Scraping Legality**
- **X Corp v. Bright Data (May 2024)**: X's claims dismissed. Scraping public data not actionable under breach of contract when preempted by Copyright Act
- **hiQ v. LinkedIn**: Confirmed public data scraping doesn't violate CFAA
- Risk for us is low: accessing public data via intermediary, not redistributing raw content
- Privacy laws (GDPR/CCPA) still apply

**Data Enrichment (Twitter Handle -> Full Lead)**
| Provider | Can Take Twitter Handle? | Email Success Rate | Cost |
|----------|------------------------|--------------------|------|
| People Data Labs | Yes (directly) | ~30-50% | $0.004/record |
| Hunter.io | No (domain-based) | Varies | $34-299/mo |
| Apollo.io | No (name+company) | Higher if data exists | Freemium |
| Proxycurl | Discontinued | N/A | N/A |

**Cost at Scale (1,000 users x 10 searches/month)**
- Data (SocialData): ~$150-200/mo
- Full stack (data + Claude API): ~$400-900/mo
- With enrichment: ~$800-1,900/mo
- **Cost per search: $0.04-$0.19**
- Official API Pro equivalent: $5,000/mo (25x more expensive)

**Risk Mitigation Strategy**
Build a provider abstraction layer with automatic failover:
1. Primary: SocialData.tools
2. Secondary: TwitterAPI.io
3. Tertiary: Bright Data
4. Emergency: Official Pro tier ($5,000/mo)

---

## Topic 7: ICP Refinement & Positioning

**Full document**: `topic-7-icp-positioning.md`

### Key Takeaways

**Who Has the Most Acute Pain?**

| Segment | Pain Level | WTP | Reachability | Launch Priority |
|---------|-----------|-----|-------------|----------------|
| Solo founders / indie hackers | High | $29/mo | Exceptional (live on Twitter) | **#1 Launch** |
| B2B sales teams / SDRs | Highest | $49-149/mo | Medium | #2 Expansion |
| Agencies (social, PR, marketing) | High | $99-299/mo | Medium-High | #3 Expansion |
| Recruiters | Medium | $49-99/mo | Low (live on LinkedIn) | Later |
| VCs / investors | Medium | $99-199/mo | Low (small segment) | Later |

**Positioning: Horizontal Product, Vertical Marketing**
- Keep the tool general-purpose: "Describe who you want to find. Get a ranked list of real people."
- Create vertical landing pages for each use case (sales, creators, agencies, founders)
- No competitor positions as "AI-powered natural language people discovery"
- This is our unique angle

**Start as a Standalone Tool**
- Resist building CRM integrations, APIs, or team features before users demand them
- CSV export bridges tool -> workflow
- Add platform features when 10+ users independently request the same integration

**Pricing Strategy**
| Tier | Price | Searches/mo | Target |
|------|-------|-------------|--------|
| Free | $0 | 5 | Trial/conversion |
| Starter | $29/mo | 50 | Solo founders |
| Pro | $79/mo | 200 | Power users / small teams |
| Team | $149/mo | 500, 3 seats | Agencies / sales teams |

**First 100 Users Playbook**
1. Twitter itself: build-in-public content + demo screenshots (natural flywheel)
2. Use your own tool to find potential users (dog-fooding)
3. Indie Hackers / Reddit communities
4. Product Hunt launch (after 20-50 core users for social proof)
5. Find 10 people who genuinely need it, then find where 10 more like them hang out

**Minimum Viable Product (What Makes Someone Pay)**
Already built: natural language search input, ranked results with relevance explanations, basic account info, 15-25 results per search, under 30 seconds
Still needed for v1:
- **CSV export** (table stakes)
- **Free tier** (5 searches, no signup friction)

v1.5 upgrade drivers:
- Saved searches
- Email alerts for new matches
- Result filtering/sorting

v2+ (build only when users ask):
- CRM integrations
- Contact enrichment (email/company)
- Team features / shared lists

---

## Cross-Topic Synthesis

### The Big Picture

**The discovery gap is confirmed and large.** Every research topic converges on the same insight: finding the right people on X is a universal pain point across sales, marketing, recruiting, investing, and community building. The manual process (5-15 hours/week of searching, scrolling, qualifying) doesn't scale, and no existing tool solves it with LLM-level understanding.

### Our Competitive Moat

| What We Do | What Competitors Do |
|-----------|-------------------|
| Natural language intent -> multi-angle search | Keyword-in-bio matching |
| LLM ranks by contextual relevance | Follower count / engagement sorting |
| Explains WHY each person is relevant | Lists profiles with no context |
| Handles vague queries ("AI founders who tweet about dev tools") | Requires exact keywords |
| Real-time conversation-based discovery | Static profile databases |

### Three Strategic Decisions (Confirmed by Research)

1. **Launch ICP**: Solo founders / indie hackers. They live on X, have acute discovery pain, tolerate early-stage products, and spread word-of-mouth. Expand to sales teams and agencies at v1.5+.

2. **Positioning**: "Describe who you want to find" (horizontal tool, vertical marketing). No competitor owns this framing. The LLM-powered natural language interface IS the product differentiation.

3. **Pricing**: Free (5 searches) / $29 / $79 / $149. Anchored to market (SparkToro, Breakcold, Tweet Hunter) and validated by SaaS benchmarks.

### Risks to Monitor

| Risk | Severity | Mitigation |
|------|----------|-----------|
| SocialData.tools shutdown | High | Provider abstraction layer with TwitterAPI.io + Bright Data failover |
| X API policy changes | Medium | Legal precedent (Bright Data v. X) favors public data access |
| Competitor copies LLM approach | Medium | Speed to market + community lock-in + data moat from usage |
| X platform decline (48% engagement drop in 2025) | Low-Medium | Multi-platform expansion (Bluesky, LinkedIn) as v2+ feature |
| Cost scaling issues | Low | $0.04-0.19/search is very manageable; Claude API is the main cost driver |

### Immediate Next Steps

1. **Add CSV export** to current product (table stakes gap)
2. **Add free tier** (5 searches, no signup required)
3. **Build landing page** with vertical messaging for founders
4. **Dog-food**: use the tool to find our first 10-20 users on X
5. **Build in public**: start sharing screenshots and results on Twitter
6. **Product Hunt prep**: gather 20-50 core users, then launch

### Research Files Index

| File | Topic | Size |
|------|-------|------|
| `topic-1-x-algorithm.md` | How X's Algorithm Works | 31KB |
| `topic-2-x-business-use.md` | How People Use X for Business | 39KB |
| `topic-3-sales-lead-gen.md` | Sales Lead Generation Playbook | 30KB |
| `topic-4-x-chats-features.md` | X Chats & New Platform Features | 14KB |
| `topic-5-competitive-analysis.md` | Deep Competitive Analysis | 29KB |
| `topic-6-api-data-access.md` | X API & Data Access | 28KB |
| `topic-7-icp-positioning.md` | ICP Refinement & Positioning | 36KB |
| **Total research** | | **~207KB** |
