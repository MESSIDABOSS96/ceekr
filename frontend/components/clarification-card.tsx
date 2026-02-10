"use client";

import type { ClarificationQuestion } from "@/lib/types";

interface ClarificationCardProps {
  questions: ClarificationQuestion[];
}

export function ClarificationCard({ questions }: ClarificationCardProps) {
  return (
    <div className="mb-6 rounded-2xl border border-border-subtle bg-surface-card p-6">
      <p className="mb-4 text-[0.95rem] font-semibold text-text-primary">
        Need a bit more context to find the right people
      </p>
      <div className="space-y-3">
        {questions.map((q, i) => (
          <div key={i}>
            <p className="text-[0.9rem] font-medium text-text-primary">
              {q.question}
            </p>
            <p className="text-[0.8rem] italic text-text-muted">{q.reason}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
