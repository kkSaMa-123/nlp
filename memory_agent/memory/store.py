"""A small in-memory vector store for extracted memory notes."""

from __future__ import annotations

import re
from typing import Any

import numpy as np


class MemoryStore:
    """Store memory dicts and retrieve the most relevant ones by cosine score."""

    def __init__(self, embed_model, top_k: int = 8, keyword_weight: float = 0.0):
        self.embed_model = embed_model
        self.top_k = top_k
        self.keyword_weight = keyword_weight
        self.memories: list[dict[str, Any]] = []
        self.embeddings: np.ndarray | None = None

    def add_many(self, memories: list[dict[str, Any]]) -> None:
        clean = []
        for memory in memories:
            text = str(memory.get("text", "")).strip()
            if not text:
                continue
            item = dict(memory)
            item["id"] = item.get("id") or f"mem-{len(self.memories) + len(clean) + 1}"
            item["text"] = text
            item["status"] = item.get("status", "active")
            clean.append(item)

        if not clean:
            return

        self.memories.extend(clean)
        self.rebuild_index()

    def add_one(self, memory: dict[str, Any]) -> dict[str, Any] | None:
        before = len(self.memories)
        self.add_many([memory])
        if len(self.memories) == before:
            return None
        return self.memories[-1]

    def rebuild_index(self) -> None:
        if not self.memories:
            self.embeddings = None
            return
        texts = [m["text"] for m in self.memories]
        vecs = self.embed_model.encode(texts, normalize_embeddings=True)
        self.embeddings = np.asarray(vecs, dtype=np.float32)

    def get(self, memory_id: str) -> dict[str, Any] | None:
        for memory in self.memories:
            if memory.get("id") == memory_id:
                return memory
        return None

    def mark_obsolete(self, memory_id: str, reason: str = "") -> bool:
        memory = self.get(memory_id)
        if memory is None:
            return False
        memory["status"] = "obsolete"
        if reason:
            memory["obsolete_reason"] = reason
        return True

    def update_text(self, memory_id: str, text: str, extra: dict[str, Any] | None = None) -> bool:
        memory = self.get(memory_id)
        if memory is None:
            return False
        memory["text"] = text.strip()
        if extra:
            memory.update(extra)
        self.rebuild_index()
        return True

    def active_memories(self) -> list[dict[str, Any]]:
        return [m for m in self.memories if m.get("status", "active") == "active"]

    def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        if self.embeddings is None or not self.memories:
            return []

        qvec = self.embed_model.encode([query], normalize_embeddings=True)[0]
        qvec = np.asarray(qvec, dtype=np.float32)
        vector_scores = self.embeddings @ qvec
        keyword_scores = np.asarray(
            [self._keyword_score(query, memory["text"]) for memory in self.memories],
            dtype=np.float32,
        )
        scores = vector_scores + self.keyword_weight * keyword_scores

        active_idx = [
            idx
            for idx, memory in enumerate(self.memories)
            if memory.get("status", "active") == "active"
        ]
        if not active_idx:
            return []

        ranked_idx = sorted(active_idx, key=lambda idx: float(scores[idx]), reverse=True)
        k = min(top_k or self.top_k, len(ranked_idx))
        top_idx = ranked_idx[:k]
        results = []
        for idx in top_idx:
            item = dict(self.memories[int(idx)])
            item["score"] = float(scores[int(idx)])
            item["vector_score"] = float(vector_scores[int(idx)])
            item["keyword_score"] = float(keyword_scores[int(idx)])
            results.append(item)
        return results

    def _keyword_score(self, query: str, text: str) -> float:
        query_terms = self._terms(query)
        if not query_terms:
            return 0.0
        text_terms = self._terms(text)
        if not text_terms:
            return 0.0
        overlap = query_terms & text_terms
        return len(overlap) / len(query_terms)

    def _terms(self, text: str) -> set[str]:
        stopwords = {
            "a",
            "an",
            "and",
            "are",
            "did",
            "does",
            "for",
            "had",
            "has",
            "have",
            "how",
            "in",
            "is",
            "of",
            "on",
            "or",
            "the",
            "to",
            "was",
            "were",
            "what",
            "when",
            "who",
            "with",
            "would",
        }
        return {
            token
            for token in re.findall(r"[a-z0-9]+", text.lower())
            if len(token) > 2 and token not in stopwords
        }
