"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { DotGridBackground } from "@/components/dot-grid-background";
import { WorkspaceView } from "@/components/workspace-view";
import { fetchWorkspace } from "@/lib/api";
import { loadOverlaps } from "@/lib/workspace-storage";
import type { WorkspaceData, JournalOverlap } from "@/lib/types";

type LoadState =
  | { status: "loading" }
  | { status: "not_found" }
  | { status: "loaded"; data: WorkspaceData; overlaps: JournalOverlap[] };

export default function WorkspacePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    fetchWorkspace(params.id)
      .then((data) => {
        const overlaps = data.overlaps?.length
          ? data.overlaps
          : loadOverlaps(params.id);
        setLoadState({ status: "loaded", data, overlaps });
      })
      .catch((err) => {
        if (err.message === "not_found") {
          setLoadState({ status: "not_found" });
        } else {
          setLoadState({ status: "not_found" });
        }
      });
  }, [params.id]);

  if (loadState.status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <DotGridBackground />
        <p className="text-sm text-text-muted animate-pulse">Loading workspace...</p>
      </div>
    );
  }

  if (loadState.status === "not_found") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center text-center">
        <DotGridBackground />
        <h1 className="font-mono-display text-[2rem] sm:text-[3rem] font-bold tracking-tight text-text-primary mb-4">
          Workspace not found
        </h1>
        <p className="text-text-muted mb-8">
          This workspace doesn&apos;t exist or has been deleted.
        </p>
        <button
          onClick={() => router.push("/")}
          className="rounded-lg bg-surface-card border border-border-subtle px-6 py-2.5 text-sm text-text-primary hover:bg-surface-card/80 transition-colors"
        >
          Start a new search
        </button>
      </div>
    );
  }

  return (
    <>
      <DotGridBackground magnify={false} />
      <WorkspaceView initialData={loadState.data} overlaps={loadState.overlaps} />
    </>
  );
}
