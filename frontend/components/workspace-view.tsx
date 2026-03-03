"use client";

import { useReducer, useRef, useEffect, useCallback, useState } from "react";
import { WorkspaceHeader } from "./workspace-header";
import { JournalNode } from "./journal-node";
import { OverlapLines } from "./overlap-lines";
import { ZoomControls } from "./zoom-controls";
import { JournalDetailPanel } from "./journal-detail-panel";
import { AgentPanel } from "./agent-panel";
import { fetchJournalPeople, fetchWorkspace, updateLayout } from "@/lib/api";
import type { WorkspaceData, JournalPerson, JournalOverlap, ChatAction } from "@/lib/types";

// ── State ──

interface WorkspaceState {
  data: WorkspaceData;
  positions: Record<string, { x: number; y: number }>;
  zoom: number;
  panX: number;
  panY: number;
  openJournalId: string | null;
  openJournalPeople: JournalPerson[] | null;
  journalLoading: boolean;
  chatOpen: boolean;
}

type Action =
  | { type: "OPEN_JOURNAL"; journalId: string }
  | { type: "JOURNAL_LOADED"; people: JournalPerson[] }
  | { type: "CLOSE_JOURNAL" }
  | { type: "MOVE_NODE"; journalId: string; x: number; y: number }
  | { type: "SET_ZOOM"; zoom: number }
  | { type: "PAN"; panX: number; panY: number }
  | { type: "TOGGLE_CHAT" }
  | { type: "UPDATE_DATA"; data: WorkspaceData };

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function reducer(state: WorkspaceState, action: Action): WorkspaceState {
  switch (action.type) {
    case "OPEN_JOURNAL":
      return {
        ...state,
        openJournalId: action.journalId,
        openJournalPeople: null,
        journalLoading: true,
      };
    case "JOURNAL_LOADED":
      return {
        ...state,
        openJournalPeople: action.people,
        journalLoading: false,
      };
    case "CLOSE_JOURNAL":
      return {
        ...state,
        openJournalId: null,
        openJournalPeople: null,
        journalLoading: false,
      };
    case "MOVE_NODE":
      return {
        ...state,
        positions: {
          ...state.positions,
          [action.journalId]: { x: action.x, y: action.y },
        },
      };
    case "SET_ZOOM":
      return { ...state, zoom: clamp(action.zoom, 0.5, 2.5) };
    case "PAN":
      return { ...state, panX: action.panX, panY: action.panY };
    case "TOGGLE_CHAT":
      return { ...state, chatOpen: !state.chatOpen };
    case "UPDATE_DATA":
      return { ...state, data: action.data };
    default:
      return state;
  }
}

function buildInitialState(data: WorkspaceData): WorkspaceState {
  const positions: Record<string, { x: number; y: number }> = {};
  for (const j of data.journals) {
    positions[j.id] = { x: j.canvas_x, y: j.canvas_y };
  }
  return {
    data,
    positions,
    zoom: 1.0,
    panX: 0,
    panY: 0,
    openJournalId: null,
    openJournalPeople: null,
    journalLoading: false,
    chatOpen: false,
  };
}

// ── Canvas math ──

const CANVAS_W = 1000;
const CANVAS_H = 800;

function useCanvasScaling(
  containerRef: React.RefObject<HTMLDivElement | null>,
  zoom: number,
) {
  const sizeRef = useRef({ width: 0, height: 0 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      sizeRef.current = { width, height };
    });
    obs.observe(el);
    // Initialize
    sizeRef.current = { width: el.clientWidth, height: el.clientHeight };
    return () => obs.disconnect();
  }, [containerRef]);

  const getScaling = useCallback(() => {
    const { width, height } = sizeRef.current;
    if (width === 0 || height === 0) return { scale: 1, offsetX: 0, offsetY: 0, width, height };
    const baseScale = Math.min(width / CANVAS_W, height / CANVAS_H) * 0.85;
    const scale = baseScale * zoom;
    const offsetX = (width - CANVAS_W * scale) / 2;
    const offsetY = (height - CANVAS_H * scale) / 2;
    return { scale, offsetX, offsetY, width, height };
  }, [zoom]);

  return getScaling;
}

// ── Component ──

interface WorkspaceViewProps {
  initialData: WorkspaceData;
  overlaps: JournalOverlap[];
}

export function WorkspaceView({ initialData, overlaps }: WorkspaceViewProps) {
  const [state, dispatch] = useReducer(reducer, initialData, buildInitialState);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const getScaling = useCanvasScaling(containerRef, state.zoom);
  const layoutTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Panning refs
  const isPanning = useRef(false);
  const panStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });
  const panRef = useRef({ panX: 0, panY: 0 });

  // Force a re-render when container resizes so nodes reposition
  const renderKey = useRef(0);
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver(() => {
      renderKey.current++;
      // Trigger re-render by dispatching a no-op zoom
      dispatch({ type: "SET_ZOOM", zoom: state.zoom });
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, [state.zoom]);

  // Keep panRef in sync for wheel handler
  useEffect(() => {
    panRef.current = { panX: state.panX, panY: state.panY };
  }, [state.panX, state.panY]);

  // Wheel: pinch-to-zoom or scroll-to-pan
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (e.ctrlKey) {
        // Pinch-to-zoom
        const delta = e.deltaY > 0 ? -0.05 : 0.05;
        dispatch({ type: "SET_ZOOM", zoom: state.zoom + delta });
      } else {
        // Regular scroll → pan
        dispatch({
          type: "PAN",
          panX: panRef.current.panX - e.deltaX,
          panY: panRef.current.panY - e.deltaY,
        });
      }
    };
    el.addEventListener("wheel", handleWheel, { passive: false });
    return () => el.removeEventListener("wheel", handleWheel);
  }, [state.zoom]);

  // Canvas panning handlers
  const handleCanvasPointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (e.target !== e.currentTarget || e.button !== 0) return;
      isPanning.current = true;
      panStart.current = {
        x: e.clientX,
        y: e.clientY,
        panX: state.panX,
        panY: state.panY,
      };
      e.currentTarget.setPointerCapture(e.pointerId);
    },
    [state.panX, state.panY],
  );

  const handleCanvasPointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!isPanning.current) return;
      const dx = e.clientX - panStart.current.x;
      const dy = e.clientY - panStart.current.y;
      dispatch({
        type: "PAN",
        panX: panStart.current.panX + dx,
        panY: panStart.current.panY + dy,
      });
    },
    [],
  );

  const handleCanvasPointerUp = useCallback(() => {
    isPanning.current = false;
  }, []);

  // Open journal
  const handleOpenJournal = useCallback(
    (journalId: string) => {
      dispatch({ type: "OPEN_JOURNAL", journalId });
      fetchJournalPeople(state.data.workspace_id, journalId)
        .then((people) => dispatch({ type: "JOURNAL_LOADED", people }))
        .catch(() => dispatch({ type: "JOURNAL_LOADED", people: [] }));
    },
    [state.data.workspace_id],
  );

  // Drag end → convert screen position back to canvas coords, persist
  const handleDragEnd = useCallback(
    (journalId: string, screenX: number, screenY: number) => {
      const { scale, offsetX, offsetY } = getScaling();
      const canvasX = (screenX - offsetX - state.panX) / scale;
      const canvasY = (screenY - offsetY - state.panY) / scale;
      dispatch({ type: "MOVE_NODE", journalId, x: canvasX, y: canvasY });

      // Debounced save
      if (layoutTimerRef.current) clearTimeout(layoutTimerRef.current);
      layoutTimerRef.current = setTimeout(() => {
        // Gather all current positions
        const positionsToSave = Object.entries({
          ...state.positions,
          [journalId]: { x: canvasX, y: canvasY },
        }).map(([id, pos]) => ({
          journal_id: id,
          canvas_x: pos.x,
          canvas_y: pos.y,
        }));
        updateLayout(state.data.workspace_id, positionsToSave);
      }, 500);
    },
    [getScaling, state.data.workspace_id, state.positions, state.panX, state.panY],
  );

  const { scale, offsetX, offsetY, width, height } = getScaling();

  const openJournal = state.openJournalId
    ? state.data.journals.find((j) => j.id === state.openJournalId) ?? null
    : null;

  // Handle agent chat actions
  const handleChatAction = useCallback(
    async (action: ChatAction) => {
      switch (action.type) {
        case "remove_profiles":
          // TODO: Remove people from workspace state when backend supports it
          break;
        case "apply_filters":
          // TODO: Apply filter state when filter UI exists on workspace
          break;
        case "run_targeted_search":
        case "regroup_journals":
          // Reload workspace data from backend to get updated state
          try {
            const updated = await fetchWorkspace(state.data.workspace_id);
            dispatch({ type: "UPDATE_DATA", data: updated });
            // Update positions for any new journals
            for (const j of updated.journals) {
              if (!state.positions[j.id]) {
                dispatch({ type: "MOVE_NODE", journalId: j.id, x: j.canvas_x, y: j.canvas_y });
              }
            }
          } catch {
            // Ignore reload errors
          }
          break;
      }
    },
    [state.data.workspace_id, state.positions],
  );

  return (
    <div className="h-screen w-full relative">
      <WorkspaceHeader
        query={state.data.query}
        summary={state.data.summary}
        journalCount={state.data.journals.length}
        totalPeople={state.data.total_people}
      />

      {/* Agent panel */}
      <AgentPanel
        workspaceId={state.data.workspace_id}
        workspaceQuery={state.data.query}
        workspaceSummary={state.data.summary}
        journals={state.data.journals}
        totalPeople={state.data.total_people}
        activeJournalId={state.openJournalId}
        isOpen={state.chatOpen}
        onToggle={() => dispatch({ type: "TOGGLE_CHAT" })}
        onAction={handleChatAction}
      />

      {/* Canvas container — shifts right when agent panel is open */}
      <div
        ref={containerRef}
        className="absolute inset-0 overflow-hidden cursor-grab transition-[left] duration-300"
        style={{ left: state.chatOpen ? 380 : 0 }}
        onPointerDown={handleCanvasPointerDown}
        onPointerMove={handleCanvasPointerMove}
        onPointerUp={handleCanvasPointerUp}
      >
        {/* Overlap lines */}
        <OverlapLines
          overlaps={overlaps}
          positions={state.positions}
          scale={scale}
          offsetX={offsetX}
          offsetY={offsetY}
          panX={state.panX}
          panY={state.panY}
          width={width}
          height={height}
        />

        {/* Journal nodes */}
        {state.data.journals.map((journal) => {
          const pos = state.positions[journal.id];
          if (!pos) return null;
          const sx = pos.x * scale + offsetX + state.panX;
          const sy = pos.y * scale + offsetY + state.panY;

          return (
            <JournalNode
              key={journal.id}
              journal={journal}
              screenX={sx}
              screenY={sy}
              scale={scale}
              isOpen={state.openJournalId === journal.id}
              onOpen={() => handleOpenJournal(journal.id)}
              onDragEnd={(newSX, newSY) => handleDragEnd(journal.id, newSX, newSY)}
            />
          );
        })}

        {/* Zoom controls */}
        <ZoomControls
          onZoomIn={() => dispatch({ type: "SET_ZOOM", zoom: state.zoom + 0.1 })}
          onZoomOut={() => dispatch({ type: "SET_ZOOM", zoom: state.zoom - 0.1 })}
        />
      </div>

      {/* Journal detail panel */}
      <JournalDetailPanel
        journal={openJournal}
        people={state.openJournalPeople}
        loading={state.journalLoading}
        onClose={() => dispatch({ type: "CLOSE_JOURNAL" })}
      />
    </div>
  );
}
