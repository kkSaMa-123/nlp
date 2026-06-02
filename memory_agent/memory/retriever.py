"""Retriever wrapper for memory search and lightweight reranking."""

from __future__ import annotations

from typing import Any

from memory_agent.memory.store import MemoryStore


class MemoryRetriever:
    """Retrieve active memories from a MemoryStore.

    The current project keeps the vector index in MemoryStore. This wrapper gives
    the retrieval step an explicit module so experiments can swap retrieval
    strategies without changing the agent controller.
    """

    def __init__(self, store: MemoryStore, top_k: int | None = None):
        self.store = store
        self.top_k = top_k

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        return self.store.search(query, top_k=top_k or self.top_k)

