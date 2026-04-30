from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

import chromadb

from writer_profile.corpus.models import AnnotatedPost, Platform, Post, PostMetadata
from writer_profile.retrieval.embedder import Embedder


@dataclass
class ExemplarHit:
    post: Post
    metadata: PostMetadata
    score: float


class ExemplarStore:
    def __init__(
        self,
        *,
        embedder: Embedder,
        collection: str = "posts",
        path: str | None = None,
        api_key: str | None = None,
        host: str | None = None,
        tenant: str | None = None,
        database: str | None = None,
    ) -> None:
        if api_key and host and tenant and database:
            self._client = chromadb.CloudClient(
                cloud_port=443,
                cloud_host=host,
                api_key=api_key,
                tenant=tenant,
                database=database,
            )
        else:
            self._client = chromadb.PersistentClient(path=path or ".chroma")
        self._col = self._client.get_or_create_collection(
            name=collection, metadata={"hnsw:space": "cosine"}
        )
        self._embedder = embedder

    def add_many(self, items: list[AnnotatedPost], max_doc_chars: int = 4000) -> None:
        if not items:
            return
        ids = [hashlib.md5(i.post.id.encode()).hexdigest()[:24] for i in items]
        docs = [i.post.text[:max_doc_chars] for i in items]
        vectors = self._embedder.embed(docs).tolist()
        metadatas = [
            {
                "author": i.post.author,
                "platform": i.post.platform.value,
                "tone": i.metadata.tone.value,
                "length_bucket": i.metadata.length_bucket,
                "language": i.metadata.language,
                "topics": ",".join(i.metadata.topics[:5]),
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
        documents = result.get("documents", [[]])
        ids = result.get("ids", [[]])
        if not metadatas or not metadatas[0]:
            return hits
        for i, (meta, dist) in enumerate(zip(metadatas[0], distances[0], strict=True)):
            doc_text = documents[0][i] if documents and documents[0] else ""
            doc_id = ids[0][i] if ids and ids[0] else f"unknown_{i}"
            topics = meta.get("topics", "").split(",") if meta.get("topics") else []
            post = Post(
                id=doc_id,
                author=meta["author"],
                platform=Platform(meta["platform"]),
                text=doc_text,
                created_at=datetime.now(UTC),
            )
            pm = PostMetadata(
                topics=topics,
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
        candidates = self.query(text=text, platform=platform, author=author, k=k * 3)
        if len(candidates) <= k:
            return candidates

        by_tone: dict[str, list[ExemplarHit]] = {}
        for hit in candidates:
            tone = hit.metadata.tone
            if tone not in by_tone:
                by_tone[tone] = []
            by_tone[tone].append(hit)

        diverse: list[ExemplarHit] = []
        tone_keys = list(by_tone.keys())
        idx = 0
        while len(diverse) < k and any(by_tone.values()):
            tone = tone_keys[idx % len(tone_keys)]
            if by_tone[tone]:
                diverse.append(by_tone[tone].pop(0))
            idx += 1
            tone_keys = [t for t in tone_keys if by_tone[t]]
            if not tone_keys:
                break

        return diverse[:k]
