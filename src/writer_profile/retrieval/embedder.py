from __future__ import annotations

from typing import Protocol

import numpy as np


class EmbedderProtocol(Protocol):
    def embed(self, texts: list[str]) -> np.ndarray: ...
    def embed_single(self, text: str) -> np.ndarray: ...


class GeminiEmbedder:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-embedding-2",
        dimensions: int = 768,
    ) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._dimensions = dimensions

    def embed(self, texts: list[str]) -> np.ndarray:
        from google.genai import types

        embeddings = []
        for text in texts:
            result = self._client.models.embed_content(
                model=self._model,
                contents=f"task: search result | query: {text}",
                config=types.EmbedContentConfig(output_dimensionality=self._dimensions),
            )
            embeddings.append(result.embeddings[0].values)
        return np.asarray(embeddings, dtype=np.float32)

    def embed_single(self, text: str) -> np.ndarray:
        return self.embed([text])[0]


class StubEmbedder:
    def __init__(self, dimensions: int = 768) -> None:
        self._dimensions = dimensions

    def embed(self, texts: list[str]) -> np.ndarray:
        rng = np.random.default_rng(seed=42)
        vecs = rng.standard_normal((len(texts), self._dimensions)).astype(np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs / norms

    def embed_single(self, text: str) -> np.ndarray:
        return self.embed([text])[0]


Embedder = GeminiEmbedder
