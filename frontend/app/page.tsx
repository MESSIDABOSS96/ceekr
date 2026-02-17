"use client";

import { useRouter } from "next/navigation";
import { SearchPage } from "@/components/search-page";
import type { SearchCompletePayload } from "@/components/search-page";
import { generateId } from "@/lib/nanoid";
import { saveSearch } from "@/lib/search-storage";

export default function Home() {
  const router = useRouter();

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
    router.replace(`/s/${id}`);
  };

  return <SearchPage onSearchComplete={handleSearchComplete} />;
}
