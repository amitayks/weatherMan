#!/usr/bin/env python3
"""
State management for daily posting schedule.

This module handles:
1. Daily schedule persistence to JSON file
2. Loading and validating existing schedules
3. Tracking which cities have been posted
"""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config

from .scheduler import select_daily_cities, calculate_posting_times


@dataclass
class DailySchedule:
    """
    Daily posting schedule with selected cities and posting times.

    Attributes:
        date: Date in YYYY-MM-DD format
        selected_cities: List of dicts with city_id, posting_time_utc, posted status
        generation_timestamp: When this schedule was created (ISO format)
    """

    date: str
    selected_cities: list[dict]
    generation_timestamp: str

    def is_current_day(self) -> bool:
        """
        Check if this schedule is for today (UTC).

        Returns:
            True if schedule date matches current UTC date
        """
        today_utc = datetime.now(timezone.utc).date()
        return self.date == today_utc.isoformat()

    def needs_posting(
        self, city_id: str, current_time: datetime, tolerance_minutes: int = 30
    ) -> bool:
        """
        Check if a city should post now based on its scheduled time.

        Args:
            city_id: City identifier to check
            current_time: Current time to compare against (should be UTC)
            tolerance_minutes: Minutes before/after scheduled time to allow posting

        Returns:
            True if city is scheduled, hasn't been posted yet, and current time
            is within tolerance window of scheduled time
        """
        for city_entry in self.selected_cities:
            if city_entry["city_id"] == city_id:
                # Check if already posted
                if city_entry.get("posted", False):
                    return False

                # Parse scheduled posting time
                posting_time = datetime.fromisoformat(city_entry["posting_time_utc"])

                # Ensure both times are timezone-aware
                if current_time.tzinfo is None:
                    current_time = current_time.replace(tzinfo=timezone.utc)
                if posting_time.tzinfo is None:
                    posting_time = posting_time.replace(tzinfo=timezone.utc)

                # Calculate time difference in minutes
                time_diff = abs((current_time - posting_time).total_seconds() / 60)

                return time_diff <= tolerance_minutes

        # City not in today's schedule
        return False

    def mark_posted(self, city_id: str) -> None:
        """
        Mark a city as posted.

        Args:
            city_id: City identifier to mark as posted
        """
        for city_entry in self.selected_cities:
            if city_entry["city_id"] == city_id:
                city_entry["posted"] = True
                return

    def to_dict(self) -> dict:
        """
        Convert schedule to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the schedule
        """
        return asdict(self)


class StateManager:
    """
    Manages daily schedule persistence to JSON file.

    The state file is stored in the state/ directory and tracks:
    - Which cities were selected for today
    - Their scheduled posting times
    - Whether they've been posted yet
    """

    STATE_FILE = "state/daily_schedule.json"

    def __init__(self, state_file: Optional[str] = None):
        """
        Initialize state manager.

        Args:
            state_file: Optional custom path to state file
        """
        self.state_file = state_file or self.STATE_FILE

    def load_schedule(self) -> Optional[DailySchedule]:
        """
        Load schedule from JSON file.

        Returns:
            DailySchedule object if file exists and is valid, None otherwise
        """
        if not os.path.exists(self.state_file):
            return None

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            return DailySchedule(
                date=data["date"],
                selected_cities=data["selected_cities"],
                generation_timestamp=data["generation_timestamp"],
            )
        except (json.JSONDecodeError, KeyError, IOError) as e:
            print(f"⚠️  Warning: Could not load schedule from {self.state_file}: {e}")
            return None

    def save_schedule(self, schedule: DailySchedule) -> None:
        """
        Save schedule to JSON file.

        Args:
            schedule: DailySchedule object to save
        """
        # Ensure state directory exists
        state_dir = Path(self.state_file).parent
        state_dir.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(schedule.to_dict(), f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"❌ Error: Could not save schedule to {self.state_file}: {e}")
            raise

    def get_or_create_schedule(self, config: 'Config') -> DailySchedule:
        """
        Load existing schedule or create new one for today.

        If the existing schedule is for a previous day or doesn't exist,
        generates a new schedule by:
        1. Selecting cities using weighted random selection
        2. Calculating evenly distributed posting times
        3. Saving the new schedule to disk

        Args:
            config: Configuration object containing all cities

        Returns:
            DailySchedule for today
        """
        # Try to load existing schedule
        schedule = self.load_schedule()

        # Check if schedule is valid for today
        if schedule is not None and schedule.is_current_day():
            print(f"📅 Loaded existing schedule for {schedule.date}")
            return schedule

        # Generate new schedule for today
        print("📅 Generating new daily schedule...")

        # Select cities
        selected_cities = select_daily_cities(config, num_cities=6)
        print(
            f"🎲 Selected cities (weighted random): {', '.join(city.name for city in selected_cities)}"
        )

        # Calculate posting times
        posting_times = calculate_posting_times(selected_cities)

        # Create schedule data structure
        today_utc = datetime.now(timezone.utc)
        today_date = today_utc.date().isoformat()

        selected_cities_data = []
        for city in selected_cities:
            posting_time = posting_times[city.id]
            selected_cities_data.append(
                {
                    "city_id": city.id,
                    "posting_time_utc": posting_time.isoformat(),
                    "posted": False,
                }
            )
            print(f"   - {city.name} → {posting_time.strftime('%H:%M UTC')}")

        new_schedule = DailySchedule(
            date=today_date,
            selected_cities=selected_cities_data,
            generation_timestamp=today_utc.isoformat(),
        )

        # Save to disk
        self.save_schedule(new_schedule)
        print(f"💾 Schedule saved to {self.state_file}")

        return new_schedule
