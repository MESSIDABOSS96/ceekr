"use client";

import { useState, useEffect, useRef } from "react";
import type { ActivityStep, ActivityStepType } from "@/lib/types";

// ── Pipeline steps in display order ──

interface PipelineStep {
  type: ActivityStepType;
  label: string;
}

const PIPELINE_STEPS: PipelineStep[] = [
  { type: "intent_analysis", label: "Understanding your search" },
  { type: "searching", label: "Searching Twitter" },
  { type: "filtering", label: "Filtering candidates" },
  { type: "ranking", label: "Ranking accounts by relevance" },
];

// Map step types that share a pipeline row
function toPipelineType(step: ActivityStepType): ActivityStepType | null {
  switch (step) {
    case "init":
    case "intent_analysis":
      return "intent_analysis";
    case "query_generation":
    case "searching":
    case "fallback":
      return "searching";
    case "filtering":
    case "filtering_done":
      return "filtering";
    case "ranking":
    case "grouping":
      return "ranking";
    default:
      return null;
  }
}

type StepStatus = "pending" | "active" | "done";

function getStepStatuses(
  steps: ActivityStep[],
  isComplete: boolean,
): Map<ActivityStepType, StepStatus> {
  const statuses = new Map<ActivityStepType, StepStatus>();

  // Initialize all as pending
  for (const ps of PIPELINE_STEPS) {
    statuses.set(ps.type, "pending");
  }

  if (isComplete) {
    // All done
    for (const ps of PIPELINE_STEPS) {
      statuses.set(ps.type, "done");
    }
    return statuses;
  }

  if (steps.length === 0) return statuses;

  // Walk through received steps and mark pipeline stages
  const reachedTypes = new Set<ActivityStepType>();
  for (const s of steps) {
    const pt = toPipelineType(s.step);
    if (pt) reachedTypes.add(pt);
  }

  // The last received step's pipeline type is "active"
  const lastStep = steps[steps.length - 1];
  const activePipelineType = toPipelineType(lastStep.step);

  // Mark statuses: anything before active = done, active = active, rest = pending
  let passedActive = false;
  for (const ps of PIPELINE_STEPS) {
    if (ps.type === activePipelineType) {
      statuses.set(ps.type, "active");
      passedActive = true;
    } else if (!passedActive && reachedTypes.has(ps.type)) {
      statuses.set(ps.type, "done");
    }
    // else stays "pending"
  }

  return statuses;
}

// ── Icons ──

function CheckCircle() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="shrink-0">
      <circle cx="9" cy="9" r="9" className="fill-twitter" />
      <path
        d="M5.5 9.5L7.5 11.5L12.5 6.5"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function EmptyCircle() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="shrink-0">
      <circle cx="9" cy="9" r="8" className="stroke-text-muted" strokeWidth="1.5" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      className="shrink-0 animate-spin"
    >
      <circle
        cx="9"
        cy="9"
        r="8"
        className="stroke-text-muted"
        strokeWidth="1.5"
        opacity="0.3"
      />
      <path
        d="M9 1C13.4183 1 17 4.58172 17 9"
        className="stroke-twitter"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ChevronDown({ open }: { open: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      className={`shrink-0 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
    >
      <path
        d="M4 6L8 10L12 6"
        className="stroke-text-muted"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ── Step label enrichment ──

function getStepLabel(ps: PipelineStep, steps: ActivityStep[]): string {
  // Find the latest step matching this pipeline type for count info
  const matching = steps.filter((s) => toPipelineType(s.step) === ps.type);
  if (matching.length === 0) return ps.label;

  const last = matching[matching.length - 1];
  const counts = last.counts;

  switch (ps.type) {
    case "searching":
      if (counts?.accounts) return `Searching Twitter — ${counts.accounts} accounts found`;
      return ps.label;
    case "filtering":
      if (counts?.total) return `Filtering ${counts.total} candidates`;
      return ps.label;
    case "ranking":
      if (counts?.accounts) return `Ranking ${counts.accounts} accounts by relevance`;
      return ps.label;
    default:
      return ps.label;
  }
}

// ── Status line (bottom) ──

function getStatusLine(steps: ActivityStep[]): { text: string; count?: string } | null {
  if (steps.length === 0) return null;
  const last = steps[steps.length - 1];
  const counts = last.counts;

  let count: string | undefined;
  if (counts?.accounts) count = `${counts.accounts} accounts`;
  else if (counts?.total) count = `${counts.total} candidates`;
  else if (counts?.passed) count = `${counts.passed} matches`;
  else if (counts?.found) count = `${counts.found} found`;

  return { text: last.message, count };
}

// ── Component ──

interface ThinkingPanelProps {
  steps: ActivityStep[];
  progress: number;
  isComplete: boolean;
}

export function ThinkingPanel({ steps, progress, isComplete }: ThinkingPanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const collapseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto-collapse after completion
  useEffect(() => {
    if (isComplete) {
      collapseTimerRef.current = setTimeout(() => setCollapsed(true), 1500);
    } else {
      setCollapsed(false);
      if (collapseTimerRef.current) {
        clearTimeout(collapseTimerRef.current);
        collapseTimerRef.current = null;
      }
    }
    return () => {
      if (collapseTimerRef.current) clearTimeout(collapseTimerRef.current);
    };
  }, [isComplete]);

  const statuses = getStepStatuses(steps, isComplete);
  const statusLine = getStatusLine(steps);

  // Collapsed summary
  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-border-subtle bg-surface-card/50 px-4 py-2.5 text-sm text-text-muted transition-colors hover:bg-surface-card hover:text-text-secondary"
      >
        <CheckCircle />
        <span>Search complete — {steps.length} steps</span>
        <ChevronDown open={false} />
      </button>
    );
  }

  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-border-subtle bg-surface-card">
      {/* Collapsible header (only when complete) */}
      {isComplete && (
        <button
          onClick={() => setCollapsed(true)}
          className="flex w-full items-center gap-2 px-4 pt-3 pb-1 text-xs text-text-muted hover:text-text-secondary transition-colors"
        >
          <span>Thinking</span>
          <ChevronDown open={true} />
        </button>
      )}

      {/* Step checklist */}
      <div className="px-4 py-3 space-y-2.5">
        {PIPELINE_STEPS.map((ps) => {
          const status = statuses.get(ps.type) ?? "pending";
          const label = getStepLabel(ps, steps);

          return (
            <div key={ps.type} className="flex items-center gap-2.5">
              {status === "done" && <CheckCircle />}
              {status === "active" && <Spinner />}
              {status === "pending" && <EmptyCircle />}
              <span
                className={`text-sm ${
                  status === "done"
                    ? "text-text-secondary"
                    : status === "active"
                      ? "text-text-primary"
                      : "text-text-muted"
                }`}
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Bottom section: status + progress bar */}
      {!isComplete && (
        <div className="border-t border-border-subtle px-4 py-2.5">
          {statusLine && (
            <div className="mb-2 flex items-center justify-between gap-3">
              <p className="text-xs text-text-muted truncate animate-pulse">{statusLine.text}</p>
              {statusLine.count && (
                <span className="shrink-0 rounded-full bg-surface-search px-2 py-0.5 text-xs text-text-secondary">
                  {statusLine.count}
                </span>
              )}
            </div>
          )}
          <div className="h-1 w-full overflow-hidden rounded-full bg-surface-search">
            <div
              className="h-full rounded-full bg-twitter transition-all duration-1000 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
