"use client";

import { SlidersHorizontal } from "lucide-react";
import { countActiveFilters } from "@/lib/filter-utils";
import type { Filters } from "@/lib/types";

const CHIPS = [
  "Founders",
  "Engineers",
  "Investors",
  "< 50K followers",
  "Active recently",
];

interface FilterChipsProps {
  onChipClick: (chip: string) => void;
  filters: Filters;
  onFiltersOpen: () => void;
  showSuggestionChips?: boolean;
}

export function FilterChips({
  onChipClick,
  filters,
  onFiltersOpen,
  showSuggestionChips = true,
}: FilterChipsProps) {
  const activeCount = countActiveFilters(filters);

  return (
    <div className="flex flex-wrap justify-center gap-2">
      {/* Filters button — always first */}
      <button
        onClick={onFiltersOpen}
        className={`inline-flex items-center gap-1.5 rounded-full border px-4 py-1.5 text-[0.82rem] font-medium transition-all ${
          activeCount > 0
            ? "border-twitter/40 bg-twitter/[0.08] text-twitter"
            : "border-white/10 text-text-secondary hover:border-twitter/40 hover:bg-twitter/[0.06] hover:text-twitter"
        }`}
      >
        <SlidersHorizontal className="h-3.5 w-3.5" />
        Filters
        {activeCount > 0 && (
          <span className="ml-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-twitter text-[0.65rem] font-bold text-white">
            {activeCount}
          </span>
        )}
      </button>

      {/* Suggestion chips */}
      {showSuggestionChips &&
        CHIPS.map((chip) => (
          <button
            key={chip}
            onClick={() => onChipClick(chip)}
            className="rounded-full border border-white/10 px-4 py-1.5 text-[0.82rem] font-medium text-text-secondary transition-all hover:border-twitter/40 hover:bg-twitter/[0.06] hover:text-twitter"
          >
            {chip}
          </button>
        ))}
    </div>
  );
}
