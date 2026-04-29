"use client";

import { useState, useEffect } from "react";
import { Copy, Check, RefreshCw, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { GenerateResponse } from "@/lib/api";

interface DraftDisplayProps {
  draft: GenerateResponse;
  onRevoice: (editedText: string) => void;
  isRevoicing: boolean;
}

export function DraftDisplay({
  draft,
  onRevoice,
  isRevoicing,
}: DraftDisplayProps) {
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState(draft.text);

  useEffect(() => {
    setEditedText(draft.text);
    setIsEditing(false);
  }, [draft.text]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(draft.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error("Failed to copy:", error);
    }
  };

  const handleRevoice = () => {
    onRevoice(editedText);
  };

  const handleCancel = () => {
    setEditedText(draft.text);
    setIsEditing(false);
  };

  const hasChanges = editedText !== draft.text;

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-card">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium",
              draft.platform === "linkedin"
                ? "bg-blue-500/10 text-blue-400"
                : "bg-sky-500/10 text-sky-400"
            )}
          >
            {draft.platform === "linkedin" ? "LinkedIn" : "Twitter"}
          </span>
          <span className="text-xs text-muted-foreground">
            {draft.sources_used} source{draft.sources_used !== 1 ? "s" : ""}{" "}
            used
          </span>
        </div>
        <button
          onClick={handleCopy}
          className={cn(
            "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
            copied
              ? "bg-green-500/10 text-green-400"
              : "hover:bg-muted/50 text-muted-foreground hover:text-foreground"
          )}
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5" />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              Copy
            </>
          )}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 p-4">
        {isEditing ? (
          <textarea
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            className={cn(
              "h-full w-full resize-none rounded-lg border border-border bg-background p-4 text-sm text-foreground",
              "focus:ring-primary/50 focus:outline-none focus:ring-2"
            )}
            autoFocus
          />
        ) : (
          <div
            onClick={() => setIsEditing(true)}
            className="h-full cursor-text whitespace-pre-wrap text-sm text-foreground"
          >
            {draft.text}
          </div>
        )}
      </div>

      {/* Validation Issues */}
      {!draft.validation_ok && draft.validation_issues.length > 0 && (
        <div className="border-t border-border px-4 py-3">
          <p className="text-xs font-medium text-amber-400">
            Validation Issues:
          </p>
          <ul className="mt-1 space-y-0.5">
            {draft.validation_issues.map((issue, index) => (
              <li key={index} className="text-xs text-amber-400/80">
                {issue}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Edit Mode Actions */}
      {isEditing && hasChanges && (
        <div className="flex items-center gap-2 border-t border-border px-4 py-3">
          <button
            onClick={handleRevoice}
            disabled={isRevoicing}
            className={cn(
              "bg-primary/10 flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium text-primary transition-colors",
              "hover:bg-primary/20",
              "disabled:cursor-not-allowed disabled:opacity-50"
            )}
          >
            {isRevoicing ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Re-voicing...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4" />
                Re-voice
              </>
            )}
          </button>
          <button
            onClick={handleCancel}
            disabled={isRevoicing}
            className={cn(
              "flex items-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-muted-foreground transition-colors",
              "hover:bg-muted/50 hover:text-foreground",
              "disabled:cursor-not-allowed disabled:opacity-50"
            )}
          >
            <X className="h-4 w-4" />
            Cancel
          </button>
        </div>
      )}

      {/* Click to edit hint */}
      {!isEditing && (
        <div className="border-t border-border px-4 py-2">
          <p className="text-center text-xs text-muted-foreground">
            Click the text above to edit
          </p>
        </div>
      )}
    </div>
  );
}
