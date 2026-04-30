"use client";

import { useEffect, useState } from "react";
import { listProfiles, type Profile } from "@/lib/api";
import { FileIcon, ProfileIcon, GenerateIcon } from "@/components/icons";

export default function Home() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await listProfiles();
        setProfiles(data);
      } catch {
        // API not available
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8">
      <header className="mb-8 lg:mb-12">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
          Welcome back
        </h1>
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="card-elevated rounded-2xl border border-border p-5">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted-foreground">
              Voice Profiles
            </p>
            <div className="bg-primary/10 flex h-9 w-9 items-center justify-center rounded-xl">
              <ProfileIcon
                className="h-[18px] w-[18px] text-primary"
                weight="fill"
              />
            </div>
          </div>
          <p className="mt-5 text-4xl font-semibold tracking-tight text-foreground">
            {loading ? "—" : profiles.length}
          </p>
          <p className="mt-1.5 text-xs text-muted-foreground">
            {profiles.length === 1 ? "Active profile" : "Active profiles"}
          </p>
        </div>

        <div className="card-elevated rounded-2xl border border-border p-5">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted-foreground">
              Ready to Generate
            </p>
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/10">
              <GenerateIcon
                className="h-[18px] w-[18px] text-emerald-600"
                weight="fill"
              />
            </div>
          </div>
          <p className="mt-5 text-4xl font-semibold tracking-tight text-foreground">
            {loading ? "—" : profiles.length > 0 ? "Yes" : "No"}
          </p>
          <p className="mt-1.5 text-xs text-muted-foreground">
            {profiles.length > 0 ? "Profiles loaded" : "Add a profile first"}
          </p>
        </div>

        <div className="card-elevated rounded-2xl border border-border p-5 sm:col-span-2 lg:col-span-1">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted-foreground">
              Platforms
            </p>
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-500/10">
              <FileIcon
                className="h-[18px] w-[18px] text-blue-600"
                weight="fill"
              />
            </div>
          </div>
          <p className="mt-5 text-4xl font-semibold tracking-tight text-foreground">
            2
          </p>
          <p className="mt-1.5 text-xs text-muted-foreground">
            LinkedIn & Twitter
          </p>
        </div>
      </div>

      {profiles.length > 0 && (
        <div className="mt-8">
          <div className="card-elevated rounded-2xl border border-border">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <h2 className="text-sm font-semibold text-foreground">
                Your Profiles
              </h2>
            </div>
            <div className="divide-y divide-border">
              {profiles.map((profile) => (
                <div
                  key={`${profile.author}-${profile.platform}`}
                  className="flex items-center gap-4 px-5 py-4"
                >
                  <div className="from-primary/20 to-primary/5 flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br">
                    <span className="text-base font-semibold text-primary">
                      {profile.author.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">
                      {profile.author
                        .replace(/_/g, " ")
                        .replace(/\b\w/g, (c) => c.toUpperCase())}
                    </p>
                    <p className="text-xs capitalize text-muted-foreground">
                      {profile.platform}
                    </p>
                  </div>
                  <span className="rounded-full bg-emerald-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-600">
                    Active
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {!loading && profiles.length === 0 && (
        <div className="mt-8">
          <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border bg-card py-16">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
              <ProfileIcon
                className="h-7 w-7 text-muted-foreground"
                weight="fill"
              />
            </div>
            <p className="mt-5 text-base font-medium text-foreground">
              No profiles yet
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Add voice profiles to start generating content
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
