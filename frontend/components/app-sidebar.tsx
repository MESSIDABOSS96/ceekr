"use client";

import {
  Home,
  BarChart3,
  FolderOpen,
  Users,
  Zap,
  Database,
  FileText,
  BookOpen,
  MoreHorizontal,
  Settings,
  HelpCircle,
  Search,
  MoreVertical,
} from "lucide-react";
import { Separator } from "@/components/ui/separator";

interface NavItem {
  label: string;
  icon: React.ReactNode;
  active?: boolean;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    title: "Home",
    items: [
      { label: "Dashboard", icon: <Home className="h-5 w-5" />, active: true },
      { label: "Lifecycle", icon: <BarChart3 className="h-5 w-5" /> },
      { label: "Analytics", icon: <Zap className="h-5 w-5" /> },
      { label: "Projects", icon: <FolderOpen className="h-5 w-5" /> },
      { label: "Team", icon: <Users className="h-5 w-5" /> },
    ],
  },
  {
    title: "Documents",
    items: [
      { label: "Data Library", icon: <Database className="h-5 w-5" /> },
      { label: "Reports", icon: <FileText className="h-5 w-5" /> },
      { label: "Word Assistant", icon: <BookOpen className="h-5 w-5" /> },
      { label: "More", icon: <MoreHorizontal className="h-5 w-5" /> },
    ],
  },
];

const bottomItems: NavItem[] = [
  { label: "Settings", icon: <Settings className="h-5 w-5" /> },
  { label: "Get Help", icon: <HelpCircle className="h-5 w-5" /> },
  { label: "Search", icon: <Search className="h-5 w-5" /> },
];

export function AppSidebar() {
  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-border-subtle bg-surface">
      {/* Brand */}
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-border-subtle">
          <span className="text-sm font-bold text-text-primary">A</span>
        </div>
        <span className="text-[0.95rem] font-semibold text-text-primary">
          Acme Inc.
        </span>
      </div>

      <Separator className="bg-border-subtle" />

      {/* Navigation groups */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {navGroups.map((group, gi) => (
          <div key={group.title} className={gi > 0 ? "mt-6" : ""}>
            <p className="mb-2 px-3 text-[0.75rem] font-medium uppercase tracking-wider text-text-muted">
              {group.title}
            </p>
            <ul className="space-y-0.5">
              {group.items.map((item) => (
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
          </div>
        ))}
      </nav>

      {/* Bottom section */}
      <div className="px-3 pb-2">
        <Separator className="mb-3 bg-border-subtle" />
        <ul className="space-y-0.5">
          {bottomItems.map((item) => (
            <li key={item.label}>
              <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-[0.88rem] text-text-secondary transition-colors hover:bg-white/[0.05] hover:text-text-primary">
                <span className="shrink-0 text-text-muted">{item.icon}</span>
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Account */}
      <div className="border-t border-border-subtle px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/10 text-sm font-medium text-text-primary">
            U
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[0.85rem] font-medium text-text-primary">
              shadcn
            </p>
            <p className="truncate text-[0.78rem] text-text-muted">
              m@example.com
            </p>
          </div>
          <button className="shrink-0 rounded-md p-1 text-text-muted transition-colors hover:text-text-secondary">
            <MoreVertical className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
