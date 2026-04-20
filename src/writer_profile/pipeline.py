from __future__ import annotations

from dataclasses import dataclass, field

from writer_profile.corpus.models import Platform
from writer_profile.generation.generator import generate_draft
from writer_profile.generation.refine import RefineStep, refine
from writer_profile.llm import LLMClient
from writer_profile.platforms.base import Constraint
from writer_profile.retrieval.store import ExemplarHit, ExemplarStore


@dataclass
class PostDraft:
    text: str
    platform: Platform
    topic: str
    exemplars_used: list[ExemplarHit]
    refine_history: list[RefineStep]
    validation_ok: bool
    validation_issues: list[str] = field(default_factory=list)


class GenerationPipeline:
    def __init__(
        self,
        *,
        store: ExemplarStore,
        llm: LLMClient,
        writing_model: str,
        constraints: dict[Platform, Constraint],
        retrieval_k: int = 5,
        refine_max_iterations: int = 2,
    ) -> None:
        self._store = store
        self._llm = llm
        self._writing_model = writing_model
        self._constraints = constraints
        self._retrieval_k = retrieval_k
        self._refine_max_iterations = refine_max_iterations

    def generate(self, *, topic: str, platform: Platform) -> PostDraft:
        if platform not in self._constraints:
            raise KeyError(f"no constraint registered for platform {platform.value}")

        constraint = self._constraints[platform]
        exemplars = self._store.query(text=topic, platform=platform, k=self._retrieval_k)

        initial = generate_draft(
            topic=topic,
            platform=platform,
            exemplars=exemplars,
            constraint=constraint,
            llm=self._llm,
            model=self._writing_model,
        )

        refined = refine(
            draft=initial,
            platform=platform,
            constraint=constraint,
            llm=self._llm,
            model=self._writing_model,
            max_iterations=self._refine_max_iterations,
        )

        final_validation = constraint.validate(refined.final_draft)
        return PostDraft(
            text=refined.final_draft,
            platform=platform,
            topic=topic,
            exemplars_used=exemplars,
            refine_history=refined.history,
            validation_ok=bool(final_validation),
            validation_issues=list(final_validation.issues),
        )
