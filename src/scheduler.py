#!/usr/bin/env python3
"""
Daily city scheduler with weighted random selection.

This module handles:
1. Weighted random selection of cities based on probability weights
2. Calculation of evenly distributed posting times across 24 hours UTC
"""

import random
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config, CityConfig


def select_daily_cities(config: 'Config', num_cities: int = 6) -> list['CityConfig']:
    """
    Select N cities using weighted random selection.

    Cities with higher weight values (1-100) are more likely to be selected.
    Selection is done without replacement, so each city appears at most once.

    Args:
        config: Configuration object containing all cities
        num_cities: Number of cities to select (default: 6, syncs with 4-hour cron)

    Returns:
        List of selected CityConfig objects

    Raises:
        ValueError: If num_cities exceeds available enabled cities
    """
    # Get all enabled cities
    enabled_cities = config.get_enabled_cities()

    if len(enabled_cities) < num_cities:
        raise ValueError(
            f"Cannot select {num_cities} cities: only {len(enabled_cities)} enabled cities available"
        )

    # Extract weights
    cities_list = list(enabled_cities)
    weights = [city.weight for city in cities_list]

    # Weighted random sampling without replacement
    selected = []
    remaining_cities = cities_list.copy()
    remaining_weights = weights.copy()

    for _ in range(num_cities):
        # Select one city based on weights
        chosen = random.choices(remaining_cities, weights=remaining_weights, k=1)[0]
        selected.append(chosen)

        # Remove chosen city from remaining pool
        idx = remaining_cities.index(chosen)
        remaining_cities.pop(idx)
        remaining_weights.pop(idx)

    return selected


def calculate_posting_times(selected_cities: list['CityConfig']) -> dict[str, datetime]:
    """
    Calculate evenly distributed posting times across 24 hours UTC.

    For N cities, posts are distributed with equal intervals:
    - Interval = 24 hours / N cities
    - First post at 00:00 UTC
    - Subsequent posts at interval increments

    Example for 6 cities:
    - Interval: 24/6 = 4 hours
    - Times: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC

    Args:
        selected_cities: List of CityConfig objects to schedule

    Returns:
        Dictionary mapping city_id to posting time (datetime in UTC)
        Example: {"tokyo": datetime(2025, 12, 6, 0, 0, tzinfo=UTC), ...}
    """
    if not selected_cities:
        return {}

    num_cities = len(selected_cities)
    interval_hours = 24.0 / num_cities

    # Get current date at midnight UTC
    now_utc = datetime.now(timezone.utc)
    midnight_today = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    posting_schedule = {}

    for i, city in enumerate(selected_cities):
        # Calculate hours offset for this city
        hours_offset = i * interval_hours

        # Split into hours and minutes
        hours = int(hours_offset)
        minutes = int((hours_offset - hours) * 60)

        # Calculate posting time
        posting_time = midnight_today + timedelta(hours=hours, minutes=minutes)

        posting_schedule[city.id] = posting_time

    return posting_schedule


def get_utc_midnight_today() -> datetime:
    """
    Get current date at midnight UTC.

    Returns:
        datetime object at 00:00:00 UTC for today
    """
    now_utc = datetime.now(timezone.utc)
    return now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
