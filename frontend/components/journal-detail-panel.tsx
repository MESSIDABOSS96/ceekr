"use client";

import { useEffect } from "react";
import { X } from "lucide-react";
import { ResultCard } from "@/components/result-card";
import type { WorkspaceJournal, JournalPerson } from "@/lib/types";

interface JournalDetailPanelProps {
  journal: WorkspaceJournal | null;
  people: JournalPerson[] | null;
  loading: boolean;
  onClose: () => void;
}

export function JournalDetailPanel({
  journal,
  people,
  loading,
  onClose,
}: JournalDetailPanelProps) {
  const isOpen = journal !== null;

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-black/40 backdrop-blur-sm transition-opacity duration-300 ${
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        onClick={onClose}
      />

      {/* Centered modal */}
      <div
        className={`fixed inset-0 z-50 flex items-center justify-center transition-all duration-300 ${
          isOpen
            ? "opacity-100 scale-100"
            : "opacity-0 scale-95 pointer-events-none"
        }`}
        onClick={onClose}
      >
        <div
          className="w-full max-w-[960px] max-h-[85vh] rounded-2xl border border-border-subtle bg-surface flex flex-col overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {journal && (
            <>
              {/* Header */}
              <div className="shrink-0 flex items-start gap-3 border-b border-border-subtle px-5 py-4">
                <div
                  className="mt-1 h-3 w-3 shrink-0 rounded-full"
                  style={{ backgroundColor: journal.color }}
                />
                <div className="flex-1 min-w-0">
                  <h2 className="text-base font-semibold text-text-primary leading-tight">
                    {journal.label}
                  </h2>
                  <span className="mt-1 text-xs text-text-muted">
                    {journal.people_count}{" "}
                    {journal.people_count === 1 ? "person" : "people"}
                  </span>
                </div>
                <button
                  onClick={onClose}
                  className="shrink-0 rounded-lg p-1.5 text-text-muted hover:text-text-primary hover:bg-white/5 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* People list */}
              <div className="flex-1 min-h-0 overflow-y-auto">
                <div className="p-4 grid grid-cols-2 gap-3">
                  {loading && (
                    <p className="col-span-2 text-sm text-text-muted animate-pulse text-center py-8">
                      Loading people...
                    </p>
                  )}
                  {!loading && people && people.length === 0 && (
                    <p className="col-span-2 text-sm text-text-muted text-center py-8">
                      No people in this journal.
                    </p>
                  )}
                  {!loading &&
                    people?.map((person) => (
                      <ResultCard key={person.user_id} account={person} />
                    ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
