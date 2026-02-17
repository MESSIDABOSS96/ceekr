"use client";

import { useState } from "react";
import { ResultCard } from "@/components/result-card";
import { MOCK_ACCOUNTS } from "../mock-data";

type Layout = "column" | "grid-2" | "grid-3";

export default function LayoutComparePage() {
  const [layout, setLayout] = useState<Layout>("column");

  return (
    <div className="min-h-screen bg-background pb-16">
      <div className="px-4">
        <div className="flex flex-col items-center pt-10 pb-6">
          <h1 className="font-mono-display text-2xl font-bold text-text-primary">
            Layout Comparison
          </h1>
          <p className="mt-2 text-sm text-text-muted">
            Compare column vs grid layout for result cards
          </p>
        </div>

        <div className="flex justify-center pb-8">
          <div className="inline-flex rounded-lg border border-border-primary bg-bg-secondary p-1">
            <button
              onClick={() => setLayout("column")}
              className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
                layout === "column"
                  ? "bg-bg-primary text-text-primary shadow-sm"
                  : "text-text-muted hover:text-text-secondary"
              }`}
            >
              Column
            </button>
            <button
              onClick={() => setLayout("grid-2")}
              className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
                layout === "grid-2"
                  ? "bg-bg-primary text-text-primary shadow-sm"
                  : "text-text-muted hover:text-text-secondary"
              }`}
            >
              2-Col Grid
            </button>
            <button
              onClick={() => setLayout("grid-3")}
              className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
                layout === "grid-3"
                  ? "bg-bg-primary text-text-primary shadow-sm"
                  : "text-text-muted hover:text-text-secondary"
              }`}
            >
              3-Col Grid
            </button>
          </div>
        </div>

        <div
          className={
            layout === "column"
              ? "mx-auto max-w-2xl space-y-4"
              : "grid gap-4 justify-center"
          }
          style={
            layout === "grid-2"
              ? { gridTemplateColumns: "repeat(2, 504px)" }
              : layout === "grid-3"
                ? { gridTemplateColumns: "repeat(3, 400px)" }
                : undefined
          }
        >
          {MOCK_ACCOUNTS.map((account) => (
            <ResultCard key={account.user_id} account={account} />
          ))}
        </div>
      </div>
    </div>
  );
}
