"use client";

import { useState, useCallback, useRef } from "react";
import { ArrowRight } from "lucide-react";
import type { ClarificationQuestion } from "@/lib/types";

interface ClarificationPanelProps {
  questions: ClarificationQuestion[];
  originalQuery: string;
  onSubmit: (enrichedQuery: string) => void;
}

export function ClarificationPanel({
  questions,
  originalQuery,
  onSubmit,
}: ClarificationPanelProps) {
  const [answers, setAnswers] = useState<Record<number, string>>(
    () => Object.fromEntries(questions.map((_, i) => [i, ""]))
  );
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const setAnswer = useCallback((index: number, value: string) => {
    setAnswers((prev) => ({ ...prev, [index]: value }));
  }, []);

  const handleSubmit = useCallback(() => {
    const parts: string[] = [originalQuery];

    for (let i = 0; i < questions.length; i++) {
      const answer = answers[i]?.trim();
      if (answer) {
        parts.push(`${questions[i].question} ${answer}`);
      }
    }

    onSubmit(parts.join(" | "));
  }, [originalQuery, questions, answers, onSubmit]);

  const hasAnyAnswer = Object.values(answers).some((a) => a.trim().length > 0);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, index: number) => {
      if (e.key === "Enter") {
        e.preventDefault();
        // If there's a next input, focus it; otherwise submit
        const nextInput = inputRefs.current[index + 1];
        if (nextInput) {
          nextInput.focus();
        } else if (hasAnyAnswer) {
          handleSubmit();
        }
      }
    },
    [hasAnyAnswer, handleSubmit],
  );

  return (
    <div className="mt-4 animate-in fade-in slide-in-from-top-2 duration-300">
      <div className="rounded-2xl border border-white/[0.08] bg-surface-card px-6 py-5">
        <p className="mb-4 text-sm text-text-secondary">
          A few details would help narrow this down
        </p>

        <div className="space-y-4">
          {questions.map((q, i) => (
            <div key={i}>
              <p className="mb-2 text-[0.82rem] font-medium text-text-primary">
                {q.question}
              </p>
              <input
                ref={(el) => { inputRefs.current[i] = el; }}
                type="text"
                value={answers[i] ?? ""}
                onChange={(e) => setAnswer(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(e, i)}
                placeholder={q.placeholder ? `e.g. ${q.placeholder}` : ""}
                className="w-full rounded-xl border border-white/[0.08] bg-white/[0.03] px-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted/50 focus:border-white/[0.14] focus:outline-none"
              />
            </div>
          ))}
        </div>

        <div className="mt-5 flex justify-end">
          <button
            type="button"
            onClick={handleSubmit}
            className="flex items-center gap-2 rounded-full bg-accent px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-accent/90 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            disabled={!hasAnyAnswer}
          >
            Search
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
