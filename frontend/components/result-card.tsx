import { BadgeCheck } from "lucide-react";
import type { RankedAccount } from "@/lib/types";

function formatCount(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 10_000) return `${Math.floor(count / 1_000)}K`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K`;
  return String(count);
}

const BUCKET_STYLES: Record<string, { label: string; className: string }> = {
  top_match: {
    label: "Top Match",
    className: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  },
  strong_match: {
    label: "Strong Match",
    className: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  },
  good_match: {
    label: "Good Match",
    className: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
  },
};

interface ResultCardProps {
  account: RankedAccount;
}

export function ResultCard({ account: r }: ResultCardProps) {
  const pfpUrl = r.profile_image_url?.replace("_normal.", "_bigger.") || "";
  const bucketStyle = BUCKET_STYLES[r.bucket] || BUCKET_STYLES.good_match;

  // Get highlighted tweets
  const highlightedTweets = r.highlight_tweet_indices
    ?.map((i) => r.recent_tweets[i])
    .filter(Boolean)
    .slice(0, 2);

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
        <span
          className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[0.72rem] font-medium ${bucketStyle.className}`}
        >
          {bucketStyle.label}
        </span>
      </div>

      {/* Metadata */}
      <p className="mb-3 text-[0.82rem] text-text-muted">
        {formatCount(r.followers_count)} followers
        {r.location && <> &middot; {r.location}</>}
      </p>

      {/* Summary / Why relevant */}
      <p className="text-[0.88rem] leading-relaxed text-text-body">
        {r.summary || r.why_relevant}
      </p>

      {/* Highlighted tweets */}
      {highlightedTweets && highlightedTweets.length > 0 && (
        <div className="mt-3 space-y-2">
          {highlightedTweets.map((tweet) => (
            <div
              key={tweet.id}
              className="rounded-lg border border-border-subtle bg-surface-overlay px-3 py-2 text-[0.82rem] text-text-secondary"
            >
              <p className="line-clamp-3">{tweet.text}</p>
            </div>
          ))}
        </div>
      )}
    </a>
  );
}
