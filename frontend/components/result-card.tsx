"use client";

import { BadgeCheck } from "lucide-react";
import type { RankedAccount } from "@/lib/types";
import { TweetCard } from "./tweet-card";

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

  const highlightedTweets = r.highlight_tweet_indices
    ?.map((i) => r.recent_tweets[i])
    .filter(Boolean)
    .filter((t, i, arr) => arr.findIndex((x) => x.id === t.id) === i)
    .slice(0, 3);

  return (
    <a
      href={r.profile_url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block rounded-2xl border border-border-subtle bg-surface-card p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-white/12 hover:shadow-[0_8px_24px_rgba(0,0,0,0.3)] focus-visible:outline-2 focus-visible:outline-twitter"
    >
      {/* Header row: avatar + info */}
      <div className="flex items-start gap-3">
        {pfpUrl ? (
          <img
            src={pfpUrl}
            alt=""
            className="h-14 w-14 shrink-0 rounded-full object-cover"
          />
        ) : (
          <div className="h-14 w-14 shrink-0 rounded-full bg-zinc-700" />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="truncate text-[0.95rem] font-bold text-text-primary leading-tight">
              {r.name}
            </span>
            {r.verified && (
              <BadgeCheck className="h-[18px] w-[18px] shrink-0 text-twitter" />
            )}
          </div>
          <span className="block truncate text-[0.88rem] text-text-secondary">
            @{r.handle}
          </span>
          <div className="mt-1 flex items-center gap-1.5 text-[0.82rem]">
            <span className="font-semibold text-text-primary">
              {formatCount(r.followers_count)}
            </span>
            <span className="text-text-primary">followers</span>
            {r.location && (
              <>
                <span className="text-text-muted">&middot;</span>
                <span className="text-text-primary truncate">{r.location}</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Summary as primary text */}
      {(r.summary || r.why_relevant) && (
        <p className="mt-4 text-[0.85rem] leading-relaxed text-text-body">
          {r.summary || r.why_relevant}
        </p>
      )}

      {/* Highlighted tweets as horizontal card row */}
      {highlightedTweets && highlightedTweets.length > 0 && (
        <div className="mt-4 flex gap-3 overflow-x-auto scrollbar-on-hover">
          {highlightedTweets.map((tweet) => (
            <TweetCard
              key={tweet.id}
              tweet={tweet}
              handle={r.handle}
              displayName={r.name}
              profileImageUrl={r.profile_image_url}
              verified={r.verified}
            />
          ))}
        </div>
      )}
    </a>
  );
}
