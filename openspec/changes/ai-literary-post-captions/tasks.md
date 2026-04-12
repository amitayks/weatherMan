## 1. Forecast fetching

- [x] 1.1 Add `ForecastEntry` dataclass to `src/weather.py` with fields: timestamp, temperature_c, feels_like_c, humidity, main_condition, description, clouds_percent, wind_speed, precipitation_mm
- [x] 1.2 Extend `WeatherData` dataclass with `forecast_entries: list[ForecastEntry] = []`
- [x] 1.3 Add `precipitation_next_6h`, `temp_trend_6h`, `next_condition_change`, `max_temp_24h`, `min_temp_24h` as computed properties on `WeatherData`
- [x] 1.4 Add `WeatherAPI.get_forecast(city)` that calls the `/forecast` endpoint with `cnt=8`, 10s timeout
- [x] 1.5 Handle missing `rain`/`snow` keys by defaulting `precipitation_mm` to 0
- [x] 1.6 Handle missing optional fields (clouds, wind) with safe defaults
- [x] 1.7 Modify `get_weather_for_city` to fetch forecast alongside current weather; on forecast failure, log and return with empty forecast_entries
- [x] 1.8 Verify empty-forecast path returns safe defaults from the derived properties

## 2. Notability scorer

- [x] 2.1 Create `src/notability.py` with `NotabilityResult` dataclass (primary_angle, supporting_signals, all_scored, weather_summary)
- [x] 2.2 Define the 20-category signal taxonomy as a list of named constants
- [x] 2.3 Implement signal-extraction rules for each of the 20 categories using thresholds from the spec
- [x] 2.4 Implement base scoring: extreme/stormy/first_snow → 8+, change signals → 6+, sensory → 4-6, expected → ≤3
- [x] 2.5 Implement the `unremarkable_day` fallback when no signal scores above 3
- [x] 2.6 Implement recent-angle penalty: -5 if most recent, -3 if in last 5
- [x] 2.7 Implement deterministic tie-breaking with a fixed priority list within tied scores
- [x] 2.8 Implement primary-angle + up-to-2-supporting selection, supporting must score ≥3
- [x] 2.9 Ensure scorer is pure (no random, no network, no time.now beyond what's in WeatherData)
- [x] 2.10 Build `weather_summary` dict output with structured facts for downstream prompt use

## 3. Caption memory

- [x] 3.1 Create `src/caption_memory.py` with `CaptionHistoryEntry` dataclass and `CaptionMemory` class
- [x] 3.2 Implement load/save from `state/caption_history.json` (create directory on save if missing)
- [x] 3.3 Implement `get_recent(city_id, n=10)` returning last N entries
- [x] 3.4 Implement `add_entry(city_id, angle, literary_form, narrator, tone, first_three_words, timestamp)`; trim city list to last 10
- [x] 3.5 Implement `get_recent_angles(city_id, n=5)` returning just the angle strings, newest first
- [x] 3.6 Handle missing file gracefully (fresh memory)
- [x] 3.7 Atomic save (write to temp file then rename) to avoid partial-write corruption

## 4. Caption prompts module

- [x] 4.1 Create `src/caption_prompts.py`
- [x] 4.2 Define the `SEED_NOUNS` list (minimum 200 concrete nouns, hand-curated)
- [x] 4.3 Define rotation taxonomies: `LITERARY_FORMS`, `NARRATORS`, `TONES`, `SENSORY_DEVICES` (matching spec values)
- [x] 4.4 Define `FORBIDDEN_CLICHES` list with at least 10 entries, each as a lowercased substring to match
- [x] 4.5 Write the platform-agnostic system-prompt base (role, style guide, banned-cliché list, output-format rule)
- [x] 4.6 Write platform-specific system prompt suffixes (Twitter 260 chars, Instagram 300-800, TikTok 80-180)
- [x] 4.7 Write at least 6 few-shot examples with one-line "why this works" annotations; examples span: sunny, rainy, cold, humid, foggy, perfect-day
- [x] 4.8 Implement `build_system_prompt(platform)` returning assembled string
- [x] 4.9 Implement `build_user_prompt(notability_result, params, recent_history)` composing the per-call message with weather summary, chosen angle, rotated params, recent-history context
- [x] 4.10 Implement `roll_parameters()` returning a dict with one random selection from each rotation dimension

## 5. Caption generator orchestration

- [x] 5.1 Create `src/caption_generator.py` with `CaptionGenerator` class
- [x] 5.2 Wire `google-genai` client reuse from existing image generator setup (same API key)
- [x] 5.3 Implement `generate(city, weather, platform, memory)` orchestrating: notability scoring → param roll → prompt assembly → Gemini call → validation → retry → fallback
- [x] 5.4 Call Gemini with model `gemini-2.5-pro`, `max_output_tokens=400`, `timeout=30s`
- [x] 5.5 Implement caption validation: length range per platform, forbidden-cliché scan (case-insensitive), weather-fact presence (temp + condition)
- [x] 5.6 On validation failure, retry exactly once with a correction hint appended to the user prompt
- [x] 5.7 On second failure, exception, or timeout, return the template fallback caption
- [x] 5.8 After successful generation, record entry in `CaptionMemory`
- [x] 5.9 Implement `_build_fallback(city, weather, platform)` producing the minimal template (name + temp + condition + date, no hashtags)
- [x] 5.10 Log full prompt + response at DEBUG level to a dedicated logger

## 6. Platform integration

- [x] 6.1 In `src/platforms/twitter.py`, replace `build_tweet_text` with a call to the caption generator for the Twitter platform; remove template body
- [x] 6.2 In `src/platforms/instagram.py`, replace the body of `build_caption` so the AI-generated text is the body; append the existing hashtag block after two blank lines
- [x] 6.3 In `src/platforms/tiktok.py`, replace `build_description` body similarly; append existing hashtag block
- [x] 6.4 Thread a single shared `CaptionGenerator` and `CaptionMemory` instance through `process_city` in `src/main.py` so all platforms share state within one post
- [x] 6.5 Ensure memory is saved once per city after all 3 platform captions are generated (not 3 times)

## 7. Config and state

- [x] 7.1 Add optional `character` field to `CityConfig` in `src/config.py` (string, default `""`)
- [x] 7.2 Pass `character` through to the user prompt when non-empty
- [x] 7.3 Ensure `state/` directory is created on first run if missing
- [x] 7.4 Confirm `.gitignore` covers `state/caption_history.json` or confirm whether history should be committed (follow existing `state/` convention) — follows `state/recently_posted.json` convention: committed, not ignored

## 8. Tests

- [x] 8.1 Unit tests for notability scorer: one test per signal category with a synthetic WeatherData producing that angle as primary
- [x] 8.2 Unit tests for recent-angles penalty: verify -3 and -5 reductions
- [x] 8.3 Unit tests for unremarkable_day fallback
- [x] 8.4 Unit tests for WeatherData derived properties with non-empty and empty forecasts
- [x] 8.5 Unit tests for CaptionMemory load/save/trim/missing-file
- [x] 8.6 Unit tests for caption validation: length over limit, cliché present, temp missing, condition missing
- [x] 8.7 Unit tests for parameter rotation: each dimension returns one value from its list
- [x] 8.8 Mock-Gemini integration tests for caption generator: happy path, validation-fail-then-retry, both-fail-then-fallback, timeout → fallback
- [x] 8.9 Test that caption history records an entry on success and does not on fallback

## 9. Dry-run review

- [ ] 9.1 Run `python -m src.main --dry-run --city <id>` across at least 20 varied cities (different weather types)
- [ ] 9.2 Manually review each generated caption against the style guide; record which captions feel weak
- [ ] 9.3 Tune: add new clichés to the banned list based on observed output; adjust few-shot examples; adjust validation thresholds if over-trimming
- [ ] 9.4 Re-run after tuning; confirm subjective quality bar is met before live rollout

## 10. Live rollout

- [ ] 10.1 Merge to main and monitor first scheduled run (~5 hours after merge)
- [ ] 10.2 Inspect generated captions on each of the 3 platforms; verify lengths, hashtag placement, no template fallback unless expected
- [ ] 10.3 Review Gemini DEBUG logs for any validation retries or fallbacks
- [ ] 10.4 Monitor monthly Gemini spend after 1 week; confirm ≤ $5 projected

## 11. Sensor-model refactor (post-design-pivot)

- [x] 11.1 Create `src/glitch_log.py` with `GlitchLog` class (JSONL append, 60-day prune, atomic rewrite on prune)
- [x] 11.2 Drop retry loop from `CaptionGenerator.generate` — make exactly one Gemini call per caption
- [x] 11.3 Delete `_build_correction_hint` and the `correction_hint` parameter from `build_user_prompt`
- [x] 11.4 Rename `_validate` → `_diagnose`; return `(slip_code, detail)` instead of `(ok, reason)`
- [x] 11.5 Remove length checks from diagnosis (user's verified accounts accept long posts; voice takes precedence over trim)
- [x] 11.6 Restrict period-voice fallback to hard failures only (empty response / exception); style slips post through
- [x] 11.7 Record every style slip to the glitch log (city, platform, caption, slip code, detail, angle, params, main_condition, temp_c)
- [x] 11.8 Skip `CaptionMemory.add_entry` on hard-failure fallback (don't pollute anti-repetition with templates)
- [x] 11.9 Wire `GlitchLog` instance through `process_city` in `src/main.py`
- [x] 11.10 Update `preview_caption.py` to reflect the sensor-model flow (show slip diagnosis instead of retry)
- [x] 11.11 Rewrite `tests/test_caption_generator.py` for sensor invariants (one call, style-slip posts and logs, hard failure falls back)
- [x] 11.12 Add `tests/test_glitch_log.py` covering append, read, prune, malformed-line tolerance, custom retention
- [x] 11.13 Update `specs/caption-generation/spec.md` — replace retry/validation/fallback requirements with sensor-model requirements + glitch-log retention spec
- [x] 11.14 Update `design.md` D8 — document the pivot from retry to sensor, including dropped length validation
