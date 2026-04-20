import json
from datetime import datetime, timezone

import pytest

from writer_profile.corpus.ingest import ingest_file
from writer_profile.corpus.models import Platform, Post
from writer_profile.llm import StubLLMClient
from writer_profile.retrieval.embedder import Embedder
from writer_profile.retrieval.store import ExemplarStore


@pytest.fixture(scope="module")
def embedder() -> Embedder:
    return Embedder(model_name="sentence-transformers/all-MiniLM-L6-v2")


def _post_to_line(p: Post) -> str:
    return p.model_dump_json()


def test_ingest_file_populates_store_with_extracted_metadata(tmp_path, embedder):
    src = tmp_path / "posts.jsonl"
    p1 = Post(
        id="p1",
        platform=Platform.TWITTER,
        text="ai evaluation is the new bottleneck",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    src.write_text(_post_to_line(p1))

    meta_json = json.dumps(
        {
            "topics": ["ai", "evaluation"],
            "tone": "observational",
            "length_bucket": "short",
            "language": "en",
        }
    )
    llm = StubLLMClient(responses=[meta_json])
    store = ExemplarStore(path=str(tmp_path / "c"), embedder=embedder, collection="ingest")

    count = ingest_file(
        path=src,
        store=store,
        llm=llm,
        classifier_model="claude-haiku-4-5-20251001",
    )
    assert count == 1

    hits = store.query(text="ai evaluation", platform=Platform.TWITTER, k=1)
    assert len(hits) == 1
    assert hits[0].post.id == "p1"
    assert "ai" in hits[0].metadata.topics
