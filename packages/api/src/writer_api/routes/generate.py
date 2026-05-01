from fastapi import APIRouter, HTTPException

from writer_api.models.moe import MoEResponse
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


@router.post("/generate/moe", response_model=MoEResponse)
async def generate_post_moe(request: GenerateRequest) -> MoEResponse:
    """Generate a post using mixture of experts (Chroma + Exa retrieval, parallel multi-LLM gen + scoring)."""
    profile = _profiles.load(request.author, request.platform)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No voice profile found for {request.author} on {request.platform.value}",
        )
    try:
        return await _generator.generate_moe(request, profile)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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
