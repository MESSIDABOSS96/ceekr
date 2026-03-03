# Twitter/X Search Use Cases & Verticals: Jobs-to-Be-Done Analysis (Feb 2026)

This document maps the specific tasks, goals, and use cases that lead people to Twitter's search bar — and where Twitter fails them. Each use case is assessed for Ceekr opportunity alignment.

---

## 1. Personal/Social Use Cases

### 1A. Finding Old Tweets They Remember Seeing

**What they're trying to accomplish:**
Users remember seeing a specific tweet — a funny take, an insightful thread, a news reaction — and want to find it again. This is one of the most frequent and most frustrating search tasks on Twitter.

**How they currently try to do it on Twitter:**
- Searching remembered keywords from the tweet
- Using `from:username` if they remember who posted it
- Scrolling through their likes or bookmarks
- Using Twitter's advanced search with date range filters

**Where Twitter search fails them:**
- **Keyword matching misses semantic intent.** Searching "that tweet about startups being like surfing" won't find a tweet that said "building a company is like riding a wave." No semantic understanding.
- **Results are biased toward popular/recent content.** The "Top" tab shows engagement-heavy tweets, burying the specific older tweet the user wants.
- **Bookmarks are unsearchable.** Twitter's bookmark feature has no search functionality and silently caps at 800 items, deleting the oldest without warning.
- **Deleted tweets vanish completely.** If the author deleted the tweet, it's gone with no archive access.
- **Date range filtering is imprecise.** Users often don't remember the exact date, and Twitter's date search requires precise YYYY-MM-DD format.

**Workarounds:**
- Google `site:twitter.com` + remembered keywords (often works better than native search)
- Thread Reader App (for threads that were unrolled)
- Screenshotting tweets as a backup (widespread practice)
- Third-party bookmark managers: Twillot, Dewey, Readwise

**What a "perfect" search would look like:**
"Find the tweet I saw last month about how startups are like surfing — I think it was from a YC founder" — returning results based on *meaning*, not just keywords, with fuzzy date matching.

---

### 1B. Finding What Someone Said About a Topic

**What they're trying to accomplish:**
Users want to know what a specific person has said about a specific topic. e.g., "What has @elonmusk said about Mars colonization?" or "Has @paulg ever tweeted about remote work?"

**How they currently try to do it on Twitter:**
- `from:username keyword` advanced search
- Scrolling through someone's profile and using Ctrl+F in the browser
- Using the "Search this profile" feature (when available)

**Where Twitter search fails them:**
- **The `from:username keyword` pattern is broken.** Typefully founder Fabrizio Rinaldi reported in October 2024 that this pattern was returning zero results for queries that should match dozens of tweets.
- **Profile search is limited.** The "Search this profile" feature only searches recent tweets and misses older content.
- **No thread awareness.** If someone discussed a topic across a 20-tweet thread, individual tweets from that thread may not contain the search keyword.
- **No context windows.** Can't search for "what did they say about X in the context of Y."

**Workarounds:**
- Google `site:twitter.com/username keyword` — often more reliable than native search
- Thread Reader App for searching unrolled threads
- Manually scrolling through a user's media/likes/posts tabs

**What a "perfect" search would look like:**
"What has @pmarca said about AI regulation?" — returning a synthesized answer with cited tweets, including threads and replies, organized chronologically.

---

### 1C. Finding Conversations/Threads on a Specific Topic

**What they're trying to accomplish:**
Users want to find in-depth discussions — multi-tweet threads, reply chains with genuine debate, Twitter Spaces recaps — on a specific topic. Not just individual hot takes, but *conversations*.

**Where Twitter search fails them:**
- **Search returns individual tweets, not threads.** There's no "show me threads about X" filter.
- **No thread discovery.** Twitter doesn't surface popular threads as a content type.
- **Reply chains are invisible.** Rich back-and-forth discussions between experts are completely unsearchable.
- **Quality signal is weak.** Engagement metrics don't distinguish between viral hot takes and thoughtful analysis.

**Workarounds:**
- Thread Reader App (threadreaderapp.com) for unrolling and discovering threads
- Google `site:threadreaderapp.com topic` for indexed threads
- Following curated accounts that retweet good threads
- Twitter Lists to monitor specific communities

**What a "perfect" search would look like:**
"Show me the best discussions about AI safety from the last month" — returning full threads ranked by depth of discussion, expertise of participants, and substantive engagement.

---

### 1D. Checking What People Are Saying About a Current Event

**What they're trying to accomplish:**
Something just happened and users want to see real-time reactions, eyewitness accounts, expert commentary, and emerging consensus.

**Where Twitter search fails them:**
- **"Top" results are algorithmically curated and often stale.** By the time an event is trending, "Top" shows tweets from hours ago.
- **"Latest" is a firehose of noise.** No "Latest from credible accounts" filter.
- **Paid verification destroyed credibility signals.** Anyone with $8/month has the same badge.
- **Bot activity floods trending topics.** Makes it hard to gauge genuine sentiment.
- **No expert layer.** During a medical emergency, can't filter for "actual doctors." During a tech outage, can't filter for "engineers at the affected company."

**Workarounds:**
- Curated Twitter Lists of experts in specific domains
- TweetDeck / X Pro with column-based monitoring (now paywalled)
- Third-party social listening tools (Meltwater, Brand24, Sprout Social)
- Going to Reddit, which has better community-based discussion structure

**What a "perfect" search would look like:**
A layered real-time view: eyewitness accounts at the top, expert analysis next, general public reaction below. Automatic credibility scoring based on actual expertise.

---

### 1E. Finding People to Follow Based on Interests

**What they're trying to accomplish:**
Discover interesting people to follow — experts in their field, people with similar hobbies, thought leaders in a niche. Curate their timeline to be more valuable.

**Where Twitter search fails them:**
- **"Who to Follow" is engagement-optimized, not quality-optimized.** Recommends accounts that keep you scrolling, not accounts that make your timeline better.
- **Can't search by "type of person."** No way to say "find climate scientists who tweet regularly about policy."
- **Bio search is primitive.** Can't combine "what they tweet about" + "who they are" + "where they are."
- **Follower/following lists capped at ~50 visible.** No way to search someone's full follower list.
- **No "people like X" discovery.** Can't say "show me more accounts like @example."

**Workarounds:**
- Followerwonk (search bios by keyword)
- Manually browsing followers of thought leaders
- Asking on Twitter: "Who should I follow for X topic?"
- Curated "follow lists" in blog posts or threads
- SparkToro ($50+/mo)

**What a "perfect" search would look like:**
"Find people who actively tweet about machine learning engineering, have been in the field for 5+ years, and share practical code/tutorials rather than just opinions." Natural language description of a *person*, not keywords.

**This is Ceekr's core use case.**

---

## 2. Professional/Business Use Cases

### 2A. Journalists: Finding Sources and Eyewitness Accounts

**What they're trying to accomplish:**
Find sources/experts to quote, locate eyewitness accounts, verify information, monitor breaking news, investigate tweet history.

**Where Twitter search fails them:**
- OSINT tool ecosystem destroyed (Twint, GetOldTweets3, etc.) by API restrictions
- Paid verification makes expert identification impossible during breaking news
- Location search (`near:`, `geocode:`) is unreliable
- Fake accounts actively target journalists
- AI-generated content undermines verification

**Workarounds:** Bellingcat toolkit, Google site:twitter.com, commercial OSINT platforms, curated Lists.

**Ceekr opportunity: MODERATE.** "Find experts who frequently comment on X topic" aligns well. Geographic/temporal needs don't.

---

### 2B. Marketers: Brand Mentions, Competitor Analysis, Audience Research

**What they're trying to accomplish:**
Monitor brand mentions, track competitors, understand audience language, find user-generated content, identify influencers.

**Where Twitter search fails them:**
- Misses indirect mentions ("just switched from Notion to Obsidian" without @-tagging)
- No sentiment layer
- No audience overlap analysis
- No historical trending
- Influencer discovery is entirely manual
- 91% of brand mentions are untagged

**Workarounds:** Brandwatch ($1,000+/mo), Sprout Social ($199+/seat/mo + $999 listening add-on), Brand24, Mention, Meltwater.

**Ceekr opportunity: HIGH.** "Find people talking about [competitor] who seem frustrated" and micro-influencer discovery fill the gap between free and enterprise.

---

### 2C. Sales: Finding Prospects, Monitoring Buying Signals

**What they're trying to accomplish:**
Find prospects matching ICP, identify buying signals, warm up cold outreach, research before calls.

**Where Twitter search fails them:**
- **No intent classification.** Can't distinguish someone complaining (buying signal) vs writing about it (content creator).
- **No ICP filtering.** Can't search "CTOs at Series B startups who tweeted about needing better analytics."
- **Manual and unscalable.** 2-3 hours daily for a single SDR.
- **No CRM integration.** Everything is copy-paste.
- **No real-time monitoring.** Can't set up persistent alerts.

**Workarounds:** LaGrowthMachine, Apollo, PhantomBuster, Hootsuite, X Pro, Warble.

**What a "perfect" search would look like:**
"Find startup founders who tweeted in the last 2 weeks about struggling with customer churn, who run B2B SaaS companies, and haven't mentioned any competitor."

**Ceekr opportunity: VERY HIGH.** Highest-WTP segment ($49-149/mo per seat). People discovery with intent classification is the sweet spot.

---

### 2D. Recruiters: Finding Candidates

**Where Twitter search fails them:**
- Bio search is keyword-only ("ML engineer" misses "AI/ML researcher")
- No skills/experience filtering
- Can't combine tweet content + bio criteria
- Follower lists capped at ~50 visible

**Ceekr opportunity: MODERATE.** Supplements LinkedIn, doesn't replace it.

---

### 2E. Investors/VCs: Due Diligence, Founder Scouting

**What they're trying to accomplish:**
Scout emerging founders, track market narratives, due diligence on public statements.

**Where Twitter search fails them:**
- No "founder behavior" detection. Only Evertrace attempts to track "early-stage founder behavior through subtle tweet patterns."
- No structured market intelligence
- Incomplete archives undermine due diligence

**Ceekr opportunity: HIGH.** Very high-WTP ($200+/mo). Finding people based on behavioral signals is core.

---

### 2F-2G. Customer Support & PR/Crisis

Social listening and monitoring needs, not people discovery. Dominated by enterprise tools (Brandwatch, Meltwater, Sprout Social).

**Ceekr opportunity: LOW.**

---

## 3. Research/Academic Use Cases

### 3A. Academic Researchers
- API access destroyed: 17 years of free access rescinded within 6 months. API costs increased 9,900%.
- 100+ research projects canceled. Many researchers migrated to Bluesky/Reddit.
- **Ceekr opportunity: LOW.** Data access at scale, not people discovery.

### 3B. Political Analysts
- Need data analytics at scale, sentiment classification, representative sampling.
- **Ceekr opportunity: LOW.**

### 3C. OSINT Practitioners
- Highly specialized: geolocation, network analysis, evidence preservation.
- Tool ecosystem devastated by API restrictions.
- **Ceekr opportunity: LOW.**

### 3D. Data Journalists
- Need to find sources with first-hand knowledge, trace claims, verify information.
- **Ceekr opportunity: MODERATE.** "Find people with expertise in [topic]" aligns well.

---

## 4. Developer/Technical Use Cases

### 4A. Finding Bug Reports
Content search, not people discovery. No temporal clustering of issues. **Ceekr opportunity: LOW.**

### 4B. Discovering New Tools/Libraries
Discovery is engagement-biased, not stack-aware. **Ceekr opportunity: MODERATE.** "Find developers who are experts in [my stack]" is strong.

### 4C. Finding Technical Discussions
Threads invisible as content type. Expert voices buried. **Ceekr opportunity: MODERATE.** "Find people with deep expertise in [technology]" is strong.

---

## 5. Community/Discovery Use Cases

### 5A. Finding Niche Communities
- Communities hard to discover (basic keyword matching only)
- Lists aren't searchable by topic
- Hashtag communities are noisy
- **Ceekr opportunity: VERY HIGH.** "Find my community" is the emotional hook.

### 5B. Discovering Experts in Specific Fields
- No expertise signals, follower count ≠ expertise
- No network authority scoring
- Best signal: "who do other experts follow?" — Twitter can't query this
- **Ceekr opportunity: VERY HIGH.** Core value proposition.

### 5C. Finding Events/Spaces
- Spaces discovery is poor, events buried in noise
- **Ceekr opportunity: LOW.**

### 5D. Finding Collaborators/Co-Founders
- No matching, intent invisible, skills assessment impossible
- **Ceekr opportunity: HIGH.** Build-in-public community is launch audience.

---

## 6. Cross-Cutting Themes: 5 Structural Failures

### 6.1 Keyword-Only Matching (No Semantic Understanding)
Twitter search has zero understanding of meaning. "People struggling with customer retention" won't find "our churn rate is killing us." This is the single biggest failure across every use case.

**Ceekr advantage:** LLM-powered query generation translates natural language into multiple keyword queries; LLM ranking understands actual intent.

### 6.2 Returns Tweets, Not People
Most use cases are about finding people. Twitter has no way to go from "tweets about this topic" to "people worth connecting with."

**Ceekr advantage:** This IS Ceekr's product.

### 6.3 No Quality or Credibility Signals
A bot, a teenager, a Nobel laureate, and a content marketer all appear identically. Only signals: follower count (gameable), checkmark (purchasable), engagement (manipulable).

**Ceekr advantage:** LLM evaluation of *why* someone is relevant.

### 6.4 No Persistent Discovery
Every search is manual, one-time. No "keep watching and alert me."

**Ceekr opportunity (v2):** Saved searches with alerts.

### 6.5 Massive Gap Between Free and Enterprise
Twitter search: free but broken. Enterprise tools: $200-1,200+/month. Almost nothing in the $19-99/mo range.

**Ceekr advantage:** Positioned squarely in this gap.

---

## 7. Vertical Prioritization for Ceekr

### Tier 1: Strong Fit, Build Now

| Vertical | Why It Fits | WTP | Segment Size |
|---|---|---|---|
| **Expert/Community Discovery** (5B, 5A) | Core product — find people by expertise/interest | $19-49/mo | Millions of active Twitter users |
| **Sales Prospecting** (2C) | Find prospects by behavior/intent, highest revenue | $49-149/mo/seat | 666K+ SDRs in US alone |
| **Co-Founder/Collaborator Discovery** (5D) | Build-in-public community = launch audience | $19-49/mo | 200K-500K globally |
| **VC/Investor Founder Scouting** (2E) | Find founders showing "pre-company" signals | $99-299/mo | ~50K active VCs globally |

### Tier 2: Good Fit, Build Next

| Vertical | Why It Fits | WTP | Notes |
|---|---|---|---|
| **Influencer/Creator Discovery** | Find micro-influencers in niches | $49-99/mo | High demand from DTC brands |
| **Recruiting** | Find passive candidates | $49-99/mo | Supplement to LinkedIn |
| **Journalist Source Finding** | Find experts by topic | $29-79/mo | Smaller market |
| **Developer Discovery** | Find experts in tech stacks | $19-49/mo | DevRel and hiring teams |

### Tier 3: Adjacent, Consider Later

| Vertical | Why Lower Priority |
|---|---|
| Brand/Competitor Monitoring | Social listening, not discovery. Dominated by Brandwatch, Sprout |
| PR/Crisis Management | Real-time monitoring. Enterprise budgets only |
| Political Analysis | Data analytics at scale. Niche, seasonal |
| Academic Research | Data access problem, not UX. API pricing is the blocker |
| OSINT | Highly specialized. Different product category |

### The Key Insight

**The verticals where Ceekr wins are those where the core job is "find me the right *people*"** — not "find me tweets," "monitor mentions," or "analyze data." Nobody is building a great people search engine for Twitter. Ceekr's LLM-powered people discovery is differentiated precisely because Twitter returns tweets and everyone else builds monitoring tools.

---

## Sources
- [Twitter Search: How It Works (GetGuru)](https://www.getguru.com/reference/twitter-search)
- [7 Fixes to Twitter Search Incomplete Results (Hollyland)](https://www.hollyland.com/blog/tips/twitter-search-incomplete-results)
- [How bad is Twitter's search function? (Team Blind)](https://www.teamblind.com/post/How-bad-is-Twitters-search-function-zbPNNWC3)
- [Why is Twitter search so awful? (Quora)](https://www.quora.com/Why-is-Twitter-search-so-awful)
- [OSINT for Journalists (OSINT Industries)](https://www.osint.industries/post/osint-journalism-our-guide-to-osint-for-journalists)
- [AI undermining OSINT (Reuters Institute)](https://reutersinstitute.politics.ox.ac.uk/news/ai-undermining-osints-core-assumptions-heres-how-journalists-should-adapt)
- [What happened to academic research on Twitter? (CJR)](https://www.cjr.org/tow_center/qa-what-happened-to-academic-research-on-twitter.php)
- [The Day Data Transparency Died (SAGE)](https://journals.sagepub.com/doi/10.1177/15365042241252125)
- [Twitter Prospecting Tools (ColdIQ)](https://coldiq.com/blog/twitter-prospecting-tools)
- [Twitter for Sales Prospecting (LaGrowthMachine)](https://lagrowthmachine.com/twitter-for-sales/)
- [Finding Prospects on Twitter (Social Media Examiner)](https://www.socialmediaexaminer.com/3-ways-to-find-prospects-using-twitter/)
- [Sourcing on Twitter (Entrustech)](https://medium.com/@entrustech/sourcing-on-twitter-x-how-to-find-more-candidates-2a12f8cb0c43)
- [Evertrace Founder Detection Engine](https://www.evertrace.ai/)
- [Real-Time Crisis Management on Twitter (5W PR)](https://www.5wpr.com/new/real-time-crisis-management-on-twitter-a-guide/)
- [Brandwatch vs Sprout Social (Mention)](https://mention.com/en/blog/brandwatch-vs-sproutsocial/)
- [Twitter Bookmarks Pain Points (Twillot)](https://www.twillot.com/en/blog/twitter-bookmarks-pain-points-2025)
- [How to Search for People on Twitter (Fedica)](https://fedica.com/blog/how-to-search-for-people-on-twitter-x/)
- [Finding Communities on Twitter (Socinator)](https://socinator.com/blog/how-to-find-communities-on-twitter/)
- [How would you beat Twitter with JTBD (thrv)](https://www.thrv.com/blog/how-would-you-beat-twitter)
- [Investigating Social Media Accounts (DataJournalism.com)](https://datajournalism.com/read/handbook/verification-3/investigating-actors-content/how-to-analyze-social-media-accounts)
- [Bellingcat Online Investigation Toolkit](https://bellingcat.gitbook.io/toolkit)
- [Full Archive Search Issues (X Developers)](https://devcommunity.x.com/t/full-archive-search-endpoint-returning-incomplete-results/249134)
