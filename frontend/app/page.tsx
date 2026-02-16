"use client";

import { useReducer, useRef, useCallback, useMemo, useState, useEffect } from "react";
import { SearchBox } from "@/components/search-box";
import { ProgressRing } from "@/components/progress-ring";
import { FilterChips } from "@/components/filter-chips";
import { FilterPanel } from "@/components/filter-panel";
import { ResultCard } from "@/components/result-card";
import { streamSearch } from "@/lib/api";
import { applyFilters } from "@/lib/filter-utils";
import { DEFAULT_FILTERS } from "@/lib/types";
import type {
  SearchQuery,
  RankedAccount,
  Filters,
} from "@/lib/types";

// ── State machine ──────────────────────────────────────────

type Phase = "landing" | "searching" | "results";

interface State {
  phase: Phase;
  query: string;
  searchedQuery: string;
  progressMessages: string[];
  queries: SearchQuery[];
  results: RankedAccount[];
  quality: "strong" | "moderate" | "weak" | null;
  refinementQuestions: string[];
  error: string | null;
  // Filters
  filters: Filters;
  filterPanelOpen: boolean;
}

type Action =
  | { type: "SET_QUERY"; query: string }
  | { type: "START_SEARCH" }
  | { type: "PROGRESS"; message: string }
  | { type: "QUERIES"; queries: SearchQuery[] }
  | {
      type: "RESULTS";
      ranked: RankedAccount[];
      quality: "strong" | "moderate" | "weak";
      refinement_questions: string[];
    }
  | { type: "ERROR"; message: string }
  | { type: "RESET" }
  | { type: "SET_FILTERS"; filters: Filters }
  | { type: "SET_FILTER_PANEL_OPEN"; open: boolean };

const initialState: State = {
  phase: "landing",
  query: "",
  searchedQuery: "",
  progressMessages: [],
  queries: [],
  results: [],
  quality: null,
  refinementQuestions: [],
  error: null,
  filters: { ...DEFAULT_FILTERS },
  filterPanelOpen: false,
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SET_QUERY":
      return { ...state, query: action.query };
    case "START_SEARCH":
      return {
        ...state,
        phase: "searching",
        searchedQuery: state.query,
        progressMessages: [],
        queries: [],
        results: [],
        quality: null,
        refinementQuestions: [],
        error: null,
      };
    case "PROGRESS":
      return {
        ...state,
        progressMessages: [...state.progressMessages, action.message],
      };
    case "QUERIES":
      return { ...state, queries: action.queries };
    case "RESULTS":
      return {
        ...state,
        phase: "results",
        results: action.ranked,
        quality: action.quality,
        refinementQuestions: action.refinement_questions,
      };
    case "ERROR":
      return {
        ...state,
        phase: state.results.length > 0 ? "results" : "landing",
        error: action.message,
      };
    case "RESET":
      return { ...initialState };
    case "SET_FILTERS":
      return { ...state, filters: action.filters };
    case "SET_FILTER_PANEL_OPEN":
      return { ...state, filterPanelOpen: action.open };
    default:
      return state;
  }
}

// ── Progress helper ───────────────────────────────────────

function getSearchProgress(state: State): number {
  if (state.phase === "results") return 100;
  const msg = state.progressMessages[state.progressMessages.length - 1] ?? "";
  if (msg.startsWith("Picking")) return 85;
  if (msg.startsWith("Getting warmer")) return 75;
  if (msg.startsWith("Separating")) return 70;
  if (msg.includes("wider net")) return 55;
  if (msg.startsWith("Pulling") || msg.startsWith("The plot")) return 50;
  if (state.queries.length > 0) return 30;
  if (msg.startsWith("Reading your mind")) return 15;
  if (state.progressMessages.length > 0) return 5;
  return 0;
}

// ── Page ───────────────────────────────────────────────────

export default function Home() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const abortRef = useRef<AbortController | null>(null);

  // Landing page typing animation
  const SUBHEADER = "Find anyone on ";
  const [titleCharIndex, setTitleCharIndex] = useState(5);
  const [subCharIndex, setSubCharIndex] = useState(SUBHEADER.length);
  const hasAnimatedRef = useRef(false);

  useEffect(() => {
    if (state.phase !== "landing") return;
    if (hasAnimatedRef.current) {
      setTitleCharIndex(5);
      setSubCharIndex(SUBHEADER.length);
      return;
    }
    hasAnimatedRef.current = true;
    setTitleCharIndex(0);
    setSubCharIndex(0);

    const timers: ReturnType<typeof setTimeout>[] = [];

    // Type "Ceekr" at 100ms per char
    for (let i = 0; i < 5; i++) {
      timers.push(setTimeout(() => setTitleCharIndex(i + 1), (i + 1) * 100));
    }

    // After title finishes (500ms) + small pause (200ms), type subheader at 40ms per char
    const subStart = 700;
    for (let i = 0; i < SUBHEADER.length; i++) {
      timers.push(setTimeout(() => setSubCharIndex(i + 1), subStart + (i + 1) * 40));
    }

    return () => timers.forEach(clearTimeout);
  }, [state.phase]);

  const filteredResults = useMemo(
    () => applyFilters(state.results, state.filters),
    [state.results, state.filters],
  );

  const doSearch = useCallback(
    (queryText: string) => {
      if (!queryText.trim()) return;

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      dispatch({ type: "SET_QUERY", query: queryText });
      dispatch({ type: "START_SEARCH" });

      streamSearch(
        queryText,
        {
          onProgress: (message) =>
            dispatch({ type: "PROGRESS", message }),
          onQueries: (queries) =>
            dispatch({ type: "QUERIES", queries }),
          onResults: (results) => {
            dispatch({
              type: "RESULTS",
              ranked: results.ranked,
              quality: results.quality,
              refinement_questions: results.refinement_questions,
            });
            dispatch({ type: "SET_QUERY", query: "" });
          },
          onError: (message) => {
            dispatch({ type: "ERROR", message });
          },
        },
        controller.signal,
      ).catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        dispatch({ type: "ERROR", message: String(err.message || err) });
      });
    },
    [],
  );

  const handleSubmit = useCallback(() => {
    if (!state.query.trim()) return;
    doSearch(state.query);
  }, [state.query, doSearch]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    dispatch({ type: "SET_QUERY", query: "" });
    dispatch({ type: "RESET" });
  }, []);

  const isSearching = state.phase === "searching";
  const showCompactHeader = state.phase !== "landing";

  return (
    <div className="min-h-screen pb-16">
      {/* Header + Search */}
      {showCompactHeader ? (
        <div className="flex flex-col items-center pt-10 pb-8">
          <div
            className="mb-6 flex items-center gap-4 sm:gap-5 cursor-pointer hover:opacity-70 transition-opacity"
            onClick={() => dispatch({ type: "RESET" })}
          >
            <h1 className="font-mono-display text-[3rem] sm:text-[4.5rem] font-bold tracking-tight text-text-primary leading-none">
              Ceekr
            </h1>
          </div>
          <div className="w-full max-w-[640px]">
            <SearchBox
              value={state.query}
              onChange={(q) => dispatch({ type: "SET_QUERY", query: q })}
              onSubmit={handleSubmit}
              onStop={handleStop}
              placeholder="Describe who you're looking for..."
              disabled={isSearching}
              searching={isSearching}
            />
            {isSearching && state.progressMessages.length > 0 && (
              <div className="mt-4 flex items-center justify-center gap-2.5">
                <p className="text-sm text-text-muted animate-pulse">
                  {state.progressMessages[state.progressMessages.length - 1]}
                </p>
                <ProgressRing percentage={getSearchProgress(state)} size={20} />
              </div>
            )}
            {state.phase === "results" && state.searchedQuery && (
              <p className="mt-4 text-center text-sm text-text-muted">
                Showing {filteredResults.length} result{filteredResults.length !== 1 ? "s" : ""} for &ldquo;{state.searchedQuery}&rdquo;
              </p>
            )}
          </div>
        </div>
      ) : (
        <div className="flex min-h-[80vh] flex-col items-center justify-center text-center">
          <div className="mb-4">
            <h1 className="font-mono-display text-[3rem] sm:text-[4.5rem] font-bold tracking-tight text-text-primary leading-none">
              {"Ceekr".slice(0, titleCharIndex)}
              {titleCharIndex < 5 && (
                <span className="animate-cursor ml-0.5 text-text-muted">|</span>
              )}
            </h1>
          </div>

          <p className="mb-10 text-base sm:text-lg text-text-secondary tracking-wide">
            {SUBHEADER.slice(0, subCharIndex)}
            {subCharIndex > 0 && subCharIndex < SUBHEADER.length && (
              <span className="animate-cursor ml-0.5 text-text-muted">|</span>
            )}
            {subCharIndex >= SUBHEADER.length && (
              <svg viewBox="0 0 24 24" className="inline h-4 w-4 sm:h-5 sm:w-5 fill-text-secondary align-middle -mt-0.5" aria-label="X">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
              </svg>
            )}
            {subCharIndex === 0 && <span className="opacity-0">.</span>}
          </p>

          <div className="w-full max-w-[640px]">
            <SearchBox
              value={state.query}
              onChange={(q) => dispatch({ type: "SET_QUERY", query: q })}
              onSubmit={handleSubmit}
              onStop={handleStop}
              placeholder="Describe who you're looking for..."
              disabled={isSearching}
              searching={isSearching}
            />
            {isSearching && state.progressMessages.length > 0 && (
              <div className="mt-4 flex items-center justify-center gap-2.5">
                <p className="text-sm text-text-muted animate-pulse">
                  {state.progressMessages[state.progressMessages.length - 1]}
                </p>
                <ProgressRing percentage={getSearchProgress(state)} size={20} />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error */}
      {state.error && (
        <p className="mb-4 text-sm text-red-400">
          {state.error}
        </p>
      )}

      {/* Filter chips — hidden on landing */}
      {state.phase === "results" && (
        <div className="mb-6">
          <FilterChips
            filters={state.filters}
            onFiltersOpen={() =>
              dispatch({ type: "SET_FILTER_PANEL_OPEN", open: true })
            }
          />
        </div>
      )}

      {/* Filter panel modal */}
      <FilterPanel
        open={state.filterPanelOpen}
        onOpenChange={(open) =>
          dispatch({ type: "SET_FILTER_PANEL_OPEN", open })
        }
        filters={state.filters}
        onFiltersChange={(f) => dispatch({ type: "SET_FILTERS", filters: f })}
        results={state.results}
      />


      {/* Results */}
      {state.phase === "results" && (
        <>
          <div className="space-y-4">
            {filteredResults.map((r) => (
              <ResultCard key={r.user_id} account={r} />
            ))}
          </div>

          {filteredResults.length === 0 && state.results.length > 0 && (
            <div className="mb-4 rounded-xl border border-border-subtle bg-surface-card px-4 py-6 text-center text-[0.88rem] text-text-muted">
              No results match your current filters. Try adjusting them.
            </div>
          )}
        </>
      )}
    </div>
  );
}
