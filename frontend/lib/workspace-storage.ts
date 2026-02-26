import type { JournalOverlap } from "./types";

export function saveOverlaps(workspaceId: string, overlaps: JournalOverlap[]) {
  try {
    localStorage.setItem(`ceekr_overlaps_${workspaceId}`, JSON.stringify(overlaps));
  } catch {
    // localStorage full or unavailable
  }
}

export function loadOverlaps(workspaceId: string): JournalOverlap[] {
  try {
    const raw = localStorage.getItem(`ceekr_overlaps_${workspaceId}`);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch {
    return [];
  }
}
