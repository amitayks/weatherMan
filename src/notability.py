"""Notability scoring — picks the most interesting weather angle for a post.

This is Layer 1 of the caption pipeline: a pure function that analyzes weather
data and outputs one primary "angle" plus supporting signals. No LLM, no
randomness, no network. Same inputs produce same outputs.
"""

from dataclasses import dataclass, field
from typing import Optional

from .weather import WeatherData


# Signal category labels
SIGNAL_EXTREME_HEAT = "extreme_heat"
SIGNAL_EXTREME_COLD = "extreme_cold"
SIGNAL_HEATWAVE = "heatwave"
SIGNAL_COLD_SNAP = "cold_snap"
SIGNAL_STICKY_HEAT = "sticky_heat"
SIGNAL_DRY_CRISP = "dry_crisp"
SIGNAL_RAIN_NOW_CLEARING = "rain_now_clearing"
SIGNAL_RAIN_COMING = "rain_coming"
SIGNAL_EXTENDED_RAIN = "extended_rain"
SIGNAL_HEAVY_RAIN = "heavy_rain"
SIGNAL_STORMY = "stormy"
SIGNAL_FOG_MIST = "fog_mist"
SIGNAL_FIRST_SNOW_SEASON = "first_snow_season"
SIGNAL_SNOW_FALLING = "snow_falling"
SIGNAL_GUSTY_WIND = "gusty_wind"
SIGNAL_OVERCAST_CALM = "overcast_calm"
SIGNAL_PERFECT_DAY = "perfect_day"
SIGNAL_GOLDEN_HOUR_NOW = "golden_hour_now"
SIGNAL_FROST_RISK_TONIGHT = "frost_risk_tonight"
SIGNAL_TEMP_SWING = "temp_swing"
UNREMARKABLE_DAY = "unremarkable_day"

ALL_SIGNAL_CATEGORIES = [
    SIGNAL_EXTREME_HEAT, SIGNAL_EXTREME_COLD, SIGNAL_HEATWAVE, SIGNAL_COLD_SNAP,
    SIGNAL_STICKY_HEAT, SIGNAL_DRY_CRISP,
    SIGNAL_RAIN_NOW_CLEARING, SIGNAL_RAIN_COMING, SIGNAL_EXTENDED_RAIN,
    SIGNAL_HEAVY_RAIN, SIGNAL_STORMY, SIGNAL_FOG_MIST,
    SIGNAL_FIRST_SNOW_SEASON, SIGNAL_SNOW_FALLING,
    SIGNAL_GUSTY_WIND, SIGNAL_OVERCAST_CALM,
    SIGNAL_PERFECT_DAY, SIGNAL_GOLDEN_HOUR_NOW,
    SIGNAL_FROST_RISK_TONIGHT, SIGNAL_TEMP_SWING,
]

# Tie-break order: earlier entries win on equal scores.
PRIORITY_ORDER = [
    SIGNAL_STORMY,
    SIGNAL_FIRST_SNOW_SEASON,
    SIGNAL_EXTREME_HEAT,
    SIGNAL_EXTREME_COLD,
    SIGNAL_HEATWAVE,
    SIGNAL_COLD_SNAP,
    SIGNAL_HEAVY_RAIN,
    SIGNAL_SNOW_FALLING,
    SIGNAL_RAIN_NOW_CLEARING,
    SIGNAL_RAIN_COMING,
    SIGNAL_EXTENDED_RAIN,
    SIGNAL_TEMP_SWING,
    SIGNAL_FROST_RISK_TONIGHT,
    SIGNAL_GUSTY_WIND,
    SIGNAL_STICKY_HEAT,
    SIGNAL_FOG_MIST,
    SIGNAL_DRY_CRISP,
    SIGNAL_GOLDEN_HOUR_NOW,
    SIGNAL_PERFECT_DAY,
    SIGNAL_OVERCAST_CALM,
]


@dataclass
class ScoredSignal:
    """A single weather signal with its notability score."""
    category: str
    score: int  # 0-10
    data: dict = field(default_factory=dict)


@dataclass
class NotabilityResult:
    """Output of the notability scorer."""
    primary_angle: str
    supporting_signals: list[str]
    all_scored: list[ScoredSignal]
    weather_summary: dict


_RAINY_CONDITIONS = {"rain", "drizzle", "thunderstorm"}
_WET_CONDITIONS = _RAINY_CONDITIONS | {"snow"}


def _is_rainy_str(main: str) -> bool:
    return main.lower() in _RAINY_CONDITIONS


def _is_wet_str(main: str) -> bool:
    return main.lower() in _WET_CONDITIONS


def _extract_signals(weather: WeatherData, recent_angles: list[str]) -> list[ScoredSignal]:
    """Apply all 20 signal rules to the weather data."""
    signals: list[ScoredSignal] = []

    temp = weather.temperature_c
    feels = weather.feels_like_c
    humidity = weather.humidity
    wind = weather.wind_speed
    clouds = weather.clouds_percent
    main = weather.main_condition
    desc = weather.description.lower()

    raining_now = _is_rainy_str(main) or "drizzle" in desc or "rain" in desc
    precip_next_6h = weather.precipitation_next_6h

    # Forecast-derived flags
    rain_in_next_6h = False
    clear_in_next_6h = False
    if weather.forecast_entries:
        for entry in weather.forecast_entries[:2]:
            if _is_wet_str(entry.main_condition) or entry.precipitation_mm > 0:
                rain_in_next_6h = True
            elif entry.main_condition.lower() in ("clear", "clouds") and entry.precipitation_mm == 0:
                clear_in_next_6h = True

    # Consecutive rain hours (current + forecast until dry)
    consecutive_rain_hours = 0
    if raining_now:
        consecutive_rain_hours = 3
        for entry in weather.forecast_entries:
            if _is_wet_str(entry.main_condition) or entry.precipitation_mm > 0:
                consecutive_rain_hours += 3
            else:
                break

    # 1. extreme_heat
    if temp >= 32:
        signals.append(ScoredSignal(SIGNAL_EXTREME_HEAT, 9, {"temp": temp}))

    # 2. extreme_cold
    if temp <= 0:
        signals.append(ScoredSignal(SIGNAL_EXTREME_COLD, 9, {"temp": temp}))

    # 3. heatwave
    if temp >= 28 and feels >= 30:
        signals.append(ScoredSignal(SIGNAL_HEATWAVE, 8, {"temp": temp, "feels_like": feels}))

    # 4. cold_snap
    if temp <= 5:
        signals.append(ScoredSignal(SIGNAL_COLD_SNAP, 8, {"temp": temp}))

    # 5. sticky_heat
    if temp >= 24 and humidity >= 75:
        signals.append(ScoredSignal(SIGNAL_STICKY_HEAT, 5, {"temp": temp, "humidity": humidity}))

    # 6. dry_crisp
    if humidity <= 35 and 10 <= temp <= 25:
        signals.append(ScoredSignal(SIGNAL_DRY_CRISP, 5, {"temp": temp, "humidity": humidity}))

    # 7. rain_now_clearing
    if raining_now and clear_in_next_6h and not rain_in_next_6h:
        signals.append(ScoredSignal(SIGNAL_RAIN_NOW_CLEARING, 7, {"current": desc}))

    # 8. rain_coming
    if not raining_now and rain_in_next_6h:
        signals.append(ScoredSignal(SIGNAL_RAIN_COMING, 7, {"precip_next_6h": precip_next_6h}))

    # 9. extended_rain
    if raining_now and consecutive_rain_hours >= 12:
        signals.append(ScoredSignal(SIGNAL_EXTENDED_RAIN, 6, {"hours": consecutive_rain_hours}))

    # 10. heavy_rain
    heavy = False
    if weather.forecast_entries:
        first = weather.forecast_entries[0]
        if first.precipitation_mm >= 10:
            heavy = True
    if heavy or (raining_now and "heavy" in desc):
        signals.append(ScoredSignal(SIGNAL_HEAVY_RAIN, 8, {}))

    # 11. stormy
    if main.lower() == "thunderstorm":
        signals.append(ScoredSignal(SIGNAL_STORMY, 9, {}))

    # 12. fog_mist
    if main.lower() in ("fog", "mist", "haze"):
        signals.append(ScoredSignal(SIGNAL_FOG_MIST, 5, {}))

    # 13. first_snow_season (best-effort: snow now, no snow_falling in recent history)
    if main.lower() == "snow" and SIGNAL_SNOW_FALLING not in recent_angles and SIGNAL_FIRST_SNOW_SEASON not in recent_angles:
        signals.append(ScoredSignal(SIGNAL_FIRST_SNOW_SEASON, 9, {}))

    # 14. snow_falling
    if main.lower() == "snow":
        signals.append(ScoredSignal(SIGNAL_SNOW_FALLING, 7, {}))

    # 15. gusty_wind
    if wind >= 10:
        signals.append(ScoredSignal(SIGNAL_GUSTY_WIND, 5, {"wind": wind}))

    # 16. overcast_calm
    if clouds >= 85 and wind <= 3:
        signals.append(ScoredSignal(SIGNAL_OVERCAST_CALM, 4, {"clouds": clouds, "wind": wind}))

    # 17. perfect_day
    if 18 <= temp <= 26 and clouds <= 30 and wind <= 5 and precip_next_6h == 0 and not raining_now:
        signals.append(ScoredSignal(SIGNAL_PERFECT_DAY, 6, {"temp": temp}))

    # 18. golden_hour_now
    try:
        minutes_to_sunset = (weather.sunset - weather.timestamp).total_seconds() / 60
        if 0 <= minutes_to_sunset <= 60 and clouds <= 60:
            signals.append(ScoredSignal(SIGNAL_GOLDEN_HOUR_NOW, 6, {}))
    except Exception:
        pass

    # 19. frost_risk_tonight
    if weather.forecast_entries:
        low = min(e.temperature_c for e in weather.forecast_entries)
        if low <= 2 and temp > low:
            signals.append(ScoredSignal(SIGNAL_FROST_RISK_TONIGHT, 6, {"low": low}))

    # 20. temp_swing
    if weather.forecast_entries:
        temps = [temp] + [e.temperature_c for e in weather.forecast_entries]
        swing = max(temps) - min(temps)
        if swing >= 10:
            signals.append(ScoredSignal(SIGNAL_TEMP_SWING, 6, {"swing": round(swing, 1)}))

    return signals


def _apply_recent_penalty(signals: list[ScoredSignal], recent_angles: list[str]) -> list[ScoredSignal]:
    """Reduce score for signals matching recent angles: -5 most recent, -3 in last 5."""
    if not recent_angles:
        return signals

    most_recent = recent_angles[0]
    last_five = set(recent_angles[:5])

    adjusted: list[ScoredSignal] = []
    for s in signals:
        if s.category == most_recent:
            penalty = 5
        elif s.category in last_five:
            penalty = 3
        else:
            penalty = 0
        new_score = max(0, s.score - penalty)
        adjusted.append(ScoredSignal(s.category, new_score, s.data))
    return adjusted


def _build_weather_summary(weather: WeatherData) -> dict:
    """Produce a structured-facts dict the caption prompt can reference."""
    next_change = weather.next_condition_change
    return {
        "city": weather.city_name,
        "country": weather.country,
        "temperature_c": round(weather.temperature_c, 1),
        "feels_like_c": round(weather.feels_like_c, 1),
        "humidity": weather.humidity,
        "description": weather.description,
        "main_condition": weather.main_condition,
        "wind_speed_ms": round(weather.wind_speed, 1),
        "clouds_percent": weather.clouds_percent,
        "time_of_day": weather.time_of_day,
        "is_daytime": weather.is_daytime,
        "timestamp": weather.timestamp.isoformat(),
        "sunrise": weather.sunrise.isoformat(),
        "sunset": weather.sunset.isoformat(),
        "precipitation_next_6h_mm": round(weather.precipitation_next_6h, 1),
        "temp_trend_6h": weather.temp_trend_6h,
        "max_temp_24h": round(weather.max_temp_24h, 1),
        "min_temp_24h": round(weather.min_temp_24h, 1),
        "next_condition_change": (
            {"when": next_change[0].isoformat(), "to": next_change[1]}
            if next_change else None
        ),
    }


def score_notability(
    weather: WeatherData,
    recent_angles: Optional[list[str]] = None,
) -> NotabilityResult:
    """Score weather signals and pick the primary angle.

    Pure function: given identical (weather, recent_angles), the output is
    identical — no randomness, no network calls, no wall-clock reads.

    Args:
        weather: Current weather + forecast data.
        recent_angles: Most-recent-first list of primary angles from recent posts.

    Returns:
        NotabilityResult with primary_angle (category string or "unremarkable_day"),
        up-to-2 supporting signals, full scored list, and a weather_summary dict.
    """
    recent = list(recent_angles) if recent_angles else []

    raw_signals = _extract_signals(weather, recent)
    adjusted = _apply_recent_penalty(raw_signals, recent)
    summary = _build_weather_summary(weather)

    priority_map = {cat: i for i, cat in enumerate(PRIORITY_ORDER)}
    sorted_signals = sorted(
        adjusted,
        key=lambda s: (-s.score, priority_map.get(s.category, 999)),
    )

    if not sorted_signals or sorted_signals[0].score <= 3:
        return NotabilityResult(
            primary_angle=UNREMARKABLE_DAY,
            supporting_signals=[],
            all_scored=sorted_signals,
            weather_summary=summary,
        )

    primary = sorted_signals[0]
    supporting = [s.category for s in sorted_signals[1:3] if s.score >= 3]

    return NotabilityResult(
        primary_angle=primary.category,
        supporting_signals=supporting,
        all_scored=sorted_signals,
        weather_summary=summary,
    )
