"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { SquarePen, Search, PanelLeftClose, PanelLeftOpen, User } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { fetchWorkspaces } from "@/lib/api";
import { groupByDate, relativeTime } from "@/lib/date-utils";
import { loadSidebarCollapsed, saveSidebarCollapsed } from "@/lib/sidebar-storage";
import type { WorkspaceSummary } from "@/lib/types";

interface SidebarProps {
  onNewSearch: () => void;
}

export function Sidebar({ onNewSearch }: SidebarProps) {
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(true);
  const [hydrated, setHydrated] = useState(false);
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchVisible, setSearchVisible] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Hydrate collapsed state from localStorage
  useEffect(() => {
    setCollapsed(loadSidebarCollapsed());
    setHydrated(true);
  }, []);

  // Fetch workspaces on mount
  useEffect(() => {
    fetchWorkspaces()
      .then(setWorkspaces)
      .catch(() => {});
  }, []);

  const expand = useCallback(() => {
    setCollapsed(false);
    saveSidebarCollapsed(false);
  }, []);

  const collapse = useCallback(() => {
    setCollapsed(true);
    saveSidebarCollapsed(true);
    setSearchVisible(false);
    setSearchQuery("");
  }, []);

  const toggleMobile = useCallback(() => {
    setMobileOpen((prev) => !prev);
  }, []);

  const openSearchExpanded = useCallback(() => {
    expand();
    setSearchVisible(true);
    setTimeout(() => searchInputRef.current?.focus(), 100);
  }, [expand]);

  // Filter workspaces by search query
  const filtered = searchQuery
    ? workspaces.filter((w) =>
        w.query.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : workspaces;

  const groups = groupByDate(filtered, (w) => w.created_at);

  // Don't render until hydrated to avoid flash
  if (!hydrated) return <div className="hidden md:block w-[54px] shrink-0" />;

  // ── Expanded sidebar content ──
  const expandedContent = (
    <>
      {/* Row 1: Moon logo + collapse button */}
      <div className="flex items-center justify-between p-2">
        <button
          onClick={() => router.push("/")}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg hover:bg-white/5 transition-colors"
          title="Home"
        >
          <img
            src="/moon-logo.png"
            alt="Ceekr"
            className="h-6 w-6 rounded-sm"
          />
        </button>
        <button
          onClick={
            mobileOpen
              ? () => setMobileOpen(false)
              : collapse
          }
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-text-secondary hover:bg-white/5 hover:text-text-primary transition-colors"
          title="Close sidebar"
        >
          <PanelLeftClose className="h-[18px] w-[18px]" />
        </button>
      </div>

      {/* Row 2: New search */}
      <div className="px-2">
        <button
          onClick={() => {
            onNewSearch();
            if (mobileOpen) setMobileOpen(false);
          }}
          className="flex h-9 w-full items-center gap-2 rounded-lg px-2 text-sm text-text-secondary hover:bg-white/5 hover:text-text-primary transition-colors"
        >
          <SquarePen className="h-[18px] w-[18px]" />
          New search
        </button>
      </div>

      {/* Row 3: Search workspaces */}
      <div className="px-2">
        {searchVisible ? (
          <div className="flex h-9 items-center gap-2 rounded-lg border border-border-subtle bg-white/5 px-2">
            <Search className="h-[18px] w-[18px] shrink-0 text-text-muted" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search workspaces..."
              className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted outline-none"
              onBlur={() => {
                if (!searchQuery) setSearchVisible(false);
              }}
              onKeyDown={(e) => {
                if (e.key === "Escape") {
                  setSearchQuery("");
                  setSearchVisible(false);
                }
              }}
            />
          </div>
        ) : (
          <button
            onClick={() => {
              setSearchVisible(true);
              setTimeout(() => searchInputRef.current?.focus(), 50);
            }}
            className="flex h-9 w-full items-center gap-2 rounded-lg px-2 text-sm text-text-secondary hover:bg-white/5 hover:text-text-primary transition-colors"
          >
            <Search className="h-[18px] w-[18px]" />
            Search workspaces
          </button>
        )}
      </div>

      {/* Separator */}
      <div className="mx-2 mt-1 border-t border-border-subtle" />

      {/* History list */}
      <ScrollArea className="flex-1 px-2 overflow-x-hidden">
        {groups.map(({ group, items }) => (
          <div key={group} className="mb-3 overflow-hidden">
            <p className="px-2 pb-1 pt-3 text-xs font-medium text-text-muted">
              {group}
            </p>
            {items.map((w) => (
              <button
                key={w.id}
                onClick={() => {
                  router.push(`/w/${w.id}`);
                  if (mobileOpen) setMobileOpen(false);
                }}
                className="block w-full rounded-lg px-2 py-1.5 text-left text-sm text-text-secondary hover:bg-white/5 hover:text-text-primary transition-colors truncate"
              >
                {w.query}
              </button>
            ))}
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="px-2 pt-4 text-xs text-text-muted">
            {searchQuery ? "No matches" : "No searches yet"}
          </p>
        )}
      </ScrollArea>

      {/* Separator */}
      <div className="mx-2 border-t border-border-subtle" />

      {/* Account section */}
      <div className="p-2">
        <div className="flex items-center gap-2 rounded-lg px-2 py-1.5">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white/10">
            <User className="h-3.5 w-3.5 text-text-secondary" />
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-sm text-text-primary truncate">Guest</span>
            <span className="text-xs text-text-muted">Sign in</span>
          </div>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className="hidden md:flex flex-col shrink-0 bg-surface-overlay border-r border-border-subtle overflow-hidden transition-[width] duration-200 ease-in-out relative z-20"
        style={{ width: collapsed ? 54 : 260 }}
      >
        {collapsed ? (
          /* ── Collapsed: vertical icon strip ── */
          <div className="flex flex-col items-center gap-1 pt-2">
            <button
              onClick={expand}
              className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-white/5 transition-colors group/logo"
              title="Open sidebar"
            >
              <img
                src="/moon-logo.png"
                alt="Ceekr"
                className="h-6 w-6 rounded-sm group-hover/logo:hidden"
              />
              <PanelLeftOpen className="h-[18px] w-[18px] text-text-secondary hidden group-hover/logo:block" />
            </button>
            <button
              onClick={onNewSearch}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary hover:bg-white/5 hover:text-text-primary transition-colors"
              title="New search"
            >
              <SquarePen className="h-[18px] w-[18px]" />
            </button>
            <button
              onClick={openSearchExpanded}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary hover:bg-white/5 hover:text-text-primary transition-colors"
              title="Search workspaces"
            >
              <Search className="h-[18px] w-[18px]" />
            </button>
          </div>
        ) : (
          expandedContent
        )}
      </aside>

      {/* Mobile toggle button — moon logo */}
      <button
        onClick={toggleMobile}
        className="fixed top-3 left-3 z-50 flex h-9 w-9 items-center justify-center rounded-lg hover:bg-white/5 transition-colors md:hidden"
        aria-label="Open sidebar"
      >
        <img
          src="/moon-logo.png"
          alt="Ceekr"
          className="h-6 w-6 rounded-sm"
        />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/40 md:hidden"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col bg-surface-overlay border-r border-border-subtle md:hidden">
            {expandedContent}
          </aside>
        </>
      )}
    </>
  );
}
