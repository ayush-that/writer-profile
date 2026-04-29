"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import type { GenerateResponse } from "@/lib/api";
import { CopyIcon, CheckIcon, RefreshIcon, FileIcon } from "./icons";

interface DraftDisplayProps {
  draft: GenerateResponse | null;
  onRevoice: (editedText: string) => void;
  isRevoicing: boolean;
  isGenerating: boolean;
}

export function DraftDisplay({
  draft,
  onRevoice,
  isRevoicing,
  isGenerating,
}: DraftDisplayProps) {
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState("");

  useEffect(() => {
    if (draft) {
      setEditedText(draft.text);
      setIsEditing(false);
    }
  }, [draft?.text]);

  const handleCopy = async () => {
    if (!draft) return;
    try {
      await navigator.clipboard.writeText(draft.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  const hasChanges = draft && editedText !== draft.text;

  if (!draft) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border bg-card p-8 sm:p-12",
          isGenerating && "animate-pulse"
        )}
      >
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
          <FileIcon className="h-7 w-7 text-muted-foreground" weight="fill" />
        </div>
        <p className="mt-5 text-base font-medium text-foreground">
          {isGenerating ? "Generating your post..." : "Your post will appear here"}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {isGenerating ? "This may take a few seconds" : "Fill out the form and click generate"}
        </p>
      </div>
    );
  }

  return (
    <div className="card-elevated flex flex-col rounded-2xl border border-border">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-5 py-4">
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "rounded-full px-3 py-1.5 text-[10px] font-bold uppercase tracking-wide",
              draft.platform === "linkedin"
                ? "bg-blue-50 text-blue-600"
                : "bg-sky-50 text-sky-600"
            )}
          >
            {draft.platform}
          </span>
          {draft.sources_used > 0 && (
            <span className="text-xs text-muted-foreground">
              {draft.sources_used} sources
            </span>
          )}
        </div>
        <button
          onClick={handleCopy}
          className={cn(
            "btn-ghost flex items-center gap-2 rounded-xl border border-border px-3.5 py-2 text-xs font-semibold transition-all",
            copied
              ? "border-emerald-200 bg-emerald-50 text-emerald-600"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          {copied ? (
            <CheckIcon className="h-3.5 w-3.5" weight="bold" />
          ) : (
            <CopyIcon className="h-3.5 w-3.5" weight="bold" />
          )}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      <div className="min-h-[200px] flex-1 p-5 sm:min-h-[240px]">
        {isEditing ? (
          <textarea
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            className="h-full min-h-[180px] w-full resize-none rounded-xl border border-border bg-white p-4 text-sm leading-relaxed text-foreground transition-all duration-200 sm:min-h-[220px]"
            autoFocus
          />
        ) : (
          <div
            onClick={() => setIsEditing(true)}
            className="cursor-text whitespace-pre-wrap text-sm leading-[1.7] text-foreground"
          >
            {draft.text}
          </div>
        )}
      </div>

      {isEditing && hasChanges && (
        <div className="flex flex-col gap-3 border-t border-border p-5 sm:flex-row sm:items-center">
          <button
            onClick={() => onRevoice(editedText)}
            disabled={isRevoicing}
            className={cn(
              "btn-primary flex flex-1 items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-bold text-white",
              "disabled:cursor-not-allowed disabled:opacity-50"
            )}
          >
            <RefreshIcon
              className={cn("h-4 w-4", isRevoicing && "animate-spin")}
              weight="bold"
            />
            {isRevoicing ? "Re-voicing..." : "Re-voice"}
          </button>
          <button
            onClick={() => {
              setEditedText(draft.text);
              setIsEditing(false);
            }}
            disabled={isRevoicing}
            className="btn-ghost rounded-xl border border-border px-5 py-3 text-sm font-semibold text-muted-foreground hover:text-foreground"
          >
            Cancel
          </button>
        </div>
      )}

      {!isEditing && (
        <div className="border-t border-border px-5 py-3">
          <p className="text-center text-[10px] font-medium text-muted-foreground">
            Click text to edit · Re-voice to apply your changes
          </p>
        </div>
      )}
    </div>
  );
}
