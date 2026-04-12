"""Append-only JSONL log of caption validation slips — a learning signal.

When a caption slips past a style rule (cliché, missing temperature,
missing condition), we record the slip and still post the caption. The log
accumulates over time and is read back periodically to inform prompt tuning.

Storage: ``state/caption_glitches.jsonl`` — one JSON object per line,
append-only. Entries older than the retention window are pruned on the next
write. Intended to ride alongside ``state/recently_posted.json`` in the
GitHub Actions cron-commit pattern.
"""

import json
import os
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


RETENTION_DAYS = 60


@dataclass
class GlitchEntry:
    """One recorded slip."""
    ts: str                 # ISO 8601 timestamp
    city: str               # city id
    platform: str           # twitter / instagram / tiktok
    caption: str            # the caption that slipped (what actually got posted)
    slip: str               # slip-reason code: "cliche" | "missing_temp" | "missing_condition" | "hard_failure"
    detail: str = ""        # optional detail (e.g., the banned phrase matched)
    length: int = 0
    angle: str = ""
    main_condition: str = ""
    temp_c: float = 0.0
    params: dict = field(default_factory=dict)


class GlitchLog:
    """JSONL-backed log of caption slips."""

    DEFAULT_PATH = "state/caption_glitches.jsonl"

    def __init__(self, path: Optional[str] = None, retention_days: int = RETENTION_DAYS):
        self.path = path or self.DEFAULT_PATH
        self.retention_days = retention_days

    # ── reads ──────────────────────────────────────────────────────────

    def read_all(self) -> list[GlitchEntry]:
        """Return every entry currently on disk (oldest first)."""
        if not os.path.exists(self.path):
            return []
        entries: list[GlitchEntry] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    entries.append(GlitchEntry(
                        ts=d.get("ts", ""),
                        city=d.get("city", ""),
                        platform=d.get("platform", ""),
                        caption=d.get("caption", ""),
                        slip=d.get("slip", ""),
                        detail=d.get("detail", ""),
                        length=int(d.get("length", 0)),
                        angle=d.get("angle", ""),
                        main_condition=d.get("main_condition", ""),
                        temp_c=float(d.get("temp_c", 0.0)),
                        params=d.get("params", {}) or {},
                    ))
                except (json.JSONDecodeError, ValueError, TypeError):
                    # Skip malformed lines; do not crash the run
                    continue
        return entries

    # ── writes ─────────────────────────────────────────────────────────

    def record(
        self,
        *,
        city: str,
        platform: str,
        caption: str,
        slip: str,
        detail: str = "",
        angle: str = "",
        main_condition: str = "",
        temp_c: float = 0.0,
        params: Optional[dict] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Append a slip entry. Prunes stale entries first."""
        ts = timestamp or datetime.now(timezone.utc)
        entry = GlitchEntry(
            ts=ts.isoformat(),
            city=city,
            platform=platform,
            caption=caption,
            slip=slip,
            detail=detail,
            length=len(caption),
            angle=angle,
            main_condition=main_condition,
            temp_c=round(float(temp_c), 1),
            params=params or {},
        )

        # Prune + write in a single atomic rewrite whenever stale entries exist;
        # otherwise just append. This keeps the common case cheap (single-line
        # append) and the uncommon case correct (full rewrite after prune).
        if self._has_stale_entries():
            self._rewrite_with_prune(appending=entry)
        else:
            self._append_raw(entry)

    # ── internals ──────────────────────────────────────────────────────

    def _has_stale_entries(self) -> bool:
        if not os.path.exists(self.path):
            return False
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        # Cheap peek: only read the first line; if it's stale, full prune.
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                first = f.readline().strip()
            if not first:
                return False
            d = json.loads(first)
            first_ts = datetime.fromisoformat(d.get("ts", ""))
            return first_ts < cutoff
        except (json.JSONDecodeError, ValueError, OSError):
            return False

    def _append_raw(self, entry: GlitchEntry) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    def _rewrite_with_prune(self, appending: Optional[GlitchEntry] = None) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        existing = self.read_all()
        kept: list[GlitchEntry] = []
        for e in existing:
            try:
                if datetime.fromisoformat(e.ts) >= cutoff:
                    kept.append(e)
            except ValueError:
                # Keep malformed-timestamp entries out
                continue
        if appending is not None:
            kept.append(appending)

        path = Path(self.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            suffix=".tmp",
            delete=False,
        ) as tmp:
            for e in kept:
                tmp.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")
            tmp_name = tmp.name
        os.replace(tmp_name, self.path)
