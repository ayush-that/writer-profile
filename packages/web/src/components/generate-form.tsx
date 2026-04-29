"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { listProfiles, type Profile, type GenerateRequest } from "@/lib/api";
import { ChevronIcon, SparkleIcon } from "./icons";

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
      } catch {
        // API not available
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
      <div className="space-y-2">
        <label className="text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
          Author
        </label>
        <div className="relative">
          <select
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            disabled={loadingProfiles || profiles.length === 0}
            className={cn(
              "w-full appearance-none rounded-xl border border-border bg-white px-4 py-3.5 pr-10 text-sm font-medium text-foreground",
              "transition-all duration-200",
              "disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-60"
            )}
          >
            {loadingProfiles ? (
              <option>Loading...</option>
            ) : profiles.length === 0 ? (
              <option>No profiles available</option>
            ) : (
              [...new Set(profiles.map((p) => p.author))].map((author) => (
                <option key={author} value={author}>
                  {author
                    .replace(/_/g, " ")
                    .replace(/\b\w/g, (c) => c.toUpperCase())}
                </option>
              ))
            )}
          </select>
          <ChevronIcon
            className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            weight="bold"
          />
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
          Platform
        </label>
        <div className="flex gap-3">
          {(["linkedin", "twitter"] as const).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPlatform(p)}
              className={cn(
                "flex-1 rounded-xl border-2 px-4 py-3 text-sm font-semibold",
                platform === p
                  ? "border-foreground bg-foreground text-white"
                  : "border-border bg-white text-muted-foreground hover:border-muted-foreground hover:text-foreground"
              )}
            >
              {p === "linkedin" ? "LinkedIn" : "Twitter"}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
          Topic
        </label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="What should the post be about?"
          className="w-full rounded-xl border border-border bg-white px-4 py-3.5 text-sm font-medium text-foreground transition-all duration-200 placeholder:font-normal placeholder:text-muted-foreground"
        />
      </div>

      <div className="space-y-2">
        <label className="text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
          Angle{" "}
          <span className="text-muted-foreground/70 font-medium normal-case tracking-normal">
            (optional)
          </span>
        </label>
        <textarea
          value={angle}
          onChange={(e) => setAngle(e.target.value)}
          placeholder="Specific perspective or hook"
          rows={2}
          className="w-full resize-none rounded-xl border border-border bg-white px-4 py-3.5 text-sm font-medium text-foreground transition-all duration-200 placeholder:font-normal placeholder:text-muted-foreground"
        />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
            Virality
          </label>
          <span className="text-sm font-bold tabular-nums text-foreground">
            {virality}%
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={virality}
          onChange={(e) => setVirality(Number(e.target.value))}
          className="w-full accent-primary"
        />
        <p className="text-[10px] leading-relaxed text-muted-foreground">
          Higher = more engaging hooks · Lower = more authentic voice
        </p>
      </div>

      <button
        type="submit"
        disabled={isLoading || !author || !topic}
        className={cn(
          "btn-primary flex w-full items-center justify-center gap-2.5 rounded-2xl px-6 py-4 text-sm font-bold text-white",
          "disabled:transform-none disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
        )}
      >
        <SparkleIcon className="h-[18px] w-[18px]" weight="fill" />
        {isLoading ? "Generating..." : "Generate Post"}
      </button>
    </form>
  );
}
