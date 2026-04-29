"use client";

import { useState } from "react";
import { AlertCircle, FileText } from "lucide-react";
import { GenerateForm } from "@/components/generate-form";
import { DraftDisplay } from "@/components/draft-display";
import {
  generatePost,
  revoicePost,
  type GenerateRequest,
  type GenerateResponse,
} from "@/lib/api";
import { cn } from "@/lib/utils";

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
    <div className="flex h-full flex-col p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Generate Post</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Create authentic content that matches your writing style
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 flex items-center gap-3 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-400" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Two Column Layout */}
      <div className="grid flex-1 gap-6 lg:grid-cols-2">
        {/* Left: Form */}
        <div className="rounded-lg border border-border bg-card p-6">
          <GenerateForm onSubmit={handleGenerate} isLoading={isGenerating} />
        </div>

        {/* Right: Result */}
        <div className="flex flex-col">
          {draft ? (
            <DraftDisplay
              draft={draft}
              onRevoice={handleRevoice}
              isRevoicing={isRevoicing}
            />
          ) : (
            <div
              className={cn(
                "flex flex-1 flex-col items-center justify-center rounded-lg border border-dashed border-border",
                isGenerating ? "animate-pulse" : ""
              )}
            >
              <FileText className="h-12 w-12 text-muted" />
              <p className="mt-4 text-sm text-muted-foreground">
                {isGenerating
                  ? "Generating your post..."
                  : "Your generated post will appear here"}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
