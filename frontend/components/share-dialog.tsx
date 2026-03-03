"use client";

import { useState } from "react";
import { Link } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface ShareDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  query: string;
  summary: string;
  journalCount: number;
  peopleCount: number;
}

export function ShareDialog({
  open,
  onOpenChange,
  query,
  summary,
  journalCount,
  peopleCount,
}: ShareDialogProps) {
  const [copied, setCopied] = useState(false);

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleShareX = () => {
    const url = window.location.href;
    const text = `Check out this workspace: "${query}"`;
    window.open(
      `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`,
      "_blank",
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-surface-card border-border-subtle sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-text-primary">
            Share this workspace
          </DialogTitle>
        </DialogHeader>

        {/* Preview card */}
        <div className="bg-surface rounded-xl border border-border-subtle p-4">
          <p className="text-sm font-medium text-text-primary line-clamp-2">
            &ldquo;{query}&rdquo;
          </p>
          {summary && (
            <p className="mt-1 text-xs text-text-secondary line-clamp-2">
              {summary}
            </p>
          )}
          <p className="mt-2 text-xs text-text-muted">
            {journalCount} {journalCount === 1 ? "group" : "groups"} &middot;{" "}
            {peopleCount} {peopleCount === 1 ? "person" : "people"}
          </p>
        </div>

        {/* Share buttons */}
        <div className="flex items-center justify-center gap-8 pt-2">
          <div className="flex flex-col items-center gap-2">
            <button
              onClick={handleCopyLink}
              className="flex h-12 w-12 items-center justify-center rounded-full bg-white/10 text-text-primary hover:bg-white/15 transition-colors"
            >
              <Link className="h-5 w-5" />
            </button>
            <span className="text-xs text-text-secondary">
              {copied ? "Link copied!" : "Copy link"}
            </span>
          </div>

          <div className="flex flex-col items-center gap-2">
            <button
              onClick={handleShareX}
              className="flex h-12 w-12 items-center justify-center rounded-full bg-white/10 text-text-primary hover:bg-white/15 transition-colors"
            >
              <svg
                viewBox="0 0 24 24"
                className="h-5 w-5 fill-current"
                aria-label="X"
              >
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
            </button>
            <span className="text-xs text-text-secondary">Share on X</span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
