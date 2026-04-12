## ADDED Requirements

### Requirement: Signal extraction from weather data

The system SHALL extract a fixed set of categorical "signals" from the combined current-weather and 24-hour-forecast data for a city.

#### Scenario: Signals always extracted
- **WHEN** a `WeatherData` object with forecast entries is provided
- **THEN** the notability scorer produces a list of signals, each with category label and raw data references

#### Scenario: Signal taxonomy covers 20 categories
- **WHEN** signals are extracted
- **THEN** the scorer considers at least the following 20 signal categories:
  - `extreme_heat` (temp ≥ 32°C)
  - `extreme_cold` (temp ≤ 0°C)
  - `heatwave` (temp ≥ 28°C AND feels_like ≥ 30°C)
  - `cold_snap` (temp ≤ 5°C in a typically-warm city)
  - `sticky_heat` (temp ≥ 24°C AND humidity ≥ 75%)
  - `dry_crisp` (humidity ≤ 35% AND temp between 10-25°C)
  - `rain_now_clearing` (currently raining AND forecast ≤ 6h shows clear)
  - `rain_coming` (currently dry AND forecast ≤ 6h shows rain)
  - `extended_rain` (rain now AND rain continues ≥ 12h in forecast)
  - `heavy_rain` (rain volume in last 1h ≥ 4mm OR forecast 3h ≥ 10mm)
  - `stormy` (main_condition == Thunderstorm)
  - `fog_mist` (main_condition in {Fog, Mist, Haze} AND visibility low if available)
  - `first_snow_season` (snow now AND inferred no snow in last N days — best-effort)
  - `snow_falling` (main_condition == Snow)
  - `gusty_wind` (wind_speed ≥ 10 m/s)
  - `overcast_calm` (clouds_percent ≥ 85% AND wind_speed ≤ 3 m/s)
  - `perfect_day` (temp 18-26°C AND clouds ≤ 30% AND wind ≤ 5 m/s AND no precipitation)
  - `golden_hour_now` (current time within 1h of sunset AND clear-ish)
  - `frost_risk_tonight` (forecast low within 24h ≤ 2°C)
  - `temp_swing` (forecast shows ≥ 10°C variation within 24h)

### Requirement: Signal scoring

Each extracted signal SHALL be assigned a notability score from 0 to 10 using a deterministic rule set.

#### Scenario: Extreme signals score high
- **WHEN** a signal is in {extreme_heat, extreme_cold, heatwave, first_snow_season, stormy}
- **THEN** its base score is at least 8

#### Scenario: Change signals score medium-high
- **WHEN** a signal is in {rain_now_clearing, rain_coming, temp_swing, frost_risk_tonight}
- **THEN** its base score is at least 6

#### Scenario: Sensory-quality signals score medium
- **WHEN** a signal is in {sticky_heat, dry_crisp, overcast_calm, fog_mist, gusty_wind, golden_hour_now}
- **THEN** its base score is between 4 and 6

#### Scenario: Expected / baseline signals score low
- **WHEN** a signal describes conditions typical for the city (flagged via optional city baseline) or simply current cloud/condition state with no change
- **THEN** its score is no higher than 3

### Requirement: Angle selection

The scorer SHALL select exactly one primary angle and up to two supporting signals for each caption generation request.

#### Scenario: Primary angle is highest scorer
- **WHEN** signals have been scored
- **THEN** the signal with the highest score becomes the `primary_angle`
- **AND** if multiple signals tie for highest, selection is deterministic by a fixed priority order within the tied set

#### Scenario: Supporting signals picked from remaining
- **WHEN** a primary angle is chosen
- **THEN** up to 2 next-highest-scoring signals are returned as `supporting_signals`
- **AND** supporting signals must score at least 3

#### Scenario: Low-interest fallback angle
- **WHEN** no signal scores above 3
- **THEN** the scorer emits the sentinel angle `unremarkable_day` with supporting signals describing the mundane state (temp + condition)

### Requirement: Recent-angles deprioritization

The scorer SHALL accept a list of recently used angles and reduce scores for signals matching recent angles.

#### Scenario: Recent angle penalty
- **WHEN** a signal's category appears in the `recent_angles` list (last 5 uses for this city)
- **THEN** that signal's score is reduced by 3 (minimum 0)

#### Scenario: Very recent angle strong penalty
- **WHEN** a signal's category appears as the most recent post's angle
- **THEN** that signal's score is reduced by 5 instead of 3

### Requirement: Deterministic and side-effect-free

The notability scorer SHALL be a pure function: same inputs produce same outputs, no network calls, no randomness.

#### Scenario: Scorer is testable
- **WHEN** the scorer is called twice with the same `(WeatherData, recent_angles)` inputs
- **THEN** it returns identical output (including identical supporting-signal ordering)

### Requirement: Scorer output contract

The scorer SHALL return a structured object consumable by the caption generator.

#### Scenario: Output shape
- **WHEN** the scorer completes
- **THEN** it returns an object containing:
  - `primary_angle: str` (category label from the taxonomy, or `unremarkable_day`)
  - `supporting_signals: list[str]` (0-2 category labels)
  - `all_scored: list[{category, score, data}]` (for logging/debugging)
  - `weather_summary: dict` (structured facts: temp, feels_like, humidity, condition, wind, clouds, precipitation_next_6h, temp_trend_6h)
