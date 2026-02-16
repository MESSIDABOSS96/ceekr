import type {
  SearchQuery,
  SearchResults,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface StreamCallbacks {
  onProgress?: (message: string) => void;
  onQueries?: (queries: SearchQuery[]) => void;
  onResults?: (results: SearchResults) => void;
  onError?: (message: string) => void;
  onDone?: () => void;
}

function dispatchEvent(
  event: string,
  data: string,
  callbacks: StreamCallbacks,
) {
  try {
    const parsed = JSON.parse(data);
    switch (event) {
      case "progress":
        callbacks.onProgress?.(parsed.message);
        break;
      case "queries":
        callbacks.onQueries?.(parsed);
        break;
      case "results":
        callbacks.onResults?.(parsed);
        break;
      case "error":
        callbacks.onError?.(parsed.message);
        break;
    }
  } catch {
    // Skip malformed JSON
  }
}

export async function streamSearch(
  query: string,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
) {
  const body = { query };

  const response = await fetch(`${API_URL}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    callbacks.onError?.(`Server error: ${response.status}`);
    callbacks.onDone?.();
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError?.("No response stream");
    callbacks.onDone?.();
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";
  // Persist across chunks so split event/data lines still pair up
  let currentEvent = "";
  let currentData = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const rawLine of lines) {
        const line = rawLine.replace(/\r$/, "");

        // SSE comment (e.g. ": ping ...")
        if (line.startsWith(":")) continue;

        if (line.startsWith("event:")) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          currentData = line.slice(5).trim();
        } else if (line === "") {
          // Empty line = end of SSE message
          if (currentEvent && currentData) {
            dispatchEvent(currentEvent, currentData, callbacks);
          }
          currentEvent = "";
          currentData = "";
        }
      }
    }
  } finally {
    reader.releaseLock();
    callbacks.onDone?.();
  }
}
