from __future__ import annotations

from dataclasses import dataclass, field

from writer_profile.corpus.models import Idea, Platform
from writer_profile.generation.generator import generate_draft
from writer_profile.generation.refine import RefineStep, refine
from writer_profile.llm import LLMClient
from writer_profile.platforms.author_derived import constraint_for
from writer_profile.retrieval.store import ExemplarHit, ExemplarStore
from writer_profile.virality.hooks import HookLibrary
from writer_profile.voice.profile import VoiceProfile
from writer_profile.voice.store import VoiceProfileStore


@dataclass
class PostDraft:
    text: str
    author: str
    platform: Platform
    idea: Idea
    exemplars_used: list[ExemplarHit]
    refine_history: list[RefineStep]
    validation_ok: bool
    validation_issues: list[str] = field(default_factory=list)


class GenerationPipeline:
    def __init__(
        self,
        *,
        store: ExemplarStore,
        profiles: VoiceProfileStore,
        hooks: HookLibrary,
        llm: LLMClient,
        writing_model: str,
        retrieval_k: int = 5,
        refine_max_iterations: int = 2,
        hook_suggestion_k: int = 5,
    ) -> None:
        self._store = store
        self._profiles = profiles
        self._hooks = hooks
        self._llm = llm
        self._writing_model = writing_model
        self._retrieval_k = retrieval_k
        self._refine_max_iterations = refine_max_iterations
        self._hook_k = hook_suggestion_k

    def _profile(self, author: str, platform: Platform) -> VoiceProfile:
        return self._profiles.load(author=author, platform=platform)

    def generate(
        self,
        *,
        author: str,
        platform: Platform,
        idea: Idea,
        virality_strength: float = 0.15,
        hook_seed: int | None = None,
    ) -> PostDraft:
        profile = self._profile(author, platform)
        constraint = constraint_for(profile)
        exemplars = self._store.query(
            text=f"{idea.topic}\n{idea.angle}".strip(),
            platform=platform,
            author=author,
            k=self._retrieval_k,
        )
        hook_suggestions = self._hooks.suggest(
            platform=platform, k=self._hook_k, seed=hook_seed
        )

        initial = generate_draft(
            profile=profile,
            idea=idea,
            exemplars=exemplars,
            constraint=constraint,
            hooks=hook_suggestions,
            llm=self._llm,
            model=self._writing_model,
            virality_strength=virality_strength,
        )

        refined = refine(
            draft=initial,
            platform=platform,
            constraint=constraint,
            llm=self._llm,
            model=self._writing_model,
            max_iterations=self._refine_max_iterations,
        )

        final = constraint.validate(refined.final_draft)
        return PostDraft(
            text=refined.final_draft,
            author=author,
            platform=platform,
            idea=idea,
            exemplars_used=exemplars,
            refine_history=refined.history,
            validation_ok=bool(final),
            validation_issues=list(final.issues),
        )
