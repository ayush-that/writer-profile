# Embeddings + Mixture of Experts

## Goal

Upgrade the writer-profile generator from "static prompt + Exa" to a system that:

1. **Semantically retrieves the most relevant scraped posts** (Chroma vector DB) for any given topic, not just random `example_posts`
2. **Combines retrieved-own-posts + Exa real-time web** as hybrid context
3. **Generates N candidate posts in parallel** using a mixture of experts (Claude Sonnet, Gemini, Mistral via OpenRouter)
4. **Scores candidates with a different mixture of judges** on voice match + virality + authenticity
5. **Returns the winner** (plus losing candidates + scores for transparency)

The user already has `CHROMA_API_KEY`, `CHROMA_HOST`, `CHROMA_TENANT`, `CHROMA_DATABASE`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `MISTRAL_API_KEY` in `.env`. We have **1,622 LinkedIn posts** in `packages/api/data/profiles/*linkedin.json` and ~489 across other profiles, all sitting in `example_posts` arrays — currently not searchable.

## Architecture

```
                        ┌──────────────────┐
  topic + author ─────► │  HybridRetriever │
                        ├──────────────────┤
                        │ • Chroma (own)   │── 5 most-similar own posts
                        │ • Exa (web)      │── 5 fresh web mentions
                        └──────────────────┘
                                  │
                                  ▼
                        ┌──────────────────┐
                        │   MoE Generator  │── parallel
                        ├──────────────────┤
                        │ Claude Sonnet 4.6│──┐
                        │ Gemini 2.5 Pro   │──┼─► N candidates
                        │ Mistral Large    │──┘
                        └──────────────────┘
                                  │
                                  ▼
                        ┌──────────────────┐
                        │   MoE Judge      │── parallel
                        ├──────────────────┤
                        │ Claude (voice)   │──┐
                        │ Gemini (virality)│──┼─► aggregated scores
                        │ Mistral (authen) │──┘
                        └──────────────────┘
                                  │
                                  ▼
                          Winner + losers + scores
```

## Files to create

```
packages/api/src/writer_api/services/
├── embeddings.py        # OpenAI/Gemini embedding wrapper
├── chroma_store.py      # Chroma client + index/query
├── hybrid_retriever.py  # Chroma + Exa fusion
├── moe_generator.py     # parallel multi-LLM generation
├── moe_judge.py         # parallel multi-LLM scoring
└── llm.py               # EXTEND: add Gemini, OpenRouter, Mistral clients

packages/api/src/writer_api/models/
└── moe.py               # Candidate, JudgeScore, MoEResponse

packages/api/src/writer_api/routes/
└── generate.py          # ADD: POST /api/generate/moe

packages/api/src/writer_api/prompts/
└── templates.py         # ADD: build_judge_prompt(...)

scripts/
└── index_posts.py       # one-shot: scan profiles → embed → upload to Chroma

packages/api/src/writer_api/config.py  # ADD: chroma_*, gemini_*, openrouter_*, mistral_* settings
packages/api/pyproject.toml            # ADD: chromadb, google-genai, mistralai
```

## Step-by-step

### Step 1 — Settings + LLM clients (foundation)

- `config.py`: add `chroma_api_key`, `chroma_host`, `chroma_tenant`, `chroma_database`, `gemini_api_key`, `openrouter_api_key`, `mistral_api_key`, `embedding_model = "text-embedding-3-small"` (or Gemini equivalent), `chroma_collection = "ceo_posts"`
- `services/llm.py`: add `GeminiClient`, `OpenRouterClient`, `MistralClient` — same `LLMClient` ABC, same `LLMResponse` dataclass. Update `get_llm_client` factory to dispatch by provider name.

### Step 2 — Embeddings + Chroma store

- `services/embeddings.py`: thin wrapper exposing `embed(texts: list[str]) -> list[list[float]]`. Default to OpenAI `text-embedding-3-small` (1536d) — falls back to Gemini if `OPENAI_API_KEY` missing.
- `services/chroma_store.py`:
  - `ChromaStore(collection_name)` using `chromadb.HttpClient` with cloud creds
  - `upsert_posts(posts: list[Post])` — `Post = {id, text, author, platform, source_type, published_date}`
  - `query(text: str, k: int, where: dict | None) -> list[QueryResult]` — supports metadata filter (e.g., `{"author": "sam_altman", "platform": "twitter"}`)

### Step 3 — Index existing posts (one-shot script)

- `scripts/index_posts.py`:
  - Walk `packages/api/data/profiles/*.json`
  - For each `example_posts[i]`, build doc id = `f"{author}__{platform}__{i}"`
  - Embed in batches of 100, upsert to Chroma with metadata
  - Idempotent: use deterministic IDs so re-runs replace, not duplicate
- Run it once to populate the cloud DB

### Step 4 — Hybrid retriever

- `services/hybrid_retriever.py`:
  - `HybridRetriever(chroma_store, exa_retriever)`
  - `retrieve(author, platform, topic, k_own=5, k_web=3) -> RetrievedBundle`
  - `RetrievedBundle = {own_posts: [...], web_posts: [...]}`
  - Chroma query is filtered to `author + platform`; Exa is open-ended web search for fresh context
- Update `prompts/templates.py` `build_generator_prompt` to take a `RetrievedBundle` and present own-posts vs web-posts as labeled sections (so the LLM knows which is voice-reference vs current-events).

### Step 5 — MoE generator

- `models/moe.py`: `Candidate(text, model, latency_ms, input_tokens, output_tokens)`, `JudgeScore(model, voice_match: float, virality: float, authenticity: float, rationale: str)`, `MoEResponse(winner: Candidate, candidates: list[Candidate], scores: list[JudgeScore], hybrid_context_summary: dict)`
- `services/moe_generator.py`:
  - `MoEGenerator(experts: list[LLMClient])` — defaults to `[Claude, Gemini, Mistral]` based on which API keys are set
  - `generate(profile, request, bundle) -> list[Candidate]` — `asyncio.gather` parallel LLM calls (use thread executor since SDKs are sync), capture latency
  - Reuses existing `build_generator_prompt`

### Step 6 — MoE judge

- `prompts/templates.py`: add `build_judge_prompt(profile, candidate, references)` — returns system+user prompt that asks for JSON: `{"voice_match": 0-1, "virality": 0-1, "authenticity": 0-1, "rationale": "..."}`
- `services/moe_judge.py`:
  - `MoEJudge(judges: list[LLMClient])` — different mix than generators (e.g., Claude+Gemini+Mistral but with different system prompts → "voice critic", "virality critic", "authenticity critic")
  - `score(candidate, profile, bundle) -> list[JudgeScore]`
  - `score_all(candidates, profile, bundle) -> dict[Candidate, list[JudgeScore]]`
  - `pick_winner(scored) -> Candidate` — weighted aggregate (voice × 0.5 + authenticity × 0.3 + virality × 0.2)

### Step 7 — Wire into API

- `services/generator.py`: extend with `generate_moe(request, profile) -> MoEResponse` that calls `HybridRetriever.retrieve` → `MoEGenerator.generate` → `MoEJudge.score_all` → `pick_winner`
- `routes/generate.py`: add `POST /api/generate/moe` returning `MoEResponse`
- Keep the legacy `POST /api/generate` working unchanged

### Step 8 — Tests + smoke

- Tests in `packages/api/tests/`:
  - `test_embeddings.py` — mock OpenAI, assert vector shape
  - `test_chroma_store.py` — use in-memory Chroma client (no cloud) for unit, integration test gated on `CHROMA_API_KEY`
  - `test_hybrid_retriever.py` — mock both stores
  - `test_moe_generator.py` — mock LLM clients, verify parallel + N candidates
  - `test_moe_judge.py` — mock judges, verify scoring + winner selection
- Smoke: hit the new endpoint with a real request to `sam_altman/twitter`

## Risk + non-goals

- **Cost**: each MoE call ≈ 3 generators + 9 judge calls = 12 LLM calls per request. Cap parallel candidates at 3, judges at 3 (so 3+9=12 max). Add a `moe_enabled: bool` request flag so callers can opt out.
- **Latency**: parallel keeps it under ~5s wall-clock if the slowest model finishes in time.
- **Cold start**: the indexing script must run before the first MoE call returns useful Chroma results. Until then, fall back to `example_posts` from the profile.
- **Not in scope**: streaming, caching of embeddings, fine-tuning, voice-profile re-extraction. Those come later.

## Subagent dispatch plan

Three independent batches that can run in parallel without stepping on each other:

1. **Batch A (foundation)** → `python-sdk` agent: settings + LLM clients (Gemini, OpenRouter, Mistral) + embeddings wrapper
2. **Batch B (storage)** → `python-sdk` agent: Chroma store + indexing script
3. **Batch C (MoE core)** → `python-sdk` agent: hybrid retriever + MoE generator + MoE judge + wiring

Then a sequential finishing pass (this agent) to:
- Run the indexing script
- Add the route
- Smoke test
- Commit
