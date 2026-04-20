import numpy as np
import pytest

from writer_profile.retrieval.embedder import Embedder


@pytest.fixture(scope="module")
def embedder() -> Embedder:
    return Embedder(model_name="sentence-transformers/all-MiniLM-L6-v2")


def test_embed_single_returns_1d_vector(embedder):
    vec = embedder.embed_single("the bottleneck in ai is evaluation")
    assert isinstance(vec, np.ndarray)
    assert vec.ndim == 1
    assert vec.shape[0] == 384


def test_embed_batch_returns_2d_matrix(embedder):
    mat = embedder.embed(["hello", "world", "third post"])
    assert mat.shape == (3, 384)
