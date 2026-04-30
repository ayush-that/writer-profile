from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from writer_api.config import settings
from writer_api.routes import generate, health, profiles

app = FastAPI(
    title="Writer Profile API",
    description="CEO Voice Agent - Generate authentic social media content",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.writer-profile\.pages\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(generate.router, prefix="/api", tags=["generate"])
app.include_router(profiles.router, prefix="/api", tags=["profiles"])
