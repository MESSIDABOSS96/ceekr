# Ceekr Workspace Pivot — Frontend Development Guide

This document is the single source of truth for building the workspace frontend. The backend (Phase 1 MVP) is complete and running. Load this into any Claude session working on the frontend.

**Last updated**: 2026-02-25 (backend implementation complete)

---

## 1. The Pivot

Ceekr is moving from "search → flat list of profile cards" to a **Clay-inspired research workspace**.

**Before**: User searches → SSE stream → flat 2-column grid of ranked profile cards.

**After**: User searches → SSE stream → **workspace** with **journals** (semantic groups of people) displayed on a spatial canvas. Each journal is a node the user can click into to see the people inside it.

**Scope for v1**: People-only. Each journal = a group of people sharing a characteristic (topic expertise, role, location, career stage, community). No tweet/article journals yet.

**Key concept — Journals**: The LLM analyzes search results and clusters them into 1-6 meaningful groups. For example, searching "AI researchers in NYC" might produce journals like "NLP at NYU/Columbia", "AI Startup Founders", "Open Source Tool Builders". A person can appear in multiple journals (e.g., both "NYC-based" and "AI-focused").

---

## 2. Architecture

```
Browser (Next.js :3000)  ──POST SSE──►  FastAPI :8000
                                         ├── WorkspaceOrchestrator
                                         │   ├── calls existing v1/v2 algorithm (unchanged)
                                         │   ├── generate_journals() LLM call (Haiku)
                                         │   └── compute_layout() + compute_overlaps()
                                         ├── SQLite (ceekr.db) — WAL mode
                                         └── existing POST /api/search (unchanged, backward compat)
```

**Data persistence**: Workspaces live in SQLite server-side. No auth required — anyone with the workspace URL can view it. The old `/s/{id}` localStorage flow still works independently.

---

## 3. Backend API Contract (Implemented)

All endpoints are live. Here are the exact response shapes.

### 3.1 `POST /api/workspace` — Create workspace (SSE stream)

**Request**: `{ "query": "AI researchers in NYC" }`
**Headers**: Optional `x-session-token` for network matching.

**SSE Events** (streamed in order):

```
event: progress
data: {"message": "Scanning Twitter..."}

event: progress
data: {"message": "Understanding your search..."}

event: intent
data: {"persona": "AI researchers", "topic": "AI/ML research", "goal": "...", "specificity": 3, "key_signals": [...], "anti_signals": [...]}

event: queries
data: [{"query": "...", "rationale": "...", "angle": "..."}, ...]

event: progress
data: {"message": "Found 24 accounts, ranking..."}

event: progress
data: {"message": "Organizing results into groups..."}

event: workspace    ← FINAL EVENT
data: {
  "workspace_id": "a1b2c3d4e5f6",
  "query": "AI researchers in NYC",
  "status": "ready",
  "summary": "Found 24 AI researchers across 4 groups...",
  "quality": "strong",
  "total_people": 24,
  "refinement_questions": [],
  "journals": [
    {
      "id": "f7e8d9c0b1a2",
      "label": "NLP Researchers at NYU/Columbia",
      "description": "Academic researchers at NYC universities working on NLP.",
      "theme": "location",
      "color": "#06b6d4",
      "people_count": 8,
      "canvas_x": 200.0,
      "canvas_y": 150.0
    },
    {
      "id": "c3d4e5f6a7b8",
      "label": "Open Source Tool Builders",
      "description": "Contributors to ML frameworks and fine-tuning tools.",
      "theme": "topic",
      "color": "#6366f1",
      "people_count": 5,
      "canvas_x": 550.0,
      "canvas_y": 300.0
    }
  ],
  "overlaps": [
    {
      "journal_a": "f7e8d9c0b1a2",
      "journal_b": "c3d4e5f6a7b8",
      "shared_count": 2,
      "shared_handles": ["sarahchen", "mljohn"]
    }
  ]
}
```

**Important**: The `workspace` event does NOT include full people data. People are fetched on demand per journal.

**Note on progress events**: The `data` field for `progress` events is a JSON object `{"message": "..."}`. For `intent` and `queries` events, the data is the parsed JSON directly.

### 3.2 `GET /api/workspace/{workspace_id}` — Load workspace

Returns the full workspace state. Used when navigating to `/w/{id}` to load an existing workspace.

```json
{
  "workspace_id": "a1b2c3d4e5f6",
  "query": "AI researchers in NYC",
  "status": "ready",
  "summary": "Found 24 AI researchers across 4 groups...",
  "quality": "strong",
  "intent": {"persona": "...", "topic": "...", "goal": "...", "specificity": 3},
  "journals": [
    {
      "id": "f7e8d9c0b1a2",
      "label": "NLP Researchers at NYU/Columbia",
      "description": "...",
      "theme": "location",
      "color": "#06b6d4",
      "people_count": 8,
      "canvas_x": 200.0,
      "canvas_y": 150.0,
      "enrichment_status": "pending"
    }
  ],
  "total_people": 24,
  "refinement_questions": [],
  "created_at": "2026-02-25T...",
  "updated_at": "2026-02-25T..."
}
```

**Differences from SSE `workspace` event**: Adds `intent`, `created_at`, `updated_at`, `enrichment_status` per journal. No `overlaps` — those need to be recomputed client-side or fetched separately (currently only available in the SSE stream).

### 3.3 `GET /api/workspace/{workspace_id}/journal/{journal_id}` — Get journal people

```json
{
  "journal_id": "f7e8d9c0b1a2",
  "people": [
    {
      "user_id": "12345",
      "handle": "sarahchen",
      "name": "Sarah Chen",
      "bio": "NLP researcher at NYU...",
      "followers_count": 12400,
      "following_count": 890,
      "tweet_count": 3400,
      "profile_url": "https://twitter.com/sarahchen",
      "profile_image_url": "https://pbs.twimg.com/...",
      "recent_tweets": [
        {
          "id": "...",
          "text": "Just published our paper on...",
          "created_at": "2026-02-20T...",
          "like_count": 234,
          "retweet_count": 45,
          "reply_count": 12,
          "media_urls": []
        }
      ],
      "matched_queries": ["\"NLP research\" NYC"],
      "location": "New York, NY",
      "verified": false,
      "created_at": "2019-03-...",
      "network": {"you_follow": false, "follows_you": false, "mutual_followers": []},
      "why_relevant": "NLP researcher at NYU...",
      "bucket": "top_match",
      "summary": "Sarah builds NLP models at NYU...",
      "highlight_tweet_indices": [0, 2],
      "suggested_approach": "Reply to her thread about eval metrics.",
      "evidence_highlights": ["Just published our paper on efficient fine-tuning..."],
      "confidence": "high",
      "enrichment": null,
      "journal_note": "NYC-based academic researcher focused on NLP at NYU"
    }
  ]
}
```

Each person in `people` has the same shape as `RankedAccount` (which the frontend already consumes from `POST /api/search`), plus an added `journal_note` field.

### 3.4 `PATCH /api/workspace/{workspace_id}/layout` — Update canvas positions

**Request**:
```json
{
  "positions": [
    {"journal_id": "f7e8d9c0b1a2", "canvas_x": 300.0, "canvas_y": 250.0},
    {"journal_id": "c3d4e5f6a7b8", "canvas_x": 650.0, "canvas_y": 180.0}
  ]
}
```

**Response**: `{"ok": true}`

Call this when the user finishes dragging a journal node. Debounce recommended.

### 3.5 `GET /api/workspaces` — List all workspaces

```json
{
  "workspaces": [
    {
      "id": "a1b2c3d4e5f6",
      "query": "AI researchers in NYC",
      "status": "ready",
      "summary": "Found 24 AI researchers across 4 groups...",
      "quality": "strong",
      "created_at": "2026-02-25T...",
      "updated_at": "2026-02-25T..."
    }
  ]
}
```

### 3.6 `DELETE /api/workspace/{workspace_id}` — Delete workspace

**Response**: `{"ok": true}` or 404.

### 3.7 Existing endpoints (unchanged)

- `POST /api/search` — Old flat search SSE stream. Still works. Frontend can keep using it or migrate.
- `POST /api/chat` — Chat with search results (not workspace-aware yet).
- `GET /api/health` — Health check.

---

## 4. Theme Colors for Journals

The backend assigns colors based on journal theme. The frontend can use these or override:

| Theme | Color | Hex |
|-------|-------|-----|
| topic | Indigo | `#6366f1` |
| role | Violet | `#8b5cf6` |
| location | Cyan | `#06b6d4` |
| approach | Amber | `#f59e0b` |
| career_stage | Emerald | `#10b981` |
| community | Pink | `#ec4899` |

Canvas bounds used by backend layout: **1000 x 800**. Journal positions are scattered organically in a loose circle with jitter.

---

## 5. TypeScript Types Needed

```typescript
// ── Workspace types ──

interface WorkspaceJournal {
  id: string;
  label: string;
  description: string;
  theme: "topic" | "role" | "location" | "approach" | "career_stage" | "community";
  color: string;              // hex color from backend
  people_count: number;
  canvas_x: number;
  canvas_y: number;
  enrichment_status?: string; // "pending" — only in GET response, not SSE
}

interface JournalOverlap {
  journal_a: string;          // journal ID
  journal_b: string;          // journal ID
  shared_count: number;
  shared_handles: string[];   // up to 5
}

interface WorkspaceData {
  workspace_id: string;
  query: string;
  status: "creating" | "ready" | "enriching";
  summary: string;
  quality: "strong" | "moderate" | "weak";
  total_people: number;
  refinement_questions: string[];
  journals: WorkspaceJournal[];
  overlaps: JournalOverlap[];
  // Only in GET response:
  intent?: { persona: string; topic: string; goal: string; specificity: number };
  created_at?: string;
  updated_at?: string;
}

interface JournalPerson extends RankedAccount {
  journal_note: string;       // Why this person is in this journal
}

interface JournalDetailResponse {
  journal_id: string;
  people: JournalPerson[];
}

interface WorkspaceListItem {
  id: string;
  query: string;
  status: string;
  summary: string;
  quality: string;
  created_at: string;
  updated_at: string;
}
```

---

## 6. Frontend Implementation Plan

### 6.1 New Routes

| Route | Purpose |
|-------|---------|
| `/w/[id]` | Workspace canvas view |
| `/w/[id]/j/[jid]` | Journal detail (or use a slide-over panel instead of a route) |

### 6.2 Data Flow

```
Landing page (/)
  User types query → hits search
  → POST /api/workspace (SSE stream)
  → Show progress UI (reuse existing progress phase)
  → On "workspace" event → navigate to /w/{workspace_id}

Workspace page (/w/{id})
  → On mount: GET /api/workspace/{id}
  → Render canvas with journal nodes at (canvas_x, canvas_y)
  → Summary + quality displayed as header/overlay
  → Overlap lines drawn between connected journals

  User clicks journal node
  → GET /api/workspace/{id}/journal/{jid}
  → Show slide-over panel or modal with people cards
  → Reuse existing ResultCard component (add journal_note display)

  User drags journal node
  → Update local position state
  → On drag end: PATCH /api/workspace/{id}/layout (debounced)
```

### 6.3 SSE Client Changes

The existing `streamSearch()` in `lib/api.ts` posts to `/api/search`. You need a parallel `streamWorkspace()` function that:

1. Posts to `/api/workspace` instead
2. Handles the same `progress`, `intent`, `queries` events
3. Adds a new `onWorkspace` callback for the final `workspace` event
4. Does NOT expect a `results` event

```typescript
interface WorkspaceStreamCallbacks {
  onProgress?: (message: string) => void;
  onIntent?: (intent: SearchIntent) => void;
  onQueries?: (queries: SearchQuery[]) => void;
  onWorkspace?: (data: WorkspaceData) => void;
  onError?: (message: string) => void;
  onDone?: () => void;
}

async function streamWorkspace(
  query: string,
  callbacks: WorkspaceStreamCallbacks,
  signal?: AbortSignal
): Promise<void>
```

### 6.4 Key UI Components to Build

**WorkspaceCanvas** — The main spatial view:
- Renders journal nodes at their (canvas_x, canvas_y) positions
- Each node: colored card/pill with label, people_count, theme indicator
- Nodes are draggable (HTML drag or pointer events)
- Draw SVG lines between journals that share people (from `overlaps`)
- Line thickness proportional to shared_count
- The existing `DotGridBackground` works as the canvas background

**JournalNode** — Individual journal on the canvas:
- Shows: label, people_count badge, theme color (left border or background tint)
- Hover: show description tooltip
- Click: open journal detail panel
- Drag: update position

**JournalDetailPanel** — Slide-over or modal when clicking a journal:
- Header: journal label + description + theme badge
- People list: reuse `ResultCard` or a compact variant
- Each person shows their `journal_note` explaining grouping
- Close button returns to canvas view

**WorkspaceHeader** — Top bar on the workspace page:
- Shows: query, summary, quality indicator, total_people count
- "Back to search" link
- Workspace URL is shareable (just `/w/{id}`)

### 6.5 Suggested Libraries

- **Dragging**: `@dnd-kit/core` or plain pointer events (HTML drag API is fine for simple cases)
- **SVG lines**: Direct `<svg>` overlay with `<line>` elements between node centers
- **No need for react-flow** unless you want pan/zoom — CSS absolute positioning + SVG lines is simpler for v1

### 6.6 State Management

Workspace state can live in a simple `useState` or `useReducer` in the workspace page:

```typescript
type WorkspacePhase = "loading" | "searching" | "ready" | "error";

interface WorkspaceState {
  phase: WorkspacePhase;
  data: WorkspaceData | null;
  journalDetail: { journalId: string; people: JournalPerson[] } | null;
  progressMessages: string[];
}
```

### 6.7 Backward Compatibility

- `/s/[id]` routes continue to work (localStorage-based, old flat search)
- The old `POST /api/search` endpoint is unchanged
- The home page (`/`) should switch to calling `POST /api/workspace` instead of `POST /api/search`
- Could add a "Convert to Workspace" button on old saved searches (would need a backend endpoint, deferred)

---

## 7. Current Frontend File Structure

```
frontend/
├── app/
│   ├── globals.css              # Tailwind v4 theme + oklch design tokens
│   ├── layout.tsx               # Root layout with DotGridBackground + FloatingAstronauts
│   ├── page.tsx                 # Home page (search entry point)
│   ├── s/[id]/page.tsx          # Old saved search page (localStorage)
│   └── preview/                 # Dev preview pages
├── components/
│   ├── search-page.tsx          # Main state machine (useReducer: landing → searching → results)
│   ├── search-box.tsx           # Search input with glow effect
│   ├── result-card.tsx          # Profile card (reusable in journal detail)
│   ├── tweet-card.tsx           # Tweet display
│   ├── filter-chips.tsx         # Active filter badges
│   ├── filter-panel.tsx         # Filter dialog
│   ├── progress-ring.tsx        # Circular progress animation
│   ├── progress-strip.tsx       # Linear progress strip
│   ├── quality-banner.tsx       # Quality indicator banner
│   ├── dot-grid-background.tsx  # Animated space dot grid (reuse as canvas bg)
│   ├── floating-astronauts.tsx  # Decorative floating astronauts
│   ├── astronaut-icon.tsx       # Astronaut SVG icon
│   └── ui/                      # shadcn components (card, badge, button, dialog, etc.)
├── lib/
│   ├── api.ts                   # SSE client (streamSearch function)
│   ├── types.ts                 # TypeScript interfaces (RankedAccount, etc.)
│   ├── search-storage.ts        # localStorage persistence for old /s/{id} flow
│   ├── filter-utils.ts          # Filter helper functions
│   ├── nanoid.ts                # ID generation
│   └── utils.ts                 # cn() utility
├── components.json              # shadcn config
├── next.config.ts
├── package.json
└── tsconfig.json
```

### Design System (globals.css)
- **Dark theme** with oklch color tokens
- Surfaces: `--color-surface` (0.16), `--color-surface-card` (0.18), `--color-surface-search` (0.19)
- Text: `--color-text-primary` (0.93), `--color-text-secondary` (0.61), `--color-text-muted` (0.49)
- Accent: `--color-twitter` (oklch 0.65 0.155 241)
- Quality: green (strong), amber (moderate), red-orange (weak)
- Border radius: 0.625rem
- Tailwind v4: CSS-based config via `@theme` in globals.css, **no tailwind.config.ts**

---

## 8. Clay.com Inspiration

The user was inspired by Clay's workbook concept:
- A spatial canvas with nodes representing different data sources/tables
- Nodes connected by arrows showing data flow
- Each node can be clicked into to see its contents (a table of people)
- The workspace gives a bird's-eye view of the research

In Ceekr's version:
- The "source" is the user's search query
- The "tables" are journals (semantic groups of people)
- Nodes on the canvas represent journals, scattered organically (not a rigid grid)
- **Connections**: Lines between journals that share people. `overlaps` tells you which journals share people and how many. Draw lines — thicker = more shared. Hovering a line could show the shared handles.

---

## 9. Future Phases (Not In Scope for v1 Frontend)

These are documented in `memory/workspace-plan-phases-2-4.md` for reference:

- **Phase 2**: Journal enrichment (fetch timelines, find similar profiles, web enrichment)
- **Phase 3**: Workspace-aware chat sidebar (LLM can create/merge/expand journals)
- **Phase 4**: Import old searches as workspaces, workspace listing with auth

An earlier UI redesign concept (intelligence brief + generative visuals) is in `memory/ui-redesign-intelligence-brief.md`. Some ideas (evidence-forward cards, visual widgets) could be repurposed for journal detail views.

---

## 10. Quick Start for Frontend Session

1. Backend is running: `python3 server.py` (port 8000)
2. Frontend: `cd frontend && npm run dev` (port 3000)
3. Test workspace creation:
   ```bash
   curl -N -X POST localhost:8000/api/workspace \
     -d '{"query":"AI researchers in NYC"}' \
     -H 'Content-Type: application/json'
   ```
4. Start by:
   - Adding workspace types to `lib/types.ts`
   - Adding `streamWorkspace()` to `lib/api.ts`
   - Creating `/w/[id]` route and WorkspaceCanvas component
   - Wiring the home page search to call workspace endpoint instead of search
