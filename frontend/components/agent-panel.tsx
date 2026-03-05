"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { X, ArrowUp, MessageCircle } from "lucide-react";
import type { ChatMessage, ChatAction, WorkspaceJournal } from "@/lib/types";
import { streamChat, fetchChatHistory } from "@/lib/api";

interface AgentPanelProps {
  workspaceId: string;
  workspaceQuery: string;
  workspaceSummary: string;
  journals: WorkspaceJournal[];
  totalPeople: number;
  activeJournalId: string | null;
  isOpen: boolean;
  onToggle: () => void;
  onAction: (action: ChatAction) => void;
}

/** Clean up the raw workspace query into a readable initial user message. */
function cleanQueryForDisplay(raw: string): string {
  // If it contains pipe separators (from clarification answers), take only the first part
  let text = raw.includes("|") ? raw.split("|")[0] : raw;
  text = text.trim();
  if (text.length > 100) {
    text = text.slice(0, 97) + "...";
  }
  return text;
}

/** Build a synthetic assistant greeting from workspace data. */
function buildGreeting(
  totalPeople: number,
  journals: WorkspaceJournal[],
): string {
  const groupCount = journals.length;
  const lines = journals.map((j) => `• **${j.label}** (${j.people_count})`);
  return `I found ${totalPeople} people organized into ${groupCount} groups:\n\n${lines.join("\n")}\n\nWhat would you like to explore?`;
}

export function AgentPanel({
  workspaceId,
  workspaceQuery,
  workspaceSummary,
  journals,
  totalPeople,
  activeJournalId,
  isOpen,
  onToggle,
  onAction,
}: AgentPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Build synthetic initial messages from workspace data (not persisted)
  const syntheticMessages = useMemo<ChatMessage[]>(() => {
    if (!workspaceQuery) return [];
    return [
      {
        id: "synthetic-user",
        role: "user" as const,
        content: cleanQueryForDisplay(workspaceQuery),
        created_at: new Date().toISOString(),
      },
      {
        id: "synthetic-assistant",
        role: "assistant" as const,
        content: buildGreeting(totalPeople, journals),
        created_at: new Date().toISOString(),
      },
    ];
  }, [workspaceQuery, totalPeople, journals]);

  // All messages to display: synthetic greeting + real messages
  const displayMessages = useMemo(() => {
    return [...syntheticMessages, ...messages];
  }, [syntheticMessages, messages]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [displayMessages, streamText]);

  // Load chat history when panel opens
  useEffect(() => {
    if (!isOpen || historyLoaded) return;
    fetchChatHistory(workspaceId)
      .then((history) => {
        setMessages(history);
        setHistoryLoaded(true);
      })
      .catch(() => setHistoryLoaded(true));
  }, [isOpen, workspaceId, historyLoaded]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen && !streaming) {
      inputRef.current?.focus();
    }
  }, [isOpen, streaming]);

  // Escape to close
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onToggle();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isOpen, onToggle]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || streaming) return;

      const userMsg: ChatMessage = {
        id: `temp-${Date.now()}`,
        role: "user",
        content: text.trim(),
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setStreaming(true);
      setStreamText("");

      const controller = new AbortController();
      abortRef.current = controller;

      let accumulated = "";
      let hadError = false;

      await streamChat(
        workspaceId,
        text.trim(),
        activeJournalId,
        {
          onToken: (token) => {
            accumulated += token;
            setStreamText(accumulated);
          },
          onAction: (action) => {
            onAction(action);
          },
          onDone: () => {
            if (!hadError && accumulated) {
              const assistantMsg: ChatMessage = {
                id: `temp-${Date.now()}-a`,
                role: "assistant",
                content: accumulated,
                created_at: new Date().toISOString(),
              };
              setMessages((prev) => [...prev, assistantMsg]);
            }
            setStreamText("");
            setStreaming(false);
            abortRef.current = null;
          },
          onError: (msg) => {
            hadError = true;
            if (accumulated) {
              const partialMsg: ChatMessage = {
                id: `temp-${Date.now()}-p`,
                role: "assistant",
                content: accumulated,
                created_at: new Date().toISOString(),
              };
              setMessages((prev) => [...prev, partialMsg]);
            }
            const errorMsg: ChatMessage = {
              id: `temp-${Date.now()}-e`,
              role: "assistant",
              content: `Something went wrong: ${msg}`,
              created_at: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, errorMsg]);
            setStreamText("");
          },
        },
        controller.signal,
      );
    },
    [workspaceId, activeJournalId, streaming, onAction],
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const canSend = input.trim().length > 0 && !streaming;

  return (
    <>
      {/* Toggle button (visible when panel is closed) */}
      {!isOpen && (
        <button
          onClick={onToggle}
          className="absolute top-14 left-6 z-30 rounded-lg border border-border-subtle bg-surface-card px-2 py-1.5 text-text-secondary hover:text-text-primary hover:bg-white/5 transition-colors"
        >
          <MessageCircle className="h-4 w-4" />
        </button>
      )}

      {/* Panel */}
      <div
        className={`fixed left-0 top-0 h-screen w-[380px] z-40 bg-surface border-r border-border-subtle flex flex-col transition-transform duration-300 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="shrink-0 flex items-center justify-between border-b border-border-subtle px-5 py-4">
          <h2 className="font-mono-display text-base font-bold tracking-tight text-text-primary">Ceekr</h2>
          <button
            onClick={onToggle}
            className="rounded-lg p-1.5 text-text-muted hover:text-text-primary hover:bg-white/5 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Messages area */}
        <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3 space-y-3">
          {displayMessages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm ${
                  msg.role === "user"
                    ? "bg-surface-card text-text-body"
                    : "text-text-body"
                }`}
              >
                <MessageContent content={msg.content} />
                {msg.action && (
                  <span className="mt-1 block text-xs text-text-muted">
                    {actionLabel(msg.action)}
                  </span>
                )}
              </div>
            </div>
          ))}

          {/* Streaming response */}
          {streaming && (
            <div className="flex justify-start">
              <div className="max-w-[85%] text-sm text-text-body">
                {streamText ? (
                  <p className="whitespace-pre-wrap">
                    {streamText}
                    <span className="inline-block w-[2px] h-[1em] bg-text-muted ml-0.5 animate-pulse" />
                  </p>
                ) : (
                  <span className="text-xs text-text-muted animate-pulse">
                    Thinking...
                  </span>
                )}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area — Clay-style with arrow inside */}
        <div className="shrink-0 border-t border-border-subtle px-4 py-3">
          <div
            className={`relative rounded-xl border border-border-subtle bg-surface-search ${
              streaming ? "opacity-50 pointer-events-none" : ""
            }`}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message..."
              rows={1}
              disabled={streaming}
              className="w-full resize-none bg-transparent rounded-xl px-3.5 py-2.5 pr-10 text-sm text-text-primary placeholder:text-text-muted focus:outline-none disabled:pointer-events-none"
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!canSend}
              className={`absolute right-2 top-1/2 -translate-y-1/2 rounded-full p-1 transition-colors ${
                canSend
                  ? "bg-text-primary text-surface hover:opacity-80"
                  : "text-text-muted/40"
              }`}
            >
              <ArrowUp className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

/** Render message content with basic markdown bold support. */
function MessageContent({ content }: { content: string }) {
  // Split on **bold** patterns
  const parts = content.split(/(\*\*[^*]+\*\*)/g);
  return (
    <p className="whitespace-pre-wrap">
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return (
            <span key={i} className="font-semibold">
              {part.slice(2, -2)}
            </span>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </p>
  );
}

function actionLabel(action: ChatAction): string {
  switch (action.type) {
    case "apply_filters":
      return "Filters applied";
    case "remove_profiles":
      return `Removed ${action.handles?.length ?? 0} profiles`;
    case "run_targeted_search":
      return `Found ${action.newResults?.length ?? 0} new people`;
    case "regroup_journals":
      return "Journals regrouped";
    default:
      return "";
  }
}
