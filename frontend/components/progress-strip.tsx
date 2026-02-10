"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import type { SearchQuery } from "@/lib/types";

interface ProgressStripProps {
  messages: string[];
  queries: SearchQuery[];
  isSearching: boolean;
}

export function ProgressStrip({
  messages,
  queries,
  isSearching,
}: ProgressStripProps) {
  const [expanded, setExpanded] = useState(false);
  const latestMessage = messages[messages.length - 1] || (isSearching ? "Starting search..." : null);

  if (!latestMessage) return null;

  return (
    <div className="mb-4 rounded-xl border border-border-subtle p-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 text-left"
      >
        {isSearching && (
          <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-twitter" />
        )}
        <span className="flex-1 text-[0.88rem] text-text-secondary">
          {latestMessage}
        </span>
        {messages.length > 1 &&
          (expanded ? (
            <ChevronUp className="h-4 w-4 text-text-muted" />
          ) : (
            <ChevronDown className="h-4 w-4 text-text-muted" />
          ))}
      </button>

      {expanded && (
        <div className="mt-3 space-y-1 border-t border-border-subtle pt-3">
          {messages.slice(0, -1).map((msg, i) => (
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
                <p key={i} className="text-[0.82rem] text-text-secondary">
                  <code className="rounded bg-white/5 px-1.5 py-0.5">
                    {q.query}
                  </code>{" "}
                  <span className="text-text-muted">— {q.angle}</span>
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
