# Writer Profile Monorepo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform writer-profile into a monorepo with a FastAPI backend and a sleek Next.js frontend, simplifying architecture by using Exa for real-time content retrieval instead of local RAG.

**Architecture:** Exa-first approach - use Exa's search API to retrieve CEO content (LinkedIn posts, news, interviews) at generation time rather than pre-embedding into ChromaDB. This eliminates vector DB maintenance, reduces cold-start time for new CEOs, and keeps content fresh. Voice profiles remain as structured JSON. Frontend uses Next.js 14 with dark theme inspired by modern SaaS dashboards (Momentum, Liquidity Dashboard patterns from Behance).

**Tech Stack:**
- Backend: FastAPI, Pydantic, Exa API, Claude/OpenAI (configurable)
- Frontend: Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Framer Motion
- Monorepo: pnpm workspaces, Turborepo
- Infrastructure: Docker, Coolify (backend) + Cloudflare Pages (frontend)

---

## Scope Check

This plan covers three independent but related subsystems:
1. **Monorepo Setup** - Project restructuring and tooling
2. **Backend API** - FastAPI server with simplified Exa-based retrieval
3. **Frontend Web** - Next.js dashboard UI

Each produces working, testable software on its own.

---

## File Structure

```
writer-profile/
├── packages/
│   ├── api/                          # FastAPI backend
│   │   ├── src/
│   │   │   ├── writer_api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main.py           # FastAPI app entry
│   │   │   │   ├── config.py         # Settings via pydantic-settings
│   │   │   │   ├── routes/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── generate.py   # POST /generate, POST /revoice
│   │   │   │   │   ├── profiles.py   # GET/POST /profiles
│   │   │   │   │   └── health.py     # GET /health
│   │   │   │   ├── services/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── exa_retriever.py    # Exa search for CEO content
│   │   │   │   │   ├── voice_extractor.py  # Build voice profiles
│   │   │   │   │   ├── generator.py        # Draft generation
│   │   │   │   │   └── llm.py              # LLM client abstraction
│   │   │   │   ├── models/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── requests.py   # API request models
│   │   │   │   │   ├── responses.py  # API response models
│   │   │   │   │   └── voice.py      # VoiceProfile model
│   │   │   │   └── prompts/
│   │   │   │       ├── __init__.py
│   │   │   │       └── templates.py  # Generation prompts
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   └── web/                          # Next.js frontend
│       ├── src/
│       │   ├── app/
│       │   │   ├── layout.tsx
│       │   │   ├── page.tsx          # Dashboard home
│       │   │   ├── generate/
│       │   │   │   └── page.tsx      # Generation UI
│       │   │   └── profiles/
│       │   │       └── page.tsx      # Profile management
│       │   ├── components/
│       │   │   ├── ui/               # shadcn components
│       │   │   ├── sidebar.tsx
│       │   │   ├── generate-form.tsx
│       │   │   ├── draft-editor.tsx
│       │   │   └── profile-card.tsx
│       │   ├── lib/
│       │   │   ├── api.ts            # API client
│       │   │   └── utils.ts
│       │   └── styles/
│       │       └── globals.css
│       ├── package.json
│       ├── tailwind.config.ts
│       ├── tsconfig.json
│       └── next.config.js
│
├── data/                             # Shared data (voice profiles, hooks)
│   ├── profiles/
│   └── hooks.jsonl
├── turbo.json
├── pnpm-workspace.yaml
├── package.json
└── docker-compose.yml
```

---

## Task 1: Initialize Monorepo Structure

**Files:**
- Create: `pnpm-workspace.yaml`
- Create: `package.json` (root)
- Create: `turbo.json`
- Create: `packages/api/pyproject.toml`
- Create: `packages/web/package.json`

- [ ] **Step 1.1: Create pnpm workspace config**

```yaml
# pnpm-workspace.yaml
packages:
  - "packages/*"
```

- [ ] **Step 1.2: Create root package.json**

```json
{
  "name": "writer-profile",
  "private": true,
  "scripts": {
    "dev": "turbo run dev",
    "build": "turbo run build",
    "lint": "turbo run lint",
    "api:dev": "cd packages/api && uv run uvicorn writer_api.main:app --reload --port 8000",
    "web:dev": "cd packages/web && pnpm dev"
  },
  "devDependencies": {
    "turbo": "^2.0.0"
  },
  "packageManager": "pnpm@9.0.0"
}
```

- [ ] **Step 1.3: Create turbo.json**

```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "dist/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "lint": {}
  }
}
```

- [ ] **Step 1.4: Create packages directories**

Run: `mkdir -p packages/api/src/writer_api packages/web/src`
Expected: Directories created

- [ ] **Step 1.5: Create API pyproject.toml**

```toml
[project]
name = "writer-api"
version = "0.1.0"
description = "CEO Voice Agent API"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn>=0.30.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.5.0",
    "exa-py>=1.0.0",
    "anthropic>=0.40.0",
    "openai>=1.40.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "ruff>=0.6.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/writer_api"]
```

- [ ] **Step 1.6: Initialize git and verify structure**

Run: `ls -la packages/`
Expected: `api/` and `web/` directories listed

- [ ] **Step 1.7: Commit monorepo structure**

```bash
git add pnpm-workspace.yaml package.json turbo.json packages/
git commit -m "chore: initialize monorepo structure with pnpm workspaces"
```

---

## Task 2: Build FastAPI Backend - Core Setup

**Files:**
- Create: `packages/api/src/writer_api/__init__.py`
- Create: `packages/api/src/writer_api/main.py`
- Create: `packages/api/src/writer_api/config.py`

- [ ] **Step 2.1: Create API __init__.py**

```python
# packages/api/src/writer_api/__init__.py
__version__ = "0.1.0"
```

- [ ] **Step 2.2: Create config.py with settings**

```python
# packages/api/src/writer_api/config.py
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    exa_api_key: SecretStr = Field(alias="EXA_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    
    llm_provider: str = "anthropic"  # "anthropic" or "openai"
    llm_model: str = "claude-sonnet-4-6"
    
    profiles_path: str = "../../data/profiles"
    hooks_path: str = "../../data/hooks.jsonl"
    
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
```

- [ ] **Step 2.3: Create main.py FastAPI app**

```python
# packages/api/src/writer_api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from writer_api.config import settings
from writer_api.routes import generate, profiles, health

app = FastAPI(
    title="Writer Profile API",
    description="CEO Voice Agent - Generate authentic social media content",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(generate.router, prefix="/api", tags=["generate"])
app.include_router(profiles.router, prefix="/api", tags=["profiles"])
```

- [ ] **Step 2.4: Test API starts**

Run: `cd packages/api && uv sync && uv run uvicorn writer_api.main:app --reload --port 8000`
Expected: Server starts on port 8000

- [ ] **Step 2.5: Commit core API setup**

```bash
git add packages/api/
git commit -m "feat(api): add FastAPI core setup with config"
```

---

## Task 3: Build API - Models and Routes

**Files:**
- Create: `packages/api/src/writer_api/models/__init__.py`
- Create: `packages/api/src/writer_api/models/requests.py`
- Create: `packages/api/src/writer_api/models/responses.py`
- Create: `packages/api/src/writer_api/models/voice.py`
- Create: `packages/api/src/writer_api/routes/__init__.py`
- Create: `packages/api/src/writer_api/routes/health.py`
- Create: `packages/api/src/writer_api/routes/generate.py`
- Create: `packages/api/src/writer_api/routes/profiles.py`

- [ ] **Step 3.1: Create models/__init__.py**

```python
# packages/api/src/writer_api/models/__init__.py
from writer_api.models.requests import GenerateRequest, RevoiceRequest
from writer_api.models.responses import GenerateResponse, ProfileResponse
from writer_api.models.voice import VoiceProfile, Platform

__all__ = [
    "GenerateRequest",
    "RevoiceRequest", 
    "GenerateResponse",
    "ProfileResponse",
    "VoiceProfile",
    "Platform",
]
```

- [ ] **Step 3.2: Create voice.py model**

```python
# packages/api/src/writer_api/models/voice.py
from enum import Enum
from pydantic import BaseModel


class Platform(str, Enum):
    twitter = "twitter"
    linkedin = "linkedin"


class LexicalPatterns(BaseModel):
    vocabulary_level: str
    recurring_phrases: list[str]
    word_preferences: dict[str, str]
    jargon_usage: str
    technicality_level: str


class StructuralHabits(BaseModel):
    avg_sentence_length: float
    paragraph_style: str
    opening_patterns: list[str]
    closing_patterns: list[str]
    uses_lists: bool
    uses_questions: bool


class TonalRegister(BaseModel):
    warmth_level: str
    humor_usage: str
    personal_disclosure: str
    conviction_style: str


class VoiceProfile(BaseModel):
    author: str
    platform: Platform
    lexical: LexicalPatterns
    structural: StructuralHabits
    tonal: TonalRegister
    example_posts: list[str]
```

- [ ] **Step 3.3: Create requests.py**

```python
# packages/api/src/writer_api/models/requests.py
from pydantic import BaseModel, Field
from writer_api.models.voice import Platform


class GenerateRequest(BaseModel):
    author: str = Field(..., description="CEO identifier (e.g., 'ali_ghodsi')")
    platform: Platform
    topic: str = Field(..., description="Topic or subject of the post")
    angle: str = Field("", description="Narrative direction or angle")
    virality: float = Field(0.15, ge=0.0, le=1.0, description="Virality hook strength")


class RevoiceRequest(BaseModel):
    author: str
    platform: Platform
    edited_draft: str = Field(..., description="Human-edited draft to re-voice")
```

- [ ] **Step 3.4: Create responses.py**

```python
# packages/api/src/writer_api/models/responses.py
from pydantic import BaseModel
from writer_api.models.voice import VoiceProfile, Platform


class GenerateResponse(BaseModel):
    text: str
    author: str
    platform: Platform
    validation_ok: bool
    validation_issues: list[str] = []
    sources_used: int = 0


class ProfileResponse(BaseModel):
    profile: VoiceProfile
    post_count: int


class ProfileListResponse(BaseModel):
    profiles: list[dict[str, str]]
```

- [ ] **Step 3.5: Create routes/__init__.py**

```python
# packages/api/src/writer_api/routes/__init__.py
```

- [ ] **Step 3.6: Create health.py route**

```python
# packages/api/src/writer_api/routes/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "writer-api"}
```

- [ ] **Step 3.7: Create generate.py route (stub)**

```python
# packages/api/src/writer_api/routes/generate.py
from fastapi import APIRouter, HTTPException

from writer_api.models import GenerateRequest, RevoiceRequest, GenerateResponse, Platform

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate_post(request: GenerateRequest):
    # TODO: Implement with services
    return GenerateResponse(
        text="[Generated post will appear here]",
        author=request.author,
        platform=request.platform,
        validation_ok=True,
        sources_used=0,
    )


@router.post("/revoice", response_model=GenerateResponse)
async def revoice_post(request: RevoiceRequest):
    # TODO: Implement with services
    return GenerateResponse(
        text=request.edited_draft,
        author=request.author,
        platform=request.platform,
        validation_ok=True,
    )
```

- [ ] **Step 3.8: Create profiles.py route (stub)**

```python
# packages/api/src/writer_api/routes/profiles.py
from fastapi import APIRouter, HTTPException

from writer_api.models import ProfileResponse, Platform
from writer_api.models.responses import ProfileListResponse

router = APIRouter()


@router.get("/profiles")
async def list_profiles():
    # TODO: Load from filesystem
    return ProfileListResponse(profiles=[
        {"author": "ali_ghodsi", "platform": "linkedin"},
        {"author": "ali_ghodsi", "platform": "twitter"},
    ])


@router.get("/profiles/{author}/{platform}", response_model=ProfileResponse)
async def get_profile(author: str, platform: Platform):
    # TODO: Load from filesystem
    raise HTTPException(status_code=404, detail="Profile not found")
```

- [ ] **Step 3.9: Test routes work**

Run: `curl http://localhost:8000/health`
Expected: `{"status":"healthy","service":"writer-api"}`

- [ ] **Step 3.10: Commit models and routes**

```bash
git add packages/api/
git commit -m "feat(api): add models and route stubs"
```

---

## Task 4: Build API - Exa Retriever Service

**Files:**
- Create: `packages/api/src/writer_api/services/__init__.py`
- Create: `packages/api/src/writer_api/services/exa_retriever.py`

- [ ] **Step 4.1: Create services/__init__.py**

```python
# packages/api/src/writer_api/services/__init__.py
from writer_api.services.exa_retriever import ExaRetriever

__all__ = ["ExaRetriever"]
```

- [ ] **Step 4.2: Create exa_retriever.py**

```python
# packages/api/src/writer_api/services/exa_retriever.py
from dataclasses import dataclass
from datetime import datetime, timedelta

from exa_py import Exa

from writer_api.config import settings
from writer_api.models.voice import Platform


@dataclass
class RetrievedContent:
    text: str
    url: str
    title: str
    source_type: str
    published_date: datetime | None = None


class ExaRetriever:
    def __init__(self):
        self._client = Exa(api_key=settings.exa_api_key.get_secret_value())

    def search_linkedin_posts(
        self,
        author_name: str,
        linkedin_handle: str,
        max_results: int = 20,
    ) -> list[RetrievedContent]:
        results = self._client.search_and_contents(
            f"site:linkedin.com/posts/{linkedin_handle}",
            num_results=max_results,
            text=True,
            start_published_date=(datetime.now() - timedelta(days=365)).isoformat(),
        )
        return [
            RetrievedContent(
                text=r.text or "",
                url=r.url,
                title=r.title or "",
                source_type="linkedin",
                published_date=datetime.fromisoformat(r.published_date) if r.published_date else None,
            )
            for r in results.results
            if r.text
        ]

    def search_news(
        self,
        author_name: str,
        max_results: int = 15,
    ) -> list[RetrievedContent]:
        results = self._client.search_and_contents(
            f'"{author_name}" CEO interview OR keynote OR announcement',
            num_results=max_results,
            text=True,
            start_published_date=(datetime.now() - timedelta(days=365)).isoformat(),
        )
        return [
            RetrievedContent(
                text=r.text or "",
                url=r.url,
                title=r.title or "",
                source_type="news",
                published_date=datetime.fromisoformat(r.published_date) if r.published_date else None,
            )
            for r in results.results
            if r.text
        ]

    def search_for_generation(
        self,
        author_name: str,
        platform: Platform,
        topic: str,
        k: int = 5,
    ) -> list[RetrievedContent]:
        site = "linkedin.com" if platform == Platform.linkedin else "twitter.com OR x.com"
        query = f'site:{site} "{author_name}" {topic}'
        
        results = self._client.search_and_contents(
            query,
            num_results=k,
            text=True,
        )
        return [
            RetrievedContent(
                text=r.text or "",
                url=r.url,
                title=r.title or "",
                source_type=platform.value,
            )
            for r in results.results
            if r.text
        ]
```

- [ ] **Step 4.3: Test Exa retriever**

Run: `cd packages/api && uv run python -c "from writer_api.services import ExaRetriever; print('OK')"`
Expected: `OK`

- [ ] **Step 4.4: Commit Exa service**

```bash
git add packages/api/src/writer_api/services/
git commit -m "feat(api): add Exa retriever service for real-time content search"
```

---

## Task 5: Build API - LLM Service and Generator

**Files:**
- Create: `packages/api/src/writer_api/services/llm.py`
- Create: `packages/api/src/writer_api/services/generator.py`
- Create: `packages/api/src/writer_api/prompts/__init__.py`
- Create: `packages/api/src/writer_api/prompts/templates.py`

- [ ] **Step 5.1: Create llm.py abstraction**

```python
# packages/api/src/writer_api/services/llm.py
from abc import ABC, abstractmethod

from writer_api.config import settings


class LLMClient(ABC):
    @abstractmethod
    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.8,
    ) -> str:
        pass


class AnthropicClient(LLMClient):
    def __init__(self):
        import anthropic
        key = settings.anthropic_api_key
        if not key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self._client = anthropic.Anthropic(api_key=key.get_secret_value())

    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.8,
    ) -> str:
        response = self._client.messages.create(
            model=settings.llm_model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in response.content if b.type == "text")


class OpenAIClient(LLMClient):
    def __init__(self):
        from openai import OpenAI
        key = settings.openai_api_key
        if not key:
            raise ValueError("OPENAI_API_KEY not set")
        self._client = OpenAI(api_key=key.get_secret_value())

    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.8,
    ) -> str:
        response = self._client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


def get_llm_client() -> LLMClient:
    if settings.llm_provider == "openai":
        return OpenAIClient()
    return AnthropicClient()
```

- [ ] **Step 5.2: Create prompts/templates.py**

```python
# packages/api/src/writer_api/prompts/templates.py
from writer_api.models.voice import VoiceProfile, Platform
from writer_api.services.exa_retriever import RetrievedContent

GENERATOR_SYSTEM = """You are a ghostwriter who perfectly mimics a CEO's authentic voice for social media.

Your task: Generate a {platform} post that sounds exactly like {author} wrote it.

## Voice Profile
{voice_profile}

## Reference Posts (from their actual content)
{reference_posts}

## Guidelines
- Match their exact vocabulary, sentence patterns, and tone
- Use their typical opening and closing styles
- Match their formatting habits (line breaks, lists, questions)
- Keep the authentic feel - never sound corporate or generic
- For Twitter/X: stay within character limits, thread if needed
- For LinkedIn: match their typical post length and structure

## Virality Enhancement ({virality_pct}% influence)
Subtly incorporate high-performing structural patterns:
- Strong hook in first line
- Clear narrative arc
- Memorable closing

Output ONLY the post text, nothing else."""


def build_generator_prompt(
    profile: VoiceProfile,
    topic: str,
    angle: str,
    references: list[RetrievedContent],
    virality: float,
) -> tuple[str, str]:
    voice_summary = f"""
Lexical: {profile.lexical.vocabulary_level} vocabulary, technicality: {profile.lexical.technicality_level}
Recurring phrases: {', '.join(profile.lexical.recurring_phrases[:5])}
Structural: {profile.structural.paragraph_style}, avg sentence length: {profile.structural.avg_sentence_length:.0f} words
Opens with: {', '.join(profile.structural.opening_patterns[:3])}
Closes with: {', '.join(profile.structural.closing_patterns[:3])}
Tone: {profile.tonal.warmth_level} warmth, {profile.tonal.humor_usage} humor, {profile.tonal.conviction_style} conviction
"""
    
    ref_posts = "\n---\n".join([
        f"[{r.source_type}] {r.text[:500]}..." if len(r.text) > 500 else f"[{r.source_type}] {r.text}"
        for r in references[:5]
    ])
    
    if not ref_posts:
        ref_posts = "\n---\n".join(profile.example_posts[:3])
    
    system = GENERATOR_SYSTEM.format(
        platform=profile.platform.value,
        author=profile.author,
        voice_profile=voice_summary,
        reference_posts=ref_posts,
        virality_pct=int(virality * 100),
    )
    
    user = f"""Generate a {profile.platform.value} post for {profile.author}.

Topic: {topic}
Angle: {angle if angle else 'Choose the best angle for engagement'}

Write the post now:"""
    
    return system, user


REVOICE_SYSTEM = """You are a voice refinement expert. Your task is to take a human-edited draft and apply {author}'s authentic voice to it.

## Voice Profile
{voice_profile}

## Key Constraint
The human made structural choices intentionally. Preserve:
- Their paragraph organization
- Their key points and order
- Any specific phrasing they emphasized

Only refine the VOICE:
- Vocabulary choices
- Sentence rhythm
- Tonal register
- Opening/closing style

Output ONLY the refined post, nothing else."""
```

- [ ] **Step 5.3: Create prompts/__init__.py**

```python
# packages/api/src/writer_api/prompts/__init__.py
from writer_api.prompts.templates import build_generator_prompt, REVOICE_SYSTEM

__all__ = ["build_generator_prompt", "REVOICE_SYSTEM"]
```

- [ ] **Step 5.4: Create generator.py service**

```python
# packages/api/src/writer_api/services/generator.py
from writer_api.models import GenerateRequest, RevoiceRequest, GenerateResponse
from writer_api.models.voice import VoiceProfile
from writer_api.prompts import build_generator_prompt, REVOICE_SYSTEM
from writer_api.services.exa_retriever import ExaRetriever
from writer_api.services.llm import get_llm_client


class GeneratorService:
    def __init__(self):
        self._retriever = ExaRetriever()
        self._llm = get_llm_client()

    def generate(
        self,
        request: GenerateRequest,
        profile: VoiceProfile,
    ) -> GenerateResponse:
        references = self._retriever.search_for_generation(
            author_name=profile.author.replace("_", " ").title(),
            platform=request.platform,
            topic=request.topic,
            k=5,
        )
        
        system, user = build_generator_prompt(
            profile=profile,
            topic=request.topic,
            angle=request.angle,
            references=references,
            virality=request.virality,
        )
        
        text = self._llm.complete(system=system, user=user)
        text = text.strip().strip('"').strip("'")
        
        return GenerateResponse(
            text=text,
            author=request.author,
            platform=request.platform,
            validation_ok=True,
            sources_used=len(references),
        )

    def revoice(
        self,
        request: RevoiceRequest,
        profile: VoiceProfile,
    ) -> GenerateResponse:
        voice_summary = f"""
Author: {profile.author}
Platform: {profile.platform.value}
Tone: {profile.tonal.warmth_level} warmth, {profile.tonal.conviction_style} conviction
Style: {profile.structural.paragraph_style}
"""
        system = REVOICE_SYSTEM.format(
            author=profile.author,
            voice_profile=voice_summary,
        )
        user = f"Re-voice this draft:\n\n{request.edited_draft}"
        
        text = self._llm.complete(system=system, user=user)
        
        return GenerateResponse(
            text=text.strip(),
            author=request.author,
            platform=request.platform,
            validation_ok=True,
        )
```

- [ ] **Step 5.5: Update services/__init__.py**

```python
# packages/api/src/writer_api/services/__init__.py
from writer_api.services.exa_retriever import ExaRetriever
from writer_api.services.generator import GeneratorService
from writer_api.services.llm import get_llm_client

__all__ = ["ExaRetriever", "GeneratorService", "get_llm_client"]
```

- [ ] **Step 5.6: Commit LLM and generator services**

```bash
git add packages/api/
git commit -m "feat(api): add LLM abstraction and generator service with prompts"
```

---

## Task 6: Build API - Wire Routes to Services

**Files:**
- Modify: `packages/api/src/writer_api/routes/generate.py`
- Modify: `packages/api/src/writer_api/routes/profiles.py`
- Create: `packages/api/src/writer_api/services/profile_store.py`

- [ ] **Step 6.1: Create profile_store.py**

```python
# packages/api/src/writer_api/services/profile_store.py
import json
from pathlib import Path

from writer_api.config import settings
from writer_api.models.voice import VoiceProfile, Platform


class ProfileStore:
    def __init__(self):
        self._root = Path(settings.profiles_path)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, author: str, platform: Platform) -> Path:
        return self._root / f"{author}_{platform.value}.json"

    def load(self, author: str, platform: Platform) -> VoiceProfile | None:
        path = self._path(author, platform)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return VoiceProfile(**data)

    def save(self, profile: VoiceProfile) -> Path:
        path = self._path(profile.author, profile.platform)
        path.write_text(profile.model_dump_json(indent=2))
        return path

    def list_profiles(self) -> list[tuple[str, Platform]]:
        profiles = []
        for path in self._root.glob("*_*.json"):
            name = path.stem
            parts = name.rsplit("_", 1)
            if len(parts) == 2:
                author, plat = parts
                try:
                    profiles.append((author, Platform(plat)))
                except ValueError:
                    pass
        return profiles
```

- [ ] **Step 6.2: Update generate.py with real implementation**

```python
# packages/api/src/writer_api/routes/generate.py
from fastapi import APIRouter, HTTPException

from writer_api.models import GenerateRequest, RevoiceRequest, GenerateResponse
from writer_api.services.generator import GeneratorService
from writer_api.services.profile_store import ProfileStore

router = APIRouter()

_generator = GeneratorService()
_profiles = ProfileStore()


@router.post("/generate", response_model=GenerateResponse)
async def generate_post(request: GenerateRequest):
    profile = _profiles.load(request.author, request.platform)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No voice profile found for {request.author} on {request.platform.value}",
        )
    return _generator.generate(request, profile)


@router.post("/revoice", response_model=GenerateResponse)
async def revoice_post(request: RevoiceRequest):
    profile = _profiles.load(request.author, request.platform)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No voice profile found for {request.author} on {request.platform.value}",
        )
    return _generator.revoice(request, profile)
```

- [ ] **Step 6.3: Update profiles.py with real implementation**

```python
# packages/api/src/writer_api/routes/profiles.py
from fastapi import APIRouter, HTTPException

from writer_api.models import ProfileResponse, Platform
from writer_api.models.responses import ProfileListResponse
from writer_api.services.profile_store import ProfileStore

router = APIRouter()

_store = ProfileStore()


@router.get("/profiles", response_model=ProfileListResponse)
async def list_profiles():
    profiles = _store.list_profiles()
    return ProfileListResponse(
        profiles=[
            {"author": author, "platform": platform.value}
            for author, platform in profiles
        ]
    )


@router.get("/profiles/{author}/{platform}", response_model=ProfileResponse)
async def get_profile(author: str, platform: Platform):
    profile = _store.load(author, platform)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse(profile=profile, post_count=len(profile.example_posts))
```

- [ ] **Step 6.4: Test complete API**

Run: `curl -X POST http://localhost:8000/api/generate -H "Content-Type: application/json" -d '{"author":"ali_ghodsi","platform":"linkedin","topic":"AI agents"}'`
Expected: Either generated text or 404 (profile not found)

- [ ] **Step 6.5: Commit wired routes**

```bash
git add packages/api/
git commit -m "feat(api): wire routes to services with profile store"
```

---

## Task 7: Initialize Next.js Frontend

**Files:**
- Create: `packages/web/package.json`
- Create: `packages/web/tsconfig.json`
- Create: `packages/web/tailwind.config.ts`
- Create: `packages/web/next.config.js`
- Create: `packages/web/postcss.config.js`
- Create: `packages/web/src/app/layout.tsx`
- Create: `packages/web/src/app/page.tsx`
- Create: `packages/web/src/app/globals.css`

- [ ] **Step 7.1: Create package.json**

```json
{
  "name": "@writer-profile/web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "framer-motion": "^11.0.0",
    "lucide-react": "^0.400.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.3.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "@types/node": "^20.12.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

- [ ] **Step 7.2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 7.3: Create tailwind.config.ts**

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        "card-foreground": "hsl(var(--card-foreground))",
        primary: "hsl(var(--primary))",
        "primary-foreground": "hsl(var(--primary-foreground))",
        muted: "hsl(var(--muted))",
        "muted-foreground": "hsl(var(--muted-foreground))",
        accent: "hsl(var(--accent))",
        "accent-foreground": "hsl(var(--accent-foreground))",
        border: "hsl(var(--border))",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 7.4: Create globals.css with dark theme**

```css
/* packages/web/src/app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 240 10% 3.9%;
    --card: 0 0% 100%;
    --card-foreground: 240 10% 3.9%;
    --primary: 24 95% 53%;
    --primary-foreground: 0 0% 98%;
    --muted: 240 4.8% 95.9%;
    --muted-foreground: 240 3.8% 46.1%;
    --accent: 24 95% 53%;
    --accent-foreground: 240 5.9% 10%;
    --border: 240 5.9% 90%;
    --radius: 0.75rem;
  }

  .dark {
    --background: 240 10% 3.9%;
    --foreground: 0 0% 98%;
    --card: 240 10% 6%;
    --card-foreground: 0 0% 98%;
    --primary: 24 95% 53%;
    --primary-foreground: 240 5.9% 10%;
    --muted: 240 3.7% 15.9%;
    --muted-foreground: 240 5% 64.9%;
    --accent: 24 80% 50%;
    --accent-foreground: 0 0% 98%;
    --border: 240 3.7% 15.9%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

- [ ] **Step 7.5: Create next.config.js**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
```

- [ ] **Step 7.6: Create postcss.config.js**

```javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 7.7: Create layout.tsx**

```tsx
// packages/web/src/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Writer Profile | CEO Voice Agent",
  description: "Generate authentic social media content in any CEO's voice",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
```

- [ ] **Step 7.8: Create initial page.tsx**

```tsx
// packages/web/src/app/page.tsx
export default function Home() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-foreground mb-4">
          Writer Profile
        </h1>
        <p className="text-muted-foreground">
          CEO Voice Agent - Coming soon
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 7.9: Install dependencies and test**

Run: `cd packages/web && pnpm install && pnpm dev`
Expected: Next.js dev server starts on port 3000

- [ ] **Step 7.10: Commit frontend setup**

```bash
git add packages/web/
git commit -m "feat(web): initialize Next.js with dark theme and Tailwind"
```

---

## Task 8: Build Frontend - Sidebar Component

**Files:**
- Create: `packages/web/src/components/sidebar.tsx`
- Create: `packages/web/src/lib/utils.ts`

- [ ] **Step 8.1: Create utils.ts**

```typescript
// packages/web/src/lib/utils.ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 8.2: Create sidebar.tsx**

```tsx
// packages/web/src/components/sidebar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  PenLine,
  Users,
  LayoutDashboard,
  Settings,
  Sparkles,
} from "lucide-react";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Generate", href: "/generate", icon: PenLine },
  { name: "Profiles", href: "/profiles", icon: Users },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-border bg-card">
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 border-b border-border px-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-orange-500 to-amber-600">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <span className="text-lg font-semibold">Writer Profile</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-4">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <item.icon className="h-5 w-5" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="border-t border-border p-4">
          <div className="rounded-lg bg-muted/50 p-3">
            <p className="text-xs text-muted-foreground">
              Powered by Exa + Claude
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
```

- [ ] **Step 8.3: Update layout to include sidebar**

```tsx
// packages/web/src/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Writer Profile | CEO Voice Agent",
  description: "Generate authentic social media content in any CEO's voice",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <Sidebar />
        <main className="ml-64 min-h-screen bg-background p-8">
          {children}
        </main>
      </body>
    </html>
  );
}
```

- [ ] **Step 8.4: Update home page with dashboard**

```tsx
// packages/web/src/app/page.tsx
export default function Home() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Generate authentic CEO voice content
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="rounded-xl border border-border bg-card p-6">
          <p className="text-sm text-muted-foreground">Active Profiles</p>
          <p className="text-3xl font-bold mt-2">2</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-6">
          <p className="text-sm text-muted-foreground">Posts Generated</p>
          <p className="text-3xl font-bold mt-2">47</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-6">
          <p className="text-sm text-muted-foreground">Avg. Voice Score</p>
          <p className="text-3xl font-bold mt-2">4.2</p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h2 className="text-lg font-semibold mb-4">Quick Generate</h2>
        <p className="text-muted-foreground">
          Start generating content by visiting the Generate page.
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 8.5: Test sidebar and layout**

Run: `pnpm dev` (in packages/web)
Expected: Dark themed dashboard with sidebar visible

- [ ] **Step 8.6: Commit sidebar**

```bash
git add packages/web/
git commit -m "feat(web): add sidebar navigation and dashboard layout"
```

---

## Task 9: Build Frontend - Generate Page

**Files:**
- Create: `packages/web/src/app/generate/page.tsx`
- Create: `packages/web/src/components/generate-form.tsx`
- Create: `packages/web/src/components/draft-display.tsx`
- Create: `packages/web/src/lib/api.ts`

- [ ] **Step 9.1: Create api.ts client**

```typescript
// packages/web/src/lib/api.ts
export interface GenerateRequest {
  author: string;
  platform: "twitter" | "linkedin";
  topic: string;
  angle?: string;
  virality?: number;
}

export interface GenerateResponse {
  text: string;
  author: string;
  platform: string;
  validation_ok: boolean;
  validation_issues: string[];
  sources_used: number;
}

export interface Profile {
  author: string;
  platform: string;
}

export async function generatePost(req: GenerateRequest): Promise<GenerateResponse> {
  const res = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to generate");
  }
  return res.json();
}

export async function revoicePost(
  author: string,
  platform: "twitter" | "linkedin",
  editedDraft: string
): Promise<GenerateResponse> {
  const res = await fetch("/api/revoice", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      author,
      platform,
      edited_draft: editedDraft,
    }),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to revoice");
  }
  return res.json();
}

export async function listProfiles(): Promise<Profile[]> {
  const res = await fetch("/api/profiles");
  if (!res.ok) throw new Error("Failed to load profiles");
  const data = await res.json();
  return data.profiles;
}
```

- [ ] **Step 9.2: Create generate-form.tsx**

```tsx
// packages/web/src/components/generate-form.tsx
"use client";

import { useState, useEffect } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { listProfiles, type Profile } from "@/lib/api";

interface GenerateFormProps {
  onGenerate: (data: {
    author: string;
    platform: "twitter" | "linkedin";
    topic: string;
    angle: string;
    virality: number;
  }) => void;
  isLoading: boolean;
}

export function GenerateForm({ onGenerate, isLoading }: GenerateFormProps) {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [author, setAuthor] = useState("");
  const [platform, setPlatform] = useState<"twitter" | "linkedin">("linkedin");
  const [topic, setTopic] = useState("");
  const [angle, setAngle] = useState("");
  const [virality, setVirality] = useState(0.15);

  useEffect(() => {
    listProfiles().then(setProfiles).catch(console.error);
  }, []);

  const uniqueAuthors = [...new Set(profiles.map((p) => p.author))];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onGenerate({ author, platform, topic, angle, virality });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Author Select */}
      <div className="space-y-2">
        <label className="text-sm font-medium">CEO / Author</label>
        <select
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          className="w-full rounded-lg border border-border bg-card px-4 py-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          required
        >
          <option value="">Select a CEO...</option>
          {uniqueAuthors.map((a) => (
            <option key={a} value={a}>
              {a.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            </option>
          ))}
        </select>
      </div>

      {/* Platform Toggle */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Platform</label>
        <div className="flex gap-2">
          {(["linkedin", "twitter"] as const).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPlatform(p)}
              className={cn(
                "flex-1 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors",
                platform === p
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border text-muted-foreground hover:bg-muted"
              )}
            >
              {p === "linkedin" ? "LinkedIn" : "X (Twitter)"}
            </button>
          ))}
        </div>
      </div>

      {/* Topic */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Topic</label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g., AI agents transforming enterprise software"
          className="w-full rounded-lg border border-border bg-card px-4 py-2.5 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          required
        />
      </div>

      {/* Angle */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Angle (optional)</label>
        <textarea
          value={angle}
          onChange={(e) => setAngle(e.target.value)}
          placeholder="e.g., Personal story about early skepticism, now converted"
          rows={3}
          className="w-full rounded-lg border border-border bg-card px-4 py-2.5 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-none"
        />
      </div>

      {/* Virality Slider */}
      <div className="space-y-2">
        <label className="text-sm font-medium">
          Virality Enhancement: {Math.round(virality * 100)}%
        </label>
        <input
          type="range"
          min="0"
          max="100"
          value={virality * 100}
          onChange={(e) => setVirality(Number(e.target.value) / 100)}
          className="w-full accent-primary"
        />
        <p className="text-xs text-muted-foreground">
          Higher = more engagement-optimized hooks. Keep subtle (10-20%) for authenticity.
        </p>
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={isLoading || !author || !topic}
        className="w-full flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-orange-500 to-amber-600 px-4 py-3 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Generating...
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4" />
            Generate Post
          </>
        )}
      </button>
    </form>
  );
}
```

- [ ] **Step 9.3: Create draft-display.tsx**

```tsx
// packages/web/src/components/draft-display.tsx
"use client";

import { useState } from "react";
import { Copy, Check, RefreshCw, Loader2 } from "lucide-react";

interface DraftDisplayProps {
  text: string;
  platform: string;
  sourcesUsed: number;
  onRevoice: (editedText: string) => void;
  isRevoicing: boolean;
}

export function DraftDisplay({
  text,
  platform,
  sourcesUsed,
  onRevoice,
  isRevoicing,
}: DraftDisplayProps) {
  const [editedText, setEditedText] = useState(text);
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(editedText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRevoice = () => {
    onRevoice(editedText);
    setIsEditing(false);
  };

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Generated Draft</span>
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            {platform}
          </span>
          {sourcesUsed > 0 && (
            <span className="text-xs text-muted-foreground">
              {sourcesUsed} sources
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            {copied ? (
              <>
                <Check className="h-4 w-4" />
                Copied
              </>
            ) : (
              <>
                <Copy className="h-4 w-4" />
                Copy
              </>
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {isEditing ? (
          <textarea
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            className="w-full min-h-[200px] rounded-lg border border-border bg-background p-4 text-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-none"
          />
        ) : (
          <div
            className="prose prose-invert max-w-none whitespace-pre-wrap cursor-pointer hover:bg-muted/50 rounded-lg p-4 -m-4 transition-colors"
            onClick={() => setIsEditing(true)}
          >
            {editedText}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="border-t border-border px-4 py-3 flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          {isEditing ? "Edit the text, then re-voice to apply CEO style" : "Click text to edit"}
        </p>
        {isEditing && (
          <div className="flex gap-2">
            <button
              onClick={() => {
                setEditedText(text);
                setIsEditing(false);
              }}
              className="rounded-lg px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleRevoice}
              disabled={isRevoicing}
              className="flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {isRevoicing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Re-voicing...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4" />
                  Re-voice
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 9.4: Create generate page**

```tsx
// packages/web/src/app/generate/page.tsx
"use client";

import { useState } from "react";
import { GenerateForm } from "@/components/generate-form";
import { DraftDisplay } from "@/components/draft-display";
import { generatePost, revoicePost, type GenerateResponse } from "@/lib/api";

export default function GeneratePage() {
  const [isLoading, setIsLoading] = useState(false);
  const [isRevoicing, setIsRevoicing] = useState(false);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentRequest, setCurrentRequest] = useState<{
    author: string;
    platform: "twitter" | "linkedin";
  } | null>(null);

  const handleGenerate = async (data: {
    author: string;
    platform: "twitter" | "linkedin";
    topic: string;
    angle: string;
    virality: number;
  }) => {
    setIsLoading(true);
    setError(null);
    setCurrentRequest({ author: data.author, platform: data.platform });

    try {
      const response = await generatePost(data);
      setResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate");
    } finally {
      setIsLoading(false);
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
      setResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to revoice");
    } finally {
      setIsRevoicing(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Generate</h1>
        <p className="text-muted-foreground mt-1">
          Create authentic CEO voice content for social media
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Form */}
        <div className="rounded-xl border border-border bg-card p-6">
          <GenerateForm onGenerate={handleGenerate} isLoading={isLoading} />
        </div>

        {/* Result */}
        <div className="space-y-4">
          {error && (
            <div className="rounded-lg border border-red-500/50 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}
          
          {result && (
            <DraftDisplay
              text={result.text}
              platform={result.platform}
              sourcesUsed={result.sources_used}
              onRevoice={handleRevoice}
              isRevoicing={isRevoicing}
            />
          )}
          
          {!result && !error && (
            <div className="rounded-xl border border-dashed border-border p-12 text-center">
              <p className="text-muted-foreground">
                Generated content will appear here
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 9.5: Test generate page**

Run: `pnpm dev` (in packages/web)
Expected: Navigate to /generate, see form and empty result area

- [ ] **Step 9.6: Commit generate page**

```bash
git add packages/web/
git commit -m "feat(web): add generate page with form and draft display"
```

---

## Task 10: Create Sample Voice Profiles

**Files:**
- Create: `data/profiles/ali_ghodsi_linkedin.json`
- Create: `data/profiles/ali_ghodsi_twitter.json`

- [ ] **Step 10.1: Create data directory**

Run: `mkdir -p data/profiles`

- [ ] **Step 10.2: Create Ali Ghodsi LinkedIn profile**

```json
{
  "author": "ali_ghodsi",
  "platform": "linkedin",
  "lexical": {
    "vocabulary_level": "executive",
    "recurring_phrases": [
      "incredibly excited",
      "data + AI",
      "open source",
      "the future of",
      "proud of the team"
    ],
    "word_preferences": {
      "team": "team",
      "company": "Databricks",
      "customers": "customers"
    },
    "jargon_usage": "moderate",
    "technicality_level": "accessible-technical"
  },
  "structural": {
    "avg_sentence_length": 18,
    "paragraph_style": "short paragraphs with clear breaks",
    "opening_patterns": [
      "Exciting news!",
      "Today we announced",
      "I'm thrilled to share"
    ],
    "closing_patterns": [
      "The future is bright.",
      "Grateful for this team.",
      "More to come."
    ],
    "uses_lists": false,
    "uses_questions": true
  },
  "tonal": {
    "warmth_level": "warm and personal",
    "humor_usage": "occasional light humor",
    "personal_disclosure": "shares company journey and team praise",
    "conviction_style": "confident but humble"
  },
  "example_posts": [
    "Today we announced the acquisition of Tabular. This is a huge moment for open source data infrastructure. The teams behind Spark and Iceberg are now under one roof. The best technology wins when it's open.",
    "Incredibly proud of what this team has built. Databricks is now a $43B company, but what matters most is the impact we're having on how enterprises use data and AI.",
    "The future of AI is not about bigger models. It's about compound systems that orchestrate multiple models, retrieval, and tools together. This is what we've been building toward."
  ]
}
```

- [ ] **Step 10.3: Create Ali Ghodsi Twitter profile**

```json
{
  "author": "ali_ghodsi",
  "platform": "twitter",
  "lexical": {
    "vocabulary_level": "casual-technical",
    "recurring_phrases": [
      "big news",
      "data lakehouse",
      "open source wins"
    ],
    "word_preferences": {
      "team": "team",
      "amazing": "incredible"
    },
    "jargon_usage": "moderate",
    "technicality_level": "accessible"
  },
  "structural": {
    "avg_sentence_length": 12,
    "paragraph_style": "punchy single sentences",
    "opening_patterns": [
      "Big day.",
      "Just announced:",
      "Thinking about"
    ],
    "closing_patterns": [
      "More soon.",
      "The future is here.",
      ""
    ],
    "uses_lists": false,
    "uses_questions": false
  },
  "tonal": {
    "warmth_level": "direct but friendly",
    "humor_usage": "rare",
    "personal_disclosure": "minimal",
    "conviction_style": "assertive"
  },
  "example_posts": [
    "Big day. Databricks acquires Tabular. The teams behind Spark and Iceberg together. Open source data wins.",
    "Everyone's building AI agents now. The compound AI systems approach is winning. This is what we've been saying for 2 years.",
    "Data lakehouse > data warehouse. Fight me."
  ]
}
```

- [ ] **Step 10.4: Verify profiles load**

Run: `curl http://localhost:8000/api/profiles`
Expected: List shows ali_ghodsi profiles

- [ ] **Step 10.5: Commit sample profiles**

```bash
git add data/
git commit -m "feat: add sample voice profiles for Ali Ghodsi"
```

---

## Task 11: Docker and Deployment Setup

**Files:**
- Create: `packages/api/Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 11.1: Create API Dockerfile**

```dockerfile
# packages/api/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install dependencies
RUN uv sync --no-dev

# Copy data
COPY ../../data /app/data

ENV PYTHONPATH=/app/src
ENV PROFILES_PATH=/app/data/profiles
ENV HOOKS_PATH=/app/data/hooks.jsonl

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "writer_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 11.2: Create docker-compose.yml**

```yaml
# docker-compose.yml
version: "3.8"

services:
  api:
    build:
      context: .
      dockerfile: packages/api/Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  web:
    build:
      context: packages/web
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000
    depends_on:
      - api
    restart: unless-stopped
```

- [ ] **Step 11.3: Create .env.example**

```bash
# .env.example

# Required
EXA_API_KEY=your_exa_api_key

# LLM Provider (choose one)
LLM_PROVIDER=anthropic  # or "openai"
LLM_MODEL=claude-sonnet-4-6  # or "gpt-4o"

# If using Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key

# If using OpenAI  
OPENAI_API_KEY=your_openai_api_key

# Optional
CORS_ORIGINS=["http://localhost:3000"]
```

- [ ] **Step 11.4: Commit deployment config**

```bash
git add packages/api/Dockerfile docker-compose.yml .env.example
git commit -m "chore: add Docker and deployment configuration"
```

---

## Task 12: Final Integration and Testing

- [ ] **Step 12.1: Start both services**

Terminal 1: `cd packages/api && uv run uvicorn writer_api.main:app --reload --port 8000`
Terminal 2: `cd packages/web && pnpm dev`

- [ ] **Step 12.2: Test end-to-end generation**

1. Open http://localhost:3000/generate
2. Select "Ali Ghodsi" as author
3. Select "LinkedIn" as platform
4. Enter topic: "The future of compound AI systems"
5. Click Generate
6. Verify post appears with CEO voice

- [ ] **Step 12.3: Test revoicing flow**

1. Click on generated text to edit
2. Make structural changes to the text
3. Click "Re-voice"
4. Verify voice is reapplied while preserving structure

- [ ] **Step 12.4: Create final commit**

```bash
git add -A
git commit -m "feat: complete monorepo with API and frontend integration"
```

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-29-writer-profile-monorepo.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?

---

## Notes on Architecture Decisions

### Why Exa Instead of Local RAG?

1. **Fresh content**: Exa searches live web content, so new CEO posts are immediately available
2. **No cold start**: Adding a new CEO doesn't require ingesting their entire corpus first
3. **Simpler infrastructure**: No ChromaDB, no embeddings service, no vector maintenance
4. **Better for generation context**: Search results are topic-relevant rather than semantic-nearest

### On "GPT 5.5"

There is no GPT 5.5 model. The plan uses a model-agnostic LLM abstraction supporting:
- **Claude** (claude-sonnet-4-6, claude-opus-4-5) - current default
- **OpenAI** (gpt-4o, gpt-4-turbo) - configurable via `LLM_PROVIDER=openai`

Set your preferred model via `LLM_MODEL` environment variable.

### UI Design Principles (from Behance inspiration)

- Dark theme with warm orange/amber accent gradient
- Card-based layout with generous spacing
- Clean sidebar navigation with icon + text
- Large stat numbers for dashboard metrics
- Minimal borders, subtle shadows
- Inter font family for readability
