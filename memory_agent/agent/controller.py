"""Memory-based agents used by the evaluation script."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from memory_agent.memory.store import MemoryStore
from memory_agent.memory.updater import MemoryUpdater
from memory_agent.memory.writer import MemoryWriter


def _load_llm_client():
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


class AppendOnlyMemoryAgent:
    """First real memory agent: extract notes once, then retrieve them for QA."""

    def __init__(self):
        LLMClient = _load_llm_client()
        self.llm = LLMClient()

        from sentence_transformers import SentenceTransformer

        embed_model_name = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
        self.embed_model = SentenceTransformer(embed_model_name)
        self.store = MemoryStore(
            self.embed_model,
            top_k=int(os.getenv("MEMORY_TOP_K", "8")),
            keyword_weight=float(os.getenv("MEMORY_KEYWORD_WEIGHT", "0.0")),
        )
        self.writer = MemoryWriter(
            self.llm,
            max_memories_per_session=int(os.getenv("MEMORY_PER_SESSION", "8")),
            include_detail_notes=os.getenv("MEMORY_DETAIL_NOTES", "0") == "1",
            detail_notes_per_session=int(os.getenv("MEMORY_DETAIL_NOTES_PER_SESSION", "3")),
        )
        self.last_retrieved: list[dict] = []
        self.log_dir = Path(os.getenv("MEMORY_LOG_DIR", "experiments/logs"))
        self.log_path = self.log_dir / f"append_agent_{int(time.time())}_{id(self)}.jsonl"

    def ingest(self, conversation: dict) -> None:
        speaker_a = conversation.get("speaker_a", "")
        speaker_b = conversation.get("speaker_b", "")
        memories = []
        for session in conversation.get("sessions", []):
            memories.extend(
                self.writer.extract_session_memories(
                    session,
                    speaker_a=speaker_a,
                    speaker_b=speaker_b,
                )
            )
        self.store.add_many(memories)
        self._write_log(
            {
                "event": "ingest",
                "speaker_a": speaker_a,
                "speaker_b": speaker_b,
                "num_sessions": len(conversation.get("sessions", [])),
                "num_memories": len(memories),
                "memories": memories,
            }
        )

    def answer(self, question: str) -> str:
        retrieved = self.store.search(question)
        self.last_retrieved = retrieved
        context = self._format_memories(retrieved)
        prompt = (
            "You are answering a question about a past conversation.\n"
            "Use only the extracted memories below. Keep the answer short, usually "
            "a phrase or one sentence. If the memories do not contain the answer, "
            "reply 'unknown'. For date questions, use the memory date when it helps "
            "resolve relative time expressions like yesterday or last week.\n\n"
            f"=== Extracted memories ===\n{context}\n\n"
            f"=== Question ===\n{question}\n\n"
            "=== Answer ==="
        )
        answer = self.llm.generate(prompt, max_tokens=64, temperature=0.0).strip()
        self._write_log(
            {
                "event": "answer",
                "question": question,
                "retrieved": retrieved,
                "prompt": prompt,
                "answer": answer,
            }
        )
        return answer

    def _format_memories(self, memories: list[dict]) -> str:
        if not memories:
            return "(none)"
        lines = []
        for memory in memories:
            date_time = memory.get("date_time", "")
            session_id = memory.get("session_id", "")
            score = memory.get("score", 0.0)
            text = memory.get("text", "")
            hint = self._relative_date_hint(text, date_time)
            suffix = f" ({hint})" if hint else ""
            lines.append(
                f"- [Session {session_id} @ {date_time}; score={score:.3f}] {text}{suffix}"
            )
        return "\n".join(lines)

    def _relative_date_hint(self, text: str, date_time: str) -> str:
        base_date = self._parse_session_date(date_time)
        if base_date is None:
            return ""

        lower = text.lower()
        target = None
        phrase = ""
        if "two days ago" in lower:
            target = base_date - timedelta(days=2)
            phrase = "two days ago"
        elif "yesterday" in lower:
            target = base_date - timedelta(days=1)
            phrase = "yesterday"
        else:
            weekdays = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }
            for name, weekday in weekdays.items():
                marker = f"last {name}"
                if marker in lower:
                    days_back = (base_date.weekday() - weekday) % 7
                    days_back = days_back or 7
                    target = base_date - timedelta(days=days_back)
                    phrase = marker
                    break

        if target is None:
            return ""
        return f"date hint: {phrase} = {target.strftime('%d %B %Y')}"

    def _parse_session_date(self, date_time: str) -> datetime | None:
        marker = " on "
        if marker not in date_time:
            return None
        raw_date = date_time.split(marker, 1)[1].strip()
        for fmt in ("%d %B, %Y", "%d %B %Y"):
            try:
                return datetime.strptime(raw_date, fmt)
            except ValueError:
                pass
        return None

    def _write_log(self, record: dict) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


class UpdateMemoryAgent(AppendOnlyMemoryAgent):
    """Memory agent with deduplication, merging, and conflict update decisions."""

    def __init__(self):
        super().__init__()
        self.updater = MemoryUpdater(
            self.llm,
            candidate_k=int(os.getenv("MEMORY_UPDATE_CANDIDATE_K", "3")),
            similarity_threshold=float(os.getenv("MEMORY_UPDATE_THRESHOLD", "0.72")),
            use_llm=os.getenv("MEMORY_UPDATE_USE_LLM", "1") == "1",
        )
        self.log_path = self.log_dir / f"update_agent_{int(time.time())}_{id(self)}.jsonl"

    def ingest(self, conversation: dict) -> None:
        speaker_a = conversation.get("speaker_a", "")
        speaker_b = conversation.get("speaker_b", "")
        extracted = []
        for session in conversation.get("sessions", []):
            session_memories = self.writer.extract_session_memories(
                session,
                speaker_a=speaker_a,
                speaker_b=speaker_b,
            )
            extracted.extend(session_memories)
            self.updater.update(self.store, session_memories)

        active_count = len(self.store.active_memories())
        obsolete_count = len(self.store.memories) - active_count
        self._write_log(
            {
                "event": "ingest",
                "agent": "UpdateMemoryAgent",
                "speaker_a": speaker_a,
                "speaker_b": speaker_b,
                "num_sessions": len(conversation.get("sessions", [])),
                "num_extracted_memories": len(extracted),
                "num_stored_memories": len(self.store.memories),
                "num_active_memories": active_count,
                "num_obsolete_memories": obsolete_count,
                "update_stats": self.updater.stats,
                "update_events": self.updater.events,
                "memories": self.store.memories,
            }
        )
