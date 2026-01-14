#!/usr/bin/env python3
"""
State management for tracking recently posted cities.

This module handles:
1. Tracking cities posted within the last 24 hours
2. Preventing duplicate posts by excluding recent cities
3. Simple JSON persistence
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class RecentlyPosted:
    """
    Tracks cities posted within the last 24 hours.

    Attributes:
        posts: List of dicts with city_id and posted_at timestamp
    """

    posts: list[dict] = field(default_factory=list)

    def add_posted(self, city_id: str) -> None:
        """
        Add a city to the recently posted list.

        Args:
            city_id: City identifier that was just posted
        """
        self.posts.append({
            "city_id": city_id,
            "posted_at": datetime.now(timezone.utc).isoformat()
        })

    def cleanup_old(self, hours: int = 24) -> int:
        """
        Remove entries older than specified hours.

        Args:
            hours: Number of hours to keep (default: 24)

        Returns:
            Number of entries removed
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        original_count = len(self.posts)

        self.posts = [
            p for p in self.posts
            if datetime.fromisoformat(p["posted_at"]) > cutoff
        ]

        return original_count - len(self.posts)

    def get_excluded_ids(self) -> list[str]:
        """
        Get list of city IDs that should be excluded from selection.

        Returns:
            List of city IDs posted within the retention period
        """
        return [p["city_id"] for p in self.posts]

    def clear(self) -> None:
        """Clear all entries (used when all cities have been posted)."""
        self.posts = []

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {"posts": self.posts}


class StateManager:
    """
    Manages recently posted state persistence to JSON file.

    The state file tracks which cities have been posted recently
    to prevent duplicate posts within a 24-hour window.
    """

    STATE_FILE = "state/recently_posted.json"

    def __init__(self, state_file: Optional[str] = None):
        """
        Initialize state manager.

        Args:
            state_file: Optional custom path to state file
        """
        self.state_file = state_file or self.STATE_FILE

    def load_recent(self) -> RecentlyPosted:
        """
        Load recently posted data from JSON file.

        Returns:
            RecentlyPosted object (empty if file doesn't exist)
        """
        if not os.path.exists(self.state_file):
            return RecentlyPosted()

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            recent = RecentlyPosted(posts=data.get("posts", []))

            # Auto-cleanup old entries on load
            removed = recent.cleanup_old(hours=24)
            if removed > 0:
                print(f"🧹 Cleaned up {removed} old entries from recently posted")

            return recent

        except (json.JSONDecodeError, KeyError, IOError) as e:
            print(f"⚠️  Warning: Could not load state from {self.state_file}: {e}")
            return RecentlyPosted()

    def save_recent(self, recent: RecentlyPosted) -> None:
        """
        Save recently posted data to JSON file.

        Args:
            recent: RecentlyPosted object to save
        """
        # Ensure state directory exists
        state_dir = Path(self.state_file).parent
        state_dir.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(recent.to_dict(), f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"❌ Error: Could not save state to {self.state_file}: {e}")
            raise
