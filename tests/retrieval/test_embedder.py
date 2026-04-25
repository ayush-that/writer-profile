import numpy as np
import pytest

from writer_profile.retrieval.embedder import StubEmbedder


@pytest.fixture(scope="module")
def embedder() -> StubEmbedder:
    return StubEmbedder(dimensions=768)


def test_embed_single_returns_1d_vector(embedder):
    vec = embedder.embed_single("the bottleneck in ai is evaluation")
    assert isinstance(vec, np.ndarray)
    assert vec.ndim == 1
    assert vec.shape[0] == 768


def test_embed_batch_returns_2d_matrix(embedder):
    mat = embedder.embed(["hello", "world", "third post"])
    assert mat.shape == (3, 768)


def test_embed_vectors_are_normalized(embedder):
    mat = embedder.embed(["hello", "world"])
    norms = np.linalg.norm(mat, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-6)
