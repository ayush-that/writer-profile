from __future__ import annotations

import logging

from writer_api.models.moe import (
    Candidate,
    MoEResponse,
    RetrievedContextSummary,
)
from writer_api.models.requests import GenerateRequest, RevoiceRequest
from writer_api.models.responses import GenerateResponse
from writer_api.models.voice import VoiceProfile
from writer_api.prompts.templates import build_generator_prompt, build_revoice_prompt
from writer_api.services.exa_retriever import ExaRetriever
from writer_api.services.hybrid_retriever import HybridRetriever
from writer_api.services.llm import get_llm_client
from writer_api.services.moe_generator import MoEGenerator
from writer_api.services.moe_judge import MoEJudge

logger = logging.getLogger(__name__)


class GeneratorService:
    def __init__(self) -> None:
        self._retriever = ExaRetriever()
        self._llm = get_llm_client()
        self._hybrid_retriever: HybridRetriever | None = None
        self._moe_generator: MoEGenerator | None = None
        self._moe_judge: MoEJudge | None = None

    def _get_hybrid_retriever(self) -> HybridRetriever:
        if self._hybrid_retriever is None:
            self._hybrid_retriever = HybridRetriever(exa_retriever=self._retriever)
        return self._hybrid_retriever

    def _get_moe_generator(self) -> MoEGenerator:
        if self._moe_generator is None:
            self._moe_generator = MoEGenerator()
        return self._moe_generator

    def _get_moe_judge(self) -> MoEJudge:
        if self._moe_judge is None:
            self._moe_judge = MoEJudge()
        return self._moe_judge

    async def generate_moe(
        self,
        request: GenerateRequest,
        profile: VoiceProfile,
    ) -> MoEResponse:
        bundle = self._get_hybrid_retriever().retrieve(
            author=profile.author,
            platform=profile.platform.value,
            topic=request.topic,
            k_own=5,
            k_web=3,
        )

        candidates: list[Candidate] = await self._get_moe_generator().generate(
            profile=profile,
            request=request,
            bundle=bundle,
        )

        scores = await self._get_moe_judge().score_all(
            candidates=candidates,
            profile=profile,
            bundle=bundle,
        )

        winner, all_scores = MoEJudge.pick_winner(candidates, scores)

        own_authors = sorted({p.author for p in bundle.own_posts})

        return MoEResponse(
            winner=winner,
            candidates=candidates,
            scores=all_scores,
            context=RetrievedContextSummary(
                own_post_count=len(bundle.own_posts),
                web_post_count=len(bundle.web_posts),
                own_post_authors=own_authors,
            ),
            author=profile.author,
            platform=profile.platform,
        )

    def generate(self, request: GenerateRequest, profile: VoiceProfile) -> GenerateResponse:
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
            word_limit=request.word_limit,
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
        system, user = build_revoice_prompt(profile=profile, edited_draft=request.edited_draft)

        response = self._llm.complete(system=system, user=user)

        return GenerateResponse(
            text=response.text.strip(),
            author=request.author,
            platform=request.platform,
            validation_ok=True,
        )
