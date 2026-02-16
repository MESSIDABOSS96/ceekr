"use client";

import type { Tweet } from "@/lib/types";

function formatCount(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 10_000) return `${Math.floor(count / 1_000)}K`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K`;
  return String(count);
}

function formatRelativeDate(dateStr: string | null): string | null {
  if (!dateStr) return null;
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return null;

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);
  const diffDays = diffMs / (1000 * 60 * 60 * 24);

  if (diffHours < 1) return "now";
  if (diffDays < 7) return `${Math.floor(diffDays)}d`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w`;

  const sameYear = date.getFullYear() === now.getFullYear();
  const month = date.toLocaleString("en-US", { month: "short" });
  if (sameYear) return `${month} ${date.getDate()}`;
  return `${month} '${String(date.getFullYear()).slice(2)}`;
}

function ReplyIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M1.751 10c0-4.42 3.58-8 8-8h4.5c4.42 0 8 3.58 8 8v0c0 4.42-3.58 8-8 8h-2.5l-4.776 3.82a.5.5 0 0 1-.724-.447V18c-2.762 0-4.5-2.238-4.5-5v-3z" />
    </svg>
  );
}

function RetweetIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor">
      <path d="M4.5 3.88l4.432 4.14-1.364 1.46L5.5 7.55V16c0 1.1.896 2 2 2H13v2H7.5c-2.209 0-4-1.791-4-4V7.55L1.432 9.48.068 8.02 4.5 3.88zM16.5 6H11V4h5.5c2.209 0 4 1.791 4 4v8.45l2.068-1.93 1.364 1.46-4.432 4.14-4.432-4.14 1.364-1.46 2.068 1.93V8c0-1.1-.896-2-2-2z" />
    </svg>
  );
}

function HeartIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M16.697 5.5c-1.222-.06-2.679.51-3.89 2.16l-.807 1.1-.807-1.1C10.07 5.96 8.578 5.39 7.39 5.5c-3.11.26-4.577 3.32-4.087 6.2.48 2.79 3.137 5.78 7.793 9.17a1.5 1.5 0 0 0 1.808 0c4.656-3.39 7.313-6.38 7.793-9.17.49-2.88-.977-5.94-4.087-6.2h.087z" />
    </svg>
  );
}

function XLogoIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  );
}

interface TweetCardProps {
  tweet: Tweet;
  handle: string;
  displayName?: string;
  profileImageUrl?: string | null;
  verified?: boolean;
}

export function TweetCard({
  tweet,
  handle,
  displayName,
  profileImageUrl,
  verified,
}: TweetCardProps) {
  const url = `https://x.com/${handle}/status/${tweet.id}`;
  const relDate = formatRelativeDate(tweet.created_at);
  const hasMedia = tweet.media_urls?.length > 0;
  const avatarUrl = profileImageUrl?.replace("_normal.", "_bigger.") || "";

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={(e) => e.stopPropagation()}
      className="flex w-[300px] shrink-0 flex-col overflow-hidden rounded-xl border border-border-subtle bg-surface-tweet"
    >
      {/* Header: avatar, name, handle, date, X logo */}
      <div className="flex items-center gap-2 px-3.5 pt-3 pb-1">
        {avatarUrl ? (
          <img
            src={avatarUrl}
            alt=""
            className="h-6 w-6 shrink-0 rounded-full object-cover"
          />
        ) : (
          <div className="h-6 w-6 shrink-0 rounded-full bg-zinc-700" />
        )}
        <div className="flex min-w-0 flex-1 items-center gap-1 text-[0.78rem] leading-tight">
          <span className="truncate font-semibold text-text-primary">
            {displayName || handle}
          </span>
          {verified && (
            <svg viewBox="0 0 22 22" className="h-3.5 w-3.5 shrink-0 fill-twitter">
              <path d="M20.396 11c-.018-.646-.215-1.275-.57-1.816-.354-.54-.852-.972-1.438-1.246.223-.607.27-1.264.14-1.897-.131-.634-.437-1.218-.882-1.687-.47-.445-1.053-.75-1.687-.882-.633-.13-1.29-.083-1.897.14-.273-.587-.704-1.086-1.245-1.44S11.647 1.62 11 1.604c-.646.017-1.273.213-1.813.568s-.969.855-1.24 1.44c-.608-.223-1.267-.272-1.902-.14-.635.13-1.22.436-1.69.882-.445.47-.749 1.055-.878 1.69-.13.633-.08 1.29.144 1.896-.587.274-1.087.705-1.443 1.245-.356.54-.555 1.17-.574 1.817.02.647.218 1.276.574 1.817.356.54.856.972 1.443 1.245-.224.606-.274 1.263-.144 1.896.13.636.433 1.221.878 1.69.47.446 1.055.752 1.69.883.635.13 1.294.083 1.902-.141.27.587.7 1.086 1.24 1.44s1.167.551 1.813.568c.647-.016 1.276-.213 1.817-.567s.972-.854 1.245-1.44c.604.223 1.26.27 1.894.14.634-.132 1.22-.438 1.69-.884.445-.47.75-1.055.88-1.69.131-.634.084-1.292-.139-1.9.588-.269 1.086-.7 1.44-1.24.353-.54.551-1.17.569-1.816zM9.662 14.85l-3.429-3.428 1.293-1.302 2.072 2.072 4.4-4.794 1.347 1.246z" />
            </svg>
          )}
          <span className="truncate text-text-muted">@{handle}</span>
          {relDate && (
            <>
              <span className="text-text-muted">&middot;</span>
              <span className="shrink-0 text-text-muted">{relDate}</span>
            </>
          )}
        </div>
        <XLogoIcon className="h-4 w-4 shrink-0 text-text-muted/60" />
      </div>

      {/* Body */}
      <div className="flex flex-1 flex-col px-3.5 pt-1.5 pb-2.5">
        <p
          className={`text-[0.82rem] leading-[1.45] text-text-body ${hasMedia ? "line-clamp-3" : "line-clamp-5"}`}
        >
          {tweet.text}
        </p>

        {/* Media */}
        {hasMedia && (
          <img
            src={tweet.media_urls[0]}
            alt=""
            className="mt-2.5 max-h-[160px] w-full rounded-lg object-cover"
          />
        )}

        {/* Engagement */}
        <div className="mt-2.5 flex items-center gap-4 text-[0.73rem] text-text-muted">
          <span className="flex items-center gap-1">
            <ReplyIcon className="h-3.5 w-3.5" />
            {formatCount(tweet.reply_count)}
          </span>
          <span className="flex items-center gap-1">
            <RetweetIcon className="h-3.5 w-3.5" />
            {formatCount(tweet.retweet_count)}
          </span>
          <span className="flex items-center gap-1">
            <HeartIcon className="h-3.5 w-3.5" />
            {formatCount(tweet.like_count)}
          </span>
        </div>
      </div>
    </a>
  );
}
