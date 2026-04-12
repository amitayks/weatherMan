"""Tests for the notability scorer — one test per signal category + penalty + fallback."""

from datetime import timedelta

import pytest

from src.notability import (
    score_notability,
    SIGNAL_EXTREME_HEAT, SIGNAL_EXTREME_COLD, SIGNAL_HEATWAVE, SIGNAL_COLD_SNAP,
    SIGNAL_STICKY_HEAT, SIGNAL_DRY_CRISP,
    SIGNAL_RAIN_NOW_CLEARING, SIGNAL_RAIN_COMING, SIGNAL_EXTENDED_RAIN,
    SIGNAL_HEAVY_RAIN, SIGNAL_STORMY, SIGNAL_FOG_MIST,
    SIGNAL_FIRST_SNOW_SEASON, SIGNAL_SNOW_FALLING,
    SIGNAL_GUSTY_WIND, SIGNAL_OVERCAST_CALM,
    SIGNAL_PERFECT_DAY, SIGNAL_GOLDEN_HOUR_NOW,
    SIGNAL_FROST_RISK_TONIGHT, SIGNAL_TEMP_SWING,
    UNREMARKABLE_DAY,
)
from tests.conftest import make_weather, make_forecast_entry


def test_extreme_heat():
    w = make_weather(temperature_c=33)
    assert score_notability(w).primary_angle == SIGNAL_EXTREME_HEAT


def test_extreme_cold():
    w = make_weather(temperature_c=-5, main_condition="Clear")
    assert score_notability(w).primary_angle == SIGNAL_EXTREME_COLD


def test_heatwave():
    # temp >=28 and feels >=30 but NOT >=32 (else extreme wins by priority)
    w = make_weather(temperature_c=29, feels_like_c=31)
    assert score_notability(w).primary_angle == SIGNAL_HEATWAVE


def test_cold_snap():
    # temp <=5 but >0
    w = make_weather(temperature_c=3, main_condition="Clear")
    assert score_notability(w).primary_angle == SIGNAL_COLD_SNAP


def test_sticky_heat():
    # temp >=24, humidity >=75, cloudy enough that perfect_day doesn't fire
    w = make_weather(
        temperature_c=25, feels_like_c=25, humidity=80,
        clouds_percent=70, main_condition="Clouds", description="broken clouds",
    )
    assert score_notability(w).primary_angle == SIGNAL_STICKY_HEAT


def test_dry_crisp():
    # Cloudy enough that perfect_day doesn't fire
    w = make_weather(
        temperature_c=18, humidity=30,
        clouds_percent=60, main_condition="Clouds", description="broken clouds",
    )
    assert score_notability(w).primary_angle == SIGNAL_DRY_CRISP


def test_rain_now_clearing():
    w = make_weather(
        main_condition="Rain",
        description="light rain",
        forecast_entries=[
            make_forecast_entry(hours_ahead=3, main_condition="Clear", precipitation_mm=0),
            make_forecast_entry(hours_ahead=6, main_condition="Clear", precipitation_mm=0),
        ],
    )
    assert score_notability(w).primary_angle == SIGNAL_RAIN_NOW_CLEARING


def test_rain_coming():
    w = make_weather(
        main_condition="Clear",
        description="clear sky",
        forecast_entries=[
            make_forecast_entry(hours_ahead=3, main_condition="Rain", precipitation_mm=2),
            make_forecast_entry(hours_ahead=6, main_condition="Rain", precipitation_mm=3),
        ],
    )
    assert score_notability(w).primary_angle == SIGNAL_RAIN_COMING


def test_extended_rain():
    # Raining now, rain continues 12+ hours. But this signal has lower score (6) than
    # HEAVY_RAIN would be — so avoid heavy thresholds. Also no clearing in next 6h.
    w = make_weather(
        temperature_c=18,
        main_condition="Rain",
        description="light rain",
        forecast_entries=[
            make_forecast_entry(hours_ahead=3, main_condition="Rain", precipitation_mm=1),
            make_forecast_entry(hours_ahead=6, main_condition="Rain", precipitation_mm=1),
            make_forecast_entry(hours_ahead=9, main_condition="Rain", precipitation_mm=1),
        ],
    )
    assert score_notability(w).primary_angle == SIGNAL_EXTENDED_RAIN


def test_heavy_rain():
    # Forecast first entry has ≥10mm precip
    w = make_weather(
        main_condition="Rain",
        description="rain",
        forecast_entries=[
            make_forecast_entry(hours_ahead=3, main_condition="Rain", precipitation_mm=12),
        ],
    )
    assert score_notability(w).primary_angle == SIGNAL_HEAVY_RAIN


def test_stormy():
    w = make_weather(main_condition="Thunderstorm", description="thunderstorm")
    assert score_notability(w).primary_angle == SIGNAL_STORMY


def test_fog_mist():
    # Fog with mild temp so it wins as primary
    w = make_weather(temperature_c=15, main_condition="Fog", description="fog")
    assert score_notability(w).primary_angle == SIGNAL_FOG_MIST


def test_first_snow_season():
    # Snow falling, and no prior SNOW_FALLING in recent_angles
    w = make_weather(
        temperature_c=-2,
        main_condition="Snow",
        description="light snow",
    )
    result = score_notability(w, recent_angles=[])
    # FIRST_SNOW_SEASON (9) beats EXTREME_COLD (9) on priority because it's earlier
    assert result.primary_angle == SIGNAL_FIRST_SNOW_SEASON


def test_snow_falling_after_recent_snow():
    # Snow falling, but we already logged snow_falling recently → no first_snow
    w = make_weather(
        temperature_c=2,
        main_condition="Snow",
        description="light snow",
    )
    result = score_notability(w, recent_angles=[SIGNAL_SNOW_FALLING, "perfect_day"])
    # SNOW_FALLING is most recent → -5 penalty, won't be primary
    # Next candidates: COLD_SNAP (temp=2 ≤5 → 8) wins
    assert result.primary_angle == SIGNAL_COLD_SNAP


def test_gusty_wind():
    w = make_weather(temperature_c=15, wind_speed=12)
    assert score_notability(w).primary_angle == SIGNAL_GUSTY_WIND


def test_overcast_calm():
    # Pure overcast calm — low score (4), so won't win unless no other signals are higher.
    # Use mild temp so no other signal fires.
    w = make_weather(temperature_c=15, wind_speed=1, clouds_percent=90, main_condition="Clouds", description="overcast clouds")
    # Score 4 > 3 threshold, so this should fire as primary
    assert score_notability(w).primary_angle == SIGNAL_OVERCAST_CALM


def test_perfect_day():
    w = make_weather(
        temperature_c=22,
        clouds_percent=20,
        wind_speed=3,
        main_condition="Clear",
        description="clear sky",
    )
    assert score_notability(w).primary_angle == SIGNAL_PERFECT_DAY


def test_golden_hour_now():
    # Timestamp within 1h of sunset. Also ensure no bigger signal fires.
    from datetime import datetime
    import pytz
    tz = pytz.timezone("UTC")
    ts = tz.localize(datetime(2026, 4, 12, 18, 30))
    ss = tz.localize(datetime(2026, 4, 12, 19, 0))
    sr = tz.localize(datetime(2026, 4, 12, 6, 0))
    w = make_weather(
        temperature_c=15,
        clouds_percent=40,
        wind_speed=3,
        timestamp=ts,
        sunset=ss,
        sunrise=sr,
        main_condition="Clouds",
        description="few clouds",
    )
    assert score_notability(w).primary_angle == SIGNAL_GOLDEN_HOUR_NOW


def test_frost_risk_tonight():
    # Temp 8 now, but forecast low ≤ 2
    w = make_weather(
        temperature_c=8,
        main_condition="Clear",
        description="clear sky",
        forecast_entries=[
            make_forecast_entry(hours_ahead=3, temperature_c=5),
            make_forecast_entry(hours_ahead=6, temperature_c=1),
            make_forecast_entry(hours_ahead=9, temperature_c=-1),
        ],
    )
    # Temp trend is falling ≥ threshold, so no perfect day. FROST_RISK expected.
    # TEMP_SWING score 6 would fire too (8 to -1 = 9? no, 9 >= 10? it's 9, below threshold)
    # actually 8 - (-1) = 9, not ≥ 10, no swing. Good.
    assert score_notability(w).primary_angle == SIGNAL_FROST_RISK_TONIGHT


def test_temp_swing():
    # Temp 15 now, forecast shows large swing 25 - 10 = 15
    w = make_weather(
        temperature_c=15,
        main_condition="Clear",
        description="clear sky",
        forecast_entries=[
            make_forecast_entry(hours_ahead=3, temperature_c=25),
            make_forecast_entry(hours_ahead=6, temperature_c=10),
        ],
    )
    assert score_notability(w).primary_angle == SIGNAL_TEMP_SWING


def test_unremarkable_day():
    # Boring weather: mild, partly cloudy, light wind, no rain forecast
    w = make_weather(
        temperature_c=17,
        humidity=55,
        main_condition="Clouds",
        description="broken clouds",
        wind_speed=4,
        clouds_percent=60,
    )
    result = score_notability(w)
    assert result.primary_angle == UNREMARKABLE_DAY
    assert result.supporting_signals == []


def test_recent_angle_penalty_minus_three():
    # Fog would normally fire at score 5. If in last-5 (but not most recent), -3 → score 2.
    # Score 2 < 3 threshold → fallback to unremarkable.
    w = make_weather(temperature_c=15, main_condition="Fog", description="fog")
    # Most recent is something else; fog is in last-5
    result = score_notability(w, recent_angles=["some_other_angle", SIGNAL_FOG_MIST])
    assert result.primary_angle == UNREMARKABLE_DAY


def test_recent_angle_penalty_minus_five_most_recent():
    # Heavy rain score 8; if most recent, -5 → 3. 3 is NOT > 3 → unremarkable
    w = make_weather(
        main_condition="Rain",
        description="rain",
        forecast_entries=[
            make_forecast_entry(hours_ahead=3, main_condition="Rain", precipitation_mm=12),
        ],
    )
    result = score_notability(w, recent_angles=[SIGNAL_HEAVY_RAIN])
    # Heavy rain score 8 - 5 = 3, not > 3 → unremarkable (no other signal fires here either)
    assert result.primary_angle == UNREMARKABLE_DAY


def test_weather_summary_present():
    w = make_weather(temperature_c=25)
    result = score_notability(w)
    assert "temperature_c" in result.weather_summary
    assert result.weather_summary["temperature_c"] == 25.0
    assert "city" in result.weather_summary


def test_supporting_signals_up_to_two():
    # Scenario with multiple signals firing
    w = make_weather(
        temperature_c=33,
        feels_like_c=35,
        humidity=80,
    )
    result = score_notability(w)
    assert result.primary_angle == SIGNAL_EXTREME_HEAT
    assert len(result.supporting_signals) <= 2


def test_deterministic_same_inputs_same_output():
    w = make_weather(temperature_c=25)
    r1 = score_notability(w, recent_angles=["foo", "bar"])
    r2 = score_notability(w, recent_angles=["foo", "bar"])
    assert r1.primary_angle == r2.primary_angle
    assert r1.supporting_signals == r2.supporting_signals
    assert [s.category for s in r1.all_scored] == [s.category for s in r2.all_scored]
