# Word Limit Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a word limit option to the generate page so users can specify target post length.

**Architecture:** Add optional `word_limit` field to API request model, incorporate it into the LLM prompt with clear instructions, and add a UI input in the generate form with sensible presets.

**Tech Stack:** FastAPI + Pydantic (backend), React + TypeScript (frontend)

---

## File Structure

| File | Responsibility |
|------|----------------|
| `packages/api/src/writer_api/models/requests.py` | Add `word_limit` field to GenerateRequest |
| `packages/api/src/writer_api/prompts/templates.py` | Update prompt to include word limit instruction |
| `packages/api/src/writer_api/services/generator.py` | Pass word_limit to prompt builder |
| `packages/web/src/lib/api.ts` | Add `word_limit` to GenerateRequest interface |
| `packages/web/src/components/generate-form.tsx` | Add word limit input UI |

---

### Task 1: Add Word Limit to API Request Model

**Files:**
- Modify: `packages/api/src/writer_api/models/requests.py`

- [ ] **Step 1: Add word_limit field to GenerateRequest**

Edit `packages/api/src/writer_api/models/requests.py`:

```python
from pydantic import BaseModel, Field

from writer_api.models.voice import Platform


class GenerateRequest(BaseModel):
    author: str
    platform: Platform
    topic: str
    angle: str = ""
    virality: float = Field(0.15, ge=0.0, le=1.0)
    word_limit: int | None = Field(None, ge=20, le=1000)


class RevoiceRequest(BaseModel):
    author: str
    platform: Platform
    edited_draft: str
```

- [ ] **Step 2: Verify API still starts**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/api && uv run python -c "from writer_api.models.requests import GenerateRequest; print('OK')"`
Expected: "OK"

- [ ] **Step 3: Commit**

```bash
git add packages/api/src/writer_api/models/requests.py
git commit -m "feat(api): add word_limit field to GenerateRequest"
```

---

### Task 2: Update Prompt Template and Generator Service

**Files:**
- Modify: `packages/api/src/writer_api/prompts/templates.py`
- Modify: `packages/api/src/writer_api/services/generator.py`

- [ ] **Step 1: Update build_generator_prompt to accept word_limit**

Edit `packages/api/src/writer_api/prompts/templates.py`. Update the function:

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

    word_limit_instruction = ""
    if word_limit:
        word_limit_instruction = f"\n- TARGET LENGTH: Approximately {word_limit} words. Stay close to this target."

    system = GENERATOR_SYSTEM.format(
        platform=profile.platform.value,
        author=profile.author,
        voice_profile=voice_summary,
        reference_posts=ref_posts,
        virality_pct=int(virality * 100),
    )
    
    # Insert word limit instruction before virality section
    if word_limit_instruction:
        system = system.replace(
            "## Virality Enhancement",
            f"{word_limit_instruction}\n\n## Virality Enhancement"
        )

    user = f"""Generate a {profile.platform.value} post for {profile.author}.

Topic: {topic}
Angle: {angle if angle else "Choose the best angle for engagement"}

Write the post now:"""

    return system, user
```

- [ ] **Step 2: Update generator service to pass word_limit**

Edit `packages/api/src/writer_api/services/generator.py`. Update the generate method:

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

- [ ] **Step 3: Verify imports work**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/api && uv run python -c "from writer_api.services.generator import GeneratorService; print('OK')"`
Expected: "OK"

- [ ] **Step 4: Commit**

```bash
git add packages/api/src/writer_api/prompts/templates.py packages/api/src/writer_api/services/generator.py
git commit -m "feat(api): add word_limit to generator prompt"
```

---

### Task 3: Add Word Limit to Frontend

**Files:**
- Modify: `packages/web/src/lib/api.ts`
- Modify: `packages/web/src/components/generate-form.tsx`

- [ ] **Step 1: Add word_limit to GenerateRequest interface**

Edit `packages/web/src/lib/api.ts`. Update the interface:

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

- [ ] **Step 2: Add wordLimit state to generate-form.tsx**

Edit `packages/web/src/components/generate-form.tsx`. After line 20 (`const [virality, setVirality] = useState(15);`), add:

```tsx
const [wordLimit, setWordLimit] = useState<number | null>(null);

const WORD_PRESETS = [
  { label: "Auto", value: null },
  { label: "Short (~50)", value: 50 },
  { label: "Medium (~150)", value: 150 },
  { label: "Long (~300)", value: 300 },
];
```

- [ ] **Step 3: Update handleSubmit**

Edit `packages/web/src/components/generate-form.tsx`. Update handleSubmit:

```tsx
const handleSubmit = (e: React.FormEvent) => {
  e.preventDefault();
  if (!author || !topic) return;

  onSubmit({
    author,
    platform,
    topic,
    angle: angle || undefined,
    virality: virality / 100,
    word_limit: wordLimit || undefined,
  });
};
```

- [ ] **Step 4: Add word limit UI**

Edit `packages/web/src/components/generate-form.tsx`. Add after the virality section (after the closing `</div>` around line 162), before the submit button:

```tsx
      <div className="space-y-3">
        <label className="text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
          Post Length
        </label>
        <div className="flex gap-2">
          {WORD_PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              onClick={() => setWordLimit(preset.value)}
              className={cn(
                "flex-1 rounded-xl border-2 px-3 py-2.5 text-xs font-semibold transition-all",
                wordLimit === preset.value
                  ? "border-foreground bg-foreground text-white"
                  : "border-border bg-white text-muted-foreground hover:border-muted-foreground hover:text-foreground"
              )}
            >
              {preset.label}
            </button>
          ))}
        </div>
        <p className="text-[10px] leading-relaxed text-muted-foreground">
          Target word count for the generated post
        </p>
      </div>
```

- [ ] **Step 5: Verify build**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/web && npm run build 2>&1 | tail -10`
Expected: Build succeeds

- [ ] **Step 6: Commit**

```bash
git add packages/web/src/lib/api.ts packages/web/src/components/generate-form.tsx
git commit -m "feat(web): add word limit selector to generate form"
```

---

### Task 4: Deploy and Test

**Files:**
- No new files

- [ ] **Step 1: Deploy API to Railway**

```bash
cd /Users/shydev/mini-projects/writer-profile/packages/api
railway up --detach --service writer-profile-api
```

- [ ] **Step 2: Build and deploy frontend**

```bash
cd /Users/shydev/mini-projects/writer-profile/packages/web
rm -rf .next out
NEXT_OUTPUT=export npm run build
npx wrangler pages deploy out --project-name=writer-profile --commit-dirty=true
```

- [ ] **Step 3: Test in browser**

Navigate to https://writer-profile.pages.dev/generate
- Verify "Post Length" selector appears below Virality
- Select "Short (~50)" and generate - verify output is approximately 50 words
- Select "Long (~300)" and generate - verify output is approximately 300 words
- Select "Auto" - verify it works without word limit constraint
