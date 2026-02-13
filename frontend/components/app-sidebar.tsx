"use client";

import { BarChart3, History, Search, MoreVertical } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/lib/auth-context";

interface NavItem {
  label: string;
  icon: React.ReactNode;
  active?: boolean;
}

const navItems: NavItem[] = [
  { label: "Search", icon: <Search className="h-5 w-5" />, active: true },
  { label: "Previous Searches", icon: <History className="h-5 w-5" /> },
  { label: "Scoring", icon: <BarChart3 className="h-5 w-5" /> },
];

export function AppSidebar() {
  const { user, logout } = useAuth();

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-border-subtle bg-surface">
      {/* Brand */}
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-border-subtle">
          <span className="text-sm font-bold text-text-primary">C</span>
        </div>
        <span className="text-[0.95rem] font-semibold text-text-primary">
          Ceekr
        </span>
      </div>

      <Separator className="bg-border-subtle" />

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-0.5">
          {navItems.map((item) => (
            <li key={item.label}>
              <button
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-[0.88rem] transition-colors ${
                  item.active
                    ? "bg-white/[0.08] text-text-primary"
                    : "text-text-secondary hover:bg-white/[0.05] hover:text-text-primary"
                }`}
              >
                <span className="shrink-0 text-text-muted">
                  {item.icon}
                </span>
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {/* Account */}
      <div className="border-t border-border-subtle px-4 py-3">
        {user ? (
          <div className="flex items-center gap-3">
            {user.profile_image_url ? (
              <img
                src={user.profile_image_url}
                alt=""
                className="h-9 w-9 shrink-0 rounded-full object-cover"
              />
            ) : (
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/10 text-sm font-medium text-text-primary">
                {user.name.charAt(0).toUpperCase()}
              </div>
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-[0.85rem] font-medium text-text-primary">
                {user.name}
              </p>
              <p className="truncate text-[0.78rem] text-text-muted">
                @{user.handle}
              </p>
            </div>
            <button
              onClick={logout}
              className="shrink-0 rounded-md p-1 text-text-muted transition-colors hover:text-text-secondary"
            >
              <MoreVertical className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/10 text-sm font-medium text-text-primary">
              U
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[0.85rem] font-medium text-text-primary">
                Guest
              </p>
              <p className="truncate text-[0.78rem] text-text-muted">
                Not signed in
              </p>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
