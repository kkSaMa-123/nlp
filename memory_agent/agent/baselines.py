"""Baseline agents for the long-term memory project.

These agents implement the minimal interface expected by eval_kit/run_generation.py:
`ingest(conversation)` followed by one or more `answer(question)` calls.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np


def _load_llm_client():
    """Import the eval kit LLM client from either project-root or eval_kit cwd."""
    try:
        from llm_client import LLMClient

        return LLMClient
    except ImportError:
        project_root = Path(__file__).resolve().parents[2]
        eval_kit_dir = project_root / "eval_kit"
        if str(eval_kit_dir) not in sys.path:
            sys.path.insert(0, str(eval_kit_dir))
        from llm_client import LLMClient

        return LLMClient


class NoMemoryAgent:
    """No-memory baseline: answer using only the current question.

    This is intentionally weak and serves as the required no-memory control group.
    It does not read or store the conversation passed to `ingest`.
    """

    def __init__(self):
        LLMClient = _load_llm_client()
        self.llm = LLMClient()

    def ingest(self, conversation: dict) -> None:
        self.conversation_meta = {
            "speaker_a": conversation.get("speaker_a", ""),
            "speaker_b": conversation.get("speaker_b", ""),
            "num_sessions": len(conversation.get("sessions", [])),
        }

    def answer(self, question: str) -> str:
        prompt = (
            "You are answering a question about a past conversation, but you do not "
            "have access to the conversation history. Answer only if the question "
            "itself contains enough information. Otherwise reply 'unknown'. "
            "Keep the answer short (a phrase or one sentence).\n\n"
            f"=== Question ===\n{question}\n\n"
            "=== Answer ==="
        )
        return self.llm.generate(prompt, max_tokens=64).strip()


class RawTurnRAGAgent:
    """Vanilla RAG baseline over raw dialogue turns.

    This baseline intentionally indexes raw conversation turns rather than
    extracted memory units. It is useful as a control group, but it is not the
    final long-term memory system required by the assignment.
    """

    def __init__(self, top_k: int | None = None):
        LLMClient = _load_llm_client()
        self.llm = LLMClient()

        from sentence_transformers import SentenceTransformer

        embed_model = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
        self.embed_model = SentenceTransformer(embed_model)
        self.top_k = top_k or int(os.getenv("RAG_TOP_K", "6"))
        self.chunks: list[str] = []
        self.embeddings: np.ndarray | None = None
        self.last_retrieved: list[str] = []

    def ingest(self, conversation: dict) -> None:
        chunks = []
        for session in conversation.get("sessions", []):
            session_id = session.get("session_id", "")
            date_time = session.get("date_time", "")
            for turn in session.get("turns", []):
                speaker = turn.get("speaker", "")
                text = turn.get("text", "")
                dia_id = turn.get("dia_id", "")
                chunks.append(
                    f"[Session {session_id} @ {date_time}; turn {dia_id}] "
                    f"{speaker}: {text}"
                )

        self.chunks = chunks
        if not chunks:
            self.embeddings = np.zeros((0, 1), dtype=np.float32)
            return

        vecs = self.embed_model.encode(chunks, normalize_embeddings=True)
        self.embeddings = np.asarray(vecs, dtype=np.float32)

    def _retrieve(self, question: str) -> list[str]:
        if self.embeddings is None or len(self.chunks) == 0:
            return []

        qvec = self.embed_model.encode([question], normalize_embeddings=True)[0]
        qvec = np.asarray(qvec, dtype=np.float32)
        scores = self.embeddings @ qvec
        top_k = min(self.top_k, len(self.chunks))
        top_idx = np.argsort(-scores)[:top_k]
        return [self.chunks[i] for i in top_idx]

    def answer(self, question: str) -> str:
        retrieved = self._retrieve(question)
        self.last_retrieved = retrieved
        context = "\n".join(retrieved)
        prompt = (
            "You are answering a question about a past conversation. "
            "Use only the retrieved dialogue snippets below. Keep the answer short "
            "(a phrase or one sentence). If the snippets do not contain the answer, "
            "reply 'unknown'.\n\n"
            f"=== Retrieved dialogue snippets ===\n{context}\n\n"
            f"=== Question ===\n{question}\n\n"
            "=== Answer ==="
        )
        return self.llm.generate(prompt, max_tokens=64).strip()
