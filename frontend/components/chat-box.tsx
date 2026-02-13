"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { ArrowRight, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import { ChatMessageBubble } from "@/components/chat-message";
import type { ChatMessage, SearchQuery } from "@/lib/types";

interface ChatBoxProps {
  messages: ChatMessage[];
  loading: boolean;
  onSend: (message: string) => void;
  disabled?: boolean;
  progressMessages?: string[];
  queries?: SearchQuery[];
  isSearching?: boolean;
}

export function ChatBox({
  messages,
  loading,
  onSend,
  disabled,
  progressMessages = [],
  queries = [],
  isSearching = false,
}: ChatBoxProps) {
  const [input, setInput] = useState("");
  const [progressExpanded, setProgressExpanded] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading, progressMessages]);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || loading || disabled) return;
    onSend(trimmed);
    setInput("");
  }, [input, loading, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const latestProgress =
    progressMessages[progressMessages.length - 1] ||
    (isSearching ? "Starting search..." : null);

  return (
    <div className="rounded-2xl border border-border-subtle bg-surface">
      {/* Messages area */}
      <div
        ref={scrollRef}
        className="min-h-[300px] max-h-[650px] overflow-y-auto px-4 pt-4 pb-2"
      >
        <div className="space-y-3">
          {messages.map((msg) => (
            <ChatMessageBubble key={msg.id} message={msg} />
          ))}

          {/* Inline progress (replaces external ProgressStrip) */}
          {isSearching && latestProgress && (
            <div className="flex justify-start">
              <div className="rounded-2xl bg-surface-card px-4 py-2.5">
                <button
                  onClick={() => setProgressExpanded(!progressExpanded)}
                  className="flex items-center gap-2 text-left"
                >
                  <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-twitter" />
                  <span className="text-[0.88rem] text-text-secondary">
                    {latestProgress}
                  </span>
                  {progressMessages.length > 1 &&
                    (progressExpanded ? (
                      <ChevronUp className="h-4 w-4 text-text-muted" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-text-muted" />
                    ))}
                </button>

                {progressExpanded && (
                  <div className="mt-2 space-y-1 border-t border-border-subtle pt-2">
                    {progressMessages.slice(0, -1).map((msg, i) => (
                      <p key={i} className="text-[0.82rem] text-text-muted">
                        {msg}
                      </p>
                    ))}
                    {queries.length > 0 && (
                      <div className="mt-2 space-y-1">
                        <p className="text-[0.78rem] font-medium uppercase tracking-wide text-text-muted">
                          Search queries
                        </p>
                        {queries.map((q, i) => (
                          <p
                            key={i}
                            className="text-[0.82rem] text-text-secondary"
                          >
                            <code className="rounded bg-white/5 px-1.5 py-0.5">
                              {q.query}
                            </code>{" "}
                            <span className="text-text-muted">
                              — {q.angle}
                            </span>
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {loading && !isSearching && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-2xl bg-surface-card px-4 py-2.5 text-[0.88rem] text-text-muted">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Thinking...
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input area */}
      <div className="border-t border-border-subtle px-3 py-2.5">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            disabled={loading || disabled}
            className="flex-1 bg-transparent px-2 py-1.5 text-[0.88rem] text-text-primary placeholder:text-text-muted outline-none disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading || disabled}
            className="flex h-6 w-6 items-center justify-center rounded-full bg-twitter text-white transition-opacity hover:opacity-80 disabled:opacity-30"
          >
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
