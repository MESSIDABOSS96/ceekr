"use client";

import { Minus, Plus } from "lucide-react";

interface ZoomControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
}

export function ZoomControls({ onZoomIn, onZoomOut }: ZoomControlsProps) {
  return (
    <div className="absolute bottom-4 right-4 z-20 flex items-center gap-1 rounded-lg border border-border-subtle bg-surface-card px-1 py-1">
      <button
        onClick={onZoomOut}
        className="rounded p-1.5 text-text-secondary hover:text-text-primary hover:bg-white/5 transition-colors"
        title="Zoom out"
      >
        <Minus className="h-3.5 w-3.5" />
      </button>
      <button
        onClick={onZoomIn}
        className="rounded p-1.5 text-text-secondary hover:text-text-primary hover:bg-white/5 transition-colors"
        title="Zoom in"
      >
        <Plus className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
