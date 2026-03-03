"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { SearchPage } from "@/components/search-page";
import { Sidebar } from "@/components/sidebar";
import { DotGridBackground } from "@/components/dot-grid-background";
import { FloatingAstronauts } from "@/components/floating-astronauts";
import { saveOverlaps } from "@/lib/workspace-storage";
import type { WorkspaceData } from "@/lib/types";

export default function Home() {
  const router = useRouter();
  const [searchKey, setSearchKey] = useState(0);

  const handleWorkspaceCreated = useCallback(
    (data: WorkspaceData) => {
      if (data.overlaps?.length) {
        saveOverlaps(data.workspace_id, data.overlaps);
      }
      router.push(`/w/${data.workspace_id}`);
    },
    [router],
  );

  const handleNewSearch = useCallback(() => {
    setSearchKey((k) => k + 1);
  }, []);

  return (
    <div className="flex min-h-screen">
      <Sidebar onNewSearch={handleNewSearch} />
      <div className="flex-1 min-w-0">
        <DotGridBackground />
        <FloatingAstronauts />
        <div className="mx-auto max-w-[1040px] px-4">
          <SearchPage
            key={searchKey}
            onWorkspaceCreated={handleWorkspaceCreated}
          />
        </div>
      </div>
    </div>
  );
}
