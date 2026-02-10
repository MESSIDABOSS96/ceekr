# Twitter Account Finder

A tool to find relevant Twitter accounts for any purpose. Describe who you want to find and why, and it returns a curated list of people worth connecting with.

## Architecture

- **Frontend**: Next.js (App Router) + Tailwind CSS + shadcn/ui — `frontend/`
- **Backend**: FastAPI with SSE streaming — `server.py`
- **LLM**: Claude API (Sonnet) via `anthropic` SDK with structured output
- **Twitter data**: SocialData.tools API via `httpx`

```
Browser (Next.js on :3000)  ──POST SSE──►  FastAPI on :8000
                                            ├── core/llm.py
                                            ├── core/twitter.py
                                            └── prompts/
```

## Key Files

- `server.py` - FastAPI backend with SSE `/api/search` endpoint
- `frontend/app/page.tsx` - Main page with `useReducer` state machine
- `frontend/lib/api.ts` - SSE client using POST fetch + ReadableStream
- `frontend/lib/types.ts` - TypeScript interfaces mirroring `core/models.py`
- `frontend/components/` - UI components (search-box, result-card, etc.)
- `config.py` - Environment variables and settings
- `core/models.py` - Pydantic models for data structures
- `core/twitter.py` - SocialData.tools API wrapper and search orchestration
- `core/llm.py` - Claude API calls for query generation and ranking
- `prompts/` - Prompt templates for LLM calls

## How It Works

1. User describes who they want to find (and optionally why)
2. Frontend sends POST to `/api/search` and reads SSE stream
3. If input is vague, Claude asks clarifying questions (streamed back as `intent` event)
4. Claude generates 3-7 Twitter search queries from different angles
5. SocialData.tools API executes searches and collects unique accounts
6. Claude ranks accounts by relevance with explanations
7. Results streamed back as `results` event with quality assessment

## API Design

**`POST /api/search`** — SSE endpoint. Input: `{ "query": "string" }`

Events streamed: `progress`, `intent`, `queries`, `results`, `error`

**`GET /api/health`** — Returns config validation status.

## Key Decisions

- **Search tweets, not profiles**: Twitter search returns tweets. We find relevant people through their tweets.
- **Multiple queries**: Different phrasings catch different conversations. 3-7 queries improve coverage.
- **LLM for query gen AND ranking**: Claude understands intent and judges true relevance.
- **Structured output via tool_use**: Guarantees valid JSON responses.
- **SSE streaming**: Real-time progress updates during search.

## Bookmarked for Later (v2+)

- [ ] Mutual followers detection (show "Mutual: @xyz, @abc")
- [ ] Auto-outreach: Generate personalized DMs/replies
- [ ] Deeper network analysis: 2nd-degree connections

## Known Issues / Gotchas

- SocialData.tools API has rate limits
- API keys must be set in `.env`

## Development Commands

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install

# Run backend (Terminal 1)
python3 server.py  # or: uvicorn server:app --reload --port 8000

# Run frontend (Terminal 2)
cd frontend && npm run dev  # http://localhost:3000
```
