from __future__ import annotations

from dataclasses import dataclass, field

from writer_profile.corpus.models import Platform
from writer_profile.generation.critics import (
    CRITICS,
    CriticFeedback,
    _is_ok,
    parse_critic_response,
    synthesize_feedback,
)
from writer_profile.generation.generator import unwrap
from writer_profile.generation.prompts import build_critic_prompt, build_refine_prompt
from writer_profile.llm import LLMClient, LLMMessage
from writer_profile.platforms.base import Constraint


@dataclass
class RefineStep:
    draft: str
    critic_feedback: str
    validator_issues: tuple[str, ...]


@dataclass
class RefineResult:
    final_draft: str
    iterations: int
    history: list[RefineStep] = field(default_factory=list)


def _critique(
    *,
    draft: str,
    platform: Platform,
    constraint: Constraint,
    llm: LLMClient,
    model: str,
) -> str:
    system, user = build_critic_prompt(draft=draft, platform=platform, constraint=constraint)
    return llm.complete(
        model=model,
        system=system,
        messages=[LLMMessage(role="user", content=user)],
        max_tokens=256,
    ).strip()


def _rewrite(
    *,
    draft: str,
    platform: Platform,
    constraint: Constraint,
    critic_feedback: str,
    validator_issues: list[str],
    llm: LLMClient,
    model: str,
) -> str:
    system, user = build_refine_prompt(
        draft=draft,
        platform=platform,
        constraint=constraint,
        critic_feedback=critic_feedback,
        validator_issues=validator_issues,
    )
    raw = llm.complete(
        model=model,
        system=system,
        messages=[LLMMessage(role="user", content=user)],
        max_tokens=1024,
    )
    return unwrap(raw)


def refine(
    *,
    draft: str,
    platform: Platform,
    constraint: Constraint,
    llm: LLMClient,
    model: str,
    max_iterations: int = 2,
) -> RefineResult:
    current = draft
    iterations = 0
    history: list[RefineStep] = []

    pending_rewrite = False
    last_feedback = ""
    last_validator_issues: list[str] = []

    while iterations < max_iterations:
        if not pending_rewrite:
            validator = constraint.validate(current)
            validator_issues = list(validator.issues) if not validator else []

            critic_feedback = _critique(
                draft=current,
                platform=platform,
                constraint=constraint,
                llm=llm,
                model=model,
            )
            iterations += 1
            history.append(
                RefineStep(
                    draft=current,
                    critic_feedback=critic_feedback,
                    validator_issues=tuple(validator_issues),
                )
            )

            if bool(validator) and _is_ok(critic_feedback):
                break

            last_feedback = critic_feedback
            last_validator_issues = validator_issues
            pending_rewrite = True
        else:
            current = _rewrite(
                draft=current,
                platform=platform,
                constraint=constraint,
                critic_feedback=last_feedback,
                validator_issues=last_validator_issues,
                llm=llm,
                model=model,
            )
            iterations += 1
            pending_rewrite = False

    return RefineResult(final_draft=current, iterations=iterations, history=history)


@dataclass
class MultiRefineStep:
    draft: str
    critic_feedbacks: list[CriticFeedback]
    validator_issues: tuple[str, ...]
    synthesized_feedback: str


@dataclass
class MultiRefineResult:
    final_draft: str
    iterations: int
    all_critics_ok: bool
    history: list[MultiRefineStep] = field(default_factory=list)


def _multi_critique(
    *,
    draft: str,
    platform: Platform,
    author: str,
    llm: LLMClient,
    model: str,
) -> list[CriticFeedback]:
    feedbacks = []
    for critic in CRITICS:
        system = critic["system"].format(author=author, platform=platform.value)
        user = f"DRAFT:\n{draft}\n\nYour critique:"
        response = llm.complete(
            model=model,
            system=system,
            messages=[LLMMessage(role="user", content=user)],
            max_tokens=256,
        )
        feedbacks.append(parse_critic_response(critic["name"], response))
    return feedbacks


def refine_multi(
    *,
    draft: str,
    platform: Platform,
    constraint: Constraint,
    author: str,
    llm: LLMClient,
    model: str,
    max_iterations: int = 2,
) -> MultiRefineResult:
    current = draft
    iterations = 0
    history: list[MultiRefineStep] = []

    while iterations < max_iterations:
        validator = constraint.validate(current)
        validator_issues = list(validator.issues) if not validator else []

        feedbacks = _multi_critique(
            draft=current,
            platform=platform,
            author=author,
            llm=llm,
            model=model,
        )
        iterations += 1

        synthesized = synthesize_feedback(feedbacks)
        all_ok = all(f.is_ok for f in feedbacks) and bool(validator)

        history.append(
            MultiRefineStep(
                draft=current,
                critic_feedbacks=feedbacks,
                validator_issues=tuple(validator_issues),
                synthesized_feedback=synthesized,
            )
        )

        if all_ok:
            return MultiRefineResult(
                final_draft=current,
                iterations=iterations,
                all_critics_ok=True,
                history=history,
            )

        current = _rewrite(
            draft=current,
            platform=platform,
            constraint=constraint,
            critic_feedback=synthesized,
            validator_issues=validator_issues,
            llm=llm,
            model=model,
        )
        iterations += 1

    return MultiRefineResult(
        final_draft=current,
        iterations=iterations,
        all_critics_ok=False,
        history=history,
    )
