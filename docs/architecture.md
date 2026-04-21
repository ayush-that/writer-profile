# CEO Voice Agent — Architecture

## Overview

Retrieval-augmented generation with a hybrid statistical/LLM voice profile, author-derived platform constraints, a dialable virality layer, and a Self-Refine loop. Multi-tenant via an `author` field on every `Post`.

## Modules

| Module | Responsibility |
|---|---|
| `corpus` | Post / Idea / metadata pydantic models, JSONL loader, Haiku metadata extractor, ingest helper |
| `retrieval` | Sentence-transformer embedder + Chroma persistent store with `(author, platform, tone)` filtering |
| `voice` | `VoiceStats` (deterministic) + LLM synthesis extractor + `VoiceProfile` schema + JSON file store |
| `platforms` | `Constraint` protocol, Twitter + LinkedIn constraints, per-author constraint derivation |
| `virality` | `HookLibrary` with 40 seed hook patterns, dialable injection strength |
| `generation` | Generator (few-shot + profile + hooks), Self-Refine loop, thread splitter, revoice |
| `eval` | LLM-as-judge, archetype sample generator |
| `pipeline` | Composition layer: `generate()` and `revoice()` endpoints |
| `cli` | Typer commands: `ingest`, `profile build/show/list`, `generate`, `revoice`, `samples`, `evaluate` |
| `app.py` | Streamlit UI wrapping the pipeline |

## Voice Profile Engine

Hybrid approach — stats feed LLM synthesis:
1. `compute_stats(posts)` produces a deterministic `VoiceStats` fingerprint (sentence-length percentiles, emoji/hashtag/question/URL/mention rates, top-k openers/closers, bigrams/trigrams, thread rate).
2. `build_voice_profile` passes the stats JSON + a sample of the longest posts to Sonnet with a schema-constrained prompt, which returns a JSON object covering lexical/structural/rhetorical/tonal dimensions.
3. The final `VoiceProfile` is the union: deterministic stats + LLM synthesis + canonical examples.
4. Stored as `profiles/<author>__<platform>.json`. Updatable by re-running `profile build`.

Rationale: pure stats don't translate to prompt behavior well; pure LLM synthesis hallucinates traits that the numbers contradict. Grounding the synthesis in the stats block keeps the LLM honest.

## Constraint derivation

`constraint_for(profile)` reads the profile's stats and builds a `Constraint`:
- Hashtags allowed only if `hashtag_rate >= 5%`.
- No hardcoded case requirement — the voice profile drives case behavior via prompt examples.
- `max_hashtags` scaled from author's `avg_hashtags_per_post`.

This replaces the original project's hardcoded personal-style rules.

## Virality layer

Hand-curated 40-entry `hooks.jsonl` instead of a full clustering pipeline. Each entry has `platform`, `pattern_type`, `template`. `suggest(platform, k)` returns `k` hooks spanning distinct pattern types. `render_injection(hooks, virality_strength)` emits one of three prompt bands based on strength (off / subtle / strong-preference).

Scope decision: spec's "cluster top-100 posts" is a multi-week subproject; a hand-curated library gives the dialable-influence property the spec explicitly asks for at <1% of the build cost.

## Re-voicing

Reuses generation pipeline infrastructure (LLM client, constraint, profile). Dedicated `build_revoice_prompt` enforces structural preservation: explicit rules to preserve paragraph count, relative order of noun phrases, and structural intent. The refine loop is not used for revoicing; one LLM call with a tight prompt is enough because the human provided the structure.

## Evaluation

- **LLM-as-judge**: Sonnet scores each candidate on voice_fidelity (1–10) + naturalness (1–10) with written reasoning + flagged AI tics. Reference corpus = up to 20 real posts by the author.
- **Manual rubric**: `samples` command generates 5 posts per platform across archetypes (product launch, acquisition, earnings, personal reflection, industry commentary) and writes a markdown sheet with per-post scoring blanks.

## Onboarding a new CEO

1. Drop JSONL of their posts at `data/posts/<author>.jsonl`.
2. `writer ingest data/posts/<author>.jsonl --author <author>`
3. `writer profile build --author <author> --platform twitter --source data/posts/<author>.jsonl`
4. `writer profile build --author <author> --platform linkedin --source data/posts/<author>.jsonl`
5. Generate via CLI or UI.

No code changes required. That's the spec's constraint met.

## What worked

- Reusing the existing refine loop (renamed conceptually but structurally identical) for critic-driven revision.
- Grounding the LLM voice extractor in deterministic stats eliminated hallucinated traits in early tests.
- Per-author `Constraint` derivation cleanly killed the original hardcoded personal-style rules.

## What didn't

- Chroma's `where` clause API is awkward for `$and` over 3 fields; we flatten to single-clause dicts when only one filter is active.
- Pydantic BaseModel + dataclass mixing forced a conversion of `VoiceStats` to BaseModel (dataclass stats wouldn't JSON-roundtrip through `VoiceProfile`).

## Scaling to more CEOs

- Per-author Chroma collections if cross-author retrieval noise becomes an issue; currently one collection with `author` filter is fine at O(10^3) posts per author.
- Profile refresh is idempotent: re-running `profile build` overwrites the JSON. Incremental refresh (append new posts) would require storing the post-ids-seen set.

## Known limitations (V1)

- No thread generation via pipeline yet — `Thread` + `split_thread` exist, but `GenerationPipeline.generate` only returns single posts. Thread generation is one prompt template + a post-split validation pass away; deferred.
- No persona-diverse critics; single-critic Self-Refine has the diminishing-returns pattern noted in the research.
- Evaluation is LLM-judge only in V1 code; manual scoring uses the sheet output.
