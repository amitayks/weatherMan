"""Shared test fixtures and helpers."""

from datetime import datetime, timedelta
from typing import Optional

import pytz

from src.weather import ForecastEntry, WeatherData


def make_weather(
    *,
    temperature_c: float = 20.0,
    feels_like_c: Optional[float] = None,
    humidity: int = 50,
    description: str = "clear sky",
    main_condition: str = "Clear",
    icon_code: str = "01d",
    wind_speed: float = 2.0,
    clouds_percent: int = 10,
    timestamp: Optional[datetime] = None,
    sunrise: Optional[datetime] = None,
    sunset: Optional[datetime] = None,
    forecast_entries: Optional[list[ForecastEntry]] = None,
    city_name: str = "Testville",
    country: str = "Testland",
    tz_name: str = "UTC",
) -> WeatherData:
    """Build a WeatherData for tests with sensible defaults."""
    tz = pytz.timezone(tz_name)
    ts = timestamp or tz.localize(datetime(2026, 4, 12, 15, 0))
    sr = sunrise or tz.localize(datetime(2026, 4, 12, 6, 0))
    ss = sunset or tz.localize(datetime(2026, 4, 12, 19, 0))

    return WeatherData(
        city_name=city_name,
        country=country,
        temperature_c=temperature_c,
        temperature_f=(temperature_c * 9 / 5) + 32,
        feels_like_c=feels_like_c if feels_like_c is not None else temperature_c,
        feels_like_f=((feels_like_c if feels_like_c is not None else temperature_c) * 9 / 5) + 32,
        humidity=humidity,
        description=description,
        main_condition=main_condition,
        icon_code=icon_code,
        wind_speed=wind_speed,
        clouds_percent=clouds_percent,
        timestamp=ts,
        sunrise=sr,
        sunset=ss,
        forecast_entries=forecast_entries or [],
    )


def make_forecast_entry(
    *,
    hours_ahead: int = 3,
    temperature_c: float = 20.0,
    main_condition: str = "Clear",
    description: str = "clear sky",
    precipitation_mm: float = 0.0,
    humidity: int = 50,
    clouds_percent: int = 10,
    wind_speed: float = 2.0,
    feels_like_c: Optional[float] = None,
    base_time: Optional[datetime] = None,
) -> ForecastEntry:
    """Build a ForecastEntry N hours ahead of a base time."""
    tz = pytz.timezone("UTC")
    base = base_time or tz.localize(datetime(2026, 4, 12, 15, 0))
    return ForecastEntry(
        timestamp=base + timedelta(hours=hours_ahead),
        temperature_c=temperature_c,
        feels_like_c=feels_like_c if feels_like_c is not None else temperature_c,
        humidity=humidity,
        main_condition=main_condition,
        description=description,
        clouds_percent=clouds_percent,
        wind_speed=wind_speed,
        precipitation_mm=precipitation_mm,
    )
