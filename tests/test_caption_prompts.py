"""Tests for the caption_prompts module: rotation, clichés, prompt assembly."""

import random

from src.caption_prompts import (
    SEED_NOUNS,
    FORBIDDEN_CLICHES,
    LITERARY_FORMS,
    NARRATORS,
    TONES,
    SENSORY_DEVICES,
    build_system_prompt,
    roll_parameters,
)


def test_seed_nouns_has_at_least_200():
    assert len(SEED_NOUNS) >= 200


def test_forbidden_cliches_at_least_10():
    assert len(FORBIDDEN_CLICHES) >= 10


def test_forbidden_cliches_lowercased():
    for c in FORBIDDEN_CLICHES:
        assert c == c.lower(), f"Cliché not lowercased: {c!r}"


def test_rotation_taxonomies_nonempty():
    assert LITERARY_FORMS
    assert NARRATORS
    assert TONES
    assert SENSORY_DEVICES


def test_roll_parameters_returns_all_dimensions():
    params = roll_parameters(rng=random.Random(42))
    assert "literary_form" in params
    assert "narrator" in params
    assert "tone" in params
    assert "sensory_device" in params
    assert "seed_noun" in params


def test_roll_parameters_values_from_taxonomies():
    rng = random.Random(123)
    params = roll_parameters(rng=rng)
    assert params["literary_form"] in LITERARY_FORMS
    assert params["narrator"] in NARRATORS
    assert params["tone"] in TONES
    assert params["sensory_device"] in SENSORY_DEVICES
    assert params["seed_noun"] in SEED_NOUNS


def test_system_prompt_twitter_includes_cliches_and_platform():
    p = build_system_prompt("twitter")
    assert "Twitter" in p
    assert "260" in p
    # At least one cliché listed
    assert FORBIDDEN_CLICHES[0] in p


def test_system_prompt_instagram_instruction():
    p = build_system_prompt("instagram")
    assert "Instagram" in p
    assert "100" in p
    assert "260" in p


def test_system_prompt_tiktok_instruction():
    p = build_system_prompt("tiktok")
    assert "TikTok" in p
    assert "80" in p
    assert "180" in p


def test_system_prompt_unknown_platform_raises():
    import pytest
    with pytest.raises(ValueError):
        build_system_prompt("myspace")
