from fastapi import APIRouter, HTTPException

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
