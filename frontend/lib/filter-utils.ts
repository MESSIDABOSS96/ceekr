import type { Filters, RankedAccount } from "./types";

export function hasActiveFilters(filters: Filters): boolean {
  return (
    filters.followerMin > 0 ||
    filters.followerMax < Infinity ||
    filters.location !== "" ||
    filters.verified !== null
  );
}

export function countActiveFilters(filters: Filters): number {
  let count = 0;
  if (filters.followerMin > 0 || filters.followerMax < Infinity) count++;
  if (filters.location !== "") count++;
  if (filters.verified !== null) count++;
  return count;
}

function matchesLocation(accountLocation: string | null, filterLocation: string): boolean {
  if (!filterLocation) return true;
  if (!accountLocation) return false;
  return accountLocation.toLowerCase().includes(filterLocation.toLowerCase());
}

export function applyFilters(results: RankedAccount[], filters: Filters): RankedAccount[] {
  if (!hasActiveFilters(filters)) return results;

  return results.filter((r) => {
    // Follower range
    if (r.followers_count < filters.followerMin) return false;
    if (filters.followerMax < Infinity && r.followers_count > filters.followerMax)
      return false;

    // Location
    if (!matchesLocation(r.location, filters.location)) return false;

    // Verified
    if (filters.verified !== null && r.verified !== filters.verified) return false;

    return true;
  });
}

export function getUniqueLocations(results: RankedAccount[]): string[] {
  const locations = new Set<string>();
  for (const r of results) {
    if (r.location) locations.add(r.location);
  }
  return Array.from(locations).sort();
}
