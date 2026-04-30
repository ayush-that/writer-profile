"use client";

import { useState } from "react";
import { GenerateForm } from "@/components/generate-form";
import { DraftDisplay } from "@/components/draft-display";
import {
  generatePost,
  revoicePost,
  type GenerateRequest,
  type GenerateResponse,
} from "@/lib/api";

export default function GeneratePage() {
  const [draft, setDraft] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isRevoicing, setIsRevoicing] = useState(false);
  const [currentRequest, setCurrentRequest] = useState<GenerateRequest | null>(
    null
  );

  const handleGenerate = async (request: GenerateRequest) => {
    setIsGenerating(true);
    setError(null);
    setCurrentRequest(request);

    try {
      const response = await generatePost(request);
      setDraft(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate post");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRevoice = async (editedText: string) => {
    if (!currentRequest) return;

    setIsRevoicing(true);
    setError(null);

    try {
      const response = await revoicePost(
        currentRequest.author,
        currentRequest.platform,
        editedText
      );
      setDraft(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to re-voice post");
    } finally {
      setIsRevoicing(false);
    }
  };

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Generate Post
        </h1>
      </header>

      {error && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-5 py-4">
          <p className="text-sm font-medium text-red-600">{error}</p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card-elevated rounded-2xl border border-border p-6">
          <GenerateForm onSubmit={handleGenerate} isLoading={isGenerating} />
        </div>

        <div className="delay-300">
          <DraftDisplay
            draft={draft}
            onRevoice={handleRevoice}
            isRevoicing={isRevoicing}
            isGenerating={isGenerating}
          />
        </div>
      </div>
    </div>
  );
}
