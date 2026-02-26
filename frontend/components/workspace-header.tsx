"use client";

import { useRouter } from "next/navigation";

export function WorkspaceHeader() {
  const router = useRouter();

  return (
    <button
      onClick={() => router.push("/")}
      className="absolute top-4 left-6 z-30 font-mono-display text-xl font-bold tracking-tight text-text-primary hover:opacity-70 transition-opacity cursor-pointer"
    >
      Ceekr
    </button>
  );
}
