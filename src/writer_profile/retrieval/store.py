from __future__ import annotations

import json
from dataclasses import dataclass

import chromadb

from writer_profile.corpus.models import AnnotatedPost, Platform, Post, PostMetadata
from writer_profile.retrieval.embedder import Embedder


@dataclass
class ExemplarHit:
    post: Post
    metadata: PostMetadata
    score: float


class ExemplarStore:
    def __init__(self, *, path: str, embedder: Embedder, collection: str = "posts") -> None:
        self._client = chromadb.PersistentClient(path=path)
        self._col = self._client.get_or_create_collection(
            name=collection, metadata={"hnsw:space": "cosine"}
        )
        self._embedder = embedder

    def add_many(self, items: list[AnnotatedPost]) -> None:
        if not items:
            return
        ids = [i.post.id for i in items]
        docs = [i.post.text for i in items]
        vectors = self._embedder.embed(docs).tolist()
        metadatas = [
            {
                "author": i.post.author,
                "platform": i.post.platform.value,
                "tone": i.metadata.tone.value,
                "length_bucket": i.metadata.length_bucket,
                "language": i.metadata.language,
                "topics_json": json.dumps(i.metadata.topics),
                "post_json": i.post.model_dump_json(),
            }
            for i in items
        ]
        self._col.upsert(ids=ids, embeddings=vectors, documents=docs, metadatas=metadatas)

    def query(
        self,
        *,
        text: str,
        platform: Platform,
        author: str | None = None,
        k: int = 5,
        tone: str | None = None,
    ) -> list[ExemplarHit]:
        vec = self._embedder.embed_single(text).tolist()
        clauses: list[dict[str, object]] = [{"platform": platform.value}]
        if author:
            clauses.append({"author": author})
        if tone:
            clauses.append({"tone": tone})
        where = clauses[0] if len(clauses) == 1 else {"$and": clauses}
        result = self._col.query(query_embeddings=[vec], n_results=k, where=where)
        hits: list[ExemplarHit] = []
        metadatas = result.get("metadatas", [[]])
        distances = result.get("distances", [[]])
        if not metadatas or not metadatas[0]:
            return hits
        for meta, dist in zip(metadatas[0], distances[0], strict=True):
            post = Post.model_validate_json(meta["post_json"])
            pm = PostMetadata(
                topics=json.loads(meta["topics_json"]),
                tone=meta["tone"],
                length_bucket=meta["length_bucket"],
                language=meta["language"],
            )
            hits.append(ExemplarHit(post=post, metadata=pm, score=1.0 - float(dist)))
        return hits

    def query_diverse(
        self,
        *,
        text: str,
        platform: Platform,
        author: str | None = None,
        k: int = 5,
    ) -> list[ExemplarHit]:
        """Query with diversity sampling across tones and length buckets."""
        # Over-retrieve
        candidates = self.query(text=text, platform=platform, author=author, k=k * 3)
        if len(candidates) <= k:
            return candidates

        # Group by tone
        by_tone: dict[str, list[ExemplarHit]] = {}
        for hit in candidates:
            tone = hit.metadata.tone
            if tone not in by_tone:
                by_tone[tone] = []
            by_tone[tone].append(hit)

        # Round-robin sample from each tone
        diverse: list[ExemplarHit] = []
        tone_keys = list(by_tone.keys())
        idx = 0
        while len(diverse) < k and any(by_tone.values()):
            tone = tone_keys[idx % len(tone_keys)]
            if by_tone[tone]:
                diverse.append(by_tone[tone].pop(0))
            idx += 1
            # Remove empty tone groups
            tone_keys = [t for t in tone_keys if by_tone[t]]
            if not tone_keys:
                break

        return diverse[:k]
