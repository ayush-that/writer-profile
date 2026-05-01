from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def fake_chromadb(monkeypatch: pytest.MonkeyPatch):
    """Install a fake `chromadb` module before chroma_store is imported.

    Returns a SimpleNamespace exposing the HttpClient/PersistentClient mocks
    plus the collection mock that get_or_create_collection returns.
    """
    fake_module = types.ModuleType("chromadb")

    collection = MagicMock(name="collection")
    collection.count.return_value = 0
    collection.query.return_value = {
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    }

    def _make_client(*_args, **_kwargs):
        client = MagicMock(name="client")
        client.get_or_create_collection.return_value = collection
        return client

    http_client = MagicMock(name="HttpClient", side_effect=_make_client)
    persistent_client = MagicMock(name="PersistentClient", side_effect=_make_client)
    cloud_client = MagicMock(name="CloudClient", side_effect=_make_client)

    fake_module.HttpClient = http_client
    fake_module.PersistentClient = persistent_client
    fake_module.CloudClient = cloud_client

    monkeypatch.setitem(sys.modules, "chromadb", fake_module)

    # Force re-import so the patched chromadb is picked up by ChromaStore.
    sys.modules.pop("writer_api.services.chroma_store", None)

    ns = types.SimpleNamespace(
        module=fake_module,
        HttpClient=http_client,
        PersistentClient=persistent_client,
        collection=collection,
    )
    yield ns

    sys.modules.pop("writer_api.services.chroma_store", None)


def _fake_embedding_client(dim: int = 4):
    client = MagicMock(name="embedding_client")
    client.embed.side_effect = lambda texts: [[0.1 * (i + 1)] * dim for i in range(len(texts))]
    return client


def test_upsert_calls_embedder_and_collection(fake_chromadb):
    from writer_api.services.chroma_store import ChromaStore, IndexedPost

    embedder = _fake_embedding_client()
    store = ChromaStore(collection_name="test_col", embedding_client=embedder)

    posts = [
        IndexedPost(id="a__twitter__0", text="hello world", author="a", platform="twitter"),
        IndexedPost(id="a__twitter__1", text="goodbye world", author="a", platform="twitter"),
    ]
    n = store.upsert_posts(posts)

    assert n == 2
    embedder.embed.assert_called_once_with(["hello world", "goodbye world"])
    fake_chromadb.collection.upsert.assert_called_once()
    kwargs = fake_chromadb.collection.upsert.call_args.kwargs
    assert kwargs["ids"] == ["a__twitter__0", "a__twitter__1"]
    assert kwargs["documents"] == ["hello world", "goodbye world"]
    assert len(kwargs["embeddings"]) == 2
    assert kwargs["metadatas"][0]["author"] == "a"
    assert kwargs["metadatas"][0]["platform"] == "twitter"
    assert kwargs["metadatas"][0]["source_type"] == "scraped"


def test_upsert_respects_batch_size(fake_chromadb):
    from writer_api.services.chroma_store import ChromaStore, IndexedPost

    embedder = _fake_embedding_client()
    store = ChromaStore(embedding_client=embedder)

    posts = [
        IndexedPost(id=f"a__t__{i}", text=f"post {i}", author="a", platform="t")
        for i in range(10)
    ]
    n = store.upsert_posts(posts, batch_size=3)

    assert n == 10
    # 10 items / batch 3 => 4 batches => 4 upsert calls + 4 embed calls
    assert fake_chromadb.collection.upsert.call_count == 4
    assert embedder.embed.call_count == 4


def test_query_returns_query_results_with_similarity(fake_chromadb):
    from writer_api.services.chroma_store import ChromaStore, QueryResult

    fake_chromadb.collection.query.return_value = {
        "ids": [["a__t__0", "a__t__1"]],
        "documents": [["hello", "world"]],
        "metadatas": [
            [
                {"author": "a", "platform": "t", "source_type": "scraped"},
                {"author": "a", "platform": "t", "source_type": "scraped"},
            ]
        ],
        "distances": [[0.1, 0.4]],
    }

    embedder = _fake_embedding_client()
    store = ChromaStore(embedding_client=embedder)

    results = store.query("hi there", k=2)

    assert len(results) == 2
    assert all(isinstance(r, QueryResult) for r in results)
    # similarity == 1 - distance
    assert results[0].score == pytest.approx(0.9)
    assert results[1].score == pytest.approx(0.6)
    assert results[0].id == "a__t__0"
    assert results[0].author == "a"
    assert results[0].platform == "t"

    # Verify the embedding was passed through
    call_kwargs = fake_chromadb.collection.query.call_args.kwargs
    assert call_kwargs["n_results"] == 2
    assert "query_embeddings" in call_kwargs


def test_query_passes_where_filter(fake_chromadb):
    from writer_api.services.chroma_store import ChromaStore

    embedder = _fake_embedding_client()
    store = ChromaStore(embedding_client=embedder)

    store.query("hi", k=3, where={"author": "sam_altman"})
    kwargs = fake_chromadb.collection.query.call_args.kwargs
    assert kwargs["where"] == {"author": "sam_altman"}


def test_query_wraps_multi_key_where_in_and(fake_chromadb):
    from writer_api.services.chroma_store import ChromaStore

    embedder = _fake_embedding_client()
    store = ChromaStore(embedding_client=embedder)

    store.query("hi", k=3, where={"author": "sam_altman", "platform": "twitter"})
    kwargs = fake_chromadb.collection.query.call_args.kwargs
    where = kwargs["where"]
    assert "$and" in where
    sub = {list(d.keys())[0]: list(d.values())[0] for d in where["$and"]}
    assert sub == {"author": "sam_altman", "platform": "twitter"}


def test_uses_cloud_client_when_cloud_creds_set(fake_chromadb, monkeypatch):
    from pydantic import SecretStr

    from writer_api.config import settings

    monkeypatch.setattr(
        settings, "chroma_api_key", SecretStr("super-secret"), raising=False
    )
    monkeypatch.setattr(settings, "chroma_tenant", "tenant-1", raising=False)
    monkeypatch.setattr(settings, "chroma_database", "db-1", raising=False)
    monkeypatch.setattr(settings, "chroma_collection", "ceo_posts", raising=False)

    from writer_api.services.chroma_store import ChromaStore

    ChromaStore(embedding_client=_fake_embedding_client())

    fake_chromadb.module.CloudClient.assert_called_once()
    fake_chromadb.PersistentClient.assert_not_called()
    kwargs = fake_chromadb.module.CloudClient.call_args.kwargs
    assert kwargs["api_key"] == "super-secret"
    assert kwargs["tenant"] == "tenant-1"
    assert kwargs["database"] == "db-1"


def test_falls_back_to_persistent_client_when_no_cloud_creds(fake_chromadb, monkeypatch):
    from writer_api.config import settings

    monkeypatch.setattr(settings, "chroma_api_key", None, raising=False)
    monkeypatch.setattr(settings, "chroma_tenant", None, raising=False)
    monkeypatch.setattr(settings, "chroma_database", None, raising=False)

    from writer_api.services.chroma_store import ChromaStore

    ChromaStore(embedding_client=_fake_embedding_client())

    fake_chromadb.PersistentClient.assert_called_once()
    fake_chromadb.HttpClient.assert_not_called()


def test_count_proxies_to_collection(fake_chromadb):
    from writer_api.services.chroma_store import ChromaStore

    fake_chromadb.collection.count.return_value = 42
    store = ChromaStore(embedding_client=_fake_embedding_client())
    assert store.count() == 42
