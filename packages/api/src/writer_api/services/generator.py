from __future__ import annotations

from writer_api.models.moe import Candidate, MoEResponse, RetrievedContextSummary
from writer_api.models.requests import GenerateRequest, RevoiceRequest
from writer_api.models.responses import GenerateResponse, Source
from writer_api.models.voice import VoiceProfile
from writer_api.prompts.templates import build_generator_prompt, build_revoice_prompt
from writer_api.services.exa_retriever import ExaRetriever
from writer_api.services.hybrid_retriever import HybridRetriever
from writer_api.services.llm import LLMClient, get_llm_client
from writer_api.services.moe_generator import MoEGenerator
from writer_api.services.moe_judge import MoEJudge
from writer_api.services.voice_tells import extract_tells, sanitize_output


class GeneratorService:
    def __init__(self) -> None:
        self._retriever: ExaRetriever | None = None
        self._llm: LLMClient | None = None
        self._hybrid_retriever: HybridRetriever | None = None
        self._moe_generator: MoEGenerator | None = None
        self._moe_judge: MoEJudge | None = None

    def _get_retriever(self) -> ExaRetriever:
        if self._retriever is None:
            self._retriever = ExaRetriever()
        return self._retriever

    def _get_llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = get_llm_client()
        return self._llm

    def _get_hybrid_retriever(self) -> HybridRetriever:
        if self._hybrid_retriever is None:
            self._hybrid_retriever = HybridRetriever(exa_retriever=self._get_retriever())
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

        tells = extract_tells(profile.example_posts)

        candidates: list[Candidate] = await self._get_moe_generator().generate(
            profile=profile,
            request=request,
            bundle=bundle,
            tells=tells,
        )

        scores = await self._get_moe_judge().score_all(
            candidates=candidates,
            profile=profile,
            bundle=bundle,
            tells=tells,
        )

        winner, all_scores = MoEJudge.pick_winner(candidates, scores)

        own_sources = [
            Source(
                url="",
                title=f"{profile.author} — past post",
                source_type="chroma",
                snippet=(p.text or "")[:280],
                origin="own",
                score=p.score,
            )
            for p in bundle.own_posts
        ]
        web_sources = [
            Source(
                url=w.url,
                title=w.title,
                source_type=w.source_type,
                snippet=(w.text or "")[:280],
                origin="web",
            )
            for w in bundle.web_posts
            if w.url
        ]
        sources = own_sources + web_sources

        return MoEResponse(
            text=winner.text,
            sources=sources,
            sources_used=len(sources),
            winner=winner,
            candidates=candidates,
            scores=all_scores,
            context=RetrievedContextSummary(
                own_post_count=len(bundle.own_posts),
                web_post_count=len(bundle.web_posts),
                own_post_authors=[profile.author] if bundle.own_posts else [],
            ),
            author=profile.author,
            platform=profile.platform,
        )

    def generate(self, request: GenerateRequest, profile: VoiceProfile) -> GenerateResponse:
        author_name = profile.author.replace("_", " ").title()

        references = self._get_retriever().search_for_generation(
            author_name=author_name,
            platform=request.platform,
            topic=request.topic,
            k=5,
        )

        ref_dicts = [{"text": r.text, "source_type": r.source_type} for r in references]

        tells = extract_tells(profile.example_posts)

        system, user = build_generator_prompt(
            profile=profile,
            topic=request.topic,
            angle=request.angle or "",
            references=ref_dicts,
            virality=request.virality,
            word_limit=request.word_limit,
            tells=tells,
        )

        response = self._get_llm().complete(system=system, user=user)
        text = sanitize_output(response.text, tells)
        text = text.strip().strip('"').strip("'")

        sources = [
            Source(
                url=r.url,
                title=r.title,
                source_type=r.source_type,
                snippet=(r.text or "")[:280],
                origin="web",
            )
            for r in references
            if r.url
        ]

        return GenerateResponse(
            text=text,
            author=request.author,
            platform=request.platform,
            validation_ok=True,
            sources_used=len(references),
            sources=sources,
        )

    def revoice(self, request: RevoiceRequest, profile: VoiceProfile) -> GenerateResponse:
        system, user = build_revoice_prompt(profile=profile, edited_draft=request.edited_draft)

        tells = extract_tells(profile.example_posts)

        response = self._get_llm().complete(system=system, user=user)
        text = sanitize_output(response.text, tells).strip()

        return GenerateResponse(
            text=text,
            author=request.author,
            platform=request.platform,
            validation_ok=True,
        )
