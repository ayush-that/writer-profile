from __future__ import annotations

from writer_api.config import settings


_OPENAI_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}

_GEMINI_DIMENSIONS = {
    "text-embedding-004": 768,
    "gemini-embedding-001": 3072,
    "gemini-embedding-2": 3072,
    "gemini-embedding-2-preview": 3072,
}


class EmbeddingClient:
    def __init__(self, provider: str | None = None, model: str | None = None) -> None:
        self._provider = provider or settings.embedding_provider

        if self._provider == "openai":
            import openai

            if not settings.openai_api_key:
                raise ValueError("OpenAI API key is required for openai embeddings")

            self._model = model or settings.embedding_model
            self._client = openai.OpenAI(
                api_key=settings.openai_api_key.get_secret_value()
            )
            self._dimension = _OPENAI_DIMENSIONS.get(self._model, 1536)

        elif self._provider == "gemini":
            from google import genai

            if not settings.gemini_api_key:
                raise ValueError("Gemini API key is required for gemini embeddings")

            self._model = model or "gemini-embedding-001"
            self._client = genai.Client(
                api_key=settings.gemini_api_key.get_secret_value()
            )
            self._dimension = _GEMINI_DIMENSIONS.get(self._model, 768)

        else:
            raise ValueError(f"Unsupported embedding provider: {self._provider}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._provider == "openai":
            response = self._client.embeddings.create(
                model=self._model,
                input=texts,
            )
            return [item.embedding for item in response.data]

        elif self._provider == "gemini":
            response = self._client.models.embed_content(
                model=self._model,
                contents=texts,
            )
            return [list(emb.values) for emb in response.embeddings]

        raise ValueError(f"Unsupported embedding provider: {self._provider}")

    @property
    def dimension(self) -> int:
        return self._dimension


def get_embedding_client() -> EmbeddingClient:
    return EmbeddingClient()
