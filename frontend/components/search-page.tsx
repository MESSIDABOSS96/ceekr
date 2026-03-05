"use client";

import { useReducer, useRef, useCallback, useMemo, useState, useEffect } from "react";
import { SearchBox } from "@/components/search-box";
import { ThinkingPanel } from "@/components/thinking-panel";
import { FilterChips } from "@/components/filter-chips";
import { FilterPanel } from "@/components/filter-panel";
import { ResultCard } from "@/components/result-card";
import { ClarificationPanel } from "@/components/clarification-panel";
import { checkIntent, streamSearch, streamWorkspace } from "@/lib/api";
import { applyFilters } from "@/lib/filter-utils";
import { DEFAULT_FILTERS } from "@/lib/types";
import type {
  ActivityStep,
  ActivityStepType,
  SearchQuery,
  RankedAccount,
  Filters,
  WorkspaceData,
  ClarificationQuestion,
} from "@/lib/types";

// ── Props ─────────────────────────────────────────────────

export interface InitialSearchState {
  query: string;
  results: RankedAccount[];
  quality: "strong" | "moderate" | "weak";
  refinementQuestions: string[];
  queries: SearchQuery[];
}

export interface SearchCompletePayload {
  query: string;
  results: RankedAccount[];
  quality: "strong" | "moderate" | "weak";
  refinementQuestions: string[];
  queries: SearchQuery[];
}

interface SearchPageProps {
  initialState?: InitialSearchState;
  onSearchComplete?: (payload: SearchCompletePayload) => void;
  onWorkspaceCreated?: (data: WorkspaceData) => void;
  onReset?: () => void;
}

// ── State machine ──────────────────────────────────────────

type Phase = "landing" | "checking" | "clarifying" | "searching" | "results";

interface State {
  phase: Phase;
  query: string;
  searchedQuery: string;
  activitySteps: ActivityStep[];
  queries: SearchQuery[];
  results: RankedAccount[];
  quality: "strong" | "moderate" | "weak" | null;
  refinementQuestions: string[];
  error: string | null;
  filters: Filters;
  filterPanelOpen: boolean;
  clarificationQuestions: ClarificationQuestion[];
}

type Action =
  | { type: "SET_QUERY"; query: string }
  | { type: "INTENT_CHECK_START" }
  | { type: "INTENT_RECEIVED"; questions: ClarificationQuestion[] }
  | { type: "SUBMIT_CLARIFICATION"; enrichedQuery: string }
  | { type: "START_SEARCH" }
  | { type: "PROGRESS"; step: ActivityStep }
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

const defaultState: State = {
  phase: "landing",
  query: "",
  searchedQuery: "",
  activitySteps: [],
  queries: [],
  results: [],
  quality: null,
  refinementQuestions: [],
  error: null,
  filters: { ...DEFAULT_FILTERS },
  filterPanelOpen: false,
  clarificationQuestions: [],
};

function buildInitialState(initial?: InitialSearchState): State {
  if (!initial) return { ...defaultState };
  return {
    ...defaultState,
    phase: "results",
    searchedQuery: initial.query,
    queries: initial.queries,
    results: initial.results,
    quality: initial.quality,
    refinementQuestions: initial.refinementQuestions,
  };
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SET_QUERY":
      return { ...state, query: action.query };
    case "INTENT_CHECK_START":
      return {
        ...state,
        phase: "checking",
        searchedQuery: state.query,
        error: null,
        clarificationQuestions: [],
      };
    case "INTENT_RECEIVED":
      return {
        ...state,
        phase: "clarifying",
        clarificationQuestions: action.questions,
      };
    case "SUBMIT_CLARIFICATION":
      return {
        ...state,
        phase: "searching",
        searchedQuery: action.enrichedQuery,
        activitySteps: [],
        queries: [],
        results: [],
        quality: null,
        refinementQuestions: [],
        clarificationQuestions: [],
        error: null,
      };
    case "START_SEARCH":
      return {
        ...state,
        phase: "searching",
        searchedQuery: state.query,
        activitySteps: [],
        queries: [],
        results: [],
        quality: null,
        refinementQuestions: [],
        clarificationQuestions: [],
        error: null,
      };
    case "PROGRESS":
      return {
        ...state,
        activitySteps: [...state.activitySteps, action.step],
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
      return { ...defaultState };
    case "SET_FILTERS":
      return { ...state, filters: action.filters };
    case "SET_FILTER_PANEL_OPEN":
      return { ...state, filterPanelOpen: action.open };
    default:
      return state;
  }
}

// ── Progress helper ───────────────────────────────────────

const STEP_PROGRESS: Record<ActivityStepType, number> = {
  init: 5,
  intent_analysis: 15,
  query_generation: 25,
  searching: 45,
  filtering: 65,
  filtering_done: 75,
  ranking: 85,
  grouping: 92,
  fallback: 55,
  generic: 0,
};

function getSearchProgress(state: State): number {
  if (state.phase === "results") return 100;
  if (state.activitySteps.length === 0) return 0;
  // Take the max progress across all steps seen (never go backward)
  let maxProgress = 0;
  for (const s of state.activitySteps) {
    const p = STEP_PROGRESS[s.step] ?? 0;
    if (p > maxProgress) maxProgress = p;
  }
  return maxProgress;
}

// ── Subtitle typewriter ───────────────────────────────────

const SUBTITLE_EXAMPLES = [
  "ex-Stripe engineers",
  "solo devs shipping in public",
  "urban farming advocates",
  "infra nerds who left FAANG",
  "indie documentary filmmakers",
  "AI researchers at non-OpenAI labs",
];

const TYPE_SPEED = 45;
const DELETE_SPEED = 25;
const PAUSE_AFTER_TYPE = 2500;
const PAUSE_AFTER_DELETE = 400;

// ── Component ─────────────────────────────────────────────

export function SearchPage({ initialState, onSearchComplete, onWorkspaceCreated, onReset }: SearchPageProps) {
  const [state, dispatch] = useReducer(reducer, initialState, buildInitialState);
  const abortRef = useRef<AbortController | null>(null);
  const queriesRef = useRef<SearchQuery[]>([]);

  // Landing page typing animation
  const SUBHEADER_PREFIX = "Find ";
  const [titleCharIndex, setTitleCharIndex] = useState(5);
  const [subCharIndex, setSubCharIndex] = useState(SUBHEADER_PREFIX.length);
  const hasAnimatedRef = useRef(false);

  // Subtitle typewriter state
  const [rotatingText, setRotatingText] = useState("");
  const rotatingIndexRef = useRef(0);
  const rotatingPhaseRef = useRef<"typing" | "pausing" | "deleting" | "gap">("typing");
  const rotatingCharRef = useRef(0);
  const introComplete = subCharIndex >= SUBHEADER_PREFIX.length;

  // Static "anyone" typewriter when leaving landing
  const STATIC_TEXT = "anyone";
  const [staticSubtitle, setStaticSubtitle] = useState("");
  const isLanding = state.phase === "landing";

  useEffect(() => {
    if (isLanding) {
      setStaticSubtitle("");
      return;
    }
    let i = 0;
    setStaticSubtitle("");
    const timer = setInterval(() => {
      i++;
      setStaticSubtitle(STATIC_TEXT.slice(0, i));
      if (i >= STATIC_TEXT.length) clearInterval(timer);
    }, TYPE_SPEED);
    return () => clearInterval(timer);
  }, [isLanding]);

  useEffect(() => {
    if (state.phase !== "landing") return;
    if (hasAnimatedRef.current) {
      setTitleCharIndex(5);
      setSubCharIndex(SUBHEADER_PREFIX.length);
      return;
    }
    hasAnimatedRef.current = true;
    setTitleCharIndex(0);
    setSubCharIndex(0);

    const timers: ReturnType<typeof setTimeout>[] = [];

    for (let i = 0; i < 5; i++) {
      timers.push(setTimeout(() => setTitleCharIndex(i + 1), (i + 1) * 100));
    }

    const subStart = 700;
    for (let i = 0; i < SUBHEADER_PREFIX.length; i++) {
      timers.push(setTimeout(() => setSubCharIndex(i + 1), subStart + (i + 1) * 40));
    }

    return () => timers.forEach(clearTimeout);
  }, [state.phase]);

  // Rotating typewriter in subtitle
  useEffect(() => {
    if (!introComplete || state.phase !== "landing") {
      setRotatingText("");
      return;
    }

    rotatingPhaseRef.current = "typing";
    rotatingCharRef.current = 0;
    rotatingIndexRef.current = 0;
    setRotatingText("");

    let timer: ReturnType<typeof setTimeout>;

    function tick() {
      const example = SUBTITLE_EXAMPLES[rotatingIndexRef.current];
      const phase = rotatingPhaseRef.current;

      if (phase === "typing") {
        rotatingCharRef.current++;
        setRotatingText(example.slice(0, rotatingCharRef.current));
        if (rotatingCharRef.current >= example.length) {
          rotatingPhaseRef.current = "pausing";
          timer = setTimeout(tick, PAUSE_AFTER_TYPE);
        } else {
          timer = setTimeout(tick, TYPE_SPEED);
        }
      } else if (phase === "pausing") {
        rotatingPhaseRef.current = "deleting";
        timer = setTimeout(tick, DELETE_SPEED);
      } else if (phase === "deleting") {
        rotatingCharRef.current--;
        setRotatingText(example.slice(0, rotatingCharRef.current));
        if (rotatingCharRef.current <= 0) {
          rotatingPhaseRef.current = "gap";
          timer = setTimeout(tick, PAUSE_AFTER_DELETE);
        } else {
          timer = setTimeout(tick, DELETE_SPEED);
        }
      } else if (phase === "gap") {
        rotatingIndexRef.current =
          (rotatingIndexRef.current + 1) % SUBTITLE_EXAMPLES.length;
        rotatingCharRef.current = 0;
        rotatingPhaseRef.current = "typing";
        timer = setTimeout(tick, TYPE_SPEED);
      }
    }

    timer = setTimeout(tick, 300);
    return () => clearTimeout(timer);
  }, [introComplete, state.phase]);

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

      dispatch({ type: "START_SEARCH" });

      const progressCb = (data: Record<string, unknown>) => {
        const step: ActivityStep = {
          message: (data.message as string) ?? "",
          step: (data.step as ActivityStepType) ?? "generic",
          counts: data.counts as Record<string, number> | undefined,
          timestamp: Date.now(),
        };
        dispatch({ type: "PROGRESS", step });
      };
      const queriesCb = (queries: SearchQuery[]) => {
        queriesRef.current = queries;
        dispatch({ type: "QUERIES", queries });
      };
      const errorCb = (message: string) => dispatch({ type: "ERROR", message });
      const catchCb = (err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        dispatch({ type: "ERROR", message: String((err as Error).message || err) });
      };

      if (onWorkspaceCreated) {
        streamWorkspace(
          queryText,
          {
            onProgress: progressCb,
            onQueries: queriesCb,
            onWorkspace: (data) => {
              onWorkspaceCreated(data);
            },
            onError: errorCb,
          },
          controller.signal,
        ).catch(catchCb);
      } else {
        streamSearch(
          queryText,
          {
            onProgress: progressCb,
            onQueries: queriesCb,
            onResults: (results) => {
              dispatch({
                type: "RESULTS",
                ranked: results.ranked,
                quality: results.quality,
                refinement_questions: results.refinement_questions,
              });
              dispatch({ type: "SET_QUERY", query: "" });
              onSearchComplete?.({
                query: queryText,
                results: results.ranked,
                quality: results.quality,
                refinementQuestions: results.refinement_questions,
                queries: queriesRef.current,
              });
            },
            onError: errorCb,
          },
          controller.signal,
        ).catch(catchCb);
      }
    },
    [onSearchComplete, onWorkspaceCreated],
  );

  const handleSubmit = useCallback(async () => {
    if (!state.query.trim()) return;

    dispatch({ type: "INTENT_CHECK_START" });

    try {
      const result = await checkIntent(state.query);

      if (!result.needs_clarification) {
        // Specific enough — skip clarification, go straight to search
        doSearch(state.query);
      } else {
        // Vague — show clarification panel
        dispatch({
          type: "INTENT_RECEIVED",
          questions: result.clarification_questions,
        });
      }
    } catch {
      // On error, fall through to search directly
      doSearch(state.query);
    }
  }, [state.query, doSearch]);

  const handleClarificationSubmit = useCallback(
    (enrichedQuery: string) => {
      dispatch({ type: "SUBMIT_CLARIFICATION", enrichedQuery });
      doSearch(enrichedQuery);
    },
    [doSearch],
  );

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    dispatch({ type: "SET_QUERY", query: "" });
    dispatch({ type: "RESET" });
  }, []);

  const handleReset = useCallback(() => {
    dispatch({ type: "RESET" });
    onReset?.();
  }, [onReset]);

  const isSearching = state.phase === "searching";
  const isChecking = state.phase === "checking";
  const isClarifying = state.phase === "clarifying";
  const showCompactHeader = state.phase === "results";

  return (
    <div className="min-h-screen pb-16">
      {/* Header + Search */}
      {showCompactHeader ? (
        <div className="flex flex-col items-center pt-10 pb-8">
          <div
            className="mb-6 flex items-center gap-4 sm:gap-5 cursor-pointer hover:opacity-70 transition-opacity"
            onClick={handleReset}
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
              disabled={isSearching || isChecking}
              searching={isSearching}
              loading={isChecking}
            />
            {(isSearching || state.phase === "results") && (
              <ThinkingPanel
                steps={state.activitySteps}
                progress={getSearchProgress(state)}
                isComplete={state.phase === "results"}
              />
            )}
            {state.phase === "results" && state.searchedQuery && (
              <p className="mt-4 text-center text-sm text-text-muted">
                Showing {filteredResults.length} result{filteredResults.length !== 1 ? "s" : ""} for &ldquo;{state.searchedQuery}&rdquo;
              </p>
            )}
          </div>
        </div>
      ) : (
        <div className="flex min-h-[80vh] flex-col items-center text-center">
          <div className="my-auto flex flex-col items-center w-full">
          <div className="mb-4">
            <h1 className="font-mono-display text-[3rem] sm:text-[4.5rem] font-bold tracking-tight text-text-primary leading-none">
              {"Ceekr".slice(0, titleCharIndex)}
              {titleCharIndex < 5 && (
                <span className="animate-cursor ml-0.5 text-text-muted">|</span>
              )}
            </h1>
          </div>

          <p className="mb-10 text-base sm:text-lg text-text-secondary tracking-wide">
            {SUBHEADER_PREFIX.slice(0, subCharIndex)}
            {subCharIndex > 0 && !introComplete && (
              <span className="animate-cursor ml-0.5 text-text-muted">|</span>
            )}
            {introComplete && (
              <>
                {state.phase === "landing" ? (
                  <>
                    <span className="text-text-primary">{rotatingText}</span>
                    <span className="animate-cursor text-text-muted">|</span>
                  </>
                ) : (
                  <>
                    <span className="text-text-primary">{staticSubtitle}</span>
                    {staticSubtitle.length < STATIC_TEXT.length && (
                      <span className="animate-cursor text-text-muted">|</span>
                    )}
                  </>
                )}
                {" on "}
                <svg viewBox="0 0 24 24" className="inline h-4 w-4 sm:h-5 sm:w-5 fill-text-secondary align-middle -mt-0.5" aria-label="X">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                </svg>
              </>
            )}
            {subCharIndex === 0 && <span className="opacity-0">.</span>}
          </p>

          <div className="w-full max-w-[640px]">
            <SearchBox
              value={state.query}
              onChange={(q) => dispatch({ type: "SET_QUERY", query: q })}
              onSubmit={handleSubmit}
              onStop={handleStop}
              disabled={isSearching || isChecking}
              searching={isSearching}
              loading={isChecking}
            />

            {/* Clarification panel */}
            {isClarifying && state.clarificationQuestions.length > 0 && (
              <ClarificationPanel
                questions={state.clarificationQuestions}
                originalQuery={state.searchedQuery}
                onSubmit={handleClarificationSubmit}
              />
            )}

            {isSearching && (
              <ThinkingPanel
                steps={state.activitySteps}
                progress={getSearchProgress(state)}
                isComplete={false}
              />
            )}

          </div>
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
          <div
            className="grid gap-4 justify-center"
            style={{ gridTemplateColumns: "repeat(auto-fill, minmax(480px, 504px))" }}
          >
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
