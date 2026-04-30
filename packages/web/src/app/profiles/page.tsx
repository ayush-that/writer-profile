"use client";

import { useEffect, useState } from "react";
import { listProfiles, type Profile, getApiBase } from "@/lib/api";
import { ProfileIcon, CloseIcon } from "@/components/icons";
import { cn } from "@/lib/utils";

interface ProfileDetail {
  author: string;
  platform: string;
  lexical?: {
    vocabulary_level?: string;
    recurring_phrases?: string[];
    jargon_usage?: string;
  };
  structural?: {
    avg_sentence_length?: number;
    opening_patterns?: string[];
    closing_patterns?: string[];
  };
  tonal?: {
    warmth_level?: string;
    humor_usage?: string;
    conviction_style?: string;
  };
  example_posts?: string[];
}

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProfile, setSelectedProfile] = useState<ProfileDetail | null>(
    null
  );
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    async function fetchProfiles() {
      try {
        const data = await listProfiles();
        setProfiles(data);
      } catch {
        // API not available
      } finally {
        setLoading(false);
      }
    }
    fetchProfiles();
  }, []);

  const viewProfile = async (author: string, platform: string) => {
    setLoadingDetail(true);
    try {
      const res = await fetch(`${getApiBase()}/api/profiles/${author}/${platform}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedProfile(data);
      }
    } catch {
      // ignore
    } finally {
      setLoadingDetail(false);
    }
  };

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Voice Profiles
        </h1>
      </header>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-[3px] border-primary border-t-transparent" />
        </div>
      ) : profiles.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border bg-card py-20">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <ProfileIcon
              className="h-7 w-7 text-muted-foreground"
              weight="fill"
            />
          </div>
          <p className="mt-5 text-base font-semibold text-foreground">
            No profiles yet
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Create a profile to start generating content
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {profiles.map((profile) => (
            <div
              key={`${profile.author}-${profile.platform}`}
              className="card-elevated rounded-2xl border border-border p-5"
            >
              <div className="flex items-center gap-4">
                <div className="from-primary/20 to-primary/5 flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br">
                  <span className="text-lg font-bold text-primary">
                    {profile.author.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-foreground">
                    {profile.author
                      .replace(/_/g, " ")
                      .replace(/\b\w/g, (c) => c.toUpperCase())}
                  </p>
                  <p className="text-xs capitalize text-muted-foreground">
                    {profile.platform}
                  </p>
                </div>
              </div>
              <div className="mt-5 flex items-center justify-between">
                <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wide text-emerald-600">
                  Active
                </span>
                <button
                  onClick={() => viewProfile(profile.author, profile.platform)}
                  className="text-xs font-semibold text-primary hover:underline"
                >
                  View Profile
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {(selectedProfile || loadingDetail) && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setSelectedProfile(null)}
        >
          <div
            className="max-h-[80vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6"
            onClick={(e) => e.stopPropagation()}
          >
            {loadingDetail ? (
              <div className="flex items-center justify-center py-12">
                <div className="h-8 w-8 animate-spin rounded-full border-[3px] border-primary border-t-transparent" />
              </div>
            ) : selectedProfile ? (
              <>
                <div className="mb-6 flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-foreground">
                      {selectedProfile.author
                        .replace(/_/g, " ")
                        .replace(/\b\w/g, (c) => c.toUpperCase())}
                    </h2>
                    <p className="text-sm capitalize text-muted-foreground">
                      {selectedProfile.platform}
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedProfile(null)}
                    className="rounded-full p-2 hover:bg-muted"
                  >
                    <CloseIcon className="h-5 w-5" weight="bold" />
                  </button>
                </div>

                {selectedProfile.lexical && (
                  <div className="mb-4">
                    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Lexical
                    </h3>
                    <div className="space-y-1 text-sm">
                      {selectedProfile.lexical.vocabulary_level && (
                        <p>
                          <span className="font-medium">Vocabulary:</span>{" "}
                          {selectedProfile.lexical.vocabulary_level}
                        </p>
                      )}
                      {selectedProfile.lexical.jargon_usage && (
                        <p>
                          <span className="font-medium">Jargon:</span>{" "}
                          {selectedProfile.lexical.jargon_usage}
                        </p>
                      )}
                      {selectedProfile.lexical.recurring_phrases && (
                        <p>
                          <span className="font-medium">Phrases:</span>{" "}
                          {selectedProfile.lexical.recurring_phrases.join(", ")}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {selectedProfile.tonal && (
                  <div className="mb-4">
                    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Tonal
                    </h3>
                    <div className="space-y-1 text-sm">
                      {selectedProfile.tonal.warmth_level && (
                        <p>
                          <span className="font-medium">Warmth:</span>{" "}
                          {selectedProfile.tonal.warmth_level}
                        </p>
                      )}
                      {selectedProfile.tonal.humor_usage && (
                        <p>
                          <span className="font-medium">Humor:</span>{" "}
                          {selectedProfile.tonal.humor_usage}
                        </p>
                      )}
                      {selectedProfile.tonal.conviction_style && (
                        <p>
                          <span className="font-medium">Conviction:</span>{" "}
                          {selectedProfile.tonal.conviction_style}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {selectedProfile.example_posts &&
                  selectedProfile.example_posts.length > 0 && (
                    <div>
                      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Example Posts
                      </h3>
                      <div className="space-y-3">
                        {selectedProfile.example_posts
                          .slice(0, 3)
                          .map((post, i) => (
                            <p
                              key={i}
                              className="rounded-lg bg-muted p-3 text-sm leading-relaxed"
                            >
                              {post}
                            </p>
                          ))}
                      </div>
                    </div>
                  )}
              </>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
