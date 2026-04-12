"""Tests for GlitchLog: append, read, prune, malformed-line tolerance."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from src.glitch_log import GlitchLog, RETENTION_DAYS


def test_missing_file_read_returns_empty(tmp_path):
    g = GlitchLog(path=str(tmp_path / "gl.jsonl"))
    assert g.read_all() == []


def test_record_creates_file_and_appends(tmp_path):
    path = tmp_path / "gl.jsonl"
    g = GlitchLog(path=str(path))
    g.record(
        city="bequia",
        platform="twitter",
        caption="a short caption",
        slip="cliche",
        detail="mother nature",
        angle="rain_coming",
        main_condition="Rain",
        temp_c=25.3,
        params={"tone": "dryly_ironic"},
    )
    assert path.exists()
    entries = g.read_all()
    assert len(entries) == 1
    e = entries[0]
    assert e.city == "bequia"
    assert e.platform == "twitter"
    assert e.slip == "cliche"
    assert e.detail == "mother nature"
    assert e.length == len("a short caption")
    assert e.temp_c == 25.3
    assert e.params == {"tone": "dryly_ironic"}


def test_multiple_records_append(tmp_path):
    g = GlitchLog(path=str(tmp_path / "gl.jsonl"))
    for i in range(5):
        g.record(
            city=f"city{i}",
            platform="twitter",
            caption=f"caption {i}",
            slip="cliche",
        )
    entries = g.read_all()
    assert len(entries) == 5
    assert [e.city for e in entries] == [f"city{i}" for i in range(5)]


def test_malformed_lines_are_skipped(tmp_path):
    path = tmp_path / "gl.jsonl"
    path.write_text(
        "not json\n"
        '{"ts": "2026-04-12T10:00:00+00:00", "city": "x", "platform": "twitter", "caption": "", "slip": "cliche"}\n'
        "also not json {\n",
        encoding="utf-8",
    )
    g = GlitchLog(path=str(path))
    entries = g.read_all()
    assert len(entries) == 1
    assert entries[0].city == "x"


def test_prune_drops_entries_older_than_retention(tmp_path):
    path = tmp_path / "gl.jsonl"
    stale_ts = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS + 5)).isoformat()
    fresh_ts = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

    # Seed a stale entry directly, then append fresh via record — which triggers prune.
    path.write_text(
        json.dumps({
            "ts": stale_ts, "city": "old", "platform": "twitter",
            "caption": "stale", "slip": "cliche",
        }) + "\n",
        encoding="utf-8",
    )
    # Also add a mid-age entry to verify selective pruning
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": fresh_ts, "city": "mid", "platform": "twitter",
            "caption": "mid", "slip": "cliche",
        }) + "\n")

    g = GlitchLog(path=str(path))
    g.record(
        city="new",
        platform="twitter",
        caption="new",
        slip="cliche",
    )

    cities = [e.city for e in g.read_all()]
    assert "old" not in cities  # pruned
    assert "mid" in cities
    assert "new" in cities


def test_prune_preserves_fresh_entries(tmp_path):
    """No pruning when all entries are within retention."""
    path = tmp_path / "gl.jsonl"
    g = GlitchLog(path=str(path))
    for i in range(3):
        g.record(city=f"city{i}", platform="twitter", caption=f"c{i}", slip="cliche")
    assert len(g.read_all()) == 3

    # Adding a new entry should still leave all 3 prior entries intact
    g.record(city="new", platform="twitter", caption="new", slip="cliche")
    assert len(g.read_all()) == 4


def test_custom_retention_window(tmp_path):
    path = tmp_path / "gl.jsonl"
    # Seed entry that is 10 days old
    ten_days_ago = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    path.write_text(
        json.dumps({
            "ts": ten_days_ago, "city": "old10d", "platform": "twitter",
            "caption": "c", "slip": "cliche",
        }) + "\n",
        encoding="utf-8",
    )

    # Use a 7-day retention window — the 10-day-old entry should prune
    g = GlitchLog(path=str(path), retention_days=7)
    g.record(city="new", platform="twitter", caption="new", slip="cliche")

    cities = [e.city for e in g.read_all()]
    assert "old10d" not in cities
    assert "new" in cities


def test_record_parents_directory_created(tmp_path):
    path = tmp_path / "nested" / "sub" / "gl.jsonl"
    g = GlitchLog(path=str(path))
    g.record(city="x", platform="twitter", caption="c", slip="cliche")
    assert path.exists()
