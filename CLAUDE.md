# Twitter Account Finder

A tool to find relevant Twitter accounts for any purpose. Describe who you want to find and why, and it returns a curated list of people worth connecting with.

## Architecture

- **UI**: Streamlit (single Python file)
- **LLM**: Claude API (Sonnet) via `anthropic` SDK with structured output
- **Twitter data**: twikit (uses Twitter cookies for auth, free)

## Key Files

- `app.py` - Streamlit UI and orchestration
- `config.py` - Environment variables and settings
- `core/models.py` - Pydantic models for data structures
- `core/twitter.py` - twikit wrapper and search orchestration
- `core/llm.py` - Claude API calls for query generation and ranking
- `prompts/` - Prompt templates for LLM calls

## How It Works

1. User describes who they want to find (and optionally why)
2. If input is vague, Claude asks clarifying questions
3. Claude generates 3-5 Twitter search queries from different angles
4. twikit executes searches and collects unique accounts
5. Claude ranks accounts by relevance with explanations
6. Results displayed with scores, bios, and "why relevant" explanations

## Cookie Setup (Required)

1. Install browser extension: "Get cookies.txt LOCALLY"
2. Go to twitter.com while logged in
3. Export cookies to `cookies.txt` in project root
4. App loads cookies on startup

## Key Decisions

- **Search tweets, not profiles**: Twitter search returns tweets. We find relevant people through their tweets.
- **Multiple queries**: Different phrasings catch different conversations. 3-5 queries improve coverage.
- **LLM for query gen AND ranking**: Claude understands intent and judges true relevance.
- **Structured output via tool_use**: Guarantees valid JSON responses.

## Bookmarked for Later (v2+)

- [ ] Mutual followers detection (show "Mutual: @xyz, @abc")
- [ ] Auto-outreach: Generate personalized DMs/replies
- [ ] Deeper network analysis: 2nd-degree connections
- [ ] SocialData.tools as paid fallback if twikit proves unreliable

## Known Issues / Gotchas

- twikit can break if Twitter changes their site structure
- Cookies expire periodically (need to re-export)
- Rate limits apply even when scraping

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```
