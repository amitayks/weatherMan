"""Instagram Graph API integration for posting weather images."""

import os
import time
import requests
from pathlib import Path
from typing import Optional

from ..config import CityConfig
from ..weather import WeatherData


class InstagramPoster:
    """Post images to Instagram using Meta Graph API."""
    
    GRAPH_API_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, city: CityConfig, credentials: dict):
        self.city = city
        self.credentials = credentials
        self._validate_credentials()
    
    def _validate_credentials(self):
        """Validate Instagram credentials."""
        if not self.credentials.get("access_token"):
            raise ValueError(f"Missing Instagram access token (used for {self.city.name})")
        if not self.credentials.get("account_id"):
            raise ValueError(f"Missing Instagram account ID (used for {self.city.name})")
    
    @property
    def access_token(self) -> str:
        return self.credentials["access_token"]
    
    @property
    def account_id(self) -> str:
        return self.credentials["account_id"]
    
    def build_caption(self, weather: WeatherData) -> str:
        """Build Instagram caption with weather info and hashtags."""
        
        # Main content - Instagram allows longer captions
        lines = [
            f"{weather.emoji} {self.city.name} Weather Update",
            "",
            f"🌡️ Temperature: {weather.format_temperature('C')} ({weather.format_temperature('F')})",
            f"💨 Feels like: {weather.feels_like_c:.0f}°C",
            f"💧 Humidity: {weather.humidity}%",
            f"☁️ Conditions: {weather.description.title()}",
            "",
            f"📅 {weather.format_date('%B %d, %Y')}",
            "",
            "—" * 10,
            "",
        ]
        
        # Add hashtags - Instagram allows up to 30
        hashtags = self.city.hashtags.copy() if self.city.hashtags else []
        
        # Add standard hashtags
        standard_hashtags = [
            f"#{self.city.name.replace(' ', '')}",
            f"#{self.city.country.replace(' ', '')}",
            "#Weather",
            "#CityWeather",
            "#AIArt",
            "#IsometricArt",
            "#3DArt",
            "#DailyWeather",
            "#TravelGram",
            "#CityLife",
            "#WeatherUpdate",
            "#AIGenerated",
        ]
        
        # Combine and deduplicate
        all_hashtags = hashtags + [h for h in standard_hashtags if h not in hashtags]
        unique_hashtags = list(dict.fromkeys(all_hashtags))[:25]  # Limit to 25
        
        lines.append(" ".join(unique_hashtags))
        
        return "\n".join(lines)
    
    def upload_image_to_hosting(self, image_path: Path) -> Optional[str]:
        """
        Upload image to a public URL for Instagram.
        
        Instagram Graph API requires images to be hosted at a public URL.
        This uses a temporary hosting solution.
        
        NOTE: In production, you should use your own image hosting
        (e.g., AWS S3, Cloudinary, or your own server).
        """
        
        # Option 1: Use environment variable for your own hosting endpoint
        hosting_endpoint = os.getenv("IMAGE_HOSTING_ENDPOINT")
        
        if hosting_endpoint:
            # Upload to your own hosting
            try:
                with open(image_path, "rb") as f:
                    response = requests.post(
                        hosting_endpoint,
                        files={"image": f},
                        timeout=60,
                    )
                    response.raise_for_status()
                    return response.json().get("url")
            except Exception as e:
                print(f"Error uploading to custom hosting: {e}")
                return None
        
        # Option 2: Use imgbb (free tier available)
        imgbb_api_key = os.getenv("IMGBB_API_KEY")
        if imgbb_api_key:
            try:
                import base64
                with open(image_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode()
                
                response = requests.post(
                    "https://api.imgbb.com/1/upload",
                    data={
                        "key": imgbb_api_key,
                        "image": image_data,
                        "expiration": 86400,  # 24 hours
                    },
                    timeout=60,
                )
                response.raise_for_status()
                return response.json()["data"]["url"]
            except Exception as e:
                print(f"Error uploading to imgbb: {e}")
                return None
        
        print("No image hosting configured. Set IMAGE_HOSTING_ENDPOINT or IMGBB_API_KEY")
        return None
    
    def create_media_container(self, image_url: str, caption: str) -> Optional[str]:
        """Create a media container for the image."""
        
        url = f"{self.GRAPH_API_URL}/{self.account_id}/media"
        
        params = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token,
        }
        
        try:
            response = requests.post(url, data=params, timeout=30)
            response.raise_for_status()
            return response.json().get("id")
        except requests.RequestException as e:
            print(f"Error creating media container: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return None
    
    def publish_media(self, creation_id: str) -> Optional[str]:
        """Publish the media container."""
        
        url = f"{self.GRAPH_API_URL}/{self.account_id}/media_publish"
        
        params = {
            "creation_id": creation_id,
            "access_token": self.access_token,
        }
        
        try:
            response = requests.post(url, data=params, timeout=30)
            response.raise_for_status()
            return response.json().get("id")
        except requests.RequestException as e:
            print(f"Error publishing media: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return None
    
    def post(
        self,
        image_path: Path,
        weather: WeatherData,
        dry_run: bool = False,
    ) -> Optional[str]:
        """Post image to Instagram."""
        
        caption = self.build_caption(weather)
        
        if dry_run:
            print(f"[DRY RUN] Would post to Instagram for {self.city.name}:")
            print(f"  Image: {image_path}")
            print(f"  Caption: {caption[:100]}...")
            return "dry_run_post_id"
        
        # Step 1: Upload image to public hosting
        print(f"Uploading image to hosting for {self.city.name}...")
        image_url = self.upload_image_to_hosting(image_path)
        
        if not image_url:
            print(f"Failed to upload image for {self.city.name}")
            return None
        
        # Step 2: Create media container
        print(f"Creating Instagram media container for {self.city.name}...")
        creation_id = self.create_media_container(image_url, caption)
        
        if not creation_id:
            print(f"Failed to create media container for {self.city.name}")
            return None
        
        # Step 3: Wait for processing
        print("Waiting for media processing...")
        time.sleep(5)  # Give Instagram time to process
        
        # Step 4: Publish
        print(f"Publishing to Instagram for {self.city.name}...")
        post_id = self.publish_media(creation_id)
        
        if post_id:
            print(f"Instagram post published! ID: {post_id}")
            return post_id
        else:
            print(f"Failed to publish to Instagram for {self.city.name}")
            return None


def post_to_instagram(
    city: CityConfig,
    image_path: Path,
    weather: WeatherData,
    credentials: dict,
    dry_run: bool = False,
) -> Optional[str]:
    """Convenience function to post to Instagram."""
    if not city.platforms.instagram:
        print(f"Instagram disabled for {city.name}")
        return None

    try:
        poster = InstagramPoster(city, credentials)
        return poster.post(image_path, weather, dry_run)
    except ValueError as e:
        print(f"Instagram configuration error: {e}")
        return None
