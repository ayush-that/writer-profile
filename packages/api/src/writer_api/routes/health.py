from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    from writer_api import __version__

    return HealthResponse(status="healthy", version=__version__)


@router.get("/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    from writer_api import __version__

    return HealthResponse(status="ready", version=__version__)
