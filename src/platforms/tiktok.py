"""TikTok API integration for posting weather images as photo posts."""

import os
import time
import requests
from pathlib import Path
from typing import Optional

from ..config import CityConfig
from ..weather import WeatherData


class TikTokPoster:
    """
    Post images to TikTok using the Content Posting API.
    
    NOTE: TikTok API requires app review and approval for posting.
    Photo posts are available through the Direct Post API.
    """
    
    API_BASE = "https://open.tiktokapis.com/v2"
    
    def __init__(self, city: CityConfig):
        self.city = city
        self.credentials = city.get_credentials("tiktok")
        self._validate_credentials()
    
    def _validate_credentials(self):
        """Validate TikTok credentials."""
        if not self.credentials.get("access_token"):
            raise ValueError(f"Missing TikTok access token for {self.city.name}")
    
    @property
    def access_token(self) -> str:
        return self.credentials["access_token"]
    
    def build_description(self, weather: WeatherData) -> str:
        """Build TikTok description with weather info and hashtags."""
        
        # TikTok descriptions should be shorter and more engaging
        lines = [
            f"{weather.emoji} {self.city.name} Weather Today!",
            f"🌡️ {weather.format_temperature('C')} | {weather.description.title()}",
            "",
        ]
        
        # Add hashtags - TikTok uses hashtags heavily
        hashtags = self.city.hashtags.copy() if self.city.hashtags else []
        
        standard_hashtags = [
            f"#{self.city.name.replace(' ', '').lower()}",
            "#weather",
            "#fyp",
            "#foryou",
            "#citylife",
            "#aiart",
            "#dailyweather",
            f"#{self.city.country.replace(' ', '').lower()}",
        ]
        
        all_hashtags = hashtags + [h for h in standard_hashtags if h.lower() not in [x.lower() for x in hashtags]]
        unique_hashtags = list(dict.fromkeys(all_hashtags))[:10]
        
        lines.append(" ".join(unique_hashtags))
        
        return "\n".join(lines)
    
    def init_photo_post(self, description: str) -> Optional[dict]:
        """Initialize a photo post upload."""
        
        url = f"{self.API_BASE}/post/publish/inbox/image/init/"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        
        data = {
            "post_info": {
                "title": description[:150],  # TikTok title limit
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_comment": False,
                "disable_duet": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "photo_cover_index": 0,
                "photo_images": [],  # Will be filled with image URLs
            },
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error initializing TikTok photo post: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return None
    
    def upload_image_direct(self, image_path: Path) -> Optional[str]:
        """
        Upload image directly to TikTok's servers.
        
        Alternative: Use TikTok's Direct Post API with image URL.
        This requires the image to be hosted at a public URL.
        """
        
        # TikTok Direct Post with URL method
        # Requires image hosting similar to Instagram
        
        hosting_endpoint = os.getenv("IMAGE_HOSTING_ENDPOINT")
        imgbb_api_key = os.getenv("IMGBB_API_KEY")
        
        if hosting_endpoint:
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
                        "expiration": 86400,
                    },
                    timeout=60,
                )
                response.raise_for_status()
                return response.json()["data"]["url"]
            except Exception as e:
                print(f"Error uploading to imgbb: {e}")
        
        return None
    
    def post_photo(self, image_url: str, description: str) -> Optional[str]:
        """Post a photo to TikTok using Direct Post API."""
        
        url = f"{self.API_BASE}/post/publish/content/init/"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        
        # Photo post payload
        data = {
            "post_info": {
                "title": description[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_comment": False,
                "auto_add_music": True,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "photo_cover_index": 0,
                "photo_images": [image_url],
            },
            "post_mode": "DIRECT_POST",
            "media_type": "PHOTO",
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get("error", {}).get("code") == "ok":
                return result.get("data", {}).get("publish_id")
            else:
                print(f"TikTok API error: {result}")
                return None
                
        except requests.RequestException as e:
            print(f"Error posting to TikTok: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return None
    
    def post(
        self,
        image_path: Path,
        weather: WeatherData,
        dry_run: bool = False,
    ) -> Optional[str]:
        """Post image to TikTok."""
        
        description = self.build_description(weather)
        
        if dry_run:
            print(f"[DRY RUN] Would post to TikTok for {self.city.name}:")
            print(f"  Image: {image_path}")
            print(f"  Description: {description[:100]}...")
            return "dry_run_publish_id"
        
        # Step 1: Upload image to hosting
        print(f"Uploading image for TikTok post ({self.city.name})...")
        image_url = self.upload_image_direct(image_path)
        
        if not image_url:
            print(f"Failed to upload image for TikTok ({self.city.name})")
            print("Ensure IMAGE_HOSTING_ENDPOINT or IMGBB_API_KEY is set")
            return None
        
        # Step 2: Create post
        print(f"Creating TikTok post for {self.city.name}...")
        publish_id = self.post_photo(image_url, description)
        
        if publish_id:
            print(f"TikTok post created! Publish ID: {publish_id}")
            return publish_id
        else:
            print(f"Failed to post to TikTok for {self.city.name}")
            return None


def post_to_tiktok(
    city: CityConfig,
    image_path: Path,
    weather: WeatherData,
    dry_run: bool = False,
) -> Optional[str]:
    """Convenience function to post to TikTok."""
    if not city.platforms.tiktok:
        print(f"TikTok disabled for {city.name}")
        return None
    
    try:
        poster = TikTokPoster(city)
        return poster.post(image_path, weather, dry_run)
    except ValueError as e:
        print(f"TikTok configuration error for {city.name}: {e}")
        return None
