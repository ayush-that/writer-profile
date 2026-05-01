# Voice Tells: Em-Dash + Emoji Mimicry

## Goal

Stop the generator from emitting em-dashes (`—`, `–`, `--`) or emojis when the author doesn't use them. These are the two strongest "this was written by an LLM" signals. Treat each independently.

## Evidence (audit of current `example_posts`)

| author/platform | posts | em-dash rate | emoji rate |
|---|---|---|---|
| sam_altman/twitter | 58 | **36.2%** | 0.0% |
| sam_altman/linkedin | 178 | 41.6% | 18.5% |
| elon_musk/twitter | 20 | **0.0%** | **0.0%** |
| elon_musk/linkedin | 228 | 32.5% | 16.7% |
| guillermo_rauch/twitter | 20 | 0.0% | 25.0% |
| dario_amodei/twitter | 47 | 53.2% | 2.1% |
| ... | | | |

**Two patterns emerge:**

1. **Twitter posts are clean** — most authors use 0% em-dashes on Twitter (Sam Altman is the outlier at 36% — but his sample includes Anthropic-style news quotes). Real per-author signal for Twitter.
2. **LinkedIn is contaminated** — 30-48% em-dash rates because most LinkedIn `example_posts` are scraped news articles ABOUT the author, not posts BY them. The "voice profile" we're learning includes journalism style. **This is a data-quality bug we'll flag but not fix in this PR.**

So the rule needs to be: detect rate per (author, platform), apply hard ban if rate < threshold, log a warning when LinkedIn rates look "journalism-like" (>20%).

## Architecture

```
profile.example_posts
        │
        ▼
┌──────────────────────┐
│ VoiceTellExtractor   │  per (author, platform)
│ - em_dash_rate       │
│ - emoji_rate         │
│ - threshold = 0.05   │
└──────────────────────┘
        │
        ▼
   VoiceTells(em_dash_forbidden, emoji_forbidden)
        │
        ├─► injected as HARD RULES in generator prompt
        ├─► judge gets the rules + penalizes voice_match if violated
        └─► post-process sanitizer enforces as last-resort safety net
```

## Files

```
packages/api/src/writer_api/services/
└── voice_tells.py        # NEW: extract + sanitize

packages/api/src/writer_api/models/
└── voice.py              # EXTEND: add VoiceTells model (optional field on VoiceProfile)

packages/api/src/writer_api/prompts/
└── templates.py          # EXTEND: inject FORBIDDEN PUNCTUATION/EMOJI section
                          #         in build_generator_prompt + build_generator_prompt_hybrid
                          #         + build_judge_prompt

packages/api/src/writer_api/services/
├── generator.py          # WIRE: extract tells per request, sanitize output
├── moe_generator.py      # WIRE: same
└── moe_judge.py          # WIRE: pass tells into judge prompt

packages/api/tests/
└── test_voice_tells.py   # NEW: extraction + sanitization tests
```

## Step-by-step

### Step 1 — `services/voice_tells.py`

```python
from __future__ import annotations
import re
from dataclasses import dataclass

EM_DASH_CHARS = ("—", "–", "--")
EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF"   # symbols & pictographs
    r"\U00002700-\U000027BF"    # dingbats
    r"\U0001F600-\U0001F64F"    # emoticons
    r"\U0001F680-\U0001F6FF]"   # transport & map
)

EM_DASH_THRESHOLD = 0.05   # if author uses em-dash in <5% of posts → forbid
EMOJI_THRESHOLD = 0.05


@dataclass
class VoiceTells:
    em_dash_rate: float
    emoji_rate: float
    em_dash_forbidden: bool
    emoji_forbidden: bool
    sample_size: int


def extract_tells(posts: list[str]) -> VoiceTells:
    posts = [p for p in posts if p and p.strip()]
    if not posts:
        return VoiceTells(0.0, 0.0, em_dash_forbidden=True, emoji_forbidden=True, sample_size=0)
    em = sum(1 for p in posts if any(t in p for t in EM_DASH_CHARS))
    emj = sum(1 for p in posts if EMOJI_RE.search(p))
    em_rate = em / len(posts)
    emj_rate = emj / len(posts)
    return VoiceTells(
        em_dash_rate=em_rate,
        emoji_rate=emj_rate,
        em_dash_forbidden=em_rate < EM_DASH_THRESHOLD,
        emoji_forbidden=emj_rate < EMOJI_THRESHOLD,
        sample_size=len(posts),
    )


def sanitize_output(text: str, tells: VoiceTells) -> str:
    """Last-resort enforcement: rewrite forbidden punctuation/emojis."""
    out = text
    if tells.em_dash_forbidden:
        # Replace em-dash with comma+space; en-dash with hyphen; double-hyphen with comma
        out = out.replace(" — ", ", ").replace("—", ",")
        out = out.replace(" – ", ", ").replace("–", "-")
        out = out.replace(" -- ", ", ").replace("--", ",")
    if tells.emoji_forbidden:
        out = EMOJI_RE.sub("", out)
    # Collapse double-spaces / orphan punctuation introduced by replacements
    out = re.sub(r"\s+", " ", out).replace(" ,", ",").replace(" .", ".")
    out = re.sub(r",,+", ",", out)
    return out.strip()
```

### Step 2 — Update `models/voice.py`

Add an optional `VoiceTells` Pydantic model (mirror the dataclass). Don't make it required — it's computed lazily from `example_posts` in the generator path; we don't store it in profile JSONs (yet).

### Step 3 — Update `prompts/templates.py`

In both `build_generator_prompt` AND `build_generator_prompt_hybrid`, accept an optional `tells: VoiceTells | None` param. When present, insert a `## HARD RULES` section right above `## Guidelines`:

```
## HARD RULES — MUST FOLLOW
{author} writes {sample_size} posts. Of those:
- {em_dash_pct}% use em-dashes (—, –, --)
- {emoji_pct}% use emojis

{em_dash_rule}
{emoji_rule}

Violating these rules makes the post obviously LLM-generated. Use periods, commas, and plain text instead.
```

Where:
- `em_dash_rule` = `"FORBIDDEN: em-dashes (—, –, --). Replace with periods or commas."` if `em_dash_forbidden`
- `emoji_rule` = `"FORBIDDEN: emojis. Use plain text only."` if `emoji_forbidden`
- If neither is forbidden, skip the whole HARD RULES section.

In `build_judge_prompt`, append to the `voice_match` definition:
> Penalize heavily (set voice_match ≤ 0.3) if the candidate uses em-dashes when the author doesn't, or emojis when the author doesn't.

Also pass `tells` to `build_judge_prompt` and surface the rates in the system prompt.

### Step 4 — Wire into generator paths

**`services/generator.py`** (legacy path):
- Compute `tells = extract_tells(profile.example_posts)` once per request
- Pass to `build_generator_prompt`
- After LLM response, run `sanitize_output(text, tells)` before returning

**`services/moe_generator.py`** (MoE path):
- Same: compute tells, pass to `build_generator_prompt_hybrid`, sanitize each candidate's text before yielding

**`services/moe_judge.py`**:
- Accept `tells` and pass to `build_judge_prompt`

### Step 5 — Tests

`packages/api/tests/test_voice_tells.py`:

- `extract_tells` on posts with 0% em-dash → `em_dash_forbidden = True`
- `extract_tells` on posts with 50% em-dash → `em_dash_forbidden = False`
- `extract_tells` on empty list → both forbidden, sample_size 0
- `sanitize_output("hello — world", forbidden=True)` → `"hello, world"` (no double-space)
- `sanitize_output("nice 🚀 launch", emoji_forbidden=True)` → `"nice launch"` (no double-space)
- `sanitize_output` is no-op when nothing forbidden
- `sanitize_output` doesn't break URLs containing `--` (edge case: it shouldn't — URLs use `--` rarely in our domain)

### Step 6 — Smoke test

Run the MoE endpoint with an author known to NOT use em-dashes (Elon on Twitter, Sam on Twitter), confirm:
1. Output has zero em-dashes
2. The HARD RULES block appears in the system prompt (log it)
3. Judges score voice_match high (≥ 0.7) on clean candidates

## Threshold tuning

`5%` chosen because it gives a clean signal on Twitter data while not over-filtering on LinkedIn (which is contaminated). Future work: when we clean the LinkedIn `example_posts` to be actual posts (not news scrapes), bump threshold to 10-15%.

## Out of scope

- Fixing the LinkedIn `example_posts` data quality (filter out scraped news). Track separately.
- Other AI tells: "delve into", "it's important to note", overly-balanced "X but also Y" framing. Could extend `VoiceTells` later.
- Profile-time pre-computation + caching (right now we recompute per request — fast enough since we're checking ~200 strings).

## Subagent dispatch

Single batch — files are tightly coupled, parallelism would create merge conflicts. Dispatch one agent to do the whole thing.
