"use client";

import { useEffect, useState } from "react";
import { listProfiles, type Profile } from "@/lib/api";
import { ProfileIcon } from "@/components/icons";

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);

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

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8">
      <header className="mb-8">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
          Manage
        </p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
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
                <button className="text-xs font-semibold text-primary hover:underline">
                  View Profile
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
