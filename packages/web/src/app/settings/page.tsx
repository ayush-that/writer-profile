"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  const [provider, setProvider] = useState<"claude" | "openai">("claude");

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8">
      <header className="mb-8">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
          Configure
        </p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Settings
        </h1>
      </header>

      <div className="max-w-2xl space-y-6">
        <div className="card-elevated rounded-2xl border border-border p-6">
          <h2 className="text-sm font-bold text-foreground">API Configuration</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Backend API endpoint configuration
          </p>
          <div className="mt-6 space-y-4">
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                API URL
              </label>
              <input
                type="text"
                defaultValue="http://localhost:8000"
                disabled
                className="mt-2 w-full rounded-xl border border-border bg-muted px-4 py-3.5 text-sm font-medium text-muted-foreground"
              />
              <p className="mt-2 text-[10px] text-muted-foreground">
                Configured via environment variable
              </p>
            </div>
          </div>
        </div>

        <div className="card-elevated rounded-2xl border border-border p-6">
          <h2 className="text-sm font-bold text-foreground">LLM Provider</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Select your preferred language model
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            {(["claude", "openai"] as const).map((p) => (
              <button
                key={p}
                onClick={() => setProvider(p)}
                className={cn(
                  "flex-1 rounded-xl border-2 px-5 py-3.5 text-sm font-bold",
                  provider === p
                    ? "border-foreground bg-foreground text-white"
                    : "border-border bg-white text-muted-foreground hover:border-muted-foreground hover:text-foreground"
                )}
              >
                {p === "claude" ? "Claude" : "OpenAI"}
              </button>
            ))}
          </div>
        </div>

        <div className="card-elevated rounded-2xl border border-border p-6">
          <h2 className="text-sm font-bold text-foreground">About</h2>
          <div className="mt-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Version</span>
              <span className="text-xs font-bold text-foreground">1.0.0</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Framework</span>
              <span className="text-xs font-bold text-foreground">Next.js 16</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Backend</span>
              <span className="text-xs font-bold text-foreground">FastAPI</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
