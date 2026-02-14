import { BadgeCheck } from "lucide-react";
import type { RankedAccount } from "@/lib/types";

function formatCount(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 10_000) return `${Math.floor(count / 1_000)}K`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K`;
  return String(count);
}

interface ResultCardProps {
  account: RankedAccount;
}

export function ResultCard({ account: r }: ResultCardProps) {
  const pfpUrl = r.profile_image_url?.replace("_normal.", "_bigger.") || "";

  return (
    <a
      href={r.profile_url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block rounded-2xl border border-border-subtle bg-surface-card p-7 transition-transform hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(0,0,0,0.3)] focus-visible:outline-2 focus-visible:outline-twitter"
    >
      {/* Header */}
      <div className="mb-3 flex items-center gap-3.5">
        {pfpUrl && (
          <img
            src={pfpUrl}
            alt=""
            className="h-12 w-12 shrink-0 rounded-full object-cover"
          />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="truncate text-[1.05rem] font-bold text-text-primary">
              {r.name}
            </span>
            {r.verified && (
              <BadgeCheck className="h-[18px] w-[18px] shrink-0 text-twitter" />
            )}
          </div>
          <p className="text-[0.88rem] text-text-secondary">@{r.handle}</p>
        </div>
      </div>

      {/* Metadata */}
      <p className="mb-3 text-[0.82rem] text-text-muted">
        {formatCount(r.followers_count)} followers
        {r.location && <> &middot; {r.location}</>}
      </p>

      {/* Why relevant */}
      <p className="text-[0.88rem] leading-relaxed text-text-body">
        {r.why_relevant}
      </p>
    </a>
  );
}
