"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { SearchPage } from "@/components/search-page";
import type { SearchCompletePayload, InitialSearchState } from "@/components/search-page";
import { DotGridBackground } from "@/components/dot-grid-background";
import { FloatingAstronauts } from "@/components/floating-astronauts";
import { generateId } from "@/lib/nanoid";
import { loadSearch, saveSearch } from "@/lib/search-storage";

type LoadState =
  | { status: "loading" }
  | { status: "not_found" }
  | { status: "loaded"; data: InitialSearchState };

export default function SearchResultPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    const saved = loadSearch(params.id);
    if (!saved) {
      setLoadState({ status: "not_found" });
      return;
    }
    setLoadState({
      status: "loaded",
      data: {
        query: saved.query,
        results: saved.results,
        quality: saved.quality,
        refinementQuestions: saved.refinementQuestions,
        queries: saved.queries,
      },
    });
  }, [params.id]);

  const handleSearchComplete = (payload: SearchCompletePayload) => {
    const id = generateId();
    saveSearch({
      id,
      query: payload.query,
      results: payload.results,
      quality: payload.quality,
      refinementQuestions: payload.refinementQuestions,
      queries: payload.queries,
      createdAt: Date.now(),
    });
    router.push(`/s/${id}`);
  };

  const handleReset = () => {
    router.push("/");
  };

  if (loadState.status === "loading") {
    return null;
  }

  if (loadState.status === "not_found") {
    return (
      <div className="mx-auto max-w-[1040px] px-4">
        <DotGridBackground />
        <FloatingAstronauts />
        <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
          <h1 className="font-mono-display text-[2rem] sm:text-[3rem] font-bold tracking-tight text-text-primary mb-4">
            Results expired
          </h1>
          <p className="text-text-muted mb-8">
            This search has expired or doesn&apos;t exist in this browser.
          </p>
          <button
            onClick={() => router.push("/")}
            className="rounded-lg bg-surface-card border border-border-subtle px-6 py-2.5 text-sm text-text-primary hover:bg-surface-card/80 transition-colors"
          >
            Start a new search
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1040px] px-4">
      <DotGridBackground />
      <FloatingAstronauts />
      <SearchPage
        initialState={loadState.data}
        onSearchComplete={handleSearchComplete}
        onReset={handleReset}
      />
    </div>
  );
}
