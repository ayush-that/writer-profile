from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

import anthropic


@dataclass(frozen=True)
class LLMMessage:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class LLMCall:
    model: str
    system: str
    messages: tuple[LLMMessage, ...]


class LLMClient(Protocol):
    def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[LLMMessage],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str: ...


class AnthropicClient:
    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[LLMMessage],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        response = self._client.messages.create(
            model=model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        parts = [b.text for b in response.content if b.type == "text"]
        return "".join(parts)


@dataclass
class StubLLMClient:
    responses: list[str]
    calls: list[LLMCall] = field(default_factory=list)
    _idx: int = 0

    def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[LLMMessage],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        self.calls.append(LLMCall(model=model, system=system, messages=tuple(messages)))
        response = self.responses[self._idx]
        self._idx += 1
        return response
