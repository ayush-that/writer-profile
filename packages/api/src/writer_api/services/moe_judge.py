from __future__ import annotations

import asyncio
import json
import logging
import re
from statistics import mean

from writer_api.config import settings
from writer_api.models.moe import Candidate, JudgeScore
from writer_api.models.voice import VoiceProfile
from writer_api.prompts.templates import build_judge_prompt
from writer_api.services.hybrid_retriever import HybridBundle
from writer_api.services.llm import LLMClient, get_llm_client

logger = logging.getLogger(__name__)


VOICE_WEIGHT = 0.5
AUTHENTICITY_WEIGHT = 0.3
VIRALITY_WEIGHT = 0.2

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


class MoEJudge:
    def __init__(self, judges: list[LLMClient] | None = None) -> None:
        self._judges = judges if judges is not None else self._default_judges()

    @staticmethod
    def _default_judges() -> list[LLMClient]:
        judges: list[LLMClient] = []
        for provider in settings.moe_judge_models:
            try:
                judges.append(get_llm_client(provider=provider))
            except Exception as exc:
                logger.warning("Skipping judge '%s': %s", provider, exc)
        return judges

    async def score_all(
        self,
        candidates: list[Candidate],
        profile: VoiceProfile,
        bundle: HybridBundle,
    ) -> list[JudgeScore]:
        if not self._judges:
            raise RuntimeError("No judges available")
        if not candidates:
            return []

        tasks = []
        for c_idx, candidate in enumerate(candidates):
            for judge in self._judges:
                tasks.append(self._score_one(judge, candidate, c_idx, profile, bundle))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        scores: list[JudgeScore] = []
        for result in results:
            if isinstance(result, BaseException):
                logger.warning("Judge task raised: %s", result)
                continue
            if result is None:
                continue
            scores.append(result)
        return scores

    async def _score_one(
        self,
        judge: LLMClient,
        candidate: Candidate,
        candidate_index: int,
        profile: VoiceProfile,
        bundle: HybridBundle,
    ) -> JudgeScore | None:
        system, user = build_judge_prompt(
            profile=profile,
            candidate_text=candidate.text,
            bundle=bundle,
            candidate_index=candidate_index,
        )
        try:
            # 2048 tokens to give thinking-style models (gemini 2.5 pro) headroom
            # before they emit the JSON object.
            response = await asyncio.to_thread(judge.complete, system, user, 2048, 0.0)
        except Exception as exc:
            logger.warning("Judge call failed: %s", exc)
            return None

        parsed = self._parse_json(response.text)
        if parsed is None:
            return JudgeScore(
                judge_model=response.model,
                candidate_index=candidate_index,
                voice_match=0.5,
                virality=0.5,
                authenticity=0.5,
                overall=0.5,
                rationale="parse failed",
            )

        voice_match = self._clamp(parsed.get("voice_match", 0.5))
        virality = self._clamp(parsed.get("virality", 0.5))
        authenticity = self._clamp(parsed.get("authenticity", 0.5))
        overall = (
            voice_match * VOICE_WEIGHT
            + authenticity * AUTHENTICITY_WEIGHT
            + virality * VIRALITY_WEIGHT
        )
        rationale = str(parsed.get("rationale", "")).strip()

        return JudgeScore(
            judge_model=response.model,
            candidate_index=candidate_index,
            voice_match=voice_match,
            virality=virality,
            authenticity=authenticity,
            overall=self._clamp(overall),
            rationale=rationale,
        )

    @staticmethod
    def _clamp(value: object) -> float:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return 0.5
        if v < 0.0:
            return 0.0
        if v > 1.0:
            return 1.0
        return v

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        if not text:
            return None
        stripped = text.strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
        match = _JSON_OBJECT_RE.search(stripped)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    @staticmethod
    def pick_winner(
        candidates: list[Candidate],
        scores: list[JudgeScore],
    ) -> tuple[Candidate, list[JudgeScore]]:
        if not candidates:
            raise ValueError("No candidates to choose from")

        per_candidate: dict[int, list[float]] = {i: [] for i in range(len(candidates))}
        for score in scores:
            if 0 <= score.candidate_index < len(candidates):
                per_candidate[score.candidate_index].append(score.overall)

        best_idx = 0
        best_mean = -1.0
        for idx, vals in per_candidate.items():
            avg = mean(vals) if vals else 0.0
            if avg > best_mean:
                best_mean = avg
                best_idx = idx

        return candidates[best_idx], scores
