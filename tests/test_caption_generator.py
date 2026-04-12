"""Tests for CaptionGenerator under the sensor model.

Sensor model invariants:
  • Exactly one Gemini call per generate() invocation (no retries).
  • Style slips (cliché / missing_temp / missing_condition) → caption is
    returned AS-IS and the slip is recorded in the glitch log.
  • Hard failures (empty Gemini response, exception) → period-voice fallback.
"""

from typing import Optional
from unittest.mock import MagicMock

import pytest

from src.caption_generator import CaptionGenerator
from src.caption_memory import CaptionMemory
from src.config import CityConfig, Coordinates, PlatformConfig
from src.glitch_log import GlitchLog
from tests.conftest import make_weather


def _make_city(city_id="testville"):
    return CityConfig(
        id=city_id,
        name="Testville",
        country="Testland",
        timezone="UTC",
        coordinates=Coordinates(lat=0.0, lon=0.0),
        platforms=PlatformConfig(twitter=True, instagram=True, tiktok=True),
        landmarks=["a bench"],
    )


class _FakeResponse:
    def __init__(self, text: Optional[str]):
        self.text = text
        self.candidates = []


@pytest.fixture
def gen(monkeypatch):
    """CaptionGenerator with a mock google-genai client attached."""
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "fake-key")
    g = CaptionGenerator.__new__(CaptionGenerator)
    g.api_key = "fake-key"
    g.client = MagicMock()
    return g


# ─── _diagnose ─────────────────────────────────────────────────────────

def test_diagnose_clean_caption(gen):
    w = make_weather(temperature_c=25, description="light rain", main_condition="Rain")
    caption = (
        "Twenty-five degrees in Testville, and a light rain tapping the "
        "rooftops as the evening slowly settles."
    )
    slip, detail = gen._diagnose(caption, w)
    assert slip is None
    assert detail == ""


def test_diagnose_cliche(gen):
    w = make_weather(temperature_c=25, description="light rain", main_condition="Rain")
    caption = (
        "It is twenty-five degrees in Testville, and Mother Nature shows "
        "her hand with a gentle rain falling."
    )
    slip, detail = gen._diagnose(caption, w)
    assert slip == "cliche"
    assert detail == "mother nature"


def test_diagnose_missing_temperature(gen):
    w = make_weather(temperature_c=25, description="light rain", main_condition="Rain")
    caption = "A gentle rain falls across the harbor of Testville."
    slip, detail = gen._diagnose(caption, w)
    assert slip == "missing_temp"


def test_diagnose_missing_condition(gen):
    w = make_weather(temperature_c=25, description="light rain", main_condition="Rain")
    caption = "Twenty-five degrees in Testville today, as one might expect."
    slip, detail = gen._diagnose(caption, w)
    assert slip == "missing_condition"


def test_diagnose_does_not_check_length(gen):
    """Length is intentionally not a slip — verified accounts accept long posts."""
    w = make_weather(temperature_c=25, description="light rain", main_condition="Rain")
    long_caption = "Twenty-five degrees in Testville, rain upon the roofs. " * 20  # >1000 chars
    slip, _ = gen._diagnose(long_caption, w)
    assert slip is None  # long is fine


# ─── generate() — happy paths ──────────────────────────────────────────

def test_generate_happy_path_records_memory_not_glitch(gen, tmp_path):
    city = _make_city()
    w = make_weather(temperature_c=25, description="light rain", main_condition="Rain")
    memory = CaptionMemory(path=str(tmp_path / "ch.json"))
    glog = GlitchLog(path=str(tmp_path / "gl.jsonl"))

    good = "Twenty-five degrees in Testville, a light rain tapping the tin."
    gen.client.models.generate_content.return_value = _FakeResponse(good)

    caption = gen.generate(city, w, "twitter", memory, glog)
    assert caption == good
    # Exactly one Gemini call — no retry
    assert gen.client.models.generate_content.call_count == 1
    # Memory recorded, glitch log empty
    assert len(memory.get_recent("testville")) == 1
    assert glog.read_all() == []


def test_generate_without_glitch_log_still_works(gen, tmp_path):
    city = _make_city()
    w = make_weather(temperature_c=25, description="light rain", main_condition="Rain")
    memory = CaptionMemory(path=str(tmp_path / "ch.json"))

    good = "Twenty-five degrees in Testville, a light rain tapping the tin."
    gen.client.models.generate_content.return_value = _FakeResponse(good)

    caption = gen.generate(city, w, "twitter", memory, glitch_log=None)
    assert caption == good


def test_generate_without_memory_still_works(gen, tmp_path):
    city = _make_city()
    w = make_weather(temperature_c=25, description="light rain", main_condition="Rain")

    good = "Twenty-five degrees in Testville, a light rain tapping the tin."
    gen.client.models.generate_content.return_value = _FakeResponse(good)

    caption = gen.generate(city, w, "twitter", memory=None, glitch_log=None)
    assert caption == good


# ─── generate() — style slip: POST + log ───────────────────────────────

def test_generate_cliche_slip_posts_and_logs(gen, tmp_path):
    """A cliché is logged but the caption is still returned for posting."""
    city = _make_city()
    w = make_weather(temperature_c=25, description="light rain", main_condition="Rain")
    memory = CaptionMemory(path=str(tmp_path / "ch.json"))
    glog = GlitchLog(path=str(tmp_path / "gl.jsonl"))

    slippy = (
        "Twenty-five degrees in Testville; Mother Nature has her rain out "
        "over the harbor this evening."
    )
    gen.client.models.generate_content.return_value = _FakeResponse(slippy)

    caption = gen.generate(city, w, "twitter", memory, glog)
    # Caption IS returned as-is
    assert caption == slippy
    # Exactly one call
    assert gen.client.models.generate_content.call_count == 1
    # Glitch logged
    entries = glog.read_all()
    assert len(entries) == 1
    assert entries[0].slip == "cliche"
    assert entries[0].detail == "mother nature"
    assert entries[0].city == "testville"
    assert entries[0].platform == "twitter"
    assert entries[0].caption == slippy


def test_generate_missing_temp_slip_posts_and_logs(gen, tmp_path):
    city = _make_city()
    w = make_weather(temperature_c=25, description="light rain", main_condition="Rain")
    glog = GlitchLog(path=str(tmp_path / "gl.jsonl"))

    slippy = "A gentle rain falls across the harbor of Testville this evening."
    gen.client.models.generate_content.return_value = _FakeResponse(slippy)

    caption = gen.generate(city, w, "twitter", memory=None, glitch_log=glog)
    assert caption == slippy
    entries = glog.read_all()
    assert len(entries) == 1
    assert entries[0].slip == "missing_temp"


# ─── generate() — hard failure: fallback ───────────────────────────────

def test_generate_empty_response_uses_period_fallback(gen, tmp_path):
    city = _make_city()
    w = make_weather(temperature_c=25, description="light rain", main_condition="Rain")
    glog = GlitchLog(path=str(tmp_path / "gl.jsonl"))

    gen.client.models.generate_content.return_value = _FakeResponse(None)

    caption = gen.generate(city, w, "twitter", memory=None, glitch_log=glog)
    # Exactly one Gemini call — no retry
    assert gen.client.models.generate_content.call_count == 1
    # Fallback contains the city name and temp
    assert "Testville" in caption
    assert "25" in caption
    # Fallback is period-voice, not emoji-template
    assert "🌧️" not in caption and "🌡️" not in caption
    # Hard failure recorded
    entries = glog.read_all()
    assert len(entries) == 1
    assert entries[0].slip == "hard_failure"


def test_generate_exception_uses_period_fallback(gen, tmp_path):
    city = _make_city()
    w = make_weather(temperature_c=25, description="light rain", main_condition="Rain")
    glog = GlitchLog(path=str(tmp_path / "gl.jsonl"))

    gen.client.models.generate_content.side_effect = RuntimeError("network timeout")

    caption = gen.generate(city, w, "twitter", memory=None, glitch_log=glog)
    # Exactly one call before fallback
    assert gen.client.models.generate_content.call_count == 1
    assert "Testville" in caption
    assert "25" in caption
    entries = glog.read_all()
    assert len(entries) == 1
    assert entries[0].slip == "hard_failure"


def test_generate_hard_failure_does_not_record_memory(gen, tmp_path):
    """On hard failure we use the fallback, which is not an AI output — don't
    pollute the anti-repetition memory with it."""
    city = _make_city()
    w = make_weather(temperature_c=25, description="light rain", main_condition="Rain")
    memory = CaptionMemory(path=str(tmp_path / "ch.json"))
    glog = GlitchLog(path=str(tmp_path / "gl.jsonl"))

    gen.client.models.generate_content.return_value = _FakeResponse(None)

    gen.generate(city, w, "twitter", memory, glog)
    assert memory.get_recent("testville") == []
