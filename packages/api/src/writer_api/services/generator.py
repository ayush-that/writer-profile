"""Main generation service for creating content in a writer's voice."""

from __future__ import annotations

from writer_api.models.requests import GenerateRequest, RevoiceRequest
from writer_api.models.responses import GenerateResponse
from writer_api.models.voice import VoiceProfile
from writer_api.prompts.templates import build_generator_prompt, build_revoice_prompt
from writer_api.services.exa_retriever import ExaRetriever
from writer_api.services.llm import get_llm_client


class GeneratorService:
    """Service for generating content in a CEO's voice."""

    def __init__(self) -> None:
        self._retriever = ExaRetriever()
        self._llm = get_llm_client()

    def generate(self, request: GenerateRequest, profile: VoiceProfile) -> GenerateResponse:
        """Generate a post in the CEO's voice."""
        author_name = profile.author.replace("_", " ").title()

        references = self._retriever.search_for_generation(
            author_name=author_name,
            platform=request.platform,
            topic=request.topic,
            k=5,
        )

        ref_dicts = [{"text": r.text, "source_type": r.source_type} for r in references]

        system, user = build_generator_prompt(
            profile=profile,
            topic=request.topic,
            angle=request.angle or "",
            references=ref_dicts,
            virality=request.virality,
        )

        response = self._llm.complete(system=system, user=user)
        text = response.text.strip().strip('"').strip("'")

        return GenerateResponse(
            text=text,
            author=request.author,
            platform=request.platform,
            validation_ok=True,
            sources_used=len(references),
        )

    def revoice(self, request: RevoiceRequest, profile: VoiceProfile) -> GenerateResponse:
        """Re-voice an edited draft in the CEO's voice."""
        system, user = build_revoice_prompt(profile=profile, edited_draft=request.edited_draft)

        response = self._llm.complete(system=system, user=user)

        return GenerateResponse(
            text=response.text.strip(),
            author=request.author,
            platform=request.platform,
            validation_ok=True,
        )
