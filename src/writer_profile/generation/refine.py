from __future__ import annotations

from dataclasses import dataclass, field

from writer_profile.corpus.models import Platform
from writer_profile.generation.generator import _unwrap
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
        temperature=0.2,
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
        temperature=0.6,
    )
    return _unwrap(raw)


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

            if bool(validator) and critic_feedback.strip().upper() == "OK":
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
