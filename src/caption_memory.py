"""Per-city history of recent captions — fuels anti-repetition logic."""

import json
import os
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


MAX_ENTRIES_PER_CITY = 10


@dataclass
class CaptionHistoryEntry:
    timestamp: str  # ISO 8601
    angle: str
    literary_form: str
    narrator: str
    tone: str
    first_three_words: str

    @classmethod
    def from_dict(cls, d: dict) -> "CaptionHistoryEntry":
        return cls(
            timestamp=d.get("timestamp", ""),
            angle=d.get("angle", ""),
            literary_form=d.get("literary_form", ""),
            narrator=d.get("narrator", ""),
            tone=d.get("tone", ""),
            first_three_words=d.get("first_three_words", ""),
        )


class CaptionMemory:
    """JSON-backed store of recent caption metadata, keyed by city_id."""

    DEFAULT_PATH = "state/caption_history.json"

    def __init__(self, path: Optional[str] = None):
        self.path = path or self.DEFAULT_PATH
        self._cities: dict[str, list[CaptionHistoryEntry]] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            self._cities = {}
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw_cities = data.get("cities", {}) if isinstance(data, dict) else {}
            self._cities = {
                city_id: [CaptionHistoryEntry.from_dict(e) for e in entries]
                for city_id, entries in raw_cities.items()
                if isinstance(entries, list)
            }
        except (json.JSONDecodeError, IOError, TypeError) as e:
            print(f"⚠️  Could not load caption history from {self.path}: {e}")
            self._cities = {}

    def save(self) -> None:
        """Atomic save: write to temp file then rename."""
        path = Path(self.path)
        path.parent.mkdir(parents=True, exist_ok=True)

        serializable = {
            "cities": {
                city_id: [asdict(e) for e in entries]
                for city_id, entries in self._cities.items()
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            suffix=".tmp",
            delete=False,
        ) as tmp:
            json.dump(serializable, tmp, indent=2, ensure_ascii=False)
            tmp_name = tmp.name

        os.replace(tmp_name, self.path)

    def get_recent(self, city_id: str, n: int = MAX_ENTRIES_PER_CITY) -> list[CaptionHistoryEntry]:
        """Return the most-recent-first list of up to N entries for a city."""
        entries = self._cities.get(city_id, [])
        # Stored newest-first; just slice.
        return entries[:n]

    def get_recent_angles(self, city_id: str, n: int = 5) -> list[str]:
        """Return just the primary-angle strings for the last N entries, newest first."""
        return [e.angle for e in self.get_recent(city_id, n)]

    def add_entry(
        self,
        city_id: str,
        angle: str,
        literary_form: str,
        narrator: str,
        tone: str,
        first_three_words: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Prepend a new entry for the city; trim to MAX_ENTRIES_PER_CITY."""
        ts = timestamp or datetime.now(timezone.utc)
        entry = CaptionHistoryEntry(
            timestamp=ts.isoformat(),
            angle=angle,
            literary_form=literary_form,
            narrator=narrator,
            tone=tone,
            first_three_words=first_three_words,
        )
        existing = self._cities.get(city_id, [])
        self._cities[city_id] = ([entry] + existing)[:MAX_ENTRIES_PER_CITY]
