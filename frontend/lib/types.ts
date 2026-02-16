export interface SearchIntent {
  persona: string;
  topic: string;
  goal: string;
  specificity: number;
  key_signals: string[];
  anti_signals: string[];
}

export interface SearchQuery {
  query: string;
  rationale: string;
  angle: string;
}

export interface Tweet {
  id: string;
  text: string;
  created_at: string | null;
  like_count: number;
  retweet_count: number;
  reply_count: number;
  media_urls: string[];
}

export interface NetworkInfo {
  you_follow: boolean;
  follows_you: boolean;
  mutual_followers: string[];
}

export interface EnrichmentData {
  external_link?: string | null;
  link_label?: string | null;
  context_note?: string | null;
}

export interface RankedAccount {
  user_id: string;
  handle: string;
  name: string;
  bio: string | null;
  followers_count: number;
  following_count: number;
  tweet_count: number;
  profile_url: string;
  profile_image_url: string | null;
  recent_tweets: Tweet[];
  matched_queries: string[];
  location: string | null;
  verified: boolean;
  created_at: string | null;
  network: NetworkInfo;
  why_relevant: string;
  bucket: "top_match" | "strong_match" | "good_match";
  summary: string;
  highlight_tweet_indices: number[];
  suggested_approach: string | null;
  evidence_highlights: string[];
  confidence: "high" | "medium" | "low";
  enrichment: EnrichmentData | null;
}

export interface SearchResults {
  ranked: RankedAccount[];
  quality: "strong" | "moderate" | "weak";
  refinement_questions: string[];
}

// ── Filters ─────────────────────────────────────────────

export interface Filters {
  followerMin: number;
  followerMax: number;
  location: string;
  verified: boolean | null; // null = any
}

export const DEFAULT_FILTERS: Filters = {
  followerMin: 0,
  followerMax: Infinity,
  location: "",
  verified: null,
};
