"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Upload } from "lucide-react";
import { ShareDialog } from "./share-dialog";

interface WorkspaceHeaderProps {
  query: string;
  summary: string;
  journalCount: number;
  totalPeople: number;
}

export function WorkspaceHeader({
  query,
  summary,
  journalCount,
  totalPeople,
}: WorkspaceHeaderProps) {
  const router = useRouter();
  const [shareOpen, setShareOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => router.push("/")}
        className="absolute top-4 left-6 z-30 font-mono-display text-xl font-bold tracking-tight text-text-primary hover:opacity-70 transition-opacity cursor-pointer"
      >
        Ceekr
      </button>

      <button
        onClick={() => setShareOpen(true)}
        className="absolute top-4 right-6 z-30 flex items-center gap-1.5 rounded-lg border border-border-subtle bg-surface-card px-3 py-1.5 text-sm text-text-secondary hover:text-text-primary hover:bg-white/5 transition-colors cursor-pointer"
      >
        <Upload className="h-4 w-4" />
        Share
      </button>

      <ShareDialog
        open={shareOpen}
        onOpenChange={setShareOpen}
        query={query}
        summary={summary}
        journalCount={journalCount}
        peopleCount={totalPeople}
      />
    </>
  );
}
