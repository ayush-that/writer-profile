from __future__ import annotations

from pathlib import Path

from writer_profile.corpus.extractor import extract_metadata
from writer_profile.corpus.loader import load_posts_jsonl
from writer_profile.corpus.models import AnnotatedPost
from writer_profile.llm import LLMClient
from writer_profile.retrieval.store import ExemplarStore


def ingest_file(
    *,
    path: str | Path,
    store: ExemplarStore,
    llm: LLMClient,
    classifier_model: str,
) -> int:
    posts = load_posts_jsonl(path)
    annotated: list[AnnotatedPost] = []
    for post in posts:
        meta = extract_metadata(post, llm=llm, model=classifier_model)
        annotated.append(AnnotatedPost(post=post, metadata=meta))
    store.add_many(annotated)
    return len(annotated)
