"use client";

import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import { AppSidebar } from "./app-sidebar";

export function AuthGate({ children }: { children: ReactNode }) {
  const { status, authError, login } = useAuth();

  // Loading
  if (status === "loading") {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-text-muted border-t-transparent" />
      </div>
    );
  }

  // OAuth not configured on server
  if (status === "oauth_not_configured") {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="max-w-sm rounded-xl border border-border-subtle bg-surface-card p-6 text-center">
          <h2 className="mb-2 text-lg font-semibold text-text-primary">
            OAuth Not Configured
          </h2>
          <p className="text-sm text-text-secondary">
            Twitter OAuth is not configured on the server. Set{" "}
            <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs">
              TWITTER_CLIENT_ID
            </code>{" "}
            and{" "}
            <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs">
              TWITTER_CLIENT_SECRET
            </code>{" "}
            in your <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs">.env</code> file.
          </p>
        </div>
      </div>
    );
  }

  // Not logged in
  if (status === "unauthenticated") {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-6">
        <div className="text-center">
          <h1 className="mb-2 text-3xl font-bold tracking-tight text-text-primary">
            Twitter Account Finder
          </h1>
          <p className="text-sm text-text-secondary">
            Sign in to search and discover relevant Twitter accounts.
          </p>
        </div>

        {authError && (
          <div className="max-w-sm rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-400">
            {authError}
          </div>
        )}

        <button
          onClick={login}
          className="flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-medium text-black transition-opacity hover:opacity-80"
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
            <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
          </svg>
          Sign in with X
        </button>
      </div>
    );
  }

  // Authenticated — render full app shell
  return (
    <div className="flex h-screen overflow-hidden">
      <AppSidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[760px] px-4">{children}</div>
      </main>
    </div>
  );
}
