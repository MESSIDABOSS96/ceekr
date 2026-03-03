# X (Twitter) Platform Features: Market Research for People-Discovery Tools (Early 2026)

## 1. X Chats

### What Are They?
X Chat is a fully encrypted messaging system that replaced X's legacy Direct Messages (DMs) in late 2025. It represents a fundamental overhaul of X's private messaging infrastructure, positioning X as a competitor to WhatsApp, Signal, and Messenger.

### How Do They Work?
- **End-to-end encryption** is now standard for all messages and file sharing
- **Video and voice calls** are built in (previously a separate or limited feature)
- **Disappearing messages** with customizable deletion timers
- **Message editing and deletion** after sending
- **Screenshot controls**: senders can be notified of screenshot attempts, or screenshots can be blocked entirely
- **Group chats** support up to **256 members** (increased from previous limits)
- **Multi-device support** with no formal limit on devices; logging out deletes messages and erases private keys on that device

### Launch Timeline
- **May 2025**: XChat beta announced and began rolling out to select users ([TechCrunch](https://techcrunch.com/2025/05/30/xs-new-dm-feature-xchat-is-rolling-out-in-beta/))
- **November 14, 2025**: Full rollout began on iOS and web, replacing the old DM system entirely while preserving existing conversations ([MacRumors](https://www.macrumors.com/2025/11/17/x-launches-chat-encrypted-dm-service/), [Engadget](https://www.engadget.com/social-media/x-is-finally-rolling-out-chat-its-dm-replacement-with-encryption-and-video-calling-233032571.html))
- **December 2025**: Replacement confirmed complete for all users ([Piunikaweb](https://piunikaweb.com/2025/12/10/x-formerly-twitter-has-replaced-dms-with-x-chat-for-all-users/))
- **Standalone desktop web app** launched at chat.x.com ([Social Media Today](https://www.socialmediatoday.com/news/x-formerly-twitter-launches-separate-chat-app-desktop/808201/))
- A **standalone mobile app** is reportedly in development

### Encryption Caveats
- Metadata (sender, recipient, timestamps) is **not encrypted**
- The system lacks safeguards against **man-in-the-middle attacks** -- an insider or X itself could theoretically intercept conversations without triggering a warning
- X is developing "Safety Number Verification" to address this gap

### Who's Using Them?
Group chats with the 256-member limit are being used by crypto/Web3 communities, creator collaboratives, and business networking groups. The standalone desktop app signals X's ambition to become a primary communications platform, not just a social network.

### Relevance to People Discovery
X Chat is a **closed, encrypted channel** -- it is inherently private and not searchable. It does not surface new people. However, the 256-person group chat limit means that interest-based groups are forming, and participation in those groups can be a signal of community membership.

---

## 2. Searchability and API Access for Chat Data

### Can X Chats Be Searched or Indexed Externally?
**No.** X Chat messages are end-to-end encrypted and cannot be:
- Indexed by search engines
- Searched via the X API
- Accessed by third-party tools or scrapers

### Official API Endpoints for Chat/DM Data
The X API v2 does include DM endpoints, but these are for **sending and managing** messages via authenticated apps, not for searching or indexing chat content at scale. Access requires OAuth 2.0 user authentication and is subject to strict rate limits.

### Bottom Line for People Discovery
Chat data is a **dead end** for external people-discovery tools. The encryption model and privacy design make it inaccessible.

---

## 3. X Spaces (Audio)

### How Do Audio Spaces Fit In?
X Spaces is a live audio conversation feature -- essentially Twitter's answer to Clubhouse. Users can host or join real-time audio discussions with speakers, co-hosts, and listeners.

### Business Use Cases
Spaces are actively used for:
- **Thought leadership**: Hosting Spaces on trending industry topics positions individuals and brands as experts
- **Networking**: Live discussions lead to partnerships, job offers, and business deals
- **Product launches and Q&As**: Brands spotlight internal thought leaders
- **Podcast-style content**: Recurring scheduled Spaces serve as podcast substitutes
- **Community engagement**: Twitter's research shows a 10% increase in Spaces conversations correlates with a 3% rise in sales volume

### API Access for Spaces
The X API v2 includes dedicated Spaces endpoints:

| Endpoint | Description | Auth Required |
|----------|-------------|---------------|
| `GET /2/spaces/:id` | Look up a Space by ID | OAuth 2.0 App-Only |
| `GET /2/spaces` | Look up multiple Spaces | OAuth 2.0 App-Only |
| `GET /2/spaces/by/creator_ids` | Find Spaces by creator user IDs | OAuth 2.0 App-Only |
| `GET /2/spaces/search` | Search for Spaces by keyword in title | OAuth 2.0 App-Only |

**What you CAN get**:
- Space metadata (title, state, scheduled start time, created time)
- Creator/host user IDs
- Speaker user IDs (as an array)
- Aggregate participant count

**What you CANNOT get**:
- Individual listener identities (only aggregate count)
- Audio recordings or transcripts
- Chat messages within a Space

Under the new pay-per-use pricing pilot, single Spaces lookups cost **1 credit** -- making it one of the cheapest API operations.

### Third-Party Access
Providers like **Netrows** include Spaces in their 26-endpoint coverage. **SocialData.tools** also indexes Space metadata. However, no third-party provider can access listener lists or audio content.

### Relevance to People Discovery
Spaces data is **partially accessible** and highly relevant:
- You can discover **who hosts Spaces** on specific topics (strong signal of expertise/authority)
- You can discover **who speaks** in Spaces (strong engagement signal)
- You **cannot** discover passive listeners
- Keyword search of Space titles enables topic-based discovery

---

## 4. X Communities

### What Are Communities?
Communities are topic-based groups within X -- similar to Facebook Groups or Reddit subreddits. Users gather around shared interests, industries, or themes. Only members can create posts within a Community, but (as of February 2026) posts are visible to everyone.

### Major 2026 Change: Public Visibility
As of **February 2026**, X made a significant philosophical shift:
- **Community posts are now visible to everyone on X**, not just members
- Posts appear in the For You feed, global search results, post recommendations, and followers' timelines
- **Everyone on X can reply** to Community posts (including non-members), but replies from Community members are prioritized
- Community posts now appear on members' public profiles

This effectively transformed Communities from semi-private group spaces into **publicly visible content hubs** while maintaining membership requirements for posting.

### Activity Level
Communities are growing in adoption, particularly around:
- Tech/developer communities
- Crypto and finance
- Creator economy
- Political and news discussion
- Niche hobbies and interests

### Searchability and API Access

| Access Method | Community Data Available? |
|---------------|--------------------------|
| Official X API v2 | **No dedicated Communities endpoint** in the public API docs as of early 2026 |
| X Search (on-platform) | Community posts now appear in global search results |
| Third-party APIs | **Yes** -- Netrows and SociaVault offer Community Tweets endpoints (e.g., `GET /api/twitter/community-tweets`) |
| Scraping | Community posts are now public HTML, making them scrapable |

### Relevance to People Discovery
Communities are **highly relevant** post-February 2026:
- Community membership is a strong signal of interest/expertise
- Community posts are now publicly searchable -- you can find people through their Community activity
- Third-party APIs (SociaVault, Netrows) provide programmatic access to Community tweet data
- Since only members can post, posting in a Community signals genuine engagement with the topic

---

## 5. Long-Form Articles

### Overview
X now supports two levels of long-form content:
1. **Long-form posts**: Up to **25,000 characters** (Premium subscribers only; standard accounts remain at 280 characters)
2. **Articles**: A dedicated rich-text editor for blog-style content with formatting, headers, and images. Initially limited to Premium+ only, but **expanded to all Premium subscribers in January 2026**.

### Business Use
- **B2B thought leadership**: 64% of UK business decision-makers report discovering new industry perspectives through X, compared to 41% through LinkedIn articles
- **Creator monetization**: Articles may be weighted more heavily than short posts in the algorithm, recognizing the effort involved
- **$1M Article Prize**: X announced a $1 million prize for the top article, judged primarily on Verified Home Timeline impressions. Requirements: original, at least 1,000 words.
- **Content marketing**: Businesses use Articles as an alternative to external blog posts, keeping engagement within the X ecosystem

### API Access
- Long-form posts are returned via standard tweet endpoints in the X API v2 (the text field contains the full content)
- Articles appear as tweets with a link card; the full article content is not directly available through the API
- Third-party scrapers can access Article content by following the link

### Relevance to People Discovery
People who write long-form Articles on specific topics are **high-signal targets** for people discovery. They are demonstrating expertise, thought leadership, and investment in a subject.

---

## 6. X Premium / Verified Status

### Current Tiers (Early 2026)

| Tier | Price (Web) | Key Features |
|------|-------------|--------------|
| **Basic** | $3/month | Longer posts, post editing, reply prioritization, text formatting, bookmark folders |
| **Premium** | $8/month | All Basic + blue checkmark, reduced ads, monetization, Articles, Grok access |
| **Premium+** | $40/month | All Premium + no ads, highest reply prioritization, Radar Search, highest Grok limits |
| **Verified Organizations** | ~$1,000/month | Gold checkmark, job postings, team accounts, brand tools |

### Impact on Visibility and Reach

| Metric | Free Account | Premium | Premium+ |
|--------|-------------|---------|----------|
| Median impressions per post | <100 | ~600 | ~1,550+ |
| In-network visibility boost | 1x (baseline) | 4x | 4x+ |
| Out-of-network boost | 1x (baseline) | 2x | 2x+ |
| Reply impression advantage | baseline | 30-40% higher | highest |
| Link post engagement (post-March 2025) | ~0% | normal | normal |

**Critical finding**: Since **March 2025**, non-Premium accounts sharing links get **nearly zero engagement**. Premium accounts get ~10x more reach per post than free accounts.

---

## 7. Other New Features Affecting Business Use & People Discovery

### Grok AI Integration
- Grok now **powers the algorithm**: reads every post and video (100M+ per day)
- **Following feed is no longer chronological** (since November 2025)
- Users can **tell Grok how to adjust their feed** via natural language

### Account Deep Dive Feature
- **Country where the account was created** (based on IP address)
- **Join date** and **username change history**
- **VPN detection** (flags accounts potentially masking location)

### X Money (Payments)
- **Visa-backed digital wallet** within the X app
- Peer-to-peer transfers via @username or QR code
- X has secured money transmitter licenses in 40+ US states
- **External beta expected within 1-2 months** as of February 2026

### Radar (Real-Time Keyword Analytics)
- Available to **Premium+ subscribers** and **Verified Organizations**
- Monitor keywords with advanced search, visualize trends
- Previously cost $1,000/month -- now included in Premium+ ($40/month)

### Creator Monetization (2026 = "Year of the Creator")
- Revenue sharing pool **more than doubled** in 2025
- Over **$45 million paid out** to creators to date
- Eligibility lowered to **500 active followers** (previously 5,000)
- Creators reporting **2-3x revenue increases** in early 2026

### Job Postings (X Hiring)
- **1.5M+ active job postings** on X
- Available to Verified Organizations and Premium subscribers
- Positions X as a LinkedIn competitor for hiring

---

## 8. API Access Summary by Feature

| Feature | Official X API v2 | Third-Party APIs | Scraping | Notes |
|---------|-------------------|-----------------|----------|-------|
| **X Chat/DMs** | Send/manage only | No | No (encrypted) | Dead end for discovery |
| **Spaces** | Yes -- lookup, search | Yes (Netrows, SocialData) | Partial | Speakers available; listeners aggregate only |
| **Communities** | No dedicated endpoint | Yes (Netrows, SociaVault) | Yes (now public) | Community tweets accessible |
| **Long-form Posts** | Yes (via tweet endpoints) | Yes | Yes | Full text in tweet payload |
| **Articles** | Partial (link card only) | Partial | Yes (follow link) | Full content requires fetching URL |
| **User Profiles** | Yes | Yes | Yes | Includes verified status, follower count |
| **Tweets/Search** | Yes (7-day free; full archive at Pro) | Yes | Yes | Standard search is 6-9 day index |
| **Premium Status** | Yes (`verified`, `verified_type`) | Yes | Yes | Ranking/filtering signal |
| **Job Postings** | No public endpoint | Limited | Yes | Visible on profiles |
| **X Money** | Not yet | No | No | Still in closed beta |

### Official API Pricing (Early 2026)

| Tier | Cost | Key Limits |
|------|------|------------|
| Free | $0 | Write-only, ~500 posts/month |
| Basic | $200/month | 15K reads/month, 7-day search |
| Pro | $5,000/month | 1M reads/month, full archive search |
| Enterprise | $42,000+/month | Custom limits |
| Pay-Per-Use (Pilot) | Credit-based | 1 credit for single lookups, 5 for paginated |

### Key Third-Party API Providers

| Provider | Strengths | Community Data? | Spaces Data? |
|----------|-----------|----------------|--------------|
| **SocialData.tools** | Real-time, scalable | Likely via tweet search | Yes (metadata) |
| **Netrows** | 26 endpoints incl. Communities | Yes | Yes |
| **SociaVault** | Cost-effective, Community Tweets | Yes | Yes |
| **TwitterAPI.io** | Traditional REST, affordable | Varies | Varies |
| **Apify** | Visual scraper builder | Via scraping | Via scraping |
| **Bright Data** | Enterprise scale, legal precedent | Via scraping | Via scraping |

---

## Key Takeaways for a People-Discovery Tool

1. **Communities are now gold**: February 2026 change makes Community posts publicly visible and searchable. Third-party APIs already support this.
2. **X Chat is a black box**: Encrypted, private, inaccessible. Not useful for discovery.
3. **Spaces hosts/speakers are discoverable**: API returns speaker IDs and allows keyword search of Space titles.
4. **Premium status is a critical filter**: 10x reach multiplier means verified users dominate results.
5. **Long-form Articles signal authority**: High-value discovery targets.
6. **Grok is reshaping discovery**: AI-driven algorithm means organic discoverability is changing rapidly.
7. **API costs are significant**: Official API starts at $200/month; third-party providers are more affordable.
8. **X Money will add signal layer**: Transaction patterns could become discovery signals once public.

---

### Sources
- [TechCrunch - XChat Beta](https://techcrunch.com/2025/05/30/xs-new-dm-feature-xchat-is-rolling-out-in-beta/)
- [MacRumors - X Chat Launch](https://www.macrumors.com/2025/11/17/x-launches-chat-encrypted-dm-service/)
- [Engadget - X Chat Rollout](https://www.engadget.com/social-media/x-is-finally-rolling-out-chat-its-dm-replacement-with-encryption-and-video-calling-233032571.html)
- [Piunikaweb - DMs Replaced](https://piunikaweb.com/2025/12/10/x-formerly-twitter-has-replaced-dms-with-x-chat-for-all-users/)
- [Social Media Today - Standalone Chat App](https://www.socialmediatoday.com/news/x-formerly-twitter-launches-separate-chat-app-desktop/808201/)
- [Social Media Today - Communities Visible](https://www.socialmediatoday.com/news/x-formerly-twitter-makes-communities-posts-visible/739116/)
- [TechCrunch - Communities Update](https://techcrunch.com/2025/03/04/x-updates-communities-with-new-filters-sorting-options-and-a-way-to-see-your-own-posts/)
- [Buffer - X Premium Reach Analysis](https://buffer.com/resources/x-premium-review/)
- [Influencer Marketing Hub - Premium 10x Reach](https://influencermarketinghub.com/x-premium-users-get-10x-more-reach-report/)
- [SocialBee - X Updates 2026](https://socialbee.com/blog/twitter-updates/)
- [Finance Magnates - X Money](https://www.financemagnates.com/fintech/musks-x-introduces-x-money-account-for-peer-to-peer-payments-with-visa/)
- [TechCrunch - Radar Launch](https://techcrunch.com/2024/10/21/x-rolls-out-its-real-time-search-tool-radar-to-premium-subscribers/)
- [Quasa - 2026 Year of the Creator](https://quasa.io/media/x-declares-2026-the-year-of-the-creator-revamped-monetization-and-ongoing-experiments)
- [X Developer Docs - Spaces API](https://docs.x.com/x-api/spaces/introduction)
- [Netrows - Top API Providers 2026](https://www.netrows.com/blog/top-twitter-x-data-api-providers-2026)
