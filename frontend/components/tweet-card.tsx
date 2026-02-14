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

function formatRelativeDate(dateStr: string | null): string | null {
  if (!dateStr) return null;
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return null;

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);
  const diffDays = diffMs / (1000 * 60 * 60 * 24);

  if (diffHours < 1) return "just now";
  if (diffDays < 7) return `${Math.floor(diffDays)}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;

  const sameYear = date.getFullYear() === now.getFullYear();
  const month = date.toLocaleString("en-US", { month: "short" });
  if (sameYear) return `${month} ${date.getDate()}`;
  return `${month} '${String(date.getFullYear()).slice(2)}`;
}

interface TweetCardProps {
  tweet: Tweet;
  handle: string;
}

export function TweetCard({ tweet, handle }: TweetCardProps) {
  const url = `https://twitter.com/${handle}/status/${tweet.id}`;
  const relDate = formatRelativeDate(tweet.created_at);

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
      <div className="flex items-center gap-3.5 text-[0.73rem] text-text-muted">
        <span>{"\u2665"} {formatCount(tweet.like_count)}</span>
        <span>{"\uD83D\uDD01"} {formatCount(tweet.retweet_count)}</span>
        <span>{"\uD83D\uDCAC"} {formatCount(tweet.reply_count)}</span>
        {relDate && (
          <span className="ml-auto text-text-muted/70">{relDate}</span>
        )}
      </div>
    </a>
  );
}
