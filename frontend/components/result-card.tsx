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

  let highlightedTweets = r.highlight_tweet_indices
    ?.map((i) => r.recent_tweets[i])
    .filter(Boolean)
    .filter((t, i, arr) => arr.findIndex((x) => x.id === t.id) === i)
    .slice(0, 3);

  // Fallback: show the most popular tweet if none were highlighted
  if ((!highlightedTweets || highlightedTweets.length === 0) && r.recent_tweets?.length > 0) {
    const best = [...r.recent_tweets].sort(
      (a, b) => (b.like_count + b.retweet_count) - (a.like_count + a.retweet_count)
    )[0];
    highlightedTweets = [best];
  }

  return (
    <a
      href={r.profile_url}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex flex-col rounded-2xl border border-border-subtle bg-surface-card p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-white/12 hover:shadow-[0_8px_24px_rgba(0,0,0,0.3)] focus-visible:outline-2 focus-visible:outline-twitter"
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
                <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 shrink-0 text-text-muted" fill="currentColor">
                  <path d="M12 7c-1.93 0-3.5 1.57-3.5 3.5S10.07 14 12 14s3.5-1.57 3.5-3.5S13.93 7 12 7zm0 5c-.827 0-1.5-.673-1.5-1.5S11.173 9 12 9s1.5.673 1.5 1.5S12.827 12 12 12zm0-10c-4.687 0-8.5 3.813-8.5 8.5 0 5.967 7.621 11.116 7.945 11.332l.555.37.555-.37c.324-.216 7.945-5.365 7.945-11.332C20.5 5.813 16.687 2 12 2zm0 17.77c-1.665-1.241-6.5-5.196-6.5-9.27C5.5 6.916 8.416 4 12 4s6.5 2.916 6.5 6.5c0 4.073-4.835 8.028-6.5 9.27z" />
                </svg>
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
        <div className="mt-auto flex gap-3.5 overflow-x-auto pt-4 pb-3 scrollbar-subtle">
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
