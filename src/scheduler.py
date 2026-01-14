#!/usr/bin/env python3
"""
Simple city scheduler with weighted random selection.

This module handles selecting ONE random city per run,
excluding cities that have been posted recently.
"""

import random
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .config import Config, CityConfig


def select_random_city(
    config: 'Config',
    excluded_ids: list[str] = None
) -> Optional['CityConfig']:
    """
    Select ONE random city using weighted random selection.

    Cities with higher weight values (1-100) are more likely to be selected.
    Cities in the excluded_ids list will not be selected.

    Args:
        config: Configuration object containing all cities
        excluded_ids: List of city IDs to exclude (recently posted)

    Returns:
        Selected CityConfig object, or None if no cities available
    """
    excluded_ids = excluded_ids or []

    # Get all enabled cities
    enabled_cities = config.get_enabled_cities()

    # Filter out excluded cities
    available_cities = [
        city for city in enabled_cities
        if city.id not in excluded_ids
    ]

    # If all cities are excluded, reset and use all enabled cities
    if not available_cities:
        print("📢 All cities recently posted - resetting exclusion list")
        available_cities = list(enabled_cities)

    if not available_cities:
        print("❌ No enabled cities available")
        return None

    # Extract weights for available cities
    weights = [city.weight for city in available_cities]

    # Weighted random selection of ONE city
    selected = random.choices(available_cities, weights=weights, k=1)[0]

    return selected
