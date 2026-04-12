"""Tests for WeatherData derived properties with and without forecast entries."""

from tests.conftest import make_weather, make_forecast_entry


def test_precipitation_next_6h_empty():
    w = make_weather(forecast_entries=[])
    assert w.precipitation_next_6h == 0


def test_precipitation_next_6h_sums_two_entries():
    w = make_weather(forecast_entries=[
        make_forecast_entry(hours_ahead=3, precipitation_mm=2.0),
        make_forecast_entry(hours_ahead=6, precipitation_mm=3.5),
        make_forecast_entry(hours_ahead=9, precipitation_mm=10.0),  # should NOT be included
    ])
    assert w.precipitation_next_6h == 5.5


def test_temp_trend_6h_steady_when_no_forecast():
    w = make_weather(temperature_c=20, forecast_entries=[])
    assert w.temp_trend_6h == "steady"


def test_temp_trend_6h_rising():
    w = make_weather(
        temperature_c=15,
        forecast_entries=[
            make_forecast_entry(hours_ahead=3, temperature_c=16),
            make_forecast_entry(hours_ahead=6, temperature_c=20),  # delta 5, but we use index 1
        ],
    )
    # index 1 is "hours_ahead=6" entry: 20 - 15 = 5 → rising
    assert w.temp_trend_6h == "rising"


def test_temp_trend_6h_falling():
    w = make_weather(
        temperature_c=20,
        forecast_entries=[
            make_forecast_entry(hours_ahead=3, temperature_c=18),
            make_forecast_entry(hours_ahead=6, temperature_c=14),
        ],
    )
    assert w.temp_trend_6h == "falling"


def test_temp_trend_6h_steady_below_threshold():
    w = make_weather(
        temperature_c=20,
        forecast_entries=[
            make_forecast_entry(hours_ahead=3, temperature_c=20.5),
            make_forecast_entry(hours_ahead=6, temperature_c=21),  # delta 1 → steady
        ],
    )
    assert w.temp_trend_6h == "steady"


def test_next_condition_change_none_when_all_same():
    w = make_weather(
        main_condition="Clear",
        forecast_entries=[
            make_forecast_entry(hours_ahead=3, main_condition="Clear"),
            make_forecast_entry(hours_ahead=6, main_condition="Clear"),
        ],
    )
    assert w.next_condition_change is None


def test_next_condition_change_finds_first_different():
    w = make_weather(
        main_condition="Clear",
        forecast_entries=[
            make_forecast_entry(hours_ahead=3, main_condition="Clear"),
            make_forecast_entry(hours_ahead=6, main_condition="Rain"),
            make_forecast_entry(hours_ahead=9, main_condition="Clouds"),
        ],
    )
    change = w.next_condition_change
    assert change is not None
    assert change[1] == "Rain"


def test_max_min_temp_24h_with_empty_forecast_equal_current():
    w = make_weather(temperature_c=18, forecast_entries=[])
    assert w.max_temp_24h == 18
    assert w.min_temp_24h == 18


def test_max_min_temp_24h_across_forecast():
    w = make_weather(
        temperature_c=18,
        forecast_entries=[
            make_forecast_entry(hours_ahead=3, temperature_c=22),
            make_forecast_entry(hours_ahead=6, temperature_c=12),
        ],
    )
    assert w.max_temp_24h == 22
    assert w.min_temp_24h == 12
