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

// ── Intent Check / Clarification ─────────────────────────

export interface ClarificationQuestion {
  question: string;
  placeholder: string;
}

export interface IntentCheckResponse {
  intent: SearchIntent;
  needs_clarification: boolean;
  clarification_questions: ClarificationQuestion[];
}

// ── Activity / Thinking Panel ────────────────────────────

export type ActivityStepType =
  | "init"
  | "intent_analysis"
  | "query_generation"
  | "searching"
  | "filtering"
  | "filtering_done"
  | "ranking"
  | "grouping"
  | "fallback"
  | "generic";

export interface ActivityStep {
  message: string;
  step: ActivityStepType;
  counts?: Record<string, number>;
  timestamp: number;
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

// ── Workspace types ──

export type JournalTheme = "topic" | "role" | "location" | "approach" | "career_stage" | "community";

export interface WorkspaceJournal {
  id: string;
  label: string;
  description: string;
  theme: JournalTheme;
  color: string;
  people_count: number;
  canvas_x: number;
  canvas_y: number;
  enrichment_status?: string;
}

export interface JournalOverlap {
  journal_a: string;
  journal_b: string;
  shared_count: number;
  shared_handles: string[];
}

export interface WorkspaceData {
  workspace_id: string;
  query: string;
  status: "creating" | "ready" | "enriching";
  summary: string;
  quality: "strong" | "moderate" | "weak";
  total_people: number;
  refinement_questions: string[];
  journals: WorkspaceJournal[];
  overlaps: JournalOverlap[];
  intent?: SearchIntent;
  created_at?: string;
  updated_at?: string;
}

export interface JournalPerson extends RankedAccount {
  journal_note: string;
}

// ── Chat types ──

export interface ChatAction {
  type: "apply_filters" | "remove_profiles" | "run_targeted_search" | "regroup_journals";
  filters?: {
    min_followers?: number;
    max_followers?: number;
    bio_keywords?: string[];
    location?: string;
  };
  handles?: string[];
  search_description?: string;
  new_axis_description?: string;
  newResults?: RankedAccount[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  action?: ChatAction;
  created_at: string;
}

// ── Workspace list (sidebar) ──

export interface WorkspaceSummary {
  id: string;
  query: string;
  status: string;
  summary: string | null;
  quality: string | null;
  created_at: string;
  updated_at: string;
}
