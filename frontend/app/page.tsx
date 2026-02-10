"use client";

import { useReducer, useRef, useCallback, useMemo } from "react";
import { SearchBox } from "@/components/search-box";
import { FilterChips } from "@/components/filter-chips";
import { FilterPanel } from "@/components/filter-panel";
import { ProgressStrip } from "@/components/progress-strip";
import { ClarificationCard } from "@/components/clarification-card";
import { ResultCard } from "@/components/result-card";
import { ChatBox } from "@/components/chat-box";
import { streamSearch, sendChatMessage } from "@/lib/api";
import { applyFilters } from "@/lib/filter-utils";
import { DEFAULT_FILTERS } from "@/lib/types";
import type {
  ClarificationQuestion,
  SearchQuery,
  RankedAccount,
  Filters,
  ChatMessage,
} from "@/lib/types";

// ── State machine ──────────────────────────────────────────

type Phase = "landing" | "searching" | "clarification" | "results";

interface State {
  phase: Phase;
  query: string;
  progressMessages: string[];
  queries: SearchQuery[];
  clarificationQuestions: ClarificationQuestion[];
  results: RankedAccount[];
  quality: "strong" | "moderate" | "weak" | null;
  refinementQuestions: string[];
  error: string | null;
  // Filters
  filters: Filters;
  filterPanelOpen: boolean;
  // Chat
  chatMessages: ChatMessage[];
  chatLoading: boolean;
  // Find More
  loadingMore: boolean;
}

type Action =
  | { type: "SET_QUERY"; query: string }
  | { type: "START_SEARCH" }
  | { type: "PROGRESS"; message: string }
  | {
      type: "INTENT";
      is_clear: boolean;
      questions: ClarificationQuestion[];
    }
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
  | { type: "SET_FILTER_PANEL_OPEN"; open: boolean }
  | { type: "ADD_CHAT_MESSAGE"; message: ChatMessage }
  | { type: "SET_CHAT_LOADING"; loading: boolean }
  | { type: "REMOVE_HANDLES"; handles: string[] }
  | { type: "START_LOAD_MORE" }
  | {
      type: "APPEND_RESULTS";
      ranked: RankedAccount[];
      quality: "strong" | "moderate" | "weak";
    }
  | { type: "STOP_LOAD_MORE" };

let chatIdCounter = 0;
function nextChatId(): string {
  return `msg-${++chatIdCounter}`;
}

const initialState: State = {
  phase: "landing",
  query: "",
  progressMessages: [],
  queries: [],
  clarificationQuestions: [],
  results: [],
  quality: null,
  refinementQuestions: [],
  error: null,
  filters: { ...DEFAULT_FILTERS },
  filterPanelOpen: false,
  chatMessages: [],
  chatLoading: false,
  loadingMore: false,
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SET_QUERY":
      return { ...state, query: action.query };
    case "START_SEARCH":
      return {
        ...state,
        phase: "searching",
        progressMessages: [],
        queries: [],
        results: [],
        quality: null,
        refinementQuestions: [],
        error: null,
        // Don't reset chatMessages or filters
      };
    case "PROGRESS":
      return {
        ...state,
        progressMessages: [...state.progressMessages, action.message],
      };
    case "INTENT":
      if (!action.is_clear) {
        return {
          ...state,
          phase: "clarification",
          clarificationQuestions: action.questions,
        };
      }
      return state;
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
    case "ADD_CHAT_MESSAGE":
      return {
        ...state,
        chatMessages: [...state.chatMessages, action.message],
      };
    case "SET_CHAT_LOADING":
      return { ...state, chatLoading: action.loading };
    case "REMOVE_HANDLES":
      return {
        ...state,
        results: state.results.filter(
          (r) =>
            !action.handles.some(
              (h) => h.toLowerCase() === r.handle.toLowerCase()
            )
        ),
      };
    case "START_LOAD_MORE":
      return { ...state, loadingMore: true };
    case "APPEND_RESULTS": {
      // Deduplicate by user_id, keeping existing results first
      const existingIds = new Set(state.results.map((r) => r.user_id));
      const newResults = action.ranked.filter(
        (r) => !existingIds.has(r.user_id)
      );
      const combined = [...state.results, ...newResults];
      // Re-sort by score
      combined.sort((a, b) => b.relevance_score - a.relevance_score);
      return {
        ...state,
        loadingMore: false,
        results: combined,
        quality: action.quality === "strong" || state.quality === "strong"
          ? "strong"
          : action.quality === "moderate" || state.quality === "moderate"
            ? "moderate"
            : "weak",
      };
    }
    case "STOP_LOAD_MORE":
      return { ...state, loadingMore: false };
    default:
      return state;
  }
}

// ── Page ───────────────────────────────────────────────────

export default function Home() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const abortRef = useRef<AbortController | null>(null);

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
          onIntent: (intent) =>
            dispatch({
              type: "INTENT",
              is_clear: intent.is_clear,
              questions: intent.questions,
            }),
          onQueries: (queries) =>
            dispatch({ type: "QUERIES", queries }),
          onResults: (results) => {
            dispatch({
              type: "RESULTS",
              ranked: results.ranked,
              quality: results.quality,
              refinement_questions: results.refinement_questions,
            });
            // Build summary message with quality info
            const count = results.ranked.length;
            const q = results.quality;
            let summary = `Found ${count} account${count !== 1 ? "s" : ""}`;
            if (q === "weak") {
              summary += " — relevance is low.";
            } else if (q === "moderate") {
              summary += " — relevance is moderate.";
            } else {
              summary += ".";
            }
            summary +=
              " You can ask me to refine results, adjust filters, or search for something different.";
            dispatch({
              type: "ADD_CHAT_MESSAGE",
              message: {
                id: nextChatId(),
                role: "assistant",
                content: summary,
              },
            });
            // Add refinement suggestions as a separate message for weak results
            if (
              q === "weak" &&
              results.refinement_questions.length > 0
            ) {
              const suggestions = results.refinement_questions
                .map((rq) => `- ${rq}`)
                .join("\n");
              dispatch({
                type: "ADD_CHAT_MESSAGE",
                message: {
                  id: nextChatId(),
                  role: "assistant",
                  content: `Results could be better. Some suggestions:\n${suggestions}`,
                },
              });
            }
          },
          onError: (message) => dispatch({ type: "ERROR", message }),
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
    // Add user message to chat
    dispatch({
      type: "ADD_CHAT_MESSAGE",
      message: { id: nextChatId(), role: "user", content: state.query },
    });
    doSearch(state.query);
  }, [state.query, doSearch]);

  const handleClarificationSubmit = useCallback(() => {
    doSearch(state.query);
  }, [state.query, doSearch]);

  const doFindMore = useCallback(() => {
    if (!state.query.trim() || state.loadingMore) return;

    dispatch({ type: "START_LOAD_MORE" });

    const excludeIds = state.results.map((r) => r.user_id);

    streamSearch(
      state.query,
      {
        onResults: (results) => {
          dispatch({
            type: "APPEND_RESULTS",
            ranked: results.ranked,
            quality: results.quality,
          });
        },
        onError: (message) => {
          dispatch({ type: "STOP_LOAD_MORE" });
          dispatch({ type: "ERROR", message });
        },
      },
      undefined,
      excludeIds,
    ).catch(() => {
      dispatch({ type: "STOP_LOAD_MORE" });
    });
  }, [state.query, state.results, state.loadingMore]);

  const handleChipClick = useCallback(
    (chip: string) => {
      const newQuery = state.query
        ? `${state.query}, ${chip.toLowerCase()}`
        : chip;
      dispatch({ type: "SET_QUERY", query: newQuery });
    },
    [state.query],
  );

  const buildResultsSummary = useCallback((): string => {
    if (filteredResults.length === 0) return "No results currently shown.";
    const top = filteredResults
      .slice(0, 5)
      .map((r) => `@${r.handle} (${r.name}, score ${r.relevance_score})`)
      .join(", ");
    return `${filteredResults.length} accounts shown. Top: ${top}`;
  }, [filteredResults]);

  const handleChatSend = useCallback(
    async (text: string) => {
      const userMsg: ChatMessage = {
        id: nextChatId(),
        role: "user",
        content: text,
      };
      dispatch({ type: "ADD_CHAT_MESSAGE", message: userMsg });
      dispatch({ type: "SET_CHAT_LOADING", loading: true });

      try {
        // Build messages for API (exclude IDs)
        const apiMessages = [...state.chatMessages, userMsg].map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const response = await sendChatMessage({
          messages: apiMessages,
          filters: state.filters,
          current_results_summary: buildResultsSummary(),
        });

        // Add agent response
        dispatch({
          type: "ADD_CHAT_MESSAGE",
          message: {
            id: nextChatId(),
            role: "assistant",
            content: response.response,
          },
        });

        // Handle action
        if (response.action) {
          switch (response.action.type) {
            case "search":
              if (response.action.query) {
                dispatch({ type: "SET_QUERY", query: response.action.query });
                doSearch(response.action.query);
              }
              break;
            case "filter":
              if (response.action.filters) {
                dispatch({
                  type: "SET_FILTERS",
                  filters: { ...state.filters, ...response.action.filters },
                });
              }
              break;
            case "remove_profiles":
              if (response.action.removeHandles) {
                dispatch({
                  type: "REMOVE_HANDLES",
                  handles: response.action.removeHandles,
                });
              }
              break;
          }
        }
      } catch (err) {
        dispatch({
          type: "ADD_CHAT_MESSAGE",
          message: {
            id: nextChatId(),
            role: "assistant",
            content: "Sorry, something went wrong. Please try again.",
          },
        });
      } finally {
        dispatch({ type: "SET_CHAT_LOADING", loading: false });
      }
    },
    [state.chatMessages, state.filters, buildResultsSummary, doSearch],
  );

  const isSearching = state.phase === "searching";
  const showCompactHeader = state.phase !== "landing";
  const hasChatMessages = state.chatMessages.length > 0;

  return (
    <div className="min-h-screen pb-16">
      {/* Header */}
      {showCompactHeader ? (
        <div className="pt-10 pb-10 text-center">
          <h1 className="text-xl font-bold tracking-tight text-text-primary">
            Twitter Account Finder
          </h1>
        </div>
      ) : (
        <div className="flex min-h-[40vh] flex-col items-center justify-center pt-[14vh] text-center">
          <h1 className="mb-2 text-4xl font-bold tracking-tight text-text-primary">
            Twitter Account Finder
          </h1>
          <p className="mb-8 text-base text-text-secondary">
            Describe who you want to find. We&apos;ll search Twitter and rank
            the best matches.
          </p>
        </div>
      )}

      {/* Search box OR Chat box */}
      <div className="mb-4">
        {hasChatMessages ? (
          <ChatBox
            messages={state.chatMessages}
            loading={state.chatLoading || isSearching}
            onSend={handleChatSend}
            disabled={isSearching}
            progressMessages={state.progressMessages}
            queries={state.queries}
            isSearching={isSearching}
          />
        ) : (
          <SearchBox
            value={state.query}
            onChange={(q) => dispatch({ type: "SET_QUERY", query: q })}
            onSubmit={handleSubmit}
            placeholder="Describe who you're looking for... e.g. 'Founders who have discussed customer discovery challenges, I'm building an AI interview tool'"
            disabled={isSearching}
          />
        )}
      </div>

      {/* Filter chips — show on all phases */}
      <div className="mb-6">
        <FilterChips
          onChipClick={handleChipClick}
          filters={state.filters}
          onFiltersOpen={() =>
            dispatch({ type: "SET_FILTER_PANEL_OPEN", open: true })
          }
          showSuggestionChips={state.phase === "landing"}
        />
      </div>

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

      {/* Error */}
      {state.error && (
        <div className="mb-4 rounded-xl border border-quality-weak/20 bg-quality-weak/[0.08] px-4 py-3 text-[0.88rem] text-quality-weak">
          {state.error}
        </div>
      )}

      {/* Progress strip — only when chat is not active (first search uses external strip) */}
      {!hasChatMessages &&
        (isSearching || state.progressMessages.length > 0) &&
        state.phase !== "results" && (
          <ProgressStrip
            messages={state.progressMessages}
            queries={state.queries}
            isSearching={isSearching}
          />
        )}

      {/* Clarification */}
      {state.phase === "clarification" && (
        <>
          <ClarificationCard questions={state.clarificationQuestions} />
          <p className="mb-2 text-[0.85rem] text-text-muted">
            Update your search above with more details, then press Enter.
          </p>
          <button
            onClick={handleClarificationSubmit}
            className="rounded-full bg-twitter px-5 py-2 text-sm font-medium text-white transition-opacity hover:opacity-80"
          >
            Search again
          </button>
        </>
      )}

      {/* Results */}
      {state.phase === "results" && (
        <>
          {filteredResults.map((r) => (
            <ResultCard key={r.user_id} account={r} />
          ))}

          {filteredResults.length === 0 && state.results.length > 0 && (
            <div className="mb-4 rounded-xl border border-border-subtle bg-surface-card px-4 py-6 text-center text-[0.88rem] text-text-muted">
              No results match your current filters. Try adjusting them.
            </div>
          )}

          {/* Find More */}
          {filteredResults.length > 0 && (
            <div className="mt-2 mb-4 text-center">
              <button
                onClick={doFindMore}
                disabled={state.loadingMore}
                className="rounded-full border border-border-subtle bg-surface-card px-6 py-2.5 text-sm font-medium text-text-secondary transition-colors hover:bg-surface-card/80 hover:text-text-primary disabled:opacity-50"
              >
                {state.loadingMore ? (
                  <span className="flex items-center gap-2">
                    <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-text-muted border-t-transparent" />
                    Finding more accounts...
                  </span>
                ) : (
                  "Find More"
                )}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
