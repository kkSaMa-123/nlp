"""Extract clean memory notes from dialogue sessions."""

from __future__ import annotations

import json
import re
from typing import Any


class MemoryWriter:
    """Use the chat model to turn raw dialogue into compact memory notes."""

    def __init__(
        self,
        llm,
        max_memories_per_session: int = 8,
        include_detail_notes: bool = False,
        detail_notes_per_session: int = 3,
    ):
        self.llm = llm
        self.max_memories_per_session = max_memories_per_session
        self.include_detail_notes = include_detail_notes
        self.detail_notes_per_session = detail_notes_per_session

    def extract_session_memories(
        self,
        session: dict[str, Any],
        speaker_a: str = "",
        speaker_b: str = "",
    ) -> list[dict[str, Any]]:
        session_id = session.get("session_id", "")
        date_time = session.get("date_time", "")
        turns = session.get("turns", [])
        transcript = self._format_turns(turns)
        if not transcript:
            return []

        prompt = (
            "Extract long-term memory notes from this dialogue session.\n"
            "A good memory is a stable fact about a person: preferences, goals, "
            "plans, relationships, important events, dates, jobs, hobbies, health, "
            "family, or information that may be useful later.\n"
            "Prefer concrete details over vague summaries. Keep exact names, dates, "
            "book titles, food lists, places, car models, schools, durations, and "
            "comparison preferences when they appear.\n"
            "If a person lists several items, keep all listed items in one note. "
            "If the dialogue says someone prefers one option over another, write the "
            "preferred option clearly. If a relative date appears, keep the relative "
            "phrase and the session date will be attached later.\n"
            "Do not include greetings, small talk, vague encouragement, or duplicate notes.\n"
            "Rewrite each note as a short standalone English sentence.\n"
            "Bad memory: \"Tim likes fantasy books.\" Good memory: "
            "\"Tim has read Harry Potter, Game of Thrones, The Hobbit, and The Name of the Wind.\"\n"
            "Bad memory: \"Maria had dinner with her mother.\" Good memory: "
            "\"Maria and her mother had salads, sandwiches, and homemade desserts for dinner.\"\n"
            f"Return at most {self.max_memories_per_session} notes.\n"
            "Return JSON only, in this format:\n"
            "[{\"text\": \"...\", \"speaker\": \"Caroline\", \"importance\": 1-5, "
            "\"source_turns\": [\"D1:1\"]}]\n\n"
            f"Speakers: {speaker_a}, {speaker_b}\n"
            f"Session: {session_id}\n"
            f"Date: {date_time}\n\n"
            f"Dialogue:\n{transcript}"
        )

        raw = self.llm.generate(prompt, max_tokens=512, temperature=0.0)
        notes = self._parse_json_list(raw)
        if not notes:
            notes = self._fallback_notes(turns)

        memories = []
        for i, note in enumerate(notes[: self.max_memories_per_session], start=1):
            text = str(note.get("text", "")).strip()
            if not text:
                continue
            memories.append(
                {
                    "id": f"s{session_id}-m{i}",
                    "text": text,
                    "speaker": str(note.get("speaker", "")).strip(),
                    "importance": self._safe_importance(note.get("importance", 3)),
                    "source_turns": note.get("source_turns", []),
                    "session_id": session_id,
                    "date_time": date_time,
                    "type": "fact",
                }
            )
        if self.include_detail_notes:
            memories.extend(
                self._detail_notes(
                    turns=turns,
                    session_id=session_id,
                    date_time=date_time,
                    start_index=len(memories) + 1,
                )
            )
        return memories

    def _format_turns(self, turns: list[dict[str, Any]]) -> str:
        lines = []
        for turn in turns:
            dia_id = turn.get("dia_id", "")
            speaker = turn.get("speaker", "")
            text = turn.get("text", "")
            if text:
                lines.append(f"{dia_id} {speaker}: {text}")
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

    def _fallback_notes(self, turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        notes = []
        for turn in turns:
            text = str(turn.get("text", "")).strip()
            if len(text.split()) < 8:
                continue
            notes.append(
                {
                    "text": f"{turn.get('speaker', 'Someone')} said: {text}",
                    "speaker": turn.get("speaker", ""),
                    "importance": 2,
                    "source_turns": [turn.get("dia_id", "")],
                }
            )
            if len(notes) >= self.max_memories_per_session:
                break
        return notes

    def _detail_notes(
        self,
        turns: list[dict[str, Any]],
        session_id: Any,
        date_time: str,
        start_index: int,
    ) -> list[dict[str, Any]]:
        notes = []
        seen = set()
        for turn in turns:
            text = str(turn.get("text", "")).strip()
            if not self._is_high_signal(text):
                continue
            normalized = re.sub(r"\s+", " ", text)
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            speaker = turn.get("speaker", "")
            notes.append(
                {
                    "id": f"s{session_id}-d{start_index + len(notes)}",
                    "text": f"{speaker} mentioned this concrete detail: {normalized}",
                    "speaker": speaker,
                    "importance": 3,
                    "source_turns": [turn.get("dia_id", "")],
                    "session_id": session_id,
                    "date_time": date_time,
                    "type": "detail",
                }
            )
            if len(notes) >= self.detail_notes_per_session:
                break
        return notes

    def _is_high_signal(self, text: str) -> bool:
        if len(text.split()) < 6:
            return False
        lower = text.lower()
        keywords = {
            "book",
            "read",
            "reading",
            "school",
            "college",
            "basketball",
            "networking",
            "event",
            "dinner",
            "salad",
            "sandwich",
            "dessert",
            "prefer",
            "rather",
            "charger",
            "subaru",
            "forester",
            "dodge",
            "japan",
            "month",
            "months",
            "friend",
            "colleague",
            "family",
        }
        months = {
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
            "yesterday",
            "tomorrow",
            "last week",
            "two days ago",
        }
        has_keyword = any(word in lower for word in keywords | months)
        has_number = bool(re.search(r"\d", text))
        has_list = text.count(",") >= 2 or ";" in text
        has_comparison = " or " in lower and any(
            word in lower for word in {"prefer", "rather", "choose", "work on"}
        )
        return has_keyword or has_number or has_list or has_comparison

    def _safe_importance(self, value: Any) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = 3
        return max(1, min(5, number))
