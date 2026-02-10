import type { Tweet } from "@/lib/types";

function formatCount(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 10_000) return `${Math.floor(count / 1_000)}K`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K`;
  return String(count);
}

function truncate(text: string, max = 140): string {
  return text.length > max ? text.slice(0, max) + "..." : text;
}

interface TweetCardProps {
  tweet: Tweet;
  handle: string;
}

export function TweetCard({ tweet, handle }: TweetCardProps) {
  const url = `https://twitter.com/${handle}/status/${tweet.id}`;

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex w-[240px] shrink-0 flex-col justify-between rounded-xl border border-border-subtle bg-surface-tweet p-3.5 transition-colors hover:border-twitter/40"
    >
      <p className="mb-2.5 line-clamp-4 text-[0.82rem] leading-[1.45] text-text-body">
        {truncate(tweet.text)}
      </p>
      <div className="flex gap-3.5 text-[0.73rem] text-text-muted">
        <span>{"\u2665"} {formatCount(tweet.like_count)}</span>
        <span>{"\uD83D\uDD01"} {formatCount(tweet.retweet_count)}</span>
        <span>{"\uD83D\uDCAC"} {formatCount(tweet.reply_count)}</span>
      </div>
    </a>
  );
}
