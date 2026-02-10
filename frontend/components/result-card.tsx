import { Badge } from "@/components/ui/badge";
import { TweetCard } from "./tweet-card";
import type { RankedAccount } from "@/lib/types";

function formatCount(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 10_000) return `${Math.floor(count / 1_000)}K`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K`;
  return String(count);
}

function scoreColor(score: number) {
  if (score >= 8) return { bg: "rgba(16,185,129,0.15)", fg: "rgb(16,185,129)" };
  if (score >= 6) return { bg: "rgba(245,158,11,0.15)", fg: "rgb(245,158,11)" };
  return { bg: "rgba(255,255,255,0.06)", fg: "#8b8b8b" };
}

interface ResultCardProps {
  account: RankedAccount;
}

export function ResultCard({ account: r }: ResultCardProps) {
  const pfpUrl = r.profile_image_url?.replace("_normal.", "_bigger.") || "";
  const { bg, fg } = scoreColor(r.relevance_score);

  const networkBadge =
    r.network.follows_you && r.network.you_follow
      ? "Mutuals"
      : r.network.follows_you
        ? "Follows you"
        : r.network.you_follow
          ? "You follow"
          : null;

  return (
    <div className="mb-4 rounded-2xl border border-border-subtle bg-surface-card p-7 transition-transform hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(0,0,0,0.3)]">
      {/* Header */}
      <div className="mb-5 flex items-center gap-3.5">
        {pfpUrl && (
          <img
            src={pfpUrl}
            alt=""
            className="h-14 w-14 shrink-0 rounded-full object-cover"
          />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[1.05rem] font-bold text-text-primary">
              {r.name}
            </span>
            {r.relevance_score >= 8 && (
              <Badge
                variant="secondary"
                className="text-[0.72rem] font-semibold"
                style={{ background: "rgba(16,185,129,0.15)", color: "rgb(16,185,129)" }}
              >
                Best Match
              </Badge>
            )}
            {r.relevance_score >= 6 && r.relevance_score < 8 && (
              <Badge
                variant="secondary"
                className="text-[0.72rem] font-semibold"
                style={{ background: "rgba(245,158,11,0.15)", color: "rgb(245,158,11)" }}
              >
                Strong Match
              </Badge>
            )}
            {networkBadge && (
              <Badge
                variant="secondary"
                className="bg-twitter/10 text-twitter text-[0.72rem] font-semibold"
              >
                {networkBadge}
              </Badge>
            )}
          </div>
          <p className="text-[0.88rem] text-text-secondary">@{r.handle}</p>
        </div>
        <span
          className="shrink-0 rounded-full px-3.5 py-1.5 text-center text-sm font-bold"
          style={{ background: bg, color: fg }}
        >
          {r.relevance_score.toFixed(0)}/10
        </span>
      </div>

      {/* Stats */}
      <div className="mb-4 flex gap-8">
        {[
          { value: r.followers_count, label: "Followers" },
          { value: r.following_count, label: "Following" },
          { value: r.tweet_count, label: "Tweets" },
        ].map((s) => (
          <div key={s.label} className="flex flex-col">
            <span className="text-base font-bold text-text-primary">
              {formatCount(s.value)}
            </span>
            <span className="text-[0.75rem] font-medium uppercase tracking-wide text-text-muted">
              {s.label}
            </span>
          </div>
        ))}
      </div>

      {/* Bio */}
      <p className="mb-4 text-[0.92rem] leading-relaxed text-text-body">
        {r.bio || "No bio"}
      </p>

      {/* Score reasoning */}
      <p className="mb-4 text-[0.78rem] italic text-text-muted">
        {r.score_reasoning}
      </p>

      {/* Why relevant */}
      <div className="mb-4 rounded-r-lg border-l-[3px] border-twitter bg-twitter/[0.06] px-4 py-3">
        <p className="mb-1 text-[0.7rem] font-bold uppercase tracking-wider text-text-muted">
          Why Relevant
        </p>
        <p className="text-[0.88rem] italic leading-[1.45] text-text-body">
          &ldquo;{r.why_relevant}&rdquo;
        </p>
      </div>

      {/* Tweet snapshots */}
      {r.recent_tweets.length > 0 && (
        <div className="mb-4 flex gap-2.5 overflow-x-auto pb-2">
          {r.recent_tweets.slice(0, 3).map((tweet) => (
            <TweetCard key={tweet.id} tweet={tweet} handle={r.handle} />
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between">
        <div className="min-w-0 flex-1">
          {r.suggested_approach && (
            <p className="text-[0.88rem] italic text-text-body">
              {r.suggested_approach}
            </p>
          )}
        </div>
        <a
          href={r.profile_url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-[0.85rem] font-semibold text-twitter transition-opacity hover:opacity-75"
        >
          View Profile &rarr;
        </a>
      </div>
    </div>
  );
}
