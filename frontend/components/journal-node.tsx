"use client";

import { useRef, useCallback } from "react";
import type { WorkspaceJournal } from "@/lib/types";

export const NODE_WIDTH = 200;
export const NODE_HEIGHT = 100;

interface JournalNodeProps {
  journal: WorkspaceJournal;
  screenX: number;
  screenY: number;
  scale: number;
  isOpen: boolean;
  onOpen: () => void;
  onDragEnd: (screenX: number, screenY: number) => void;
}

export function JournalNode({
  journal,
  screenX,
  screenY,
  scale,
  isOpen,
  onOpen,
  onDragEnd,
}: JournalNodeProps) {
  const isDragging = useRef(false);
  const hasMoved = useRef(false);
  const startPos = useRef({ x: 0, y: 0 });
  const currentPos = useRef({ x: screenX, y: screenY });
  const clampedPos = useRef({ x: screenX, y: screenY });
  const nodeRef = useRef<HTMLDivElement>(null);

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (e.button !== 0) return;
      e.preventDefault();
      isDragging.current = true;
      hasMoved.current = false;
      startPos.current = { x: e.clientX, y: e.clientY };
      currentPos.current = { x: screenX, y: screenY };
      clampedPos.current = { x: screenX, y: screenY };
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [screenX, screenY],
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!isDragging.current) return;
      const dx = e.clientX - startPos.current.x;
      const dy = e.clientY - startPos.current.y;

      if (!hasMoved.current && Math.abs(dx) + Math.abs(dy) < 4) return;
      hasMoved.current = true;

      const rawX = currentPos.current.x + dx;
      const rawY = currentPos.current.y + dy;
      const nodeWidth = NODE_WIDTH * scale;
      const nodeHeight = NODE_HEIGHT * scale;
      const newX = Math.max(0, Math.min(rawX, window.innerWidth - nodeWidth));
      const newY = Math.max(0, Math.min(rawY, window.innerHeight - nodeHeight));

      clampedPos.current = { x: newX, y: newY };

      if (nodeRef.current) {
        nodeRef.current.style.left = `${newX}px`;
        nodeRef.current.style.top = `${newY}px`;
      }
    },
    [scale],
  );

  const handlePointerUp = useCallback(
    () => {
      if (!isDragging.current) return;
      isDragging.current = false;

      if (hasMoved.current) {
        onDragEnd(clampedPos.current.x, clampedPos.current.y);
      } else {
        onOpen();
      }
    },
    [onOpen, onDragEnd],
  );

  const titleOpacity = scale < 0.45 ? 0 : scale < 0.55 ? (scale - 0.45) / 0.1 : 1;

  return (
    <div
      ref={nodeRef}
      className={`absolute select-none cursor-grab active:cursor-grabbing transition-shadow duration-150 ${
        isOpen ? "ring-2 ring-white/20 shadow-2xl z-30" : "z-10 hover:shadow-xl"
      }`}
      style={{
        left: screenX,
        top: screenY,
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
        transform: `scale(${scale})`,
        transformOrigin: "top left",
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
    >
      <div
        className="h-full rounded-xl border border-border-subtle bg-surface-card overflow-hidden flex flex-col"
        style={{ borderLeftWidth: 3, borderLeftColor: journal.color }}
      >
        <div className="flex-1 min-h-0 px-3 py-2.5 flex flex-col gap-1">
          <p
            className="font-semibold text-text-primary line-clamp-2 leading-tight text-[13px]"
            style={{ opacity: titleOpacity, transition: "opacity 150ms" }}
          >
            {journal.label}
          </p>
          <div className="mt-auto flex items-center gap-2">
            <span
              className="inline-flex items-center rounded-full px-2 py-0.5 font-medium"
              style={{
                backgroundColor: journal.color + "18",
                color: journal.color,
              }}
            >
              {journal.people_count}
            </span>
            <span
              className="text-text-muted capitalize truncate text-[10px]"
            >
              {(journal.theme || "").replace("_", " ")}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
