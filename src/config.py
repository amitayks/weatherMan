"""Configuration loader for City Weather Poster."""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import pytz


@dataclass
class Coordinates:
    lat: float
    lon: float


@dataclass
class PlatformConfig:
    twitter: bool = False
    instagram: bool = False
    tiktok: bool = False


@dataclass
class CityConfig:
    """Configuration for a single city."""
    id: str
    name: str
    country: str
    timezone: str
    coordinates: Coordinates
    platforms: PlatformConfig
    landmarks: list[str]
    enabled: bool = True
    weight: int = 1  # Probability weight (1-100) for daily selection
    name_local: Optional[str] = None
    posting_times: list = field(default_factory=lambda: ["08:00", "18:00"])
    hashtags: list = field(default_factory=list)
    
    @property
    def tz(self):
        """Get pytz timezone object."""
        return pytz.timezone(self.timezone)


@dataclass
class GlobalConfig:
    """Global configuration settings."""
    default_posting_times: list
    image_width: int
    image_height: int
    image_format: str
    retry_max_attempts: int
    retry_delay_seconds: int


class Config:
    """Main configuration class."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "cities.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            self._raw = yaml.safe_load(f)
        
        self._load_global()
        self._load_cities()
    
    def _load_global(self):
        """Load global configuration."""
        g = self._raw.get("global", {})
        self.global_config = GlobalConfig(
            default_posting_times=g.get("default_posting_times", ["08:00", "18:00"]),
            image_width=g.get("image", {}).get("width", 1080),
            image_height=g.get("image", {}).get("height", 1080),
            image_format=g.get("image", {}).get("format", "png"),
            retry_max_attempts=g.get("retry", {}).get("max_attempts", 3),
            retry_delay_seconds=g.get("retry", {}).get("delay_seconds", 60),
        )
    
    def _load_cities(self):
        """Load all city configurations."""
        self.cities: dict[str, CityConfig] = {}
        
        for city_id, city_data in self._raw.get("cities", {}).items():
            coords = city_data.get("coordinates", {})
            platforms = city_data.get("platforms", {})
            
            self.cities[city_id] = CityConfig(
                id=city_id,
                name=city_data.get("name", city_id.title()),
                country=city_data.get("country", ""),
                timezone=city_data.get("timezone", "UTC"),
                coordinates=Coordinates(
                    lat=coords.get("lat", 0),
                    lon=coords.get("lon", 0),
                ),
                platforms=PlatformConfig(
                    twitter=platforms.get("twitter", False),
                    instagram=platforms.get("instagram", False),
                    tiktok=platforms.get("tiktok", False),
                ),
                landmarks=city_data.get("landmarks", []),
                enabled=city_data.get("enabled", True),
                weight=city_data.get("weight", 1),
                name_local=city_data.get("name_local"),
                posting_times=city_data.get(
                    "posting_times",
                    self.global_config.default_posting_times
                ),
                hashtags=city_data.get("hashtags", []),
            )
    
    def get_enabled_cities(self) -> list[CityConfig]:
        """Get all enabled cities."""
        return [c for c in self.cities.values() if c.enabled]
    
    def get_city(self, city_id: str) -> Optional[CityConfig]:
        """Get a specific city configuration."""
        return self.cities.get(city_id)
    
    @property
    def google_ai_api_key(self) -> str:
        """Get Google AI API key from environment."""
        return os.getenv("GOOGLE_AI_API_KEY", "")
    
    @property
    def openweather_api_key(self) -> str:
        """Get OpenWeatherMap API key from environment."""
        return os.getenv("OPENWEATHER_API_KEY", "")

    # Platform credentials (global, shared across all cities)
    @property
    def twitter_api_key(self) -> str:
        """Get Twitter API key from environment."""
        return os.getenv("TWITTER_API_KEY", "")

    @property
    def twitter_api_secret(self) -> str:
        """Get Twitter API secret from environment."""
        return os.getenv("TWITTER_API_SECRET", "")

    @property
    def twitter_access_token(self) -> str:
        """Get Twitter access token from environment."""
        return os.getenv("TWITTER_ACCESS_TOKEN", "")

    @property
    def twitter_access_token_secret(self) -> str:
        """Get Twitter access token secret from environment."""
        return os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")

    @property
    def instagram_access_token(self) -> str:
        """Get Instagram access token from environment."""
        return os.getenv("INSTAGRAM_ACCESS_TOKEN", "")

    @property
    def instagram_account_id(self) -> str:
        """Get Instagram account ID from environment."""
        return os.getenv("INSTAGRAM_ACCOUNT_ID", "")

    @property
    def tiktok_access_token(self) -> str:
        """Get TikTok access token from environment."""
        return os.getenv("TIKTOK_ACCESS_TOKEN", "")

    @property
    def tiktok_open_id(self) -> str:
        """Get TikTok Open ID from environment."""
        return os.getenv("TIKTOK_OPEN_ID", "")

    def get_platform_credentials(self, platform: str) -> dict:
        """Get global credentials for a platform."""
        if platform == "twitter":
            return {
                "api_key": self.twitter_api_key,
                "api_secret": self.twitter_api_secret,
                "access_token": self.twitter_access_token,
                "access_token_secret": self.twitter_access_token_secret,
            }
        elif platform == "instagram":
            return {
                "access_token": self.instagram_access_token,
                "account_id": self.instagram_account_id,
            }
        elif platform == "tiktok":
            return {
                "access_token": self.tiktok_access_token,
                "open_id": self.tiktok_open_id,
            }
        return {}


# Singleton instance
_config: Optional[Config] = None


def get_config(config_path: str = None) -> Config:
    """Get or create config singleton."""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
