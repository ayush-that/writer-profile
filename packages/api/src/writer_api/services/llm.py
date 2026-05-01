from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from writer_api.config import settings


@dataclass
class LLMResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int


class LLMClient(ABC):
    @abstractmethod
    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse: ...


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        import anthropic

        key = api_key
        if key is None and settings.anthropic_api_key:
            key = settings.anthropic_api_key.get_secret_value()

        if not key:
            raise ValueError("Anthropic API key is required")

        self._client = anthropic.Anthropic(api_key=key)
        self._model = model or settings.llm_model

    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )

        text = ""
        for block in message.content:
            if block.type == "text":
                text += block.text

        return LLMResponse(
            text=text,
            model=self._model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        import openai

        key = api_key
        if key is None and settings.openai_api_key:
            key = settings.openai_api_key.get_secret_value()

        if not key:
            raise ValueError("OpenAI API key is required")

        self._client = openai.OpenAI(api_key=key)
        self._model = model or "gpt-4o"

    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

        text = response.choices[0].message.content or ""
        usage = response.usage

        return LLMResponse(
            text=text,
            model=self._model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )


class GeminiClient(LLMClient):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        from google import genai

        key = api_key
        if key is None and settings.gemini_api_key:
            key = settings.gemini_api_key.get_secret_value()

        if not key:
            raise ValueError("Gemini API key is required")

        self._client = genai.Client(api_key=key)
        self._model = model or "gemini-2.5-pro"

    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        from google.genai import types

        response = self._client.models.generate_content(
            model=self._model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )

        text = response.text or ""
        usage = response.usage_metadata

        return LLMResponse(
            text=text,
            model=self._model,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
        )


class OpenRouterClient(LLMClient):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        import openai

        key = api_key
        if key is None and settings.openrouter_api_key:
            key = settings.openrouter_api_key.get_secret_value()

        if not key:
            raise ValueError("OpenRouter API key is required")

        self._client = openai.OpenAI(
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
        )
        self._model = model or "anthropic/claude-sonnet-4.6"

    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

        text = response.choices[0].message.content or ""
        usage = response.usage

        return LLMResponse(
            text=text,
            model=self._model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )


class MistralClient(LLMClient):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        try:
            from mistralai import Mistral  # newer SDK exposes top-level
        except ImportError:
            from mistralai.client.sdk import Mistral  # mistralai 2.x layout

        key = api_key
        if key is None and settings.mistral_api_key:
            key = settings.mistral_api_key.get_secret_value()

        if not key:
            raise ValueError("Mistral API key is required")

        self._client = Mistral(api_key=key)
        self._model = model or "mistral-large-latest"

    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        response = self._client.chat.complete(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

        text = response.choices[0].message.content or ""
        usage = response.usage

        return LLMResponse(
            text=text,
            model=self._model,
            input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
        )


def get_llm_client(
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> LLMClient:
    provider = provider or settings.llm_provider

    if provider == "anthropic" or provider == "claude":
        return AnthropicClient(api_key=api_key, model=model)
    elif provider == "openai":
        return OpenAIClient(api_key=api_key, model=model)
    elif provider == "gemini":
        return GeminiClient(api_key=api_key, model=model)
    elif provider == "openrouter":
        return OpenRouterClient(api_key=api_key, model=model)
    elif provider == "mistral":
        return MistralClient(api_key=api_key, model=model)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
