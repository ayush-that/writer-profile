from fastapi import APIRouter, HTTPException

from writer_api.models.responses import ProfileListResponse, ProfileResponse
from writer_api.models.voice import Platform
from writer_api.services.profile_store import ProfileStore

router = APIRouter()

_store = ProfileStore()


@router.get("/profiles", response_model=ProfileListResponse)
async def list_profiles() -> ProfileListResponse:
    """List all available voice profiles."""
    profiles = _store.list_profiles()
    return ProfileListResponse(
        profiles=[{"author": author, "platform": platform.value} for author, platform in profiles]
    )


@router.get("/profiles/{author}/{platform}", response_model=ProfileResponse)
async def get_profile(author: str, platform: Platform) -> ProfileResponse:
    """Get a specific voice profile."""
    profile = _store.load(author, platform)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse(profile=profile, post_count=len(profile.example_posts))
