"""Deduplicate and update memory notes before storing them."""

from __future__ import annotations

import json
import re
from typing import Any

from memory_agent.memory.store import MemoryStore


class MemoryUpdater:
    """Apply simple ADD / IGNORE / MERGE / UPDATE decisions for new memories."""

    def __init__(
        self,
        llm,
        candidate_k: int = 3,
        similarity_threshold: float = 0.72,
        use_llm: bool = True,
    ):
        self.llm = llm
        self.candidate_k = candidate_k
        self.similarity_threshold = similarity_threshold
        self.use_llm = use_llm
        self.stats = {
            "seen": 0,
            "add": 0,
            "ignore": 0,
            "merge": 0,
            "update": 0,
        }
        self.events: list[dict[str, Any]] = []

    def update(self, store: MemoryStore, new_memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        stored = []
        for memory in new_memories:
            result = self.update_one(store, memory)
            if result is not None:
                stored.append(result)
        return stored

    def update_one(self, store: MemoryStore, new_memory: dict[str, Any]) -> dict[str, Any] | None:
        self.stats["seen"] += 1
        new_text = str(new_memory.get("text", "")).strip()
        if not new_text:
            return None

        candidates = store.search(new_text, top_k=self.candidate_k)
        candidates = [
            candidate
            for candidate in candidates
            if candidate.get("score", 0.0) >= self.similarity_threshold
        ]
        if not candidates:
            added = store.add_one(new_memory)
            self._record("ADD", new_memory, None, added, "no similar active memory")
            return added

        best = candidates[0]
        decision = self._decide(best, new_memory)
        action = decision.get("action", "ADD").upper()
        final_text = str(decision.get("text", "")).strip()
        reason = str(decision.get("reason", "")).strip()

        if action == "IGNORE":
            self._record("IGNORE", new_memory, best, None, reason)
            return None

        if action == "MERGE" and final_text:
            ok = store.update_text(
                best["id"],
                final_text,
                {
                    "merged_from": best.get("merged_from", []) + [new_memory.get("id")],
                    "importance": max(
                        int(best.get("importance", 3)),
                        int(new_memory.get("importance", 3)),
                    ),
                },
            )
            merged = store.get(best["id"]) if ok else None
            self._record("MERGE", new_memory, best, merged, reason)
            return merged

        if action == "UPDATE":
            store.mark_obsolete(best["id"], reason or "updated by newer memory")
            updated_memory = dict(new_memory)
            if final_text:
                updated_memory["text"] = final_text
            updated_memory["replaces"] = best.get("id")
            added = store.add_one(updated_memory)
            self._record("UPDATE", new_memory, best, added, reason)
            return added

        added = store.add_one(new_memory)
        self._record("ADD", new_memory, best, added, reason or "new compatible memory")
        return added

    def _decide(self, old_memory: dict[str, Any], new_memory: dict[str, Any]) -> dict[str, str]:
        old_text = str(old_memory.get("text", ""))
        new_text = str(new_memory.get("text", ""))

        rule_decision = self._rule_decide(old_text, new_text)
        if rule_decision is not None or not self.use_llm:
            return rule_decision or {"action": "ADD", "text": new_text, "reason": "rule fallback"}

        prompt = (
            "Compare an old memory and a new memory.\n"
            "Choose exactly one action:\n"
            "- ADD: the new memory is related but contains a distinct useful fact.\n"
            "- IGNORE: the new memory repeats the old memory.\n"
            "- MERGE: both memories are compatible and should become one richer memory.\n"
            "- UPDATE: the new memory contradicts or replaces the old memory.\n\n"
            "Return JSON only:\n"
            "{\"action\":\"ADD|IGNORE|MERGE|UPDATE\","
            "\"text\":\"final memory text if needed\","
            "\"reason\":\"short reason\"}\n\n"
            f"Old memory date: {old_memory.get('date_time', '')}\n"
            f"Old memory: {old_text}\n\n"
            f"New memory date: {new_memory.get('date_time', '')}\n"
            f"New memory: {new_text}"
        )
        raw = self.llm.generate(prompt, max_tokens=160, temperature=0.0)
        parsed = self._parse_decision(raw)
        if parsed:
            return parsed
        return {"action": "ADD", "text": new_text, "reason": "could not parse updater decision"}

    def _rule_decide(self, old_text: str, new_text: str) -> dict[str, str] | None:
        old_norm = self._normalize(old_text)
        new_norm = self._normalize(new_text)
        if not old_norm or not new_norm:
            return None
        if old_norm == new_norm:
            return {"action": "IGNORE", "text": old_text, "reason": "exact duplicate"}
        if old_norm in new_norm:
            return {"action": "UPDATE", "text": new_text, "reason": "new memory is more specific"}
        if new_norm in old_norm:
            return {"action": "IGNORE", "text": old_text, "reason": "old memory already covers new memory"}

        old_terms = self._terms(old_text)
        new_terms = self._terms(new_text)
        if not old_terms or not new_terms:
            return None
        overlap = len(old_terms & new_terms) / max(1, min(len(old_terms), len(new_terms)))
        if overlap >= 0.9:
            merged = self._merge_text(old_text, new_text)
            return {"action": "MERGE", "text": merged, "reason": "high term overlap"}
        return None

    def _parse_decision(self, raw: str) -> dict[str, str] | None:
        text = raw.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                return None
            try:
                obj = json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        action = str(obj.get("action", "")).upper().strip()
        if action not in {"ADD", "IGNORE", "MERGE", "UPDATE"}:
            return None
        return {
            "action": action,
            "text": str(obj.get("text", "")).strip(),
            "reason": str(obj.get("reason", "")).strip(),
        }

    def _record(
        self,
        action: str,
        new_memory: dict[str, Any],
        old_memory: dict[str, Any] | None,
        result_memory: dict[str, Any] | None,
        reason: str,
    ) -> None:
        key = action.lower()
        if key in self.stats:
            self.stats[key] += 1
        self.events.append(
            {
                "action": action,
                "reason": reason,
                "new_memory": new_memory,
                "old_memory": old_memory,
                "result_memory": result_memory,
            }
        )

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text.lower())).strip()

    def _terms(self, text: str) -> set[str]:
        stopwords = {
            "about",
            "and",
            "are",
            "but",
            "for",
            "from",
            "has",
            "have",
            "her",
            "his",
            "into",
            "mentioned",
            "this",
            "that",
            "the",
            "their",
            "with",
        }
        return {
            token
            for token in re.findall(r"[a-z0-9]+", text.lower())
            if len(token) > 2 and token not in stopwords
        }

    def _merge_text(self, old_text: str, new_text: str) -> str:
        if old_text.rstrip(".") in new_text:
            return new_text
        if new_text.rstrip(".") in old_text:
            return old_text
        return f"{old_text.rstrip('.')}; {new_text}"
