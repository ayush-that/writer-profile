"use client";

import { useQuery } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import {
  listProfiles,
  getProfile,
  type Profile,
  type ProfileDetailResponse,
} from "@/lib/api";
import { ProfileIcon, CloseIcon } from "@/components/icons";
import { cn } from "@/lib/utils";

export default function ProfilesPage() {
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const {
    data: profiles = [],
    isLoading: loadingList,
    error: listError,
  } = useQuery({
    queryKey: ["profiles"],
    queryFn: listProfiles,
  });

  const selectedParts = selectedKey?.split("__");
  const selectedAuthor = selectedParts?.[0];
  const selectedPlatform = selectedParts?.[1];

  const {
    data: profileDetail,
    isLoading: loadingDetail,
    error: detailError,
  } = useQuery({
    queryKey: ["profile", selectedAuthor, selectedPlatform],
    queryFn: () => getProfile(selectedAuthor!, selectedPlatform!),
    enabled: !!selectedAuthor && !!selectedPlatform,
    staleTime: 10 * 60 * 1000, // Cache for 10 minutes
  });

  const closeModal = () => setSelectedKey(null);

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Voice Profiles
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {profiles.length} profiles loaded
        </p>
      </header>

      {listError ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-red-200 bg-red-50 py-20">
          <p className="text-base font-semibold text-red-600">Failed to load profiles</p>
          <p className="mt-1 text-sm text-red-500">{listError.message}</p>
        </div>
      ) : loadingList ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-[3px] border-primary border-t-transparent" />
        </div>
      ) : profiles.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border bg-card py-20">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <ProfileIcon className="h-7 w-7 text-muted-foreground" weight="fill" />
          </div>
          <p className="mt-5 text-base font-semibold text-foreground">No profiles yet</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Run the scraper scripts to populate profiles
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {profiles.map((profile) => (
            <ProfileCard
              key={`${profile.author}-${profile.platform}`}
              profile={profile}
              onView={() => setSelectedKey(`${profile.author}__${profile.platform}`)}
            />
          ))}
        </div>
      )}

      {selectedKey && (
        <ProfileModal
          detail={profileDetail}
          isLoading={loadingDetail}
          error={detailError}
          onClose={closeModal}
        />
      )}
    </div>
  );
}

function ProfileCard({
  profile,
  onView,
}: {
  profile: Profile;
  onView: () => void;
}) {
  return (
    <div className="card-elevated rounded-2xl border border-border p-5">
      <div className="flex items-center gap-4">
        <div className="from-primary/20 to-primary/5 flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br">
          <span className="text-lg font-bold text-primary">
            {profile.author.charAt(0).toUpperCase()}
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-foreground">
            {profile.author.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
          </p>
          <p className="text-xs capitalize text-muted-foreground">{profile.platform}</p>
        </div>
      </div>
      <div className="mt-5 flex items-center justify-between">
        <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wide text-emerald-600">
          Active
        </span>
        <button
          onClick={onView}
          className="text-xs font-semibold text-primary hover:underline"
        >
          View Profile
        </button>
      </div>
    </div>
  );
}

function ProfileModal({
  detail,
  isLoading,
  error,
  onClose,
}: {
  detail: ProfileDetailResponse | undefined;
  isLoading: boolean;
  error: Error | null;
  onClose: () => void;
}) {
  const profile = detail?.profile;

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="profile-modal-title"
    >
      <div
        className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white"
        onClick={(e) => e.stopPropagation()}
      >
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="h-8 w-8 animate-spin rounded-full border-[3px] border-primary border-t-transparent" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-20">
            <p className="font-medium text-red-600">Failed to load profile</p>
            <p className="mt-1 text-sm text-red-500">{error.message}</p>
          </div>
        ) : profile ? (
          <>
            {/* Header */}
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-white px-6 py-4">
              <div>
                <h2 id="profile-modal-title" className="text-xl font-bold text-foreground">
                  {profile.author.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                </h2>
                <div className="mt-1 flex items-center gap-3">
                  <span className={cn(
                    "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase",
                    profile.platform === "linkedin" ? "bg-blue-50 text-blue-600" : "bg-sky-50 text-sky-600"
                  )}>
                    {profile.platform}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {detail?.post_count || profile.example_posts.length} example posts
                  </span>
                </div>
              </div>
              <button onClick={onClose} className="rounded-full p-2 hover:bg-muted">
                <CloseIcon className="h-5 w-5" weight="bold" />
              </button>
            </div>

            <div className="space-y-6 p-6">
              {/* Lexical Patterns */}
              <Section title="Lexical Patterns" subtitle="Vocabulary and word choices">
                <div className="grid gap-3 sm:grid-cols-2">
                  <StatItem label="Vocabulary Level" value={profile.lexical.vocabulary_level} />
                  <StatItem label="Jargon Usage" value={profile.lexical.jargon_usage} />
                  <StatItem label="Technicality" value={profile.lexical.technicality_level} />
                </div>
                {profile.lexical.recurring_phrases.length > 0 && (
                  <div className="mt-3">
                    <p className="mb-2 text-xs font-medium text-muted-foreground">Recurring Phrases</p>
                    <div className="flex flex-wrap gap-1.5">
                      {profile.lexical.recurring_phrases.slice(0, 10).map((phrase, i) => (
                        <span key={i} className="rounded-full bg-muted px-2.5 py-1 text-xs">
                          {phrase}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {Object.keys(profile.lexical.word_preferences).length > 0 && (
                  <div className="mt-3">
                    <p className="mb-2 text-xs font-medium text-muted-foreground">Word Preferences</p>
                    <div className="space-y-1 text-xs">
                      {Object.entries(profile.lexical.word_preferences).map(([from, to]) => (
                        <p key={from}>
                          Prefers "<span className="font-medium">{to}</span>" over "{from}"
                        </p>
                      ))}
                    </div>
                  </div>
                )}
              </Section>

              {/* Structural Patterns */}
              <Section title="Structural Patterns" subtitle="Sentence and paragraph habits">
                <div className="grid gap-3 sm:grid-cols-2">
                  <StatItem
                    label="Avg Sentence Length"
                    value={`${profile.structural.avg_sentence_length.toFixed(1)} words`}
                  />
                  <StatItem label="Paragraph Style" value={profile.structural.paragraph_style} />
                  <StatItem label="Uses Lists" value={profile.structural.uses_lists ? "Yes" : "No"} />
                  <StatItem label="Uses Questions" value={profile.structural.uses_questions ? "Yes" : "No"} />
                </div>
                {profile.structural.opening_patterns.length > 0 && (
                  <div className="mt-3">
                    <p className="mb-2 text-xs font-medium text-muted-foreground">Opening Patterns</p>
                    <div className="space-y-1">
                      {profile.structural.opening_patterns.slice(0, 3).map((p, i) => (
                        <p key={i} className="rounded bg-muted/50 px-2 py-1 text-xs italic">"{p}"</p>
                      ))}
                    </div>
                  </div>
                )}
                {profile.structural.closing_patterns.length > 0 && (
                  <div className="mt-3">
                    <p className="mb-2 text-xs font-medium text-muted-foreground">Closing Patterns</p>
                    <div className="space-y-1">
                      {profile.structural.closing_patterns.slice(0, 3).map((p, i) => (
                        <p key={i} className="rounded bg-muted/50 px-2 py-1 text-xs italic">"{p}"</p>
                      ))}
                    </div>
                  </div>
                )}
              </Section>

              {/* Tonal Patterns */}
              <Section title="Tonal Patterns" subtitle="Voice and personality">
                <div className="grid gap-3 sm:grid-cols-2">
                  <StatItem label="Warmth Level" value={profile.tonal.warmth_level} />
                  <StatItem label="Humor Usage" value={profile.tonal.humor_usage} />
                  <StatItem label="Personal Disclosure" value={profile.tonal.personal_disclosure} />
                  <StatItem label="Conviction Style" value={profile.tonal.conviction_style} />
                </div>
              </Section>

              {/* Example Posts */}
              {profile.example_posts.length > 0 && (
                <Section
                  title="Example Posts"
                  subtitle={`${profile.example_posts.length} posts scraped`}
                >
                  <div className="space-y-3">
                    {profile.example_posts.slice(0, 5).map((post, i) => (
                      <div key={i} className="rounded-xl border border-border bg-muted/30 p-4">
                        <p className="whitespace-pre-wrap text-sm leading-relaxed">
                          {post.length > 500 ? `${post.slice(0, 500)}...` : post}
                        </p>
                        <p className="mt-2 text-[10px] text-muted-foreground">
                          {post.split(/\s+/).length} words
                        </p>
                      </div>
                    ))}
                    {profile.example_posts.length > 5 && (
                      <p className="text-center text-xs text-muted-foreground">
                        +{profile.example_posts.length - 5} more posts
                      </p>
                    )}
                  </div>
                </Section>
              )}
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center py-20">
            <p className="text-muted-foreground">Profile not found</p>
          </div>
        )}
      </div>
    </div>
  );
}

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </div>
      {children}
    </div>
  );
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-white px-3 py-2">
      <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-0.5 text-sm font-semibold capitalize text-foreground">{value}</p>
    </div>
  );
}
