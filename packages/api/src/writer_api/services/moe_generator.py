from __future__ import annotations

import asyncio
import logging
import time

from writer_api.config import settings
from writer_api.models.moe import Candidate
from writer_api.models.requests import GenerateRequest
from writer_api.models.voice import VoiceProfile
from writer_api.prompts.templates import build_generator_prompt_hybrid
from writer_api.services.hybrid_retriever import HybridBundle
from writer_api.services.llm import LLMClient, LLMResponse, get_llm_client
from writer_api.services.voice_tells import VoiceTells, sanitize_output

logger = logging.getLogger(__name__)


class MoEGenerator:
    def __init__(self, experts: list[LLMClient] | None = None) -> None:
        self._experts = experts if experts is not None else self._default_experts()

    @staticmethod
    def _default_experts() -> list[LLMClient]:
        experts: list[LLMClient] = []
        for provider in settings.moe_generator_models:
            try:
                experts.append(get_llm_client(provider=provider))
            except Exception as exc:
                logger.warning("Skipping generator '%s': %s", provider, exc)
        return experts

    async def generate(
        self,
        profile: VoiceProfile,
        request: GenerateRequest,
        bundle: HybridBundle,
        tells: VoiceTells | None = None,
    ) -> list[Candidate]:
        if not self._experts:
            raise RuntimeError("No generator experts available")

        system, user = build_generator_prompt_hybrid(
            profile=profile,
            topic=request.topic,
            angle=request.angle,
            bundle=bundle,
            virality=request.virality,
            word_limit=request.word_limit,
            tells=tells,
        )

        max_tokens = 4096 if profile.platform.value == "linkedin" else 2048

        async def _run(client: LLMClient) -> tuple[LLMResponse, int] | None:
            start = time.perf_counter()
            try:
                response = await asyncio.to_thread(
                    client.complete, system, user, max_tokens, 0.7
                )
            except Exception as exc:
                logger.warning("Generator %s failed: %s", type(client).__name__, exc)
                return None
            return response, int((time.perf_counter() - start) * 1000)

        results = await asyncio.gather(*[_run(c) for c in self._experts])

        candidates: list[Candidate] = []
        for result in results:
            if result is None:
                continue
            response, latency_ms = result
            text = (response.text or "").strip()
            if not text:
                continue
            if tells is not None:
                text = sanitize_output(text, tells)
            if not text:
                continue
            candidates.append(
                Candidate(
                    text=text,
                    model=response.model,
                    latency_ms=latency_ms,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                )
            )

        if not candidates:
            raise RuntimeError("All MoE generator experts failed")

        return candidates
