#!/usr/bin/env python3
"""
City Weather Poster - Main orchestration script.

This script handles the full workflow:
1. Select a random city (excluding recently posted)
2. Fetch current weather data
3. Generate image using Nano Banana (Gemini)
4. Post to enabled social media platforms
5. Track the posted city to prevent duplicates
"""

import argparse
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

from dotenv import load_dotenv

from .config import get_config, CityConfig, Config
from .weather import get_weather_for_city, WeatherData
from .image_generator import generate_city_image
from .platforms.twitter import post_to_twitter
from .platforms.instagram import post_to_instagram
from .platforms.tiktok import post_to_tiktok
from .state_manager import StateManager, RecentlyPosted
from .scheduler import select_random_city
from .caption_generator import CaptionGenerator
from .caption_memory import CaptionMemory
from .glitch_log import GlitchLog


def process_city(
    city: CityConfig,
    config: Config,
    caption_generator: CaptionGenerator,
    caption_memory: CaptionMemory,
    glitch_log: GlitchLog,
    dry_run: bool = False,
    output_dir: str = None,
) -> dict:
    """
    Process a single city: fetch weather, generate image, post to platforms.

    Args:
        city: City configuration
        config: Global configuration object
        dry_run: If True, simulate without actually posting
        output_dir: Directory for generated images

    Returns:
        Dict with results for each platform
    """
    results = {
        "city": city.name,
        "city_id": city.id,
        "success": False,
        "weather": None,
        "image_path": None,
        "twitter": None,
        "instagram": None,
        "tiktok": None,
        "error": None,
    }

    print(f"\n{'='*50}")
    print(f"Processing: {city.name}, {city.country}")
    print(f"Timezone: {city.timezone}")
    print(f"{'='*50}")

    # Step 1: Fetch weather
    print("\n📡 Fetching weather data...")
    weather = get_weather_for_city(city)

    if not weather:
        print("❌ Failed to fetch weather data")
        results["error"] = "Weather fetch failed"
        return results

    results["weather"] = {
        "temperature_c": weather.temperature_c,
        "description": weather.description,
        "humidity": weather.humidity,
    }

    print(f"✅ Weather: {weather.description}, {weather.temperature_c:.1f}°C")

    # Step 2: Generate image
    print("\n🎨 Generating image with Nano Banana...")
    image_path = generate_city_image(city, weather, output_dir)

    if not image_path:
        print("❌ Failed to generate image")
        results["error"] = "Image generation failed"
        return results

    results["image_path"] = str(image_path)
    print(f"✅ Image generated: {image_path}")

    # Step 3: Generate literary captions (one per enabled platform)
    print("\n✍️  Generating captions...")
    captions: dict[str, str] = {}
    for platform in ("twitter", "instagram", "tiktok"):
        if getattr(city.platforms, platform):
            captions[platform] = caption_generator.generate(
                city, weather, platform, caption_memory, glitch_log
            )
            preview = captions[platform][:80].replace("\n", " ⏎ ")
            print(f"  {platform}: {preview}{'…' if len(captions[platform]) > 80 else ''}")

    # Persist memory once per city (not once per platform)
    try:
        caption_memory.save()
    except Exception as e:
        print(f"⚠️  Could not save caption memory: {e}")

    # Step 4: Post to platforms
    print("\n📱 Posting to social media...")

    # Twitter/X
    if city.platforms.twitter:
        print("\n🐦 Posting to Twitter/X...")
        twitter_creds = config.get_platform_credentials("twitter")
        results["twitter"] = post_to_twitter(
            city, image_path, weather, twitter_creds,
            caption_body=captions["twitter"],
            dry_run=dry_run,
        )

    # Instagram
    if city.platforms.instagram:
        print("\n📸 Posting to Instagram...")
        instagram_creds = config.get_platform_credentials("instagram")
        results["instagram"] = post_to_instagram(
            city, image_path, weather, instagram_creds,
            caption_body=captions["instagram"],
            dry_run=dry_run,
        )

    # TikTok
    if city.platforms.tiktok:
        print("\n🎵 Posting to TikTok...")
        tiktok_creds = config.get_platform_credentials("tiktok")
        results["tiktok"] = post_to_tiktok(
            city, image_path, weather, tiktok_creds,
            caption_body=captions["tiktok"],
            dry_run=dry_run,
        )

    # Check if any platform succeeded
    platforms_attempted = []
    platforms_succeeded = []

    for platform in ["twitter", "instagram", "tiktok"]:
        if getattr(city.platforms, platform):
            platforms_attempted.append(platform)
            if results[platform]:
                platforms_succeeded.append(platform)

    results["success"] = len(platforms_succeeded) > 0

    print(f"\n📊 Results for {city.name}:")
    print(f"   Platforms attempted: {', '.join(platforms_attempted) or 'None'}")
    print(f"   Platforms succeeded: {', '.join(platforms_succeeded) or 'None'}")

    return results


def main():
    """Main entry point."""

    # Load environment variables from .env file if present
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="City Weather Poster - Generate and post weather images"
    )
    parser.add_argument(
        "--city",
        "-c",
        type=str,
        help="Specific city ID to process (default: random selection)",
    )
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Simulate without actually posting",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        help="Directory for generated images",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to cities.yaml config file",
    )
    parser.add_argument(
        "--list-cities",
        "-l",
        action="store_true",
        help="List all configured cities and exit",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Ignore recently-posted exclusions (post even if city was recent)",
    )

    args = parser.parse_args()

    # Load configuration
    config = get_config(args.config)

    # List cities mode
    if args.list_cities:
        print("\nConfigured Cities:")
        print("-" * 40)
        for city_id, city in config.cities.items():
            status = "✅ Enabled" if city.enabled else "❌ Disabled"
            platforms = []
            if city.platforms.twitter:
                platforms.append("Twitter")
            if city.platforms.instagram:
                platforms.append("Instagram")
            if city.platforms.tiktok:
                platforms.append("TikTok")

            print(f"\n{city_id}:")
            print(f"  Name: {city.name}, {city.country}")
            print(f"  Status: {status}")
            print(f"  Timezone: {city.timezone}")
            print(f"  Weight: {city.weight}")
            print(f"  Platforms: {', '.join(platforms) or 'None'}")
        return 0

    # Validate API keys
    if not config.google_ai_api_key:
        print("❌ Error: GOOGLE_AI_API_KEY not set")
        return 1

    if not config.openweather_api_key:
        print("❌ Error: OPENWEATHER_API_KEY not set")
        return 1

    # Initialize state manager
    state_manager = StateManager()
    recent = state_manager.load_recent()

    # Get excluded city IDs (unless --force is used)
    excluded_ids = [] if args.force else recent.get_excluded_ids()

    if excluded_ids:
        print(f"📋 Recently posted ({len(excluded_ids)} cities): {', '.join(excluded_ids[:5])}{'...' if len(excluded_ids) > 5 else ''}")

    # Determine which city to process
    if args.city:
        # Manual override - process specific city
        city = config.get_city(args.city)
        if not city:
            print(f"❌ Error: City '{args.city}' not found in configuration")
            print(f"Available cities: {', '.join(list(config.cities.keys())[:10])}...")
            return 1
        print(f"\n🎯 Manual selection: {city.name}")
    else:
        # Random selection (excluding recent)
        city = select_random_city(config, excluded_ids)
        if not city:
            print("❌ No cities available for selection")
            return 1
        print(f"\n🎲 Random selection: {city.name}")

    # Validate platform credentials for selected city
    if city.platforms.twitter:
        twitter_creds = config.get_platform_credentials("twitter")
        if not all([twitter_creds.get("api_key"), twitter_creds.get("api_secret"),
                    twitter_creds.get("access_token"), twitter_creds.get("access_token_secret")]):
            print("❌ Error: Twitter credentials incomplete")
            return 1

    if city.platforms.instagram:
        instagram_creds = config.get_platform_credentials("instagram")
        if not all([instagram_creds.get("access_token"), instagram_creds.get("account_id")]):
            print("❌ Error: Instagram credentials incomplete")
            return 1

    if city.platforms.tiktok:
        tiktok_creds = config.get_platform_credentials("tiktok")
        if not tiktok_creds.get("access_token"):
            print("❌ Error: TikTok credentials incomplete")
            return 1

    print(f"\n🌍 City Weather Poster")
    if args.dry_run:
        print("🔸 DRY RUN MODE - No actual posts will be made")
    if args.force:
        print("🔸 FORCE MODE - Ignoring recently-posted exclusions")

    # Shared caption-generation instances (one per run, reused across platforms)
    caption_generator = CaptionGenerator()
    caption_memory = CaptionMemory()
    glitch_log = GlitchLog()

    # Process the city
    try:
        result = process_city(
            city,
            config,
            caption_generator=caption_generator,
            caption_memory=caption_memory,
            glitch_log=glitch_log,
            dry_run=args.dry_run,
            output_dir=args.output_dir,
        )

        # Track successful post (unless dry run)
        if result.get("success") and not args.dry_run:
            recent.add_posted(city.id)
            state_manager.save_recent(recent)
            print(f"\n✅ {city.name} added to recently posted list")

    except Exception as e:
        print(f"❌ Error processing {city.name}: {e}")
        result = {
            "city": city.name,
            "success": False,
            "error": str(e),
        }

    # Summary
    print(f"\n{'='*50}")
    print("📋 SUMMARY")
    print(f"{'='*50}")
    print(f"City: {result.get('city', 'Unknown')}")
    print(f"Success: {'✅ Yes' if result.get('success') else '❌ No'}")
    if result.get("error"):
        print(f"Error: {result['error']}")

    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
