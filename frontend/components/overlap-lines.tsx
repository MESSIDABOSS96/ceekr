"use client";

import type { JournalOverlap } from "@/lib/types";
import { NODE_WIDTH, NODE_HEIGHT } from "./journal-node";

interface OverlapLinesProps {
  overlaps: JournalOverlap[];
  positions: Record<string, { x: number; y: number }>;
  scale: number;
  offsetX: number;
  offsetY: number;
  panX: number;
  panY: number;
  width: number;
  height: number;
}

export function OverlapLines({
  overlaps,
  positions,
  scale,
  offsetX,
  offsetY,
  panX,
  panY,
  width,
  height,
}: OverlapLinesProps) {
  if (!overlaps.length) return null;

  const toScreenCenter = (canvasX: number, canvasY: number) => ({
    x: canvasX * scale + offsetX + panX + (NODE_WIDTH * scale) / 2,
    y: canvasY * scale + offsetY + panY + (NODE_HEIGHT * scale) / 2,
  });

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      style={{ zIndex: 0 }}
      width={width}
      height={height}
    >
      {overlaps.map((overlap) => {
        const posA = positions[overlap.journal_a];
        const posB = positions[overlap.journal_b];
        if (!posA || !posB) return null;

        const a = toScreenCenter(posA.x, posA.y);
        const b = toScreenCenter(posB.x, posB.y);
        const thickness = Math.min(1 + overlap.shared_count * 0.5, 4);

        return (
          <line
            key={`${overlap.journal_a}-${overlap.journal_b}`}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke="rgba(255, 255, 255, 0.08)"
            strokeWidth={thickness}
            strokeDasharray="6 4"
          />
        );
      })}
    </svg>
  );
}
