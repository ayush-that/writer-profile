"use client";

import { useEffect, useState } from "react";
import { Sparkles, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { listProfiles, type Profile, type GenerateRequest } from "@/lib/api";

interface GenerateFormProps {
  onSubmit: (request: GenerateRequest) => void;
  isLoading: boolean;
}

export function GenerateForm({ onSubmit, isLoading }: GenerateFormProps) {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loadingProfiles, setLoadingProfiles] = useState(true);
  const [author, setAuthor] = useState("");
  const [platform, setPlatform] = useState<"twitter" | "linkedin">("linkedin");
  const [topic, setTopic] = useState("");
  const [angle, setAngle] = useState("");
  const [virality, setVirality] = useState(15);

  useEffect(() => {
    async function fetchProfiles() {
      try {
        const data = await listProfiles();
        setProfiles(data);
        if (data.length > 0) {
          setAuthor(data[0].author);
        }
      } catch (error) {
        console.error("Failed to load profiles:", error);
      } finally {
        setLoadingProfiles(false);
      }
    }
    fetchProfiles();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!author || !topic) return;

    onSubmit({
      author,
      platform,
      topic,
      angle: angle || undefined,
      virality: virality / 100,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Author Select */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground">
          CEO / Author
        </label>
        <div className="relative">
          <select
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            disabled={loadingProfiles}
            className={cn(
              "w-full appearance-none rounded-lg border border-border bg-card px-4 py-3 pr-10 text-sm text-foreground",
              "focus:ring-primary/50 focus:outline-none focus:ring-2",
              "disabled:cursor-not-allowed disabled:opacity-50"
            )}
          >
            {loadingProfiles ? (
              <option>Loading profiles...</option>
            ) : profiles.length === 0 ? (
              <option>No profiles available</option>
            ) : (
              profiles.map((profile) => (
                <option key={profile.author} value={profile.author}>
                  {profile.author}
                </option>
              ))
            )}
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        </div>
      </div>

      {/* Platform Toggle */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground">Platform</label>
        <div className="flex gap-2">
          {(["linkedin", "twitter"] as const).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPlatform(p)}
              className={cn(
                "flex-1 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors",
                platform === p
                  ? "bg-primary/10 border-primary text-primary"
                  : "hover:bg-muted/50 border-border text-muted-foreground"
              )}
            >
              {p === "linkedin" ? "LinkedIn" : "Twitter"}
            </button>
          ))}
        </div>
      </div>

      {/* Topic Input */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground">Topic</label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="What should the post be about?"
          className={cn(
            "w-full rounded-lg border border-border bg-card px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground",
            "focus:ring-primary/50 focus:outline-none focus:ring-2"
          )}
        />
      </div>

      {/* Angle Textarea */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground">
          Angle{" "}
          <span className="font-normal text-muted-foreground">(optional)</span>
        </label>
        <textarea
          value={angle}
          onChange={(e) => setAngle(e.target.value)}
          placeholder="Any specific perspective or hook you want to use?"
          rows={3}
          className={cn(
            "w-full resize-none rounded-lg border border-border bg-card px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground",
            "focus:ring-primary/50 focus:outline-none focus:ring-2"
          )}
        />
      </div>

      {/* Virality Slider */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-foreground">
            Virality
          </label>
          <span className="text-sm font-medium text-primary">{virality}%</span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={virality}
          onChange={(e) => setVirality(Number(e.target.value))}
          className="w-full accent-primary"
        />
        <p className="text-xs text-muted-foreground">
          Higher values make the post more engaging but potentially less
          authentic
        </p>
      </div>

      {/* Generate Button */}
      <button
        type="submit"
        disabled={isLoading || !author || !topic}
        className={cn(
          "gradient-primary flex w-full items-center justify-center gap-2 rounded-lg px-4 py-3 text-sm font-semibold text-white transition-opacity",
          "hover:opacity-90",
          "disabled:cursor-not-allowed disabled:opacity-50"
        )}
      >
        {isLoading ? (
          <>
            <Sparkles className="h-4 w-4 animate-pulse" />
            Generating...
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4" />
            Generate Post
          </>
        )}
      </button>
    </form>
  );
}
