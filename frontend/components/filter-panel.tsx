"use client";

import { useState, useMemo, useEffect } from "react";
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
import type { Filters, RankedAccount } from "@/lib/types";
import { getUniqueLocations } from "@/lib/filter-utils";

interface FilterPanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
  results: RankedAccount[];
}

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
  const [locationInput, setLocationInput] = useState(filters.location);
  const [locationOpen, setLocationOpen] = useState(false);

  // Sync local input when the committed filter changes externally (e.g. reset)
  useEffect(() => {
    setLocationInput(filters.location);
  }, [filters.location]);

  const locations = useMemo(() => getUniqueLocations(results), [results]);
  const filteredLocations = useMemo(() => {
    if (!locationInput) return locations;
    return locations.filter((l) =>
      l.toLowerCase().includes(locationInput.toLowerCase())
    );
  }, [locations, locationInput]);

  const update = (partial: Partial<Filters>) => {
    onFiltersChange({ ...filters, ...partial });
  };

  const sliderMin = followersToSlider(filters.followerMin);
  const sliderMax =
    filters.followerMax === Infinity
      ? FOLLOWER_STOPS.length - 1
      : followersToSlider(filters.followerMax);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-border-subtle bg-[oklch(0.16_0.004_163)] sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-text-primary">Filters</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 pt-2">
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
                value={locationInput}
                onChange={(e) => {
                  setLocationInput(e.target.value);
                  setLocationOpen(e.target.value.length > 0);
                }}
                onFocus={() => {
                  if (locationInput) setLocationOpen(true);
                }}
                onBlur={() => {
                  // Delay to allow click on suggestion, then revert to committed value
                  setTimeout(() => {
                    setLocationOpen(false);
                    setLocationInput(filters.location);
                  }, 150);
                }}
                placeholder="e.g. San Francisco"
                className="border-border-subtle bg-surface text-text-primary placeholder:text-text-muted"
              />
              {filters.location && (
                <button
                  onClick={() => {
                    update({ location: "" });
                    setLocationInput("");
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary text-xs"
                  aria-label="Clear location"
                >
                  ✕
                </button>
              )}
              {locationOpen && filteredLocations.length > 0 && (
                <div className="absolute z-50 mt-1 max-h-[200px] w-full overflow-y-auto rounded-lg border border-border-subtle bg-[oklch(0.19_0.004_163)] shadow-lg">
                  {filteredLocations.slice(0, 50).map((loc) => (
                    <button
                      key={loc}
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => {
                        update({ location: loc });
                        setLocationInput(loc);
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

          {/* Reset */}
          <button
            onClick={() =>
              onFiltersChange({
                followerMin: 0,
                followerMax: Infinity,
                location: "",
                verified: null,
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
