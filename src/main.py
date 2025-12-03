#!/usr/bin/env python3
"""
City Weather Poster - Main orchestration script.

This script handles the full workflow:
1. Load configuration for specified city/cities
2. Fetch current weather data
3. Generate image using Nano Banana (Gemini)
4. Post to enabled social media platforms
"""

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytz
from dotenv import load_dotenv

from .config import get_config, CityConfig
from .weather import get_weather_for_city, WeatherData
from .image_generator import generate_city_image
from .platforms.twitter import post_to_twitter
from .platforms.instagram import post_to_instagram
from .platforms.tiktok import post_to_tiktok


def should_post_now(city: CityConfig, tolerance_minutes: int = 30) -> bool:
    """
    Check if current time is within posting window for the city.
    
    Args:
        city: City configuration
        tolerance_minutes: Minutes before/after scheduled time to allow posting
    
    Returns:
        True if within a posting window
    """
    now = datetime.now(city.tz)
    current_time = now.strftime("%H:%M")
    current_minutes = now.hour * 60 + now.minute
    
    for posting_time in city.posting_times:
        try:
            pt_hour, pt_minute = map(int, posting_time.split(":"))
            pt_minutes = pt_hour * 60 + pt_minute
            
            # Check if within tolerance window
            diff = abs(current_minutes - pt_minutes)
            # Handle midnight wraparound
            diff = min(diff, 1440 - diff)
            
            if diff <= tolerance_minutes:
                return True
        except ValueError:
            print(f"Invalid posting time format: {posting_time}")
            continue
    
    return False


def process_city(
    city: CityConfig,
    config: Config,
    dry_run: bool = False,
    force: bool = False,
    output_dir: str = None,
) -> dict:
    """
    Process a single city: fetch weather, generate image, post to platforms.

    Args:
        city: City configuration
        config: Global configuration object
        dry_run: If True, simulate without actually posting
        force: If True, post regardless of scheduled time
        output_dir: Directory for generated images

    Returns:
        Dict with results for each platform
    """
    results = {
        "city": city.name,
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
    
    # Check posting time (unless forced)
    if not force and not should_post_now(city):
        now = datetime.now(city.tz)
        print(f"Current time: {now.strftime('%H:%M')} ({city.timezone})")
        print(f"Scheduled times: {', '.join(city.posting_times)}")
        print("Not within posting window. Skipping.")
        results["error"] = "Not within posting window"
        return results
    
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
    
    # Step 3: Post to platforms
    print("\n📱 Posting to social media...")

    # Twitter/X
    if city.platforms.twitter:
        print("\n🐦 Posting to Twitter/X...")
        twitter_creds = config.get_platform_credentials("twitter")
        results["twitter"] = post_to_twitter(city, image_path, weather, twitter_creds, dry_run)

    # Instagram
    if city.platforms.instagram:
        print("\n📸 Posting to Instagram...")
        instagram_creds = config.get_platform_credentials("instagram")
        results["instagram"] = post_to_instagram(city, image_path, weather, instagram_creds, dry_run)

    # TikTok
    if city.platforms.tiktok:
        print("\n🎵 Posting to TikTok...")
        tiktok_creds = config.get_platform_credentials("tiktok")
        results["tiktok"] = post_to_tiktok(city, image_path, weather, tiktok_creds, dry_run)
    
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
        help="Specific city ID to process (default: all enabled cities)",
    )
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Simulate without actually posting",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Post regardless of scheduled time",
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
            print(f"  Posting times: {', '.join(city.posting_times)}")
            print(f"  Platforms: {', '.join(platforms) or 'None'}")
        return 0
    
    # Validate API keys
    if not config.google_ai_api_key:
        print("❌ Error: GOOGLE_AI_API_KEY not set")
        return 1

    if not config.openweather_api_key:
        print("❌ Error: OPENWEATHER_API_KEY not set")
        return 1

    # Validate platform credentials
    # Check which platforms are enabled across all cities
    needs_twitter = any(city.platforms.twitter for city in config.get_enabled_cities())
    needs_instagram = any(city.platforms.instagram for city in config.get_enabled_cities())
    needs_tiktok = any(city.platforms.tiktok for city in config.get_enabled_cities())

    if needs_twitter:
        twitter_creds = config.get_platform_credentials("twitter")
        if not all([twitter_creds.get("api_key"), twitter_creds.get("api_secret"),
                    twitter_creds.get("access_token"), twitter_creds.get("access_token_secret")]):
            print("❌ Error: Twitter credentials incomplete")
            print("   Required: TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET")
            return 1

    if needs_instagram:
        instagram_creds = config.get_platform_credentials("instagram")
        if not all([instagram_creds.get("access_token"), instagram_creds.get("account_id")]):
            print("❌ Error: Instagram credentials incomplete")
            print("   Required: INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_ACCOUNT_ID")
            return 1

    if needs_tiktok:
        tiktok_creds = config.get_platform_credentials("tiktok")
        if not tiktok_creds.get("access_token"):
            print("❌ Error: TikTok credentials incomplete")
            print("   Required: TIKTOK_ACCESS_TOKEN")
            return 1

    # Determine which cities to process
    if args.city:
        city = config.get_city(args.city)
        if not city:
            print(f"❌ Error: City '{args.city}' not found in configuration")
            print(f"Available cities: {', '.join(config.cities.keys())}")
            return 1
        cities_to_process = [city]
    else:
        cities_to_process = config.get_enabled_cities()
    
    if not cities_to_process:
        print("No cities to process")
        return 0
    
    print(f"🌍 City Weather Poster")
    print(f"Processing {len(cities_to_process)} city/cities")
    if args.dry_run:
        print("🔸 DRY RUN MODE - No actual posts will be made")
    if args.force:
        print("🔸 FORCE MODE - Ignoring scheduled times")
    
    # Process each city
    all_results = []
    
    for city in cities_to_process:
        try:
            result = process_city(
                city,
                config,
                dry_run=args.dry_run,
                force=args.force,
                output_dir=args.output_dir,
            )
            all_results.append(result)
        except Exception as e:
            print(f"❌ Error processing {city.name}: {e}")
            all_results.append({
                "city": city.name,
                "success": False,
                "error": str(e),
            })
    
    # Summary
    print(f"\n{'='*50}")
    print("📋 SUMMARY")
    print(f"{'='*50}")
    
    successful = [r for r in all_results if r.get("success")]
    failed = [r for r in all_results if not r.get("success")]
    
    print(f"Total cities processed: {len(all_results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed/Skipped: {len(failed)}")
    
    if failed:
        print("\nFailed/Skipped cities:")
        for r in failed:
            print(f"  - {r['city']}: {r.get('error', 'Unknown error')}")
    
    # Return non-zero if all failed
    return 0 if successful or not cities_to_process else 1


if __name__ == "__main__":
    sys.exit(main())
