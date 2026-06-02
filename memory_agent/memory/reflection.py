"""Generate high-level reflection memories from lower-level memories."""

from __future__ import annotations

import json
import re
from typing import Any


class MemoryReflector:
    """Summarize active memories into high-level, reusable reflection memories."""

    def __init__(
        self,
        llm,
        max_reflections: int = 8,
        max_input_memories: int = 120,
    ):
        self.llm = llm
        self.max_reflections = max_reflections
        self.max_input_memories = max_input_memories

    def reflect(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        selected = self._select_memories(memories)
        if not selected:
            return []

        memory_text = self._format_memories(selected)
        prompt = (
            "Create high-level long-term reflection memories from the extracted "
            "conversation memories below.\n"
            "A reflection should summarize stable patterns that may help answer "
            "future questions: relationships, identity, goals, preferences, repeated "
            "activities, life plans, major themes, or cross-session conclusions.\n"
            "Do not invent facts. Do not include vague statements. Keep exact names "
            "when possible. Each reflection must be a short standalone English sentence.\n"
            f"Return at most {self.max_reflections} reflections.\n"
            "Return JSON only in this format:\n"
            "[{\"text\":\"...\", \"topic\":\"profile|relationship|goal|preference|event\", "
            "\"importance\": 1-5, \"source_memory_ids\":[\"mem-id\"]}]\n\n"
            f"Memories:\n{memory_text}"
        )
        raw = self.llm.generate(prompt, max_tokens=640, temperature=0.0)
        notes = self._parse_json_list(raw)
        if not notes:
            return self._fallback_reflections(selected)

        reflections = []
        for i, note in enumerate(notes[: self.max_reflections], start=1):
            text = str(note.get("text", "")).strip()
            if not text:
                continue
            reflections.append(
                {
                    "id": f"reflection-{i}",
                    "text": text,
                    "topic": str(note.get("topic", "")).strip(),
                    "importance": self._safe_importance(note.get("importance", 5)),
                    "source_memory_ids": note.get("source_memory_ids", []),
                    "type": "reflection",
                    "status": "active",
                    "session_id": "reflection",
                    "date_time": "",
                }
            )
        return reflections

    def _fallback_reflections(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        speaker_groups: dict[str, list[dict[str, Any]]] = {}
        for memory in memories:
            speaker = str(memory.get("speaker", "")).strip()
            if not speaker:
                speaker = self._guess_speaker(str(memory.get("text", "")))
            if not speaker:
                continue
            speaker_groups.setdefault(speaker, []).append(memory)

        reflections = []
        for speaker, group in sorted(
            speaker_groups.items(),
            key=lambda item: len(item[1]),
            reverse=True,
        ):
            topics = self._top_terms([str(m.get("text", "")) for m in group], limit=5)
            if not topics:
                continue
            source_ids = [str(m.get("id", "")) for m in group[:8] if m.get("id")]
            reflections.append(
                {
                    "id": f"reflection-{len(reflections) + 1}",
                    "text": f"{speaker}'s recurring memory themes include {', '.join(topics)}.",
                    "topic": "profile",
                    "importance": 4,
                    "source_memory_ids": source_ids,
                    "type": "reflection",
                    "status": "active",
                    "session_id": "reflection",
                    "date_time": "",
                }
            )
            if len(reflections) >= self.max_reflections:
                break
        return reflections

    def _guess_speaker(self, text: str) -> str:
        match = re.match(r"([A-Z][a-z]+)\\b", text)
        return match.group(1) if match else ""

    def _top_terms(self, texts: list[str], limit: int = 5) -> list[str]:
        stopwords = {
            "about",
            "after",
            "also",
            "and",
            "are",
            "awesome",
            "because",
            "been",
            "being",
            "caroline",
            "concrete",
            "cool",
            "detail",
            "for",
            "from",
            "good",
            "great",
            "has",
            "have",
            "her",
            "him",
            "his",
            "into",
            "like",
            "love",
            "melanie",
            "mentioned",
            "really",
            "said",
            "that",
            "the",
            "their",
            "this",
            "through",
            "what",
            "with",
        }
        counts: dict[str, int] = {}
        for text in texts:
            for token in re.findall(r"[a-z][a-z+\\-]{3,}", text.lower()):
                if token in stopwords:
                    continue
                counts[token] = counts.get(token, 0) + 1
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [term for term, _ in ranked[:limit]]

    def _select_memories(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        active = [m for m in memories if m.get("status", "active") == "active"]
        if len(active) <= self.max_input_memories:
            return active

        def rank(memory: dict[str, Any]) -> tuple[int, int]:
            importance = int(memory.get("importance", 3))
            type_bonus = 1 if memory.get("type") in {"fact", "reflection"} else 0
            return importance, type_bonus

        return sorted(active, key=rank, reverse=True)[: self.max_input_memories]

    def _format_memories(self, memories: list[dict[str, Any]]) -> str:
        lines = []
        for memory in memories:
            memory_id = memory.get("id", "")
            date_time = memory.get("date_time", "")
            memory_type = memory.get("type", "fact")
            text = memory.get("text", "")
            lines.append(f"- id={memory_id}; date={date_time}; type={memory_type}; text={text}")
        return "\n".join(lines)

    def _parse_json_list(self, raw: str) -> list[dict[str, Any]]:
        text = raw.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\[[\s\S]*\]", text)
            if not match:
                return []
            try:
                obj = json.loads(match.group(0))
            except json.JSONDecodeError:
                return []
        if not isinstance(obj, list):
            return []
        return [item for item in obj if isinstance(item, dict)]

    def _safe_importance(self, value: Any) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = 5
        return max(1, min(5, number))
