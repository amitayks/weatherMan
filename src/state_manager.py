#!/usr/bin/env python3
"""
State management for tracking recently posted cities.

This module keeps a rolling window of the 100 most recent posts. A city in
this window is excluded from random selection, so with ~5 posts per day the
same city will not reappear for roughly 20 days.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# Rolling window size. With ~5 posts/day this gives ~20 days between repeats.
MAX_RECENT_CITIES = 100


@dataclass
class RecentlyPosted:
    """
    Tracks the last N posted cities (rolling window) to prevent repeats.

    Attributes:
        posts: List of dicts with city_id and posted_at timestamp, newest last.
    """

    posts: list[dict] = field(default_factory=list)

    def add_posted(self, city_id: str) -> None:
        """Append a city entry and trim to the rolling window."""
        self.posts.append({
            "city_id": city_id,
            "posted_at": datetime.now(timezone.utc).isoformat()
        })
        self.trim_to_max()

    def trim_to_max(self, max_entries: int = MAX_RECENT_CITIES) -> int:
        """Keep only the `max_entries` newest posts. Returns number removed."""
        original = len(self.posts)
        if original > max_entries:
            self.posts = self.posts[-max_entries:]
        return original - len(self.posts)

    def get_excluded_ids(self) -> list[str]:
        """City IDs currently in the exclusion window."""
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

    The state file holds the 100 most recent posts; a city in this window is
    excluded from random selection on subsequent runs.
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
        """Load the rolling recent-posts window from disk."""
        if not os.path.exists(self.state_file):
            return RecentlyPosted()

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            recent = RecentlyPosted(posts=data.get("posts", []))

            # Trim on load in case the file was hand-edited or the window
            # shrank since the last save.
            removed = recent.trim_to_max()
            if removed > 0:
                print(f"🧹 Trimmed {removed} old entries beyond the {MAX_RECENT_CITIES}-post window")

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
