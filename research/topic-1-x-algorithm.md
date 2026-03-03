# X (Twitter) Algorithm Deep Dive: Research for People-Discovery Tools

*Compiled February 2026 from web research, open-source code analysis, and academic studies.*

---

## Table of Contents

1. [How X's Search Ranking Works](#1-how-xs-search-ranking-works)
2. [The Recommendation Algorithm ("For You" Feed)](#2-the-recommendation-algorithm-for-you-feed)
3. [How X Surfaces Accounts to Follow](#3-how-x-surfaces-accounts-to-follow)
4. [Known Algorithmic Biases](#4-known-algorithmic-biases)
5. [Algorithm Changes Since Musk Took Over](#5-algorithm-changes-since-musk-took-over)
6. [What We Learned from the Open-Sourced Algorithm](#6-what-we-learned-from-the-open-sourced-algorithm)
7. [Practical Implications for a People-Discovery Tool](#7-practical-implications-for-a-people-discovery-tool)

---

## 1. How X's Search Ranking Works

### Search Modes: "Top" vs "Latest"

X search provides two result modes:

- **"Top" results**: Tweets ranked by a combination of relevance, engagement, and account credibility. There is an engagement threshold — tweets need some minimum level of retweets, replies, and likes to qualify. This mode surfaces the most algorithmically "important" content matching the query.
- **"Latest" results**: Tweets sorted in reverse chronological order by tweet ID. No engagement threshold — every matching tweet appears. This is the raw firehose filtered only by query match.

### What Determines Search Ranking (Top Results)

The search ranking algorithm considers these signals:

**Keyword and Query Match**
- Exact keyword matching in tweet text, hashtags, and user mentions
- Queries can be up to 1,024 characters long
- Standard search API only returns data from the last 7 days

**Engagement Scoring**
The core engagement formula (from the open-sourced code):

| Signal | Weight |
|--------|--------|
| Reply that gets author reply | +75 |
| Reply | +13.5 |
| Profile open with like/reply | +12.0 |
| Conversation click with reply/like | +11.0 |
| Dwell time 2+ minutes | +10.0 |
| Retweet | +1.0 (but 20x multiplier in simplified formula) |
| Like/Favorite | +0.5 |
| Video watch 50%+ | +0.005 |

Simplified composite: `(Likes x 1) + (Retweets x 20) + (Replies x 13.5) + (Profile Clicks x 12) + (Link Clicks x 11) + (Bookmarks x 10)`

**Account Credibility (TweepCred)**
- A PageRank-derived reputation score from 0 to 100
- Factors: follower/following ratio, engagement density, account age, bio quality, language consistency, tweet quality
- Critical threshold: accounts with TweepCred < 65 have only 3 tweets considered for distribution; above 65, all tweets are eligible
- Premium subscribers get a +4 to +16 point TweepCred boost

**Time Decay**
- A post loses half its visibility score every 6 hours (half-life = 6 hours)
- The first 30 minutes after posting are critical — early engagement signals quality
- The first 2 hours determine a tweet's trajectory

**Premium/Verified Status**
- Premium accounts rank higher when multiple results match a query
- Premium subscribers receive priority placement in search results
- Since March 2026, non-Premium accounts posting links receive near-zero median engagement

### Search Operators Relevant to People Discovery

| Operator | Effect |
|----------|--------|
| `from:username` | Tweets from a specific user |
| `filter:verified` / `is:verified` | Only verified (blue checkmark) accounts |
| `min_retweets:N` | Minimum retweet threshold |
| `min_faves:N` / `min_likes:N` | Minimum likes threshold |
| `min_replies:N` | Minimum replies threshold |
| `filter:links` | Only tweets containing URLs |
| `filter:media` | Only tweets with images/video |
| `filter:replies` | Only reply tweets |
| `-filter:replies` | Exclude replies |
| `lang:en` | Language filter |
| `since:YYYY-MM-DD` / `until:YYYY-MM-DD` | Date range |

**Important**: `min_faves` and `min_retweets` are reportedly flaky in some API contexts. The newer API convention uses `min_likes` and `min_reposts`.

### Sources

- [Tweet Archivist: How the Twitter Algorithm Works in 2026](https://www.tweetarchivist.com/how-twitter-algorithm-works-2025)
- [X Developer Platform: Search Operators](https://developer.x.com/en/docs/x-api/v1/rules-and-filtering/search-operators)
- [ExportData: Advanced Twitter Search Operators](https://www.exportdata.io/blog/advanced-twitter-search-operators/)
- [SocialData API: Get Search Results](https://docs.socialdata.tools/reference/get-search-results/)

---

## 2. The Recommendation Algorithm ("For You" Feed)

### The Four-Stage Pipeline

X's recommendation system processes ~500 million daily tweets and makes ~5 billion ranking decisions per day, each completing in under 1.5 seconds using ~220 seconds of CPU time.

**Stage 1: Candidate Sourcing**
- Extracts the best ~1,500 tweets from hundreds of millions
- ~50% from accounts you follow (In-Network)
- ~50% from accounts you don't follow (Out-of-Network)
- Out-of-network sourced via SimClusters (145,000 virtual communities) and social graph analysis

**Stage 2: Ranking**
- A ~48 million parameter neural network (based on MaskNet architecture) scores each candidate
- Predicts probability of engagement across multiple dimensions (reply, retweet, like, dwell, etc.)
- Each engagement type has its own prediction head with the weights listed above

**Stage 3: Heuristics, Filters, and Product Features**
- Prevents too many consecutive tweets from one author
- Balances in-network vs. out-of-network content
- Filters spam, NSFW, misinformation
- Applies negative signal penalties

**Stage 4: Mixing and Serving**
- Blends tweets with ads, promoted content, and other recommendations
- Final assembly in the Home Mixer component

### What Makes Content Go Viral

Based on the engagement weights, the algorithm disproportionately rewards:

1. **Conversation depth** — A reply that gets a reply from the original author is worth 150x more than a like (+75 vs +0.5). This is the single strongest positive signal.
2. **Reply generation** — Getting people to reply (+13.5) is 27x more valuable than getting a like
3. **Profile curiosity** — If a tweet makes someone click the author's profile and then engage, that's +12
4. **Extended attention** — Dwell time of 2+ minutes on a conversation scores +10
5. **Retweets** — Worth 20x a like in the simplified formula
6. **Bookmarks** — Worth 10x a like (a "save for later" intent signal)

**Negative signals that kill virality:**
- Tweet report: **-369x** penalty (catastrophic — essentially removes from distribution)
- Block/mute/"show less": **-74x** penalty
- Negative feedback extends beyond the individual tweet to account-wide reputation

**Time dynamics:**
- Half-life of 6 hours means urgency matters
- Early engagement velocity in the first 30 minutes is critical
- Tweets that gain traction quickly get wider distribution; dormant tweets get buried

### Grok AI Integration (January 2026)

As of January 2026, the legacy recommendation system has been replaced by a Grok-powered transformer model:

- **Architecture**: Rust-based with four components:
  - **Home Mixer** — Orchestration layer
  - **Thunder** — In-memory post storage and retrieval for in-network content
  - **Phoenix** — Grok-based ranking engine
  - **Candidate Pipeline** — Content retrieval
- **Sentiment Analysis**: Grok reads every post and evaluates tone. Positive/constructive content gets wider distribution; negative/combative content gets reduced visibility even if engagement is high.
- **Customization**: Users can input natural language commands (e.g., "Show me more tech, less politics") to adjust their feed.
- **Open source**: Published at [github.com/xai-org/x-algorithm](https://github.com/xai-org/x-algorithm), with pledged updates every 4 weeks.

### Sources

- [X Engineering Blog: Twitter's Recommendation Algorithm](https://blog.x.com/engineering/en_us/topics/open-source/2023/twitter-recommendation-algorithm)
- [Analytics Vidhya: Inside X's Recommendation Algorithm](https://www.analyticsvidhya.com/blog/2025/09/x-recommendation-algorithm/)
- [PostEverywhere: How the X Algorithm Works in 2026](https://posteverywhere.ai/blog/how-the-x-twitter-algorithm-works)
- [Social Media Today: X's Algorithm Shifting to Grok](https://www.socialmediatoday.com/news/x-formerly-twitter-switching-to-fully-ai-powered-grok-algorithm/803174/)
- [GitHub: xai-org/x-algorithm](https://github.com/xai-org/x-algorithm)
- [nibzard: X's Grok-Powered Algorithm: The January 2026 Rewrite](https://www.nibzard.com/x-grok-algorithm)

---

## 3. How X Surfaces Accounts to Follow

### "Who to Follow" Algorithm

X's account recommendation system (historically called "WTF" — Who to Follow) uses multiple signals:

**Primary Signals:**
- **Social graph analysis**: People followed by people you follow (2nd-degree connections)
- **Uploaded contacts**: If you've shared your address book, X matches email/phone to accounts
- **Interest similarity**: Accounts that tweet about topics you engage with
- **Engagement patterns**: Accounts whose content you've liked, retweeted, or replied to
- **Location**: Geographic proximity (when available)
- **Recency of follows**: Recent follow patterns signal current interests

**Network-Based Discovery:**
- The WTF service uses collaborative filtering: "users who followed A also followed B"
- SimClusters groups users into 145,000 overlapping communities based on follow relationships
- Your community memberships determine which out-of-network accounts get surfaced

**Profile Discoverability Factors:**
- Complete bio with relevant keywords
- Consistent posting activity (not dormant)
- High engagement rate on tweets
- TweepCred reputation score above 65
- Premium subscription status (verified badge)
- Follower/following ratio (more followers than following signals authority)
- Profile picture, header image, and pinned tweet presence

### How Accounts Appear in Search People Results

When searching for people (not tweets), X considers:
- Username and display name match
- Bio keyword relevance
- Follower count (as a proxy for authority)
- Verified/Premium status
- Engagement metrics of recent tweets
- Network proximity to the searcher

### Sources

- [X Help: Account Recommendations](https://help.x.com/en/resources/recommender-systems/account-recommendations)
- [Stanford: WTF - The Who to Follow Service at Twitter](https://stanford.edu/~rezab/papers/wtf_overview.pdf)
- [X Blog: Discovering Who to Follow](https://blog.x.com/en_us/a/2010/discovering-who-to-follow)
- [Fedica: How to Search for People on Twitter/X](https://fedica.com/blog/how-to-search-for-people-on-twitter-x/)

---

## 4. Known Algorithmic Biases

### Premium/Verified Account Bias

This is the most significant and documented bias:

- **Reach boost**: Premium subscribers receive a **2x to 4x boost** in reach compared to non-Premium accounts
  - 4x visibility boost for their followers (in-network)
  - 2x boost for non-followers (out-of-network)
- **Reply priority**: Replies from Premium users appear at the top of conversation threads
- **Search priority**: Premium accounts rank higher when multiple results match a query
- **TweepCred boost**: Premium subscribers get a +4 to +16 point bonus on their reputation score
- **Link posting**: Since March 2026, non-Premium accounts posting links receive zero median engagement; Premium accounts retain ~0.25-0.3% engagement rate on link posts
- **Net effect**: Premium accounts get ~10x more reach per post than free accounts

### Engagement Velocity Bias

- The algorithm rewards early, rapid engagement ("rich get richer" dynamics)
- Content from accounts with large existing followings generates faster early engagement
- The 30-minute critical window and 6-hour half-life structurally favor accounts with active, engaged audiences
- Smaller accounts face a cold-start problem where tweets die before reaching critical mass

### Content Type Bias

- **Text-only posts outperform video by 30%** on X (unique among major platforms)
- External links receive a **30-50% reach penalty** (and near-total suppression for free accounts since March 2026)
- Native media (uploaded images/videos) gets a boost over links to external media
- Tweets with 1-2 hashtags perform optimally; 3+ hashtags trigger a penalty
- Long-form content (X Articles, threads) gets additional weight via dwell time signals

### Political/Ideological Bias

Research from the 2024 U.S. Presidential Election (published in ACM FAccT 2025) found:
- X's algorithm skews exposure toward a few high-popularity accounts across all users
- Right-leaning accounts experience the highest level of exposure inequality
- Both left- and right-leaning users encounter amplified exposure to accounts aligned with their own views (echo chamber effect)
- New accounts experience a right-leaning bias in their default timelines
- The algorithm has moved from promoting moderate content to reinforcing users' existing preferences, especially in out-of-network recommendations

### Negative Signal Asymmetry

The penalty weights are dramatically asymmetric:
- A tweet report carries a **-369x** penalty (vs +0.5 for a like)
- Block/mute carries a **-74x** penalty
- This means a single report outweighs ~738 likes
- This creates vulnerability to coordinated reporting campaigns (documented as a manipulation vector in GitHub issues on the algorithm repo)

### Account Age and Activity Bias

- Older, continuously active accounts receive higher TweepCred scores
- New accounts face a cold-start penalty until they build engagement history
- Dormant accounts that return face reduced distribution until re-establishing activity patterns

### Grok Sentiment Bias (New in 2026)

- Grok's tone analysis now actively suppresses "negative/combative" content
- This creates a bias toward positive, constructive messaging regardless of informational value
- Criticism, complaints, and investigative content may be systematically under-distributed

### Sources

- [Sprout Social: How the Twitter Algorithm Works in 2026](https://sproutsocial.com/insights/twitter-algorithm/)
- [Arxiv: Auditing Political Exposure Bias on Twitter/X](https://arxiv.org/abs/2411.01852)
- [TechPolicy.Press: New Research Points to Possible Algorithmic Bias on X](https://www.techpolicy.press/new-research-points-to-possible-algorithmic-bias-on-x/)
- [GitHub Issue #1386: Recommendation Algorithm Manipulation via Mass Blocks](https://github.com/twitter/the-algorithm/issues/1386)
- [Tweet Archivist: Twitter Subscription Features Guide](https://www.tweetarchivist.com/twitter-subscription-features-guide)
- [Circleboom: The Hidden X Algorithm](https://blog-content.circleboom.com/the-hidden-x-algorithm-tweepcred-shadow-hierarchy-dwell-time-and-the-real-rules-of-visibility/)

---

## 5. Algorithm Changes Since Musk Took Over

### Timeline of Major Changes

**Late 2022 — Acquisition**
- Elon Musk acquires Twitter for $44B in October 2022
- Massive layoffs (75% of staff), including trust & safety teams
- Begins pushing for "free speech" content moderation changes

**March 2023 — Algorithm Open-Sourced (v1)**
- Twitter publishes recommendation algorithm on GitHub (github.com/twitter/the-algorithm)
- Java/Scala codebase revealed
- Community discovers special flags for Elon Musk's account, "power users," and political affiliations
- Twitter engineers claim flags were for A/B testing, not permanent boosting

**2023 — Verification Overhaul**
- Legacy verification removed; replaced with paid Twitter Blue / X Premium
- Verified/Premium accounts begin receiving algorithmic boost
- Introduction of Grok AI chatbot (November 2023)

**2024 — Premium Dominance**
- Premium accounts receive documented 4x/2x algorithmic boosts
- External link penalty reaches 30-50%
- Algorithm increasingly penalizes content that drives users off-platform
- Average engagement rates begin declining platform-wide

**2025 — Grok Integration Begins**
- January 2025: Musk announces algorithm update prioritizing "informational and entertaining" content
- Mid-2025: Grok sentiment analysis deployed; link suppression intensified
- Average engagement rate drops to 0.12% (down 48% year-over-year — steepest decline of any major platform)
- October 2025: Musk announces full Grok takeover, "deletion of all heuristics within 4-6 weeks"
- November 2025: "Following" feed is no longer purely chronological — now sorted by Grok's predicted engagement (users can toggle back to chronological)

**January 2026 — Grok Algorithm (v2)**
- New Rust-based algorithm published on [github.com/xai-org/x-algorithm](https://github.com/xai-org/x-algorithm)
- 1,600 GitHub stars in 6 hours
- Transformer architecture ported from Grok-1
- All hand-engineered heuristics eliminated; pure ML-based ranking
- Grok reads every post and watches every video for content understanding
- xAI pledges to update the open-source repo every 4 weeks

**February/March 2026 — Current State**
- Non-Premium accounts with links receive zero median engagement
- Both "For You" and "Following" feeds are algorithm-ranked
- Grok sentiment analysis actively suppresses negative/combative tone
- Users can customize feed via natural language instructions to Grok

### The Net Effect

The platform has shifted from a chronological, engagement-driven timeline to an AI-curated, subscription-stratified content system. Key shifts:

1. **Pay-to-play**: Premium status is now nearly required for meaningful visibility
2. **Platform lock-in**: External links are heavily penalized to keep users on X
3. **AI curation**: Human-designed heuristics replaced by opaque ML models
4. **Sentiment filtering**: Algorithm now evaluates tone, not just engagement
5. **Declining engagement**: Overall platform engagement dropped 48% YoY in 2025

### Sources

- [Social Media Today: X's Algorithm Shifting to Grok](https://www.socialmediatoday.com/news/x-formerly-twitter-switching-to-fully-ai-powered-grok-algorithm/803174/)
- [Social Media Today: X Now Algorithmically Ranks Following Feed](https://www.socialmediatoday.com/news/x-formerly-twitter-sorts-following-feed-algorithm-ai-grok/806617/)
- [Hashmeta: Major Twitter Algorithm Changes in 2025](https://hashmeta.com/insights/twitter-algorithm-changes-2025)
- [PiunikaWeb: X Following Feed Not in Chronological Order](https://piunikaweb.com/2026/02/15/x-following-feed-not-in-chronological-order-heres-what-we-know/)
- [Social Media Today: X Pledges to Publish Algorithm Code](https://www.socialmediatoday.com/news/x-formerly-twitter-to-release-algorithm-code-public-open-source/809301/)
- [Wikipedia: Twitter under Elon Musk](https://en.wikipedia.org/wiki/Twitter_under_Elon_Musk)
- [Gizmodo: Elon Musk on X Timeline](https://gizmodo.com/elon-musk-says-in-one-week-he-will-fully-reveal-why-your-x-timeline-is-like-that-2000708652)

---

## 6. What We Learned from the Open-Sourced Algorithm

### The 2023 Release (github.com/twitter/the-algorithm)

**What was released:**
- The recommendation algorithm code (Java/Scala)
- SimClusters community detection system
- TweepCred reputation scoring
- Engagement prediction models (architecture, not weights)
- Home timeline mixing logic
- Content filtering heuristics

**What was NOT released:**
- Model weights and parameters (the 48M parameter neural network)
- Training data
- Feature definitions for the ML models
- Real-time configuration values

**Key Community Findings:**

1. **The engagement weight hierarchy was revealed**: Reply-chains (+75) >> Replies (+13.5) >> Profile clicks (+12) >> Retweets (+1) >> Likes (+0.5). This showed that conversation depth matters far more than passive engagement.

2. **Negative signals are catastrophically weighted**: A single report (-369x) or block (-74x) devastates distribution. This asymmetry was not widely understood before.

3. **SimClusters defines your "tribe"**: 145,000 virtual communities determine your out-of-network content. These are updated every 3 weeks. Tweet embeddings are updated each time a tweet is favorited — the "InterestedIn" vector of each user who liked the tweet is added to the tweet's vector.

4. **TweepCred gatekeeps distribution**: The threshold at 65/100 that limits low-credibility accounts to 3 distributed tweets was a major revelation. This means accounts perceived as low quality are functionally invisible.

5. **Special account flags existed**: References to flags for Elon Musk, "power users," and political affiliations were found in the code. Engineers claimed these were for A/B testing, but the finding fueled transparency concerns.

6. **50/50 split is not fixed**: The in-network/out-of-network ratio varies per user based on engagement history, not a hard 50/50 rule.

7. **The code was a snapshot, not the system**: As researcher Sol Messing noted, "You can't learn much from this release in and of itself — you need the underlying model features, parameters, and data to really understand the algorithm." The code without weights is like a recipe without quantities.

### The 2026 Release (github.com/xai-org/x-algorithm)

**What changed:**
- Rewritten in Rust (from Java/Scala)
- Transformer architecture (ported from Grok-1)
- All hand-engineered features eliminated
- Engagement weights are now explicitly documented
- Grok-based sentiment analysis integrated
- Updated every 4 weeks (vs. single snapshot in 2023)

**Key new learnings:**
- The ranking logic is now a transformer, making it harder to reason about mechanistically
- Sentiment analysis is a first-class ranking signal
- The system processes 500M tweets/day with 5B ranking decisions
- Premium boost is baked into the architecture, not a separate heuristic

### Sources

- [GitHub: twitter/the-algorithm](https://github.com/twitter/the-algorithm)
- [GitHub: xai-org/x-algorithm](https://github.com/xai-org/x-algorithm)
- [Sol Messing: What Can We Learn From Twitter's Algorithm](https://solomonmg.github.io/post/twitter-the-algorithm/)
- [NYU CSMaP: What Can We Learn From Twitter's Open Source Algorithm](https://csmapnyu.org/impact/news/what-can-we-learn-from-twitters-open-source-algorithm)
- [Steven Tey: How the Twitter Algorithm Works](https://steventey.com/blog/twitter-algorithm)
- [Tweet Hunter: Twitter Algorithm Source Code Explained](https://tweethunter.io/blog/twitter-algorithm-source-code-explained)
- [InfoQ: Twitter Open-Sources Recommendation Algorithm](https://www.infoq.com/news/2023/04/twitter-algorithm/)
- [Medium (Gowtham Boyina): Deep Dive Into X's Recommendation Algorithm](https://thegowtham.medium.com/deep-dive-inside-x-fka-twitter-s-recommendation-algorithm-460b2bd4e26a)

---

## 7. Practical Implications for a People-Discovery Tool

This section translates all of the above into actionable insights for a tool (like this one) that searches X to find relevant people and accounts.

### Search Strategy Implications

**Use "Top" search to find high-quality, algorithmically-validated accounts:**
- "Top" results have passed X's engagement threshold, meaning the tweet authors are likely established, active accounts
- The engagement scoring biases toward accounts that generate replies and conversation, which correlates with genuine expertise and community engagement
- However, "Top" results skew toward Premium/verified accounts and accounts with existing large followings

**Use "Latest" search to find emerging voices and niche experts:**
- "Latest" results are chronologically sorted with no engagement threshold
- This catches newer accounts, niche experts, and people in smaller communities who haven't crossed the engagement threshold
- Better for discovering people who are actively tweeting about a topic right now
- Your current approach of using "Latest" for the last query is sound

**Query design matters enormously:**
- Different query phrasings surface different communities (aligns with the current multi-query approach)
- Using `min_faves:N` or `min_retweets:N` operators can pre-filter for quality, but be careful with thresholds — too high and you only get celebrities
- `filter:verified` is now essentially `filter:premium` and biases toward paying users, not necessarily the most relevant experts
- Negative operators (`-filter:replies`) help exclude noise when looking for original content creators

### What the Algorithm Tells Us About Account Quality

**Signals that a person is genuinely influential in their domain:**
- High reply counts on their tweets (the algorithm weights this 13.5x-75x over likes)
- People clicking their profile from tweets (12x weight)
- Bookmarks on their content (10x weight — indicates people find it reference-worthy)
- Extended conversation dwell time (10x weight — their threads keep people reading)
- Retweet/quote-tweet ratio (people sharing their ideas with attribution)

**Signals to be skeptical of:**
- High like counts alone (likes are the weakest positive signal at 0.5x)
- Large follower counts with low engagement (possible bot followers)
- Mostly link-sharing accounts (these are algorithmically suppressed, so their tweet engagement may appear artificially low)
- Accounts that primarily post combative/negative content (now suppressed by Grok sentiment analysis, possibly underrepresented in search results)

### Ranking and Scoring Adjustments

For the tool's own ranking of discovered accounts, consider weighting these factors:

1. **Reply-to-like ratio**: High ratios indicate the person generates genuine discussion (mirrors X's own 27:1 reply:like weighting)
2. **Retweet/quote-tweet presence**: Being retweeted by others in the same domain signals peer recognition
3. **Bio completeness and keyword relevance**: Directly impacts search discoverability and signals professionalism
4. **Recent activity**: The 6-hour half-life means the most active accounts dominate search results; inactive accounts may be relevant but harder to find via search
5. **Premium status awareness**: Premium accounts are over-represented in search results. This is not necessarily a quality signal — it means they pay $8-16/month, not that they are more expert.

### Limitations and Caveats

**What search results miss:**
- Accounts that primarily post links (algorithmically suppressed since 2024-2025)
- Accounts with combative/critical tone (suppressed by Grok sentiment since 2026)
- Non-Premium accounts (structurally disadvantaged, 2-10x less visible)
- Accounts in small SimCluster communities (low out-of-network distribution)
- Accounts that have been mass-reported (even falsely — the -369x penalty is applied regardless)

**What search results over-represent:**
- Premium/verified accounts (2-4x algorithmic boost)
- Accounts with large existing followings (engagement velocity advantage)
- Accounts posting positive/constructive content (Grok sentiment boost)
- Accounts that generate controversy or replies (conversation depth is the #1 positive signal)
- English-language accounts (platform skew)

**Third-party API considerations (SocialData.tools):**
- The API mirrors X's search functionality including "Top" vs "Latest" modes
- "Top" results from the API reflect X's internal ranking, including all the biases above
- "Latest" results from the API are chronologically sorted and bypass ranking biases
- The 7-day window for standard search means the tool only finds people who tweeted recently about the topic
- Rate limits constrain how many queries can be run per search

### Recommendations for the Tool

1. **Keep the multi-query approach**: Different phrasings catch different SimCluster communities. 3-7 queries with varied angles is well-aligned with how X's content discovery works.

2. **Mix "Top" and "Latest" results**: "Top" finds established voices; "Latest" finds active participants. The current approach of making the last query "Latest" is good; consider making 50% of queries each type.

3. **Be aware of Premium bias in results**: When ranking discovered accounts, don't treat the algorithm's ranking as ground truth for relevance. An unverified account with fewer impressions might be more relevant than a Premium account that gets boosted by subscription status.

4. **Use engagement quality, not quantity, for scoring**: Reply counts and conversation engagement are better relevance signals than likes or follower counts. This aligns with X's own weighting where replies are 27x more valuable than likes.

5. **Consider adding `min_faves` or `min_retweets` operators selectively**: For broad queries that return too many results, setting a low engagement floor (e.g., `min_faves:5`) can improve signal-to-noise without being overly restrictive.

6. **Account for the link-posting penalty**: People who share lots of links (researchers, journalists, curators) are systematically under-represented in search results. If the user is looking for these types of accounts, the tool may need to search harder or use different query strategies.

7. **Profile data matters**: Since TweepCred factors in bio quality, follower ratios, and account completeness, the profiles returned by the API likely skew toward accounts that have invested in their presence. This is generally good for a people-discovery tool.

### Sources (Full List)

- [Tweet Archivist: Complete Technical Breakdown](https://www.tweetarchivist.com/how-twitter-algorithm-works-2025)
- [PostEverywhere: How the X Algorithm Works in 2026](https://posteverywhere.ai/blog/how-the-x-twitter-algorithm-works)
- [Sprout Social: Twitter Algorithm 2026](https://sproutsocial.com/insights/twitter-algorithm/)
- [Buffer: How the Twitter Algorithm Works](https://buffer.com/resources/twitter-timeline-algorithm/)
- [Social Media Today: Key Ranking Factors](https://www.socialmediatoday.com/news/x-formerly-twitter-open-source-algorithm-ranking-factors/759702/)
- [X Engineering Blog: Recommendation Algorithm](https://blog.x.com/engineering/en_us/topics/open-source/2023/twitter-recommendation-algorithm)
- [GitHub: twitter/the-algorithm](https://github.com/twitter/the-algorithm)
- [GitHub: xai-org/x-algorithm](https://github.com/xai-org/x-algorithm)
- [Arxiv: Auditing Political Exposure Bias](https://arxiv.org/abs/2411.01852)
- [SocialData API Documentation](https://docs.socialdata.tools/reference/get-search-results/)
- [X Developer: Search Operators](https://developer.x.com/en/docs/x-api/v1/rules-and-filtering/search-operators)
- [Hootsuite: How the X Algorithm Works](https://blog.hootsuite.com/twitter-algorithm/)
- [SocialBee: Understanding the X Algorithm](https://socialbee.com/blog/twitter-algorithm/)
- [Circleboom: TweepCred Explained](https://circleboom.com/blog/tweepcred-what-it-is-why-it-matters-and-how-to-increase-your-score-on-x-twitter/)
- [Circleboom: Hidden X Algorithm](https://blog-content.circleboom.com/the-hidden-x-algorithm-tweepcred-shadow-hierarchy-dwell-time-and-the-real-rules-of-visibility/)
- [Hashmeta: Major Algorithm Changes 2025](https://hashmeta.com/insights/twitter-algorithm-changes-2025)
- [Sol Messing: What Can We Learn](https://solomonmg.github.io/post/twitter-the-algorithm/)
- [NYU CSMaP: Open Source Algorithm Analysis](https://csmapnyu.org/impact/news/what-can-we-learn-from-twitters-open-source-algorithm)
- [Stanford: WTF Service at Twitter](https://stanford.edu/~rezab/papers/wtf_overview.pdf)
- [ExportData: Advanced Search Operators](https://www.exportdata.io/blog/advanced-twitter-search-operators/)
- [Social Media Today: Following Feed Algorithm](https://www.socialmediatoday.com/news/x-formerly-twitter-sorts-following-feed-algorithm-ai-grok/806617/)
