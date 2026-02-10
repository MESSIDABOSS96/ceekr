"use client";

import { useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { X } from "lucide-react";
import type {
  Filters,
  RankedAccount,
  PostingFrequency,
  AccountAge,
} from "@/lib/types";
import { getUniqueLocations } from "@/lib/filter-utils";

interface FilterPanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
  results: RankedAccount[];
}

const POSTING_OPTIONS: { value: PostingFrequency; label: string }[] = [
  { value: "daily", label: "Daily" },
  { value: "several_week", label: "Several/week" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "rarely", label: "Rarely" },
];

const AGE_OPTIONS: { value: AccountAge; label: string }[] = [
  { value: "lt1", label: "< 1 year" },
  { value: "1to3", label: "1-3 years" },
  { value: "3to5", label: "3-5 years" },
  { value: "5plus", label: "5+ years" },
];

function formatFollowers(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

// Slider uses log scale for better UX with wide follower ranges
const FOLLOWER_STOPS = [0, 100, 500, 1_000, 5_000, 10_000, 50_000, 100_000, 500_000, 1_000_000, 10_000_000];

function sliderToFollowers(val: number): number {
  const idx = Math.floor(val);
  const frac = val - idx;
  if (idx >= FOLLOWER_STOPS.length - 1) return FOLLOWER_STOPS[FOLLOWER_STOPS.length - 1];
  return Math.round(FOLLOWER_STOPS[idx] + frac * (FOLLOWER_STOPS[idx + 1] - FOLLOWER_STOPS[idx]));
}

function followersToSlider(followers: number): number {
  for (let i = 0; i < FOLLOWER_STOPS.length - 1; i++) {
    if (followers <= FOLLOWER_STOPS[i + 1]) {
      const range = FOLLOWER_STOPS[i + 1] - FOLLOWER_STOPS[i];
      if (range === 0) return i;
      return i + (followers - FOLLOWER_STOPS[i]) / range;
    }
  }
  return FOLLOWER_STOPS.length - 1;
}

export function FilterPanel({
  open,
  onOpenChange,
  filters,
  onFiltersChange,
  results,
}: FilterPanelProps) {
  const [keywordInput, setKeywordInput] = useState("");
  const [locationOpen, setLocationOpen] = useState(false);

  const locations = useMemo(() => getUniqueLocations(results), [results]);
  const filteredLocations = useMemo(() => {
    if (!filters.location) return locations;
    return locations.filter((l) =>
      l.toLowerCase().includes(filters.location.toLowerCase())
    );
  }, [locations, filters.location]);

  const update = (partial: Partial<Filters>) => {
    onFiltersChange({ ...filters, ...partial });
  };

  const addKeyword = (kw: string) => {
    const trimmed = kw.trim();
    if (trimmed && !filters.keywords.includes(trimmed)) {
      update({ keywords: [...filters.keywords, trimmed] });
    }
    setKeywordInput("");
  };

  const removeKeyword = (kw: string) => {
    update({ keywords: filters.keywords.filter((k) => k !== kw) });
  };

  const toggleMultiSelect = <T extends string>(
    current: T[],
    value: T,
    key: keyof Filters
  ) => {
    const next = current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value];
    update({ [key]: next } as Partial<Filters>);
  };

  const sliderMin = followersToSlider(filters.followerMin);
  const sliderMax =
    filters.followerMax === Infinity
      ? FOLLOWER_STOPS.length - 1
      : followersToSlider(filters.followerMax);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto border-border-subtle bg-[oklch(0.16_0.004_163)] sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-text-primary">Filters</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 pt-2">
          {/* Keywords */}
          <div className="space-y-2">
            <Label className="text-text-secondary">Topic / Niche keywords</Label>
            <Input
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addKeyword(keywordInput);
                }
              }}
              placeholder="Type and press Enter"
              className="border-border-subtle bg-surface text-text-primary placeholder:text-text-muted"
            />
            {filters.keywords.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {filters.keywords.map((kw) => (
                  <span
                    key={kw}
                    className="inline-flex items-center gap-1 rounded-full bg-twitter/10 px-2.5 py-1 text-xs font-medium text-twitter"
                  >
                    {kw}
                    <button
                      onClick={() => removeKeyword(kw)}
                      className="hover:text-white"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Follower count range */}
          <div className="space-y-3">
            <Label className="text-text-secondary">Follower count</Label>
            <Slider
              min={0}
              max={FOLLOWER_STOPS.length - 1}
              step={0.1}
              value={[sliderMin, sliderMax]}
              onValueChange={([min, max]) => {
                update({
                  followerMin: sliderToFollowers(min),
                  followerMax:
                    max >= FOLLOWER_STOPS.length - 1
                      ? Infinity
                      : sliderToFollowers(max),
                });
              }}
              className="py-2"
            />
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  value={filters.followerMin}
                  onChange={(e) =>
                    update({ followerMin: Number(e.target.value) || 0 })
                  }
                  className="h-8 w-24 border-border-subtle bg-surface text-xs text-text-primary"
                />
                <span className="text-xs text-text-muted">min</span>
              </div>
              <span className="text-text-muted">—</span>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  value={filters.followerMax === Infinity ? "" : filters.followerMax}
                  onChange={(e) =>
                    update({
                      followerMax: e.target.value
                        ? Number(e.target.value)
                        : Infinity,
                    })
                  }
                  placeholder="No max"
                  className="h-8 w-24 border-border-subtle bg-surface text-xs text-text-primary placeholder:text-text-muted"
                />
                <span className="text-xs text-text-muted">max</span>
              </div>
            </div>
          </div>

          {/* Location */}
          <div className="space-y-2">
            <Label className="text-text-secondary">Location</Label>
            <div className="relative">
              <Input
                value={filters.location}
                onChange={(e) => {
                  update({ location: e.target.value });
                  setLocationOpen(e.target.value.length > 0);
                }}
                onFocus={() => {
                  if (filters.location) setLocationOpen(true);
                }}
                onBlur={() => {
                  // Delay to allow click on suggestion
                  setTimeout(() => setLocationOpen(false), 150);
                }}
                placeholder="e.g. San Francisco"
                className="border-border-subtle bg-surface text-text-primary placeholder:text-text-muted"
              />
              {locationOpen && filteredLocations.length > 0 && (
                <div className="absolute z-50 mt-1 max-h-40 w-full overflow-y-auto rounded-lg border border-border-subtle bg-[oklch(0.19_0.004_163)] shadow-lg">
                  {filteredLocations.map((loc) => (
                    <button
                      key={loc}
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => {
                        update({ location: loc });
                        setLocationOpen(false);
                      }}
                      className="w-full px-3 py-1.5 text-left text-sm text-text-body hover:bg-twitter/10 hover:text-twitter"
                    >
                      {loc}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Verified */}
          <div className="flex items-center justify-between">
            <Label className="text-text-secondary">Verified only</Label>
            <Switch
              checked={filters.verified === true}
              onCheckedChange={(checked) =>
                update({ verified: checked ? true : null })
              }
            />
          </div>

          {/* Posting frequency */}
          <div className="space-y-2">
            <Label className="text-text-secondary">Posting frequency</Label>
            <div className="flex flex-wrap gap-1.5">
              {POSTING_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() =>
                    toggleMultiSelect(
                      filters.postingFrequency,
                      opt.value,
                      "postingFrequency"
                    )
                  }
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                    filters.postingFrequency.includes(opt.value)
                      ? "border-twitter bg-twitter/15 text-twitter"
                      : "border-border-subtle text-text-secondary hover:border-twitter/40"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Account age */}
          <div className="space-y-2">
            <Label className="text-text-secondary">Account age</Label>
            <div className="flex flex-wrap gap-1.5">
              {AGE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() =>
                    toggleMultiSelect(
                      filters.accountAge,
                      opt.value,
                      "accountAge"
                    )
                  }
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                    filters.accountAge.includes(opt.value)
                      ? "border-twitter bg-twitter/15 text-twitter"
                      : "border-border-subtle text-text-secondary hover:border-twitter/40"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Reset */}
          <button
            onClick={() =>
              onFiltersChange({
                keywords: [],
                followerMin: 0,
                followerMax: Infinity,
                location: "",
                verified: null,
                postingFrequency: [],
                accountAge: [],
              })
            }
            className="text-sm text-text-muted hover:text-text-secondary"
          >
            Reset all filters
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
