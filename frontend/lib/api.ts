import type {
  ActivityStep,
  ChatAction,
  ChatMessage,
  SearchQuery,
  SearchResults,
  WorkspaceData,
  WorkspaceSummary,
  JournalPerson,
  IntentCheckResponse,
} from "./types";
import { getSessionId } from "./sidebar-storage";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface StreamCallbacks {
  onProgress?: (data: Record<string, unknown>) => void;
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
        callbacks.onProgress?.(parsed);
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
          // Concatenate multi-line data fields per SSE spec
          const chunk = line.slice(5).trim();
          currentData = currentData ? currentData + "\n" + chunk : chunk;
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

    // Flush any remaining buffered event after stream ends
    if (currentEvent && currentData) {
      dispatchEvent(currentEvent, currentData, callbacks);
    }
  } finally {
    reader.releaseLock();
    callbacks.onDone?.();
  }
}

// ── Intent check ──

export async function checkIntent(query: string): Promise<IntentCheckResponse> {
  const response = await fetch(`${API_URL}/api/intent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!response.ok) {
    throw new Error(`Server error: ${response.status}`);
  }
  return response.json();
}

// ── Workspace SSE + REST ──

interface WorkspaceStreamCallbacks {
  onProgress?: (data: Record<string, unknown>) => void;
  onQueries?: (queries: SearchQuery[]) => void;
  onWorkspace?: (data: WorkspaceData) => void;
  onError?: (message: string) => void;
  onDone?: () => void;
}

function dispatchWorkspaceEvent(
  event: string,
  data: string,
  callbacks: WorkspaceStreamCallbacks,
) {
  try {
    const parsed = JSON.parse(data);
    switch (event) {
      case "progress":
        callbacks.onProgress?.(parsed);
        break;
      case "queries":
        callbacks.onQueries?.(parsed);
        break;
      case "workspace":
        callbacks.onWorkspace?.(parsed);
        break;
      case "error":
        callbacks.onError?.(parsed.message);
        break;
    }
  } catch {
    // Skip malformed JSON
  }
}

export async function streamWorkspace(
  query: string,
  callbacks: WorkspaceStreamCallbacks,
  signal?: AbortSignal,
) {
  const response = await fetch(`${API_URL}/api/workspace`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-session-id": getSessionId() },
    body: JSON.stringify({ query }),
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
        if (line.startsWith(":")) continue;

        if (line.startsWith("event:")) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          const chunk = line.slice(5).trim();
          currentData = currentData ? currentData + "\n" + chunk : chunk;
        } else if (line === "") {
          if (currentEvent && currentData) {
            dispatchWorkspaceEvent(currentEvent, currentData, callbacks);
          }
          currentEvent = "";
          currentData = "";
        }
      }
    }

    if (currentEvent && currentData) {
      dispatchWorkspaceEvent(currentEvent, currentData, callbacks);
    }
  } finally {
    reader.releaseLock();
    callbacks.onDone?.();
  }
}

export async function fetchWorkspace(workspaceId: string): Promise<WorkspaceData> {
  const response = await fetch(`${API_URL}/api/workspace/${workspaceId}`);
  if (!response.ok) {
    throw new Error(response.status === 404 ? "not_found" : `Server error: ${response.status}`);
  }
  return response.json();
}

export async function fetchJournalPeople(
  workspaceId: string,
  journalId: string,
): Promise<JournalPerson[]> {
  const response = await fetch(`${API_URL}/api/workspace/${workspaceId}/journal/${journalId}`);
  if (!response.ok) {
    throw new Error(`Server error: ${response.status}`);
  }
  const data = await response.json();
  return data.people;
}

export async function updateLayout(
  workspaceId: string,
  positions: { journal_id: string; canvas_x: number; canvas_y: number }[],
) {
  await fetch(`${API_URL}/api/workspace/${workspaceId}/layout`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ positions }),
  });
}

// ── Workspace Chat SSE ──

interface ChatStreamCallbacks {
  onToken: (text: string) => void;
  onAction: (action: ChatAction) => void;
  onDone: () => void;
  onError: (message: string) => void;
}

export async function streamChat(
  workspaceId: string,
  message: string,
  activeJournalId: string | null,
  callbacks: ChatStreamCallbacks,
  signal?: AbortSignal,
) {
  const response = await fetch(`${API_URL}/api/workspace/${workspaceId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, active_journal_id: activeJournalId }),
    signal,
  });

  if (!response.ok) {
    callbacks.onError(`Server error: ${response.status}`);
    callbacks.onDone();
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError("No response stream");
    callbacks.onDone();
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";
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
        if (line.startsWith(":")) continue;

        if (line.startsWith("event:")) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          const chunk = line.slice(5).trim();
          currentData = currentData ? currentData + "\n" + chunk : chunk;
        } else if (line === "") {
          if (currentEvent && currentData) {
            try {
              const parsed = JSON.parse(currentData);
              switch (currentEvent) {
                case "token":
                  callbacks.onToken(parsed.text);
                  break;
                case "action":
                  callbacks.onAction(parsed);
                  break;
                case "error":
                  callbacks.onError(parsed.message);
                  break;
                case "done":
                  break;
              }
            } catch {
              // Skip malformed JSON
            }
          }
          currentEvent = "";
          currentData = "";
        }
      }
    }

    // Flush remaining
    if (currentEvent && currentData) {
      try {
        const parsed = JSON.parse(currentData);
        if (currentEvent === "token") callbacks.onToken(parsed.text);
        else if (currentEvent === "action") callbacks.onAction(parsed);
        else if (currentEvent === "error") callbacks.onError(parsed.message);
      } catch {
        // Skip malformed JSON
      }
    }
  } finally {
    reader.releaseLock();
    callbacks.onDone();
  }
}

export async function fetchWorkspaces(): Promise<WorkspaceSummary[]> {
  const res = await fetch(`${API_URL}/api/workspaces`, {
    headers: { "x-session-id": getSessionId() },
  });
  if (!res.ok) throw new Error(`Server error: ${res.status}`);
  const data = await res.json();
  return data.workspaces;
}

export async function fetchChatHistory(workspaceId: string): Promise<ChatMessage[]> {
  const response = await fetch(`${API_URL}/api/workspace/${workspaceId}/chat`);
  if (!response.ok) {
    throw new Error(`Server error: ${response.status}`);
  }
  const data = await response.json();
  return data.messages;
}
