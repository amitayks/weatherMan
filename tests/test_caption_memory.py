"""Tests for CaptionMemory: load, save, trim, and missing-file handling."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.caption_memory import CaptionMemory, MAX_ENTRIES_PER_CITY


def test_missing_file_returns_empty(tmp_path):
    path = tmp_path / "caption_history.json"
    mem = CaptionMemory(path=str(path))
    assert mem.get_recent("somecity") == []
    assert mem.get_recent_angles("somecity") == []


def test_add_and_get_recent(tmp_path):
    path = tmp_path / "caption_history.json"
    mem = CaptionMemory(path=str(path))
    mem.add_entry(
        city_id="paris",
        angle="rain_coming",
        literary_form="prose_vignette",
        narrator="the_sky",
        tone="wistful",
        first_three_words="A low fog",
    )
    recent = mem.get_recent("paris")
    assert len(recent) == 1
    assert recent[0].angle == "rain_coming"
    assert recent[0].first_three_words == "A low fog"


def test_add_entry_prepends_newest_first(tmp_path):
    path = tmp_path / "caption_history.json"
    mem = CaptionMemory(path=str(path))
    mem.add_entry("paris", "angle_a", "form", "narrator", "tone", "first one")
    mem.add_entry("paris", "angle_b", "form", "narrator", "tone", "second one")
    mem.add_entry("paris", "angle_c", "form", "narrator", "tone", "third one")
    angles = mem.get_recent_angles("paris")
    assert angles == ["angle_c", "angle_b", "angle_a"]


def test_trim_to_max_entries(tmp_path):
    path = tmp_path / "caption_history.json"
    mem = CaptionMemory(path=str(path))
    for i in range(MAX_ENTRIES_PER_CITY + 5):
        mem.add_entry("city1", f"angle_{i}", "form", "narrator", "tone", f"opener_{i}")
    recent = mem.get_recent("city1")
    assert len(recent) == MAX_ENTRIES_PER_CITY
    # Newest should be the last one added
    assert recent[0].angle == f"angle_{MAX_ENTRIES_PER_CITY + 4}"


def test_save_and_reload_preserves_data(tmp_path):
    path = tmp_path / "caption_history.json"
    mem = CaptionMemory(path=str(path))
    mem.add_entry("rome", "stormy", "aphorism", "the_city_itself", "reverent", "The sky has")
    mem.save()

    # Reload
    mem2 = CaptionMemory(path=str(path))
    recent = mem2.get_recent("rome")
    assert len(recent) == 1
    assert recent[0].angle == "stormy"
    assert recent[0].narrator == "the_city_itself"


def test_save_creates_directory_if_missing(tmp_path):
    path = tmp_path / "nested" / "sub" / "caption_history.json"
    mem = CaptionMemory(path=str(path))
    mem.add_entry("a", "b", "c", "d", "e", "f")
    mem.save()
    assert path.exists()


def test_get_recent_angles_limit(tmp_path):
    path = tmp_path / "caption_history.json"
    mem = CaptionMemory(path=str(path))
    for i in range(7):
        mem.add_entry("c", f"a{i}", "f", "n", "t", "o")
    # n=5 → only 5 newest
    assert len(mem.get_recent_angles("c", n=5)) == 5


def test_atomic_save_no_temp_file_leftover(tmp_path):
    path = tmp_path / "caption_history.json"
    mem = CaptionMemory(path=str(path))
    mem.add_entry("c", "a", "f", "n", "t", "o")
    mem.save()
    # Only the target file should exist, no leftover .tmp files
    files = [p.name for p in tmp_path.iterdir()]
    assert "caption_history.json" in files
    assert not any(name.endswith(".tmp") for name in files)


def test_malformed_json_treated_as_empty(tmp_path):
    path = tmp_path / "caption_history.json"
    path.write_text("not valid json {", encoding="utf-8")
    mem = CaptionMemory(path=str(path))
    assert mem.get_recent("any") == []
