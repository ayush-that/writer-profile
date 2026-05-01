const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getApiBase() {
  return API_BASE;
}

export interface GenerateRequest {
  author: string;
  platform: "twitter" | "linkedin";
  topic: string;
  angle?: string;
  virality?: number;
  word_limit?: number;
}

export interface Source {
  url: string;
  title: string;
  source_type: string;
  snippet: string;
  origin: "own" | "web";
  score?: number | null;
}

export interface GenerateResponse {
  text: string;
  author: string;
  platform: string;
  validation_ok?: boolean;
  validation_issues?: string[];
  sources_used: number;
  sources: Source[];
}

export interface Profile {
  author: string;
  platform: string;
}

export async function generatePost(
  req: GenerateRequest
): Promise<GenerateResponse> {
  const response = await fetch(`${API_BASE}/api/generate/moe`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(req),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to generate post");
  }

  return response.json();
}

export async function revoicePost(
  author: string,
  platform: "twitter" | "linkedin",
  editedDraft: string
): Promise<GenerateResponse> {
  const response = await fetch(`${API_BASE}/api/revoice`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      author,
      platform,
      edited_draft: editedDraft,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to re-voice post");
  }

  return response.json();
}

export async function listProfiles(): Promise<Profile[]> {
  const response = await fetch(`${API_BASE}/api/profiles`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to list profiles");
  }

  const data = await response.json();
  return data.profiles;
}

export interface LexicalPatterns {
  vocabulary_level: string;
  recurring_phrases: string[];
  word_preferences: Record<string, string>;
  jargon_usage: string;
  technicality_level: string;
}

export interface StructuralPatterns {
  avg_sentence_length: number;
  paragraph_style: string;
  opening_patterns: string[];
  closing_patterns: string[];
  uses_lists: boolean;
  uses_questions: boolean;
}

export interface TonalPatterns {
  warmth_level: string;
  humor_usage: string;
  personal_disclosure: string;
  conviction_style: string;
}

export interface VoiceProfile {
  author: string;
  platform: string;
  lexical: LexicalPatterns;
  structural: StructuralPatterns;
  tonal: TonalPatterns;
  example_posts: string[];
}

export interface ProfileDetailResponse {
  profile: VoiceProfile;
  post_count: number;
}

export async function getProfile(
  author: string,
  platform: string
): Promise<ProfileDetailResponse> {
  const response = await fetch(`${API_BASE}/api/profiles/${author}/${platform}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch profile");
  }

  return response.json();
}
