import type { RankedAccount, SearchQuery } from "./types";

const KEY_PREFIX = "ceekr_search_";
const TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

export interface PersistedSearch {
  id: string;
  query: string;
  results: RankedAccount[];
  quality: "strong" | "moderate" | "weak";
  refinementQuestions: string[];
  queries: SearchQuery[];
  createdAt: number;
}

export function saveSearch(search: PersistedSearch): void {
  try {
    localStorage.setItem(KEY_PREFIX + search.id, JSON.stringify(search));
    pruneExpired();
  } catch {
    // Graceful degradation — quota exceeded or localStorage unavailable
  }
}

export function loadSearch(id: string): PersistedSearch | null {
  try {
    const raw = localStorage.getItem(KEY_PREFIX + id);
    if (!raw) return null;
    const search: PersistedSearch = JSON.parse(raw);
    if (Date.now() - search.createdAt > TTL_MS) {
      localStorage.removeItem(KEY_PREFIX + id);
      return null;
    }
    return search;
  } catch {
    return null;
  }
}

function pruneExpired(): void {
  try {
    const now = Date.now();
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key?.startsWith(KEY_PREFIX)) continue;
      try {
        const raw = localStorage.getItem(key);
        if (!raw) continue;
        const { createdAt } = JSON.parse(raw);
        if (now - createdAt > TTL_MS) {
          localStorage.removeItem(key);
          i--; // Adjust index after removal
        }
      } catch {
        // Skip malformed entries
      }
    }
  } catch {
    // localStorage unavailable
  }
}
