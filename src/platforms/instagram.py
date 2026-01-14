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

    GRAPH_API_URL = "https://graph.facebook.com/v21.0"  # Updated to latest API version

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

    def create_media_container(self, image_url: str, caption: str, media_type: str = "IMAGE", max_retries: int = 3) -> Optional[str]:
        """
        Create a media container for the image with retry logic.

        Instagram needs time to download the image from the hosting URL.
        This method retries on timeout errors with exponential backoff.

        Args:
            image_url: Public URL of the image
            caption: Caption for the post (ignored for Stories)
            media_type: "IMAGE" for feed posts, "STORIES" for stories
            max_retries: Number of retry attempts
        """

        url = f"{self.GRAPH_API_URL}/{self.account_id}/media"

        params = {
            "image_url": image_url,
            "access_token": self.access_token,
        }

        # Add media_type for Stories
        if media_type == "STORIES":
            params["media_type"] = "STORIES"
        else:
            # Caption only applies to feed posts, not stories
            params["caption"] = caption

        for attempt in range(max_retries):
            try:
                response = requests.post(url, data=params, timeout=60)  # Increased timeout
                response.raise_for_status()
                return response.json().get("id")
            except requests.RequestException as e:
                error_msg = ""
                if hasattr(e, 'response') and e.response is not None:
                    error_msg = e.response.text
                    # Check if it's a timeout error from Instagram
                    if "Timeout" in error_msg or "2207003" in error_msg:
                        wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                        print(f"Instagram timeout downloading image. Retry {attempt + 1}/{max_retries} in {wait_time}s...")
                        time.sleep(wait_time)
                        continue

                print(f"Error creating media container: {e}")
                if error_msg:
                    print(f"Response: {error_msg}")

                # Don't retry on non-timeout errors
                if attempt == max_retries - 1:
                    return None

        return None

    def publish_media(self, creation_id: str) -> Optional[str]:
        """Publish the media container."""

        url = f"{self.GRAPH_API_URL}/{self.account_id}/media_publish"

        params = {
            "creation_id": creation_id,
            "access_token": self.access_token,
        }

        try:
            response = requests.post(url, data=params, timeout=60)
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
        post_to_story: bool = True,
    ) -> Optional[str]:
        """Post image to Instagram feed and optionally to Story."""

        caption = self.build_caption(weather)

        if dry_run:
            print(f"[DRY RUN] Would post to Instagram for {self.city.name}:")
            print(f"  Image: {image_path}")
            print(f"  Caption: {caption[:100]}...")
            print(f"  Story: {'Yes' if post_to_story else 'No'}")
            return "dry_run_post_id"

        # Step 1: Upload image to public hosting
        print(f"Uploading image to hosting for {self.city.name}...")
        image_url = self.upload_image_to_hosting(image_path)

        if not image_url:
            print(f"Failed to upload image for {self.city.name}")
            return None

        print(f"Image hosted at: {image_url}")

        # Step 2: Wait for image to be fully accessible
        # ImgBB needs a moment before the image is reliably downloadable
        print("Waiting for image to be accessible...")
        time.sleep(5)

        # Step 3: Create media container for FEED (with retry logic)
        print(f"Creating Instagram media container for {self.city.name}...")
        creation_id = self.create_media_container(image_url, caption, media_type="IMAGE")

        if not creation_id:
            print(f"Failed to create media container for {self.city.name}")
            return None

        # Step 4: Wait for Instagram to process the media
        print("Waiting for media processing...")
        time.sleep(10)  # Increased wait time

        # Step 5: Publish to FEED
        print(f"Publishing to Instagram feed for {self.city.name}...")
        post_id = self.publish_media(creation_id)

        if post_id:
            print(f"Instagram feed post published! ID: {post_id}")
        else:
            print(f"Failed to publish to Instagram feed for {self.city.name}")
            return None

        # Step 6: Also post to STORY if enabled
        if post_to_story:
            print(f"Creating Instagram Story for {self.city.name}...")
            story_creation_id = self.create_media_container(image_url, caption, media_type="STORIES")

            if story_creation_id:
                print("Waiting for story processing...")
                time.sleep(5)

                story_id = self.publish_media(story_creation_id)
                if story_id:
                    print(f"Instagram Story published! ID: {story_id}")
                else:
                    print(f"Failed to publish Story (feed post succeeded)")
            else:
                print(f"Failed to create Story container (feed post succeeded)")

        return post_id


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
