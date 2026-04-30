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
}

export interface GenerateResponse {
  text: string;
  author: string;
  platform: string;
  validation_ok: boolean;
  validation_issues: string[];
  sources_used: number;
}

export interface Profile {
  author: string;
  platform: string;
}

export async function generatePost(
  req: GenerateRequest
): Promise<GenerateResponse> {
  const response = await fetch(`${API_BASE}/api/generate`, {
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
