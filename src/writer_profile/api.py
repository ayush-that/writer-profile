from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from writer_profile.config import Settings
from writer_profile.corpus.models import Idea, Platform
from writer_profile.llm import AnthropicClient
from writer_profile.pipeline import GenerationPipeline
from writer_profile.retrieval.embedder import Embedder
from writer_profile.retrieval.store import ExemplarStore
from writer_profile.virality.hooks import HookLibrary
from writer_profile.voice.store import VoiceProfileStore

app = FastAPI(title="Cadence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_pipeline: GenerationPipeline | None = None
_profiles: VoiceProfileStore | None = None


def get_pipeline() -> GenerationPipeline:
    global _pipeline, _profiles
    if _pipeline is None:
        settings = Settings()
        embedder = Embedder(
            api_key=settings.gemini_api_key.get_secret_value(),
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )
        store = ExemplarStore(
            embedder=embedder,
            path=settings.chroma_path,
            api_key=settings.chroma_api_key.get_secret_value() if settings.chroma_api_key else None,
            host=settings.chroma_host,
            tenant=settings.chroma_tenant,
            database=settings.chroma_database,
        )
        _profiles = VoiceProfileStore(root=settings.profiles_path)
        hooks = HookLibrary.load(settings.hooks_path)
        llm = AnthropicClient(api_key=settings.anthropic_api_key)
        _pipeline = GenerationPipeline(
            store=store,
            profiles=_profiles,
            hooks=hooks,
            llm=llm,
            writing_model=settings.writing_model,
            retrieval_k=settings.retrieval_k,
            refine_max_iterations=settings.refine_max_iterations,
            hook_suggestion_k=settings.hook_suggestion_k,
        )
    return _pipeline


def get_profiles() -> VoiceProfileStore:
    global _profiles
    if _profiles is None:
        _profiles = VoiceProfileStore(root="./data/profiles")
    return _profiles


class GenerateRequest(BaseModel):
    author: str
    platform: str
    topic: str
    angle: str | None = None
    virality: float = 0.15


class GenerateResponse(BaseModel):
    text: str
    author: str
    platform: str
    validation_ok: bool
    validation_issues: list[str]
    sources_used: int


class RevoiceRequest(BaseModel):
    author: str
    platform: str
    edited_draft: str


class ProfileItem(BaseModel):
    author: str
    platform: str


class ProfilesResponse(BaseModel):
    profiles: list[ProfileItem]


@app.get("/api/profiles", response_model=ProfilesResponse)
def list_profiles() -> ProfilesResponse:
    store = get_profiles()
    entries = store.list_profiles()
    return ProfilesResponse(profiles=[ProfileItem(author=a, platform=p.value) for a, p in entries])


@app.get("/api/profiles/{author}/{platform}")
def get_profile(author: str, platform: str) -> JSONResponse:
    profile_path = Path("./data/profiles") / f"{author}__{platform}.json"
    if not profile_path.exists():
        raise HTTPException(404, f"Profile not found: {author}/{platform}")
    with open(profile_path) as f:
        data = json.load(f)
    return JSONResponse(content=data)


@app.post("/api/generate", response_model=GenerateResponse)
def generate_post(req: GenerateRequest) -> GenerateResponse:
    try:
        platform = Platform(req.platform)
    except ValueError as e:
        raise HTTPException(400, f"Invalid platform: {req.platform}") from e

    pipe = get_pipeline()
    try:
        draft = pipe.generate(
            author=req.author,
            platform=platform,
            idea=Idea(topic=req.topic, angle=req.angle or ""),
            virality_strength=req.virality,
        )
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:
        raise HTTPException(500, str(e)) from e

    return GenerateResponse(
        text=draft.text,
        author=req.author,
        platform=req.platform,
        validation_ok=draft.validation_ok,
        validation_issues=draft.validation_issues,
        sources_used=draft.sources_used,
    )


@app.post("/api/revoice", response_model=GenerateResponse)
def revoice_post(req: RevoiceRequest) -> GenerateResponse:
    try:
        platform = Platform(req.platform)
    except ValueError as e:
        raise HTTPException(400, f"Invalid platform: {req.platform}") from e

    pipe = get_pipeline()
    try:
        draft = pipe.revoice(
            author=req.author,
            platform=platform,
            edited_draft=req.edited_draft,
        )
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:
        raise HTTPException(500, str(e)) from e

    return GenerateResponse(
        text=draft.text,
        author=req.author,
        platform=req.platform,
        validation_ok=draft.validation_ok,
        validation_issues=draft.validation_issues,
        sources_used=0,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
