"""X (Twitter) API integration for posting weather images."""

from pathlib import Path
from typing import Optional
import tweepy

from ..config import CityConfig
from ..weather import WeatherData


class TwitterPoster:
    """Post images to X (Twitter) using API v2."""
    
    def __init__(self, city: CityConfig, credentials: dict):
        self.city = city
        self.credentials = credentials
        self.client = None
        self.api_v1 = None  # Needed for media upload
        self._authenticate()
    
    def _authenticate(self):
        """Set up Twitter API authentication."""
        creds = self.credentials
        
        if not all([
            creds.get("api_key"),
            creds.get("api_secret"),
            creds.get("access_token"),
            creds.get("access_token_secret"),
        ]):
            raise ValueError(f"Missing Twitter credentials (used for {self.city.name})")
        
        # API v2 client for posting tweets
        self.client = tweepy.Client(
            consumer_key=creds["api_key"],
            consumer_secret=creds["api_secret"],
            access_token=creds["access_token"],
            access_token_secret=creds["access_token_secret"],
        )
        
        # API v1.1 for media upload (v2 doesn't support media upload directly)
        auth = tweepy.OAuth1UserHandler(
            creds["api_key"],
            creds["api_secret"],
            creds["access_token"],
            creds["access_token_secret"],
        )
        self.api_v1 = tweepy.API(auth)
    
    def build_tweet_text(self, weather: WeatherData) -> str:
        """Build the tweet text with weather info and hashtags."""
        
        # Main content
        lines = [
            f"{weather.emoji} {self.city.name} Weather",
            f"🌡️ {weather.format_temperature('C')} ({weather.format_temperature('F')})",
            f"📅 {weather.format_date('%B %d, %Y')}",
            f"☁️ {weather.description.title()}",
            "",
        ]
        
        # Add hashtags
        hashtags = self.city.hashtags or [f"#{self.city.name.replace(' ', '')}", "#Weather"]
        hashtags.extend(["#AIArt", "#CityWeather"])
        
        # Deduplicate and limit hashtags
        unique_hashtags = list(dict.fromkeys(hashtags))[:6]
        lines.append(" ".join(unique_hashtags))
        
        return "\n".join(lines)
    
    def post(
        self, 
        image_path: Path, 
        weather: WeatherData,
        dry_run: bool = False,
    ) -> Optional[str]:
        """Post image to Twitter/X."""
        
        tweet_text = self.build_tweet_text(weather)
        
        if dry_run:
            print(f"[DRY RUN] Would post to Twitter for {self.city.name}:")
            print(f"  Image: {image_path}")
            print(f"  Text: {tweet_text[:100]}...")
            return "dry_run_tweet_id"
        
        try:
            # Upload media using v1.1 API
            print(f"Uploading image to Twitter for {self.city.name}...")
            media = self.api_v1.media_upload(filename=str(image_path))
            media_id = media.media_id
            
            # Post tweet with media using v2 API
            print(f"Posting tweet for {self.city.name}...")
            response = self.client.create_tweet(
                text=tweet_text,
                media_ids=[media_id],
            )
            
            tweet_id = response.data["id"]
            print(f"Tweet posted successfully! ID: {tweet_id}")
            return tweet_id
            
        except tweepy.TweepyException as e:
            print(f"Error posting to Twitter for {self.city.name}: {e}")
            # Print additional details for debugging 403 errors
            if hasattr(e, 'response') and e.response is not None:
                print(f"Twitter API Response Status: {e.response.status_code}")
                print(f"Twitter API Response: {e.response.text}")
            if hasattr(e, 'api_errors'):
                print(f"Twitter API Errors: {e.api_errors}")
            if hasattr(e, 'api_codes'):
                print(f"Twitter API Codes: {e.api_codes}")
            return None


def post_to_twitter(
    city: CityConfig,
    image_path: Path,
    weather: WeatherData,
    credentials: dict,
    dry_run: bool = False,
) -> Optional[str]:
    """Convenience function to post to Twitter."""
    if not city.platforms.twitter:
        print(f"Twitter disabled for {city.name}")
        return None

    try:
        poster = TwitterPoster(city, credentials)
        return poster.post(image_path, weather, dry_run)
    except ValueError as e:
        print(f"Twitter configuration error: {e}")
        return None
