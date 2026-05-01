# Word Limit + Sources + Progress UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add word limit control, show sources for transparency, and display real-time progress with animated SVGs.

**Architecture:** 
- Add `word_limit` field to generate request with prompt instructions
- Return source URLs/titles in response for transparency
- Use Server-Sent Events (SSE) for real-time progress streaming
- Create custom animated SVG components for loading states

**Tech Stack:** FastAPI/Pydantic with SSE streaming (backend), Next.js/React with EventSource (frontend), TypeScript, Custom SVG animations

---

## File Structure

| File | Responsibility |
|------|----------------|
| `packages/api/src/writer_api/models/requests.py` | Add `word_limit` field to `GenerateRequest` |
| `packages/api/src/writer_api/models/responses.py` | Add `sources` list with URLs/titles |
| `packages/api/src/writer_api/prompts/templates.py` | Add word limit instruction to prompt template |
| `packages/api/src/writer_api/services/generator.py` | Pass `word_limit` to prompt builder, return sources |
| `packages/api/src/writer_api/routes/generate.py` | Add SSE streaming endpoint |
| `packages/web/src/lib/api.ts` | Add `word_limit`, `sources` types, streaming support |
| `packages/web/src/components/generate-form.tsx` | Add word limit UI control |
| `packages/web/src/components/draft-display.tsx` | Show sources panel |
| `packages/web/src/components/progress-animation.tsx` | Custom animated SVG progress indicators |
| `packages/web/src/app/generate/page.tsx` | Handle streaming progress state |

---

### Task 1: Add word_limit to Backend Request Model

**Files:**
- Modify: `packages/api/src/writer_api/models/requests.py:6-11`

- [ ] **Step 1: Add word_limit field to GenerateRequest**

```python
class GenerateRequest(BaseModel):
    author: str
    platform: Platform
    topic: str
    angle: str = ""
    virality: float = Field(0.15, ge=0.0, le=1.0)
    word_limit: int | None = Field(None, ge=20, le=500)
```

- [ ] **Step 2: Verify the change compiles**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/api && uv run python -c "from writer_api.models.requests import GenerateRequest; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add packages/api/src/writer_api/models/requests.py
git commit -m "feat(api): add word_limit field to GenerateRequest"
```

---

### Task 2: Update Prompt Template to Include Word Limit

**Files:**
- Modify: `packages/api/src/writer_api/prompts/templates.py:50-95`

- [ ] **Step 1: Update build_generator_prompt signature and add word limit instruction**

Replace the `build_generator_prompt` function:

```python
def build_generator_prompt(
    profile: VoiceProfile,
    topic: str,
    angle: str,
    references: list[dict],
    virality: float,
    word_limit: int | None = None,
) -> tuple[str, str]:
    voice_summary = f"""
Author: {profile.author}
Platform: {profile.platform.value}
Lexical: {profile.lexical.vocabulary_level} vocabulary, technicality: {profile.lexical.technicality_level}
Recurring phrases: {", ".join(profile.lexical.recurring_phrases[:5])}
Structural: {profile.structural.paragraph_style}, avg sentence length: {profile.structural.avg_sentence_length:.0f} words
Opens with: {", ".join(profile.structural.opening_patterns[:3])}
Closes with: {", ".join(profile.structural.closing_patterns[:3])}
Tone: {profile.tonal.warmth_level} warmth, {profile.tonal.humor_usage} humor, {profile.tonal.conviction_style} conviction
"""

    if references:
        ref_posts = "\n---\n".join(
            [
                f"[{r.get('source_type', 'post')}] {r.get('text', '')[:500]}..."
                if len(r.get("text", "")) > 500
                else f"[{r.get('source_type', 'post')}] {r.get('text', '')}"
                for r in references[:5]
            ]
        )
    else:
        ref_posts = "\n---\n".join(profile.example_posts[:3])

    system = GENERATOR_SYSTEM.format(
        platform=profile.platform.value,
        author=profile.author,
        voice_profile=voice_summary,
        reference_posts=ref_posts,
        virality_pct=int(virality * 100),
    )

    word_limit_instruction = ""
    if word_limit:
        word_limit_instruction = f"\nTarget length: approximately {word_limit} words. Stay close to this limit."

    user = f"""Generate a {profile.platform.value} post for {profile.author}.

Topic: {topic}
Angle: {angle if angle else "Choose the best angle for engagement"}{word_limit_instruction}

Write the post now:"""

    return system, user
```

- [ ] **Step 2: Verify the change compiles**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/api && uv run python -c "from writer_api.prompts.templates import build_generator_prompt; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add packages/api/src/writer_api/prompts/templates.py
git commit -m "feat(api): add word_limit parameter to prompt builder"
```

---

### Task 3: Pass word_limit Through Generator Service

**Files:**
- Modify: `packages/api/src/writer_api/services/generator.py:28-34`

- [ ] **Step 1: Update generate method to pass word_limit**

Replace the prompt building section in the `generate` method:

```python
        system, user = build_generator_prompt(
            profile=profile,
            topic=request.topic,
            angle=request.angle or "",
            references=ref_dicts,
            virality=request.virality,
            word_limit=request.word_limit,
        )
```

- [ ] **Step 2: Verify the change compiles**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/api && uv run python -c "from writer_api.services.generator import GeneratorService; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Test the API locally**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/api && uv run uvicorn writer_api.main:app --port 8000 &`

Then test:
```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"author":"sam_altman","platform":"linkedin","topic":"AI","word_limit":50}' | head -c 500
```

Expected: A JSON response with a short ~50 word post

- [ ] **Step 4: Commit**

```bash
git add packages/api/src/writer_api/services/generator.py
git commit -m "feat(api): pass word_limit to prompt builder in generate"
```

---

### Task 4: Add word_limit to Frontend API Types

**Files:**
- Modify: `packages/web/src/lib/api.ts:7-13`

- [ ] **Step 1: Add word_limit to GenerateRequest interface**

```typescript
export interface GenerateRequest {
  author: string;
  platform: "twitter" | "linkedin";
  topic: string;
  angle?: string;
  virality?: number;
  word_limit?: number;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/web && npm run build 2>&1 | tail -5`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/lib/api.ts
git commit -m "feat(web): add word_limit to GenerateRequest type"
```

---

### Task 5: Add Word Limit UI Control to Generate Form

**Files:**
- Modify: `packages/web/src/components/generate-form.tsx`

- [ ] **Step 1: Add wordLimit state**

After line 20 (after `const [virality, setVirality] = useState(15);`), add:

```typescript
  const [wordLimit, setWordLimit] = useState<number | null>(null);
```

- [ ] **Step 2: Update handleSubmit to include word_limit**

Replace the `onSubmit` call in `handleSubmit`:

```typescript
    onSubmit({
      author,
      platform,
      topic,
      angle: angle || undefined,
      virality: virality / 100,
      word_limit: wordLimit || undefined,
    });
```

- [ ] **Step 3: Add Word Limit UI section**

After the Virality section (after line 162 `</div>`), add:

```tsx
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
            Word Limit{" "}
            <span className="text-muted-foreground/70 font-medium normal-case tracking-normal">
              (optional)
            </span>
          </label>
          <span className="text-sm font-bold tabular-nums text-foreground">
            {wordLimit ? `~${wordLimit}` : "Auto"}
          </span>
        </div>
        <div className="flex gap-2">
          {[null, 50, 100, 150, 200].map((limit) => (
            <button
              key={limit ?? "auto"}
              type="button"
              onClick={() => setWordLimit(limit)}
              className={cn(
                "flex-1 rounded-lg border px-2 py-2 text-xs font-semibold transition-all",
                wordLimit === limit
                  ? "border-foreground bg-foreground text-white"
                  : "border-border bg-white text-muted-foreground hover:border-muted-foreground hover:text-foreground"
              )}
            >
              {limit ? `${limit}` : "Auto"}
            </button>
          ))}
        </div>
        <p className="text-[10px] leading-relaxed text-muted-foreground">
          Target word count for the generated post
        </p>
      </div>
```

- [ ] **Step 4: Verify the component compiles**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/web && npm run build 2>&1 | tail -10`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add packages/web/src/components/generate-form.tsx
git commit -m "feat(web): add word limit selector to generate form"
```

---

### Task 6: Deploy and Test End-to-End

**Files:**
- No file changes

- [ ] **Step 1: Deploy API to Coolify**

```bash
cd /Users/shydev/mini-projects/writer-profile/packages/api
cp -r ../../data/profiles data/
# DEPLOY: pushed to main → Coolify auto-builds (project: cadence)
```

Wait for deployment to complete:
```bash
sleep 30 && # Coolify dashboard: https://coolify.ayushworks.com
```

- [ ] **Step 2: Test API word limit**

```bash
curl -s "https://coolify-backend/api/generate" \
  -X POST -H "Content-Type: application/json" \
  -d '{"author":"sam_altman","platform":"linkedin","topic":"AI progress","word_limit":50}' | jq -r '.text' | wc -w
```

Expected: Word count roughly around 50 (40-60 range)

- [ ] **Step 3: Build and deploy frontend**

```bash
cd /Users/shydev/mini-projects/writer-profile/packages/web
rm -rf .next out
NEXT_OUTPUT=export npm run build
npx wrangler pages deploy out --project-name=writer-profile --commit-dirty=true
```

- [ ] **Step 4: Test in browser**

Navigate to https://writer-profile.pages.dev/generate
- Verify word limit buttons appear below Virality slider
- Select "50" word limit
- Generate a post
- Verify the generated post is approximately 50 words

- [ ] **Step 5: Commit word limit feature**

```bash
git add -A
git commit -m "feat: add word limit feature to post generation"
```

---

### Task 7: Add Sources to API Response

**Files:**
- Modify: `packages/api/src/writer_api/models/responses.py:6-12`
- Modify: `packages/api/src/writer_api/services/generator.py:39-45`

- [ ] **Step 1: Add Source model and sources field to GenerateResponse**

Update `packages/api/src/writer_api/models/responses.py`:

```python
from pydantic import BaseModel, Field

from writer_api.models.voice import Platform, VoiceProfile


class Source(BaseModel):
    title: str
    url: str
    source_type: str


class GenerateResponse(BaseModel):
    text: str
    author: str
    platform: Platform
    validation_ok: bool = True
    validation_issues: list[str] = Field(default_factory=list)
    sources_used: int = 0
    sources: list[Source] = Field(default_factory=list)


class ProfileResponse(BaseModel):
    profile: VoiceProfile
    post_count: int = 0


class ProfileListResponse(BaseModel):
    profiles: list[dict[str, str]]
```

- [ ] **Step 2: Update generator to return source details**

In `packages/api/src/writer_api/services/generator.py`, update the return statement in `generate` method:

```python
from writer_api.models.responses import GenerateResponse, Source

# ... in generate method, before the return:

        sources = [
            Source(
                title=r.title or r.url,
                url=r.url,
                source_type=r.source_type,
            )
            for r in references
            if r.url
        ]

        return GenerateResponse(
            text=text,
            author=request.author,
            platform=request.platform,
            validation_ok=True,
            sources_used=len(references),
            sources=sources,
        )
```

- [ ] **Step 3: Verify the change compiles**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/api && uv run python -c "from writer_api.services.generator import GeneratorService; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add packages/api/src/writer_api/models/responses.py packages/api/src/writer_api/services/generator.py
git commit -m "feat(api): return source details in generate response"
```

---

### Task 8: Add Streaming Endpoint for Real-Time Progress

**Files:**
- Modify: `packages/api/src/writer_api/routes/generate.py`
- Modify: `packages/api/src/writer_api/services/generator.py`

- [ ] **Step 1: Add SSE streaming endpoint to routes**

Add to `packages/api/src/writer_api/routes/generate.py`:

```python
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from writer_api.models.requests import GenerateRequest, RevoiceRequest
from writer_api.models.responses import GenerateResponse
from writer_api.services.generator import GeneratorService
from writer_api.services.profile_store import ProfileStore

router = APIRouter()

_generator = GeneratorService()
_profiles = ProfileStore()


@router.post("/generate", response_model=GenerateResponse)
async def generate_post(request: GenerateRequest) -> GenerateResponse:
    """Generate a post in a CEO's voice."""
    profile = _profiles.load(request.author, request.platform)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No voice profile found for {request.author} on {request.platform.value}",
        )
    return _generator.generate(request, profile)


@router.post("/generate/stream")
async def generate_post_stream(request: GenerateRequest):
    """Generate a post with real-time progress updates via SSE."""
    profile = _profiles.load(request.author, request.platform)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No voice profile found for {request.author} on {request.platform.value}",
        )

    async def event_stream():
        async for event in _generator.generate_stream(request, profile):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/revoice", response_model=GenerateResponse)
async def revoice_post(request: RevoiceRequest) -> GenerateResponse:
    """Re-voice an edited draft in a CEO's voice."""
    profile = _profiles.load(request.author, request.platform)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No voice profile found for {request.author} on {request.platform.value}",
        )
    return _generator.revoice(request, profile)
```

- [ ] **Step 2: Add generate_stream method to GeneratorService**

Add to `packages/api/src/writer_api/services/generator.py`:

```python
from typing import AsyncGenerator

# Add this method to the GeneratorService class:

    async def generate_stream(
        self, request: GenerateRequest, profile: VoiceProfile
    ) -> AsyncGenerator[dict, None]:
        """Generate a post with streaming progress updates."""
        author_name = profile.author.replace("_", " ").title()

        yield {"step": "searching", "message": "Searching for relevant content..."}

        references = self._retriever.search_for_generation(
            author_name=author_name,
            platform=request.platform,
            topic=request.topic,
            k=5,
        )

        yield {
            "step": "sources_found",
            "message": f"Found {len(references)} sources",
            "sources": [
                {"title": r.title or r.url, "url": r.url, "source_type": r.source_type}
                for r in references
                if r.url
            ],
        }

        yield {"step": "generating", "message": "Generating post with AI..."}

        ref_dicts = [{"text": r.text, "source_type": r.source_type} for r in references]

        system, user = build_generator_prompt(
            profile=profile,
            topic=request.topic,
            angle=request.angle or "",
            references=ref_dicts,
            virality=request.virality,
            word_limit=request.word_limit,
        )

        response = self._llm.complete(system=system, user=user)
        text = response.text.strip().strip('"').strip("'")

        yield {
            "step": "complete",
            "message": "Generation complete!",
            "result": {
                "text": text,
                "author": request.author,
                "platform": request.platform.value,
                "validation_ok": True,
                "sources_used": len(references),
                "sources": [
                    {"title": r.title or r.url, "url": r.url, "source_type": r.source_type}
                    for r in references
                    if r.url
                ],
            },
        }
```

- [ ] **Step 3: Verify the change compiles**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/api && uv run python -c "from writer_api.routes.generate import router; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add packages/api/src/writer_api/routes/generate.py packages/api/src/writer_api/services/generator.py
git commit -m "feat(api): add SSE streaming endpoint for real-time progress"
```

---

### Task 9: Create Animated SVG Progress Components

**Files:**
- Create: `packages/web/src/components/progress-animation.tsx`

- [ ] **Step 1: Create the progress animation component**

Create `packages/web/src/components/progress-animation.tsx`:

```tsx
"use client";

import { cn } from "@/lib/utils";

interface ProgressAnimationProps {
  step: "idle" | "searching" | "sources_found" | "generating" | "complete";
  className?: string;
}

export function ProgressAnimation({ step, className }: ProgressAnimationProps) {
  return (
    <div className={cn("flex flex-col items-center gap-4", className)}>
      <div className="relative h-24 w-24">
        {/* Outer rotating ring */}
        <svg
          className={cn(
            "absolute inset-0 h-24 w-24",
            step !== "idle" && step !== "complete" && "animate-spin"
          )}
          style={{ animationDuration: "3s" }}
          viewBox="0 0 100 100"
        >
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeDasharray="70 200"
            className={cn(
              "transition-colors duration-300",
              step === "idle" ? "text-muted" : "text-primary/30"
            )}
          />
        </svg>

        {/* Inner pulsing circle */}
        <svg className="absolute inset-0 h-24 w-24" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="35"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            className={cn(
              "transition-all duration-500",
              step === "idle" && "text-muted",
              step === "searching" && "text-amber-500 animate-pulse",
              step === "sources_found" && "text-blue-500",
              step === "generating" && "text-purple-500 animate-pulse",
              step === "complete" && "text-emerald-500"
            )}
          />
        </svg>

        {/* Center icon */}
        <div className="absolute inset-0 flex items-center justify-center">
          {step === "idle" && <IdleIcon />}
          {step === "searching" && <SearchIcon />}
          {step === "sources_found" && <SourcesIcon />}
          {step === "generating" && <SparklesIcon />}
          {step === "complete" && <CheckIcon />}
        </div>
      </div>

      {/* Progress steps */}
      <div className="flex items-center gap-2">
        <ProgressDot active={step !== "idle"} complete={["sources_found", "generating", "complete"].includes(step)} />
        <ProgressLine active={["sources_found", "generating", "complete"].includes(step)} />
        <ProgressDot active={["sources_found", "generating", "complete"].includes(step)} complete={["generating", "complete"].includes(step)} />
        <ProgressLine active={["generating", "complete"].includes(step)} />
        <ProgressDot active={["generating", "complete"].includes(step)} complete={step === "complete"} />
      </div>
    </div>
  );
}

function ProgressDot({ active, complete }: { active: boolean; complete: boolean }) {
  return (
    <div
      className={cn(
        "h-3 w-3 rounded-full transition-all duration-300",
        !active && "bg-muted",
        active && !complete && "bg-primary/50 animate-pulse",
        complete && "bg-primary"
      )}
    />
  );
}

function ProgressLine({ active }: { active: boolean }) {
  return (
    <div
      className={cn(
        "h-0.5 w-8 transition-all duration-500",
        active ? "bg-primary" : "bg-muted"
      )}
    />
  );
}

function IdleIcon() {
  return (
    <svg className="h-8 w-8 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg className="h-8 w-8 text-amber-500 animate-bounce" style={{ animationDuration: "1s" }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8" />
      <path d="M21 21l-4.35-4.35" strokeLinecap="round" />
    </svg>
  );
}

function SourcesIcon() {
  return (
    <svg className="h-8 w-8 text-blue-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 19.5A2.5 2.5 0 016.5 17H20" strokeLinecap="round" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
      <path d="M8 7h8M8 11h8M8 15h4" strokeLinecap="round" />
    </svg>
  );
}

function SparklesIcon() {
  return (
    <svg className="h-8 w-8 text-purple-500" viewBox="0 0 24 24" fill="currentColor">
      <path className="animate-pulse" style={{ animationDelay: "0ms" }} d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8L12 2z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="h-8 w-8 text-emerald-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
      <path d="M5 12l5 5L20 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
```

- [ ] **Step 2: Verify the component compiles**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/web && npm run build 2>&1 | tail -5`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/components/progress-animation.tsx
git commit -m "feat(web): add animated SVG progress components"
```

---

### Task 10: Update Frontend API to Support Streaming

**Files:**
- Modify: `packages/web/src/lib/api.ts`

- [ ] **Step 1: Add Source type and streaming function**

Update `packages/web/src/lib/api.ts`:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getApiBase() {
  return API_BASE;
}

export interface Source {
  title: string;
  url: string;
  source_type: string;
}

export interface GenerateRequest {
  author: string;
  platform: "twitter" | "linkedin";
  topic: string;
  angle?: string;
  virality?: number;
  word_limit?: number;
}

export interface GenerateResponse {
  text: string;
  author: string;
  platform: string;
  validation_ok: boolean;
  validation_issues: string[];
  sources_used: number;
  sources: Source[];
}

export interface StreamEvent {
  step: "searching" | "sources_found" | "generating" | "complete";
  message: string;
  sources?: Source[];
  result?: GenerateResponse;
}

export interface Profile {
  author: string;
  platform: string;
}

export async function generatePost(
  req: GenerateRequest
): Promise<GenerateResponse> {
  const response = await fetch(`${API_BASE}/api/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(req),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to generate post");
  }

  return response.json();
}

export async function* generatePostStream(
  req: GenerateRequest
): AsyncGenerator<StreamEvent> {
  const response = await fetch(`${API_BASE}/api/generate/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(req),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to generate post");
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = JSON.parse(line.slice(6));
        yield data as StreamEvent;
      }
    }
  }
}

export async function revoicePost(
  author: string,
  platform: "twitter" | "linkedin",
  editedDraft: string
): Promise<GenerateResponse> {
  const response = await fetch(`${API_BASE}/api/revoice`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      author,
      platform,
      edited_draft: editedDraft,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to re-voice post");
  }

  return response.json();
}

export async function listProfiles(): Promise<Profile[]> {
  const response = await fetch(`${API_BASE}/api/profiles`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to list profiles");
  }

  const data = await response.json();
  return data.profiles;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/web && npm run build 2>&1 | tail -5`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/lib/api.ts
git commit -m "feat(web): add streaming API support and Source type"
```

---

### Task 11: Update Draft Display to Show Sources

**Files:**
- Modify: `packages/web/src/components/draft-display.tsx`

- [ ] **Step 1: Add sources panel to draft display**

Update `packages/web/src/components/draft-display.tsx`:

```tsx
"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import type { GenerateResponse, Source } from "@/lib/api";
import { CopyIcon, CheckIcon, RefreshIcon, FileIcon } from "./icons";
import { ProgressAnimation } from "./progress-animation";

interface DraftDisplayProps {
  draft: GenerateResponse | null;
  onRevoice: (editedText: string) => void;
  isRevoicing: boolean;
  isGenerating: boolean;
  progressStep?: "idle" | "searching" | "sources_found" | "generating" | "complete";
  progressMessage?: string;
  previewSources?: Source[];
}

export function DraftDisplay({
  draft,
  onRevoice,
  isRevoicing,
  isGenerating,
  progressStep = "idle",
  progressMessage,
  previewSources,
}: DraftDisplayProps) {
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState("");
  const [showSources, setShowSources] = useState(false);

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
  const sources = draft?.sources || previewSources || [];

  if (!draft && !isGenerating) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border bg-card p-8 sm:p-12">
        <ProgressAnimation step="idle" />
        <p className="mt-5 text-base font-medium text-foreground">
          Your post will appear here
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          Fill out the form and click generate
        </p>
      </div>
    );
  }

  if (isGenerating && !draft) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-border bg-card p-8 sm:p-12">
        <ProgressAnimation step={progressStep} />
        <p className="mt-5 text-base font-medium text-foreground">
          {progressMessage || "Generating your post..."}
        </p>
        {previewSources && previewSources.length > 0 && (
          <div className="mt-4 w-full max-w-md">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Sources Found
            </p>
            <div className="space-y-1">
              {previewSources.slice(0, 3).map((source, i) => (
                <a
                  key={i}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block truncate rounded-lg bg-muted/50 px-3 py-2 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  {source.title}
                </a>
              ))}
            </div>
          </div>
        )}
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
              draft?.platform === "linkedin"
                ? "bg-blue-50 text-blue-600"
                : "bg-sky-50 text-sky-600"
            )}
          >
            {draft?.platform}
          </span>
          {sources.length > 0 && (
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              <span>{sources.length} sources</span>
              <svg
                className={cn("h-3 w-3 transition-transform", showSources && "rotate-180")}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>
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

      {showSources && sources.length > 0 && (
        <div className="border-b border-border bg-muted/30 px-5 py-3">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            Sources Used
          </p>
          <div className="space-y-1.5">
            {sources.map((source, i) => (
              <a
                key={i}
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs hover:bg-muted"
              >
                <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {source.source_type}
                </span>
                <span className="flex-1 truncate text-foreground">{source.title}</span>
                <svg className="h-3 w-3 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3" />
                </svg>
              </a>
            ))}
          </div>
        </div>
      )}

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
            {draft?.text}
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
              setEditedText(draft?.text || "");
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
```

- [ ] **Step 2: Verify the component compiles**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/web && npm run build 2>&1 | tail -5`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/components/draft-display.tsx
git commit -m "feat(web): add sources panel and progress animation to draft display"
```

---

### Task 12: Update Generate Page to Use Streaming

**Files:**
- Modify: `packages/web/src/app/generate/page.tsx`

- [ ] **Step 1: Update page to use streaming API with progress state**

Update `packages/web/src/app/generate/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { GenerateForm } from "@/components/generate-form";
import { DraftDisplay } from "@/components/draft-display";
import {
  generatePostStream,
  revoicePost,
  type GenerateRequest,
  type GenerateResponse,
  type Source,
} from "@/lib/api";

type ProgressStep = "idle" | "searching" | "sources_found" | "generating" | "complete";

export default function GeneratePage() {
  const [draft, setDraft] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isRevoicing, setIsRevoicing] = useState(false);
  const [currentRequest, setCurrentRequest] = useState<GenerateRequest | null>(null);
  const [progressStep, setProgressStep] = useState<ProgressStep>("idle");
  const [progressMessage, setProgressMessage] = useState("");
  const [previewSources, setPreviewSources] = useState<Source[]>([]);

  const handleGenerate = async (request: GenerateRequest) => {
    setIsGenerating(true);
    setError(null);
    setCurrentRequest(request);
    setDraft(null);
    setProgressStep("idle");
    setPreviewSources([]);

    try {
      for await (const event of generatePostStream(request)) {
        setProgressStep(event.step);
        setProgressMessage(event.message);

        if (event.sources) {
          setPreviewSources(event.sources);
        }

        if (event.step === "complete" && event.result) {
          setDraft(event.result);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate post");
    } finally {
      setIsGenerating(false);
      setProgressStep("idle");
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
            progressStep={progressStep}
            progressMessage={progressMessage}
            previewSources={previewSources}
          />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify the page compiles**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/web && npm run build 2>&1 | tail -10`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/app/generate/page.tsx
git commit -m "feat(web): integrate streaming progress in generate page"
```

---

### Task 13: Final Deploy and Test

**Files:**
- No file changes

- [ ] **Step 1: Copy profiles and deploy API**

```bash
cd /Users/shydev/mini-projects/writer-profile/packages/api
cp -r ../../data/profiles data/
# DEPLOY: pushed to main → Coolify auto-builds (project: cadence)
```

- [ ] **Step 2: Wait for deployment and test streaming endpoint**

```bash
sleep 45 && curl -N "https://coolify-backend/api/generate/stream" \
  -X POST -H "Content-Type: application/json" \
  -d '{"author":"sam_altman","platform":"linkedin","topic":"AI","word_limit":50}'
```

Expected: Multiple `data:` events showing progress steps

- [ ] **Step 3: Build and deploy frontend**

```bash
cd /Users/shydev/mini-projects/writer-profile/packages/web
rm -rf .next out
NEXT_OUTPUT=export npm run build
npx wrangler pages deploy out --project-name=writer-profile --commit-dirty=true
```

- [ ] **Step 4: Test in browser**

Navigate to https://writer-profile.pages.dev/generate
- Verify animated progress indicator appears during generation
- Verify sources appear in real-time as they're found
- Verify word limit selector works
- Verify sources panel is expandable after generation
- Click a source link to verify it opens correctly

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete word limit, sources, and progress UI features"
```
