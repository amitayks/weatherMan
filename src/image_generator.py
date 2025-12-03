"""Image generation using Google's Nano Banana (Gemini 2.5 Flash Image)."""

import os
import base64
from pathlib import Path
from typing import Optional
from datetime import datetime

from google import genai
from google.genai import types

from .config import CityConfig, get_config
from .weather import WeatherData


class ImageGenerator:
    """Generate city weather images using Nano Banana (Gemini 2.5 Flash Image)."""
    
    # Model name for Nano Banana
    MODEL = "gemini-2.5-flash-image-preview"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_config().google_ai_api_key
        if not self.api_key:
            raise ValueError("Google AI API key not configured")
        
        # Initialize the client
        self.client = genai.Client(api_key=self.api_key)
    
    def build_prompt(self, city: CityConfig, weather: WeatherData) -> str:
        """Build the image generation prompt."""
        
        # Format the date
        date_str = weather.format_date("%B %d, %Y")
        
        # Build the comprehensive prompt
        prompt = f"""Present a clear, 45° top-down isometric miniature 3D cartoon scene of {city.name}, featuring its most iconic landmarks and architectural elements.

LANDMARKS TO INCLUDE:
{city.landmarks}

STYLE REQUIREMENTS:
- Use soft, refined textures with realistic PBR materials
- Gentle, lifelike lighting and shadows
- Clean, minimalistic composition
- Soft, solid-colored background (subtle gradient acceptable)

CURRENT WEATHER CONDITIONS TO INTEGRATE:
- Weather: {weather.description}
- {weather.atmosphere_prompt}
- Time of day: {weather.time_of_day}
- Temperature feel: {"warm" if weather.temperature_c > 25 else "cool" if weather.temperature_c < 15 else "mild"}

TEXT OVERLAY (must be clearly legible):
- At the top-center, place the title "{city.name}" in large bold text
- Below the title: a prominent weather icon {weather.emoji}
- Below the icon: the date "{date_str}" in small text
- Below the date: the temperature "{weather.format_temperature('C')}" in medium text

TEXT STYLING:
- All text must be centered with consistent spacing
- Text may subtly overlap the tops of the buildings
- Use a clean, modern sans-serif font
- Ensure high contrast for readability

OUTPUT:
- Square 1080x1080 dimension
- High quality, suitable for social media posting"""

        return prompt
    
    def generate_image(
        self, 
        city: CityConfig, 
        weather: WeatherData,
        output_dir: str = None,
    ) -> Optional[Path]:
        """Generate a weather image for the city."""
        
        # Build the prompt
        prompt = self.build_prompt(city, weather)
        
        print(f"Generating image for {city.name}...")
        print(f"Weather: {weather.description}, {weather.temperature_c:.1f}°C")
        
        try:
            # Generate the image using Nano Banana
            response = self.client.models.generate_content(
                model=self.MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["image", "text"],
                )
            )
            
            # Extract the image from the response
            image_data = None

            # Debug: Check what we got back
            print(f"Response candidates: {len(response.candidates)}")
            if response.candidates:
                print(f"Parts in response: {len(response.candidates[0].content.parts)}")
                for i, part in enumerate(response.candidates[0].content.parts):
                    print(f"Part {i}: has inline_data={part.inline_data is not None}, text={part.text is not None if hasattr(part, 'text') else 'N/A'}")
                    if part.inline_data is not None:
                        image_data = part.inline_data.data
                        print(f"Found image data in part {i}")
                        break

            if image_data is None:
                print(f"No image generated for {city.name}")
                print(f"Full response: {response}")
                return None
            
            # Determine output path
            if output_dir is None:
                output_dir = Path(__file__).parent.parent / "output"
            else:
                output_dir = Path(output_dir)
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{city.id}_{timestamp}.png"
            output_path = output_dir / filename
            
            # Save the image
            image_bytes = base64.b64decode(image_data) if isinstance(image_data, str) else image_data
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            
            print(f"Image saved: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Error generating image for {city.name}: {e}")
            return None
    
    def generate_with_retry(
        self,
        city: CityConfig,
        weather: WeatherData,
        max_attempts: int = 3,
        output_dir: str = None,
    ) -> Optional[Path]:
        """Generate image with retry logic."""
        
        config = get_config()
        max_attempts = max_attempts or config.global_config.retry_max_attempts
        
        for attempt in range(1, max_attempts + 1):
            print(f"Attempt {attempt}/{max_attempts} for {city.name}")
            
            result = self.generate_image(city, weather, output_dir)
            if result is not None:
                return result
            
            if attempt < max_attempts:
                import time
                delay = config.global_config.retry_delay_seconds
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
        
        print(f"Failed to generate image for {city.name} after {max_attempts} attempts")
        return None


def generate_city_image(
    city: CityConfig, 
    weather: WeatherData,
    output_dir: str = None,
) -> Optional[Path]:
    """Convenience function to generate an image for a city."""
    generator = ImageGenerator()
    return generator.generate_with_retry(city, weather, output_dir=output_dir)
