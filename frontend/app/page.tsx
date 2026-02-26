"use client";

import { useRouter } from "next/navigation";
import { SearchPage } from "@/components/search-page";
import { DotGridBackground } from "@/components/dot-grid-background";
import { FloatingAstronauts } from "@/components/floating-astronauts";
import { saveOverlaps } from "@/lib/workspace-storage";
import type { WorkspaceData } from "@/lib/types";

export default function Home() {
  const router = useRouter();

  const handleWorkspaceCreated = (data: WorkspaceData) => {
    if (data.overlaps?.length) {
      saveOverlaps(data.workspace_id, data.overlaps);
    }
    router.push(`/w/${data.workspace_id}`);
  };

  return (
    <div className="mx-auto max-w-[1040px] px-4">
      <DotGridBackground />
      <FloatingAstronauts />
      <SearchPage onWorkspaceCreated={handleWorkspaceCreated} />
    </div>
  );
}
