#!/usr/bin/env python3
"""Preview a single-city Twitter caption generation with full prompt + response output.

Usage:
    python preview_caption.py <city_id>

Does not post. Calls Gemini once for Twitter. Prints:
  - Fetched weather + forecast summary
  - Chosen notability angle and scored signals
  - Rotation parameters drawn for this call
  - Full system prompt
  - Full user prompt
  - Raw Gemini response
  - Validation result (and retry attempt, if triggered)
"""

import argparse
import sys
from typing import Optional

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

from dotenv import load_dotenv
from google.genai import types

from src.config import get_config
from src.weather import get_weather_for_city
from src.notability import score_notability
from src.caption_memory import CaptionMemory
from src.caption_prompts import build_system_prompt, build_user_prompt, roll_parameters
from src.caption_generator import CaptionGenerator


RULE = "=" * 72
SUB = "-" * 72


def _section(title: str, char: str = "=") -> None:
    print()
    print(char * 72)
    print(f"  {title}")
    print(char * 72)


def _one_attempt(gen: CaptionGenerator, system_prompt: str, user_prompt: str, weather, label: str) -> tuple[str | None, Optional[str], str]:
    """Make one Gemini call, print raw response + diagnosis.

    Returns (cleaned_caption_or_none, slip_code_or_none, slip_detail).
    slip_code is None when the caption is clean; 'hard_failure' when empty/error.
    """
    _section(f"CALLING GEMINI — {label} (model={CaptionGenerator.MODEL})")
    print(f"  max_output_tokens: {gen.MAX_OUTPUT_TOKENS}")
    print(f"  thinking_budget:   {gen.THINKING_BUDGET}")
    print(f"  temperature:       {gen.TEMPERATURE}")
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=gen.MAX_OUTPUT_TOKENS,
        temperature=gen.TEMPERATURE,
        thinking_config=types.ThinkingConfig(thinking_budget=gen.THINKING_BUDGET),
        http_options=types.HttpOptions(timeout=gen.TIMEOUT_MS),
    )
    try:
        response = gen.client.models.generate_content(
            model=gen.MODEL,
            contents=user_prompt,
            config=config,
        )
    except Exception as e:
        print(f"Gemini call failed: {e}")
        return None, "hard_failure", str(e)

    # Diagnostics: finish_reason + token usage
    print("\n--- RESPONSE METADATA ---")
    try:
        cand = (response.candidates or [None])[0]
        if cand is not None:
            print(f"  finish_reason: {getattr(cand, 'finish_reason', None)}")
            sr = getattr(cand, "safety_ratings", None)
            if sr:
                print(f"  safety_ratings: {sr}")
        usage = getattr(response, "usage_metadata", None)
        if usage:
            print(f"  prompt_token_count:     {getattr(usage, 'prompt_token_count', None)}")
            print(f"  thoughts_token_count:   {getattr(usage, 'thoughts_token_count', None)}")
            print(f"  candidates_token_count: {getattr(usage, 'candidates_token_count', None)}")
            print(f"  total_token_count:      {getattr(usage, 'total_token_count', None)}")
    except Exception as e:
        print(f"  (could not read metadata: {e})")

    raw = gen._extract_text(response)
    cleaned = raw.strip().strip('"').strip("'").strip() if raw else ""

    print(f"\n--- RAW RESPONSE (repr, {len(raw)} chars) ---")
    print(repr(raw))
    print(f"\n--- CLEANED CAPTION ({len(cleaned)} chars) ---")
    print(cleaned if cleaned else "<empty>")

    if not cleaned:
        return None, "hard_failure", "empty response"

    slip, detail = gen._diagnose(cleaned, weather)
    print(f"\n--- DIAGNOSIS ---")
    if slip is None:
        print("clean — no slip detected")
    else:
        print(f"slip:   {slip}")
        print(f"detail: {detail}")
        print("(Under the sensor model this caption would STILL be posted; the slip is recorded only.)")
    return cleaned, slip, detail


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Preview a Twitter caption for one city.")
    parser.add_argument("city_id", help="City ID from cities.yaml")
    args = parser.parse_args()

    config = get_config()
    city = config.get_city(args.city_id)
    if not city:
        print(f"Unknown city: {args.city_id}")
        ids = list(config.cities.keys())
        print(f"Available ({len(ids)}): {', '.join(ids[:15])}{'...' if len(ids) > 15 else ''}")
        return 1

    _section(f"PREVIEW: {city.name}, {city.country}")

    print(f"Fetching weather + forecast for {city.name}...")
    weather = get_weather_for_city(city)
    if not weather:
        print("Weather fetch failed.")
        return 1

    _section("WEATHER SNAPSHOT", char="-")
    print(f"  description:   {weather.description}")
    print(f"  main_cond:     {weather.main_condition}")
    print(f"  temp_c:        {weather.temperature_c:.1f}")
    print(f"  feels_like_c:  {weather.feels_like_c:.1f}")
    print(f"  humidity:      {weather.humidity}%")
    print(f"  wind_ms:       {weather.wind_speed}")
    print(f"  clouds_%:      {weather.clouds_percent}")
    print(f"  is_daytime:    {weather.is_daytime}")
    print(f"  time_of_day:   {weather.time_of_day}")
    print(f"  forecast:      {len(weather.forecast_entries)} entries")
    print(f"  precip_6h:     {weather.precipitation_next_6h} mm")
    print(f"  temp_trend:    {weather.temp_trend_6h}")
    print(f"  max_24h:       {weather.max_temp_24h}")
    print(f"  min_24h:       {weather.min_temp_24h}")

    memory = CaptionMemory()
    recent_angles = memory.get_recent_angles(city.id, n=5)
    notability = score_notability(weather, recent_angles=recent_angles)

    _section("NOTABILITY (Layer 1)", char="-")
    print(f"  primary_angle:      {notability.primary_angle}")
    print(f"  supporting_signals: {notability.supporting_signals}")
    print(f"  recent_angles:      {recent_angles}")
    print(f"  top scored signals (up to 8):")
    for s in notability.all_scored[:8]:
        print(f"    - {s.category:<24} score={s.score}  data={s.data}")

    params = roll_parameters()
    _section("ROTATION PARAMETERS", char="-")
    for k, v in params.items():
        print(f"  {k:<16} {v}")

    character = getattr(city, "character", "") or None
    recent_history = memory.get_recent(city.id, n=10)

    system_prompt = build_system_prompt("twitter")
    user_prompt = build_user_prompt(
        notability=notability,
        params=params,
        recent_history=recent_history,
        character=character,
    )

    _section(f"FULL SYSTEM PROMPT ({len(system_prompt)} chars)")
    print(system_prompt)

    _section(f"FULL USER PROMPT ({len(user_prompt)} chars)")
    print(user_prompt)

    gen = CaptionGenerator()

    caption, slip, detail = _one_attempt(gen, system_prompt, user_prompt, weather, "single call")

    _section("FINAL RESULT")
    if caption is None:
        print("Hard failure — a period-voice fallback would be posted:")
        from src.caption_prompts import build_period_fallback
        fb = build_period_fallback(
            city_name=city.name,
            temperature_c=weather.temperature_c,
            main_condition=weather.main_condition,
            description=weather.description,
        )
        print(f"\n{fb}")
    elif slip is None:
        print("POST — clean AI caption:")
        print(f"\n{caption}")
    else:
        print(f"POST — AI caption with recorded slip ({slip}):")
        print(f"\n{caption}")
        print(f"\n(Glitch log would receive: slip={slip}, detail={detail!r})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
