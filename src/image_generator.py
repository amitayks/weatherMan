"""Image generation using Google's Nano Banana (Gemini 2.5 Flash Image)."""

import os
import base64
import random
from pathlib import Path
from typing import Optional
from datetime import datetime

from google import genai
from google.genai import types

from .config import CityConfig, get_config
from .weather import WeatherData


class ImageGenerator:
    """Generate city weather images using Nano Banana (Gemini 2.5 Flash Image)."""
    
    # Model name for Nano Banana (stable GA version)
    MODEL = "gemini-2.5-flash-image"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_config().google_ai_api_key
        if not self.api_key:
            raise ValueError("Google AI API key not configured")
        
        # Initialize the client
        self.client = genai.Client(api_key=self.api_key)

    def get_atmospheric_condition(self, weather: WeatherData) -> str:
        """Map weather data to detailed atmospheric description."""
        condition_lower = weather.main_condition.lower()
        desc_lower = weather.description.lower()

        if 'rain' in condition_lower or 'rain' in desc_lower or 'drizzle' in desc_lower:
            return "Rainy atmosphere - wet surfaces with reflective sheen, puddles on streets and plazas, rain streaks visible in air, darker color saturation on buildings and surfaces, overcast lighting with soft diffused shadows, grey sky, moisture in the air"
        elif 'clear' in condition_lower or ('clear' in desc_lower and 'sky' in desc_lower):
            return "Sunny atmosphere - bright even lighting across entire scene, strong defined shadows cast by buildings and objects, vibrant saturated colors, clear blue sky element visible, warm temperature feel with golden tones, crisp air quality"
        elif 'cloud' in condition_lower:
            return "Cloudy atmosphere - soft diffused lighting throughout scene, muted pastel colors, grey atmospheric tone, no harsh shadows, overcast mood, gentle even illumination"
        elif 'snow' in condition_lower or 'snow' in desc_lower:
            return "Snowy atmosphere - white snow covering roofs and ground surfaces, icicles hanging from eaves, cold blue color tones throughout, winter atmosphere, soft white blanket over scene, crisp winter air feeling"
        elif 'mist' in condition_lower or 'fog' in condition_lower or 'haze' in desc_lower or 'mist' in desc_lower:
            return "Foggy atmosphere - misty haze around buildings, reduced visibility at scene edges, ethereal dreamy quality, soft diffused lighting through fog, mysterious mood"
        else:
            return "Pleasant clear weather - natural balanced lighting, gentle soft shadows, moderate color saturation, comfortable atmosphere"

    def build_prompt(self, city: CityConfig, weather: WeatherData) -> str:
        """Build the comprehensive image generation prompt."""

        # Get weather-specific atmospheric condition
        atmospheric_condition = self.get_atmospheric_condition(weather)

        # Determine window lighting based on weather and time
        is_dark = not weather.is_daytime or 'rain' in weather.description.lower() or 'cloud' in weather.main_condition.lower()
        window_lights = "Interior building lights visible glowing warmly" if is_dark else "Windows reflective, interior lights off for bright day"

        # Randomly select 5-8 landmarks for variety
        num_landmarks = random.randint(5, min(8, len(city.landmarks)))
        selected_landmarks = random.sample(city.landmarks, num_landmarks)
        landmarks_text = "\n".join(f"- {landmark}" for landmark in selected_landmarks)

        # Build the comprehensive prompt
        prompt = f"""Generate a professional 3D isometric miniature diorama city model with weather overlay for {city.name}, {city.country}.

CONCEPT:
Create a charming architectural toy model aesthetic meeting functional weather visualization design. This is a square 1080x1080px social media graphic combining miniature city model craftsmanship with current weather information display.

CITY DIORAMA CONSTRUCTION FOR {city.name}, {city.country}:

Base Structure:
- Rounded rectangular miniature base with beveled wooden-textured edges (approximately 2cm thick appearance)
- Compact city section fitting 3-4 city blocks with efficient use of space
- 45-degree isometric viewing angle, top-down perspective showing all architectural details clearly
- Organic city planning with curved streets, river or waterway if geographically applicable, main landmarks prominently featured in composition

Architectural Elements - Iconic Landmarks and Buildings:
The scene must feature these specific landmarks and architectural elements of {city.name}:
{landmarks_text}

Additional architectural requirements:
- Render 2-4 most iconic structures as detailed miniatures with accurate proportions and recognizable signature features
- Include cluster of characteristic local architecture: row houses, apartments, historic buildings in authentic regional style
- Roof details with appropriate materials: terracotta clay tiles, slate, copper patina, or region-appropriate roofing with realistic texture and color
- Tiny individual windows with subtle reflections and interior lighting glow, properly scaled
- Miniature street-level doors and entrances with architectural detail and character
- Architectural style must be authentic to {city.name}'s historical period and cultural aesthetic

Urban Infrastructure:
- Streets with realistic texture (cobblestone, asphalt, or appropriate paving) with proper street grid or historically-accurate layout
- Central squares and plazas with miniature paving patterns, small monuments, fountains as landmarks
- If city features iconic bridges: include them with detailed stone or metal construction
- If city has waterways: render rivers, canals, or harbors with realistic water texture showing gentle ripples, reflections, and subtle movement indication
- If applicable: tiny boats, gondolas, ferries, or watercraft appropriate to the city rendered at miniature scale with details

Landscape Elements:
- Miniature stylized trees with round puffy foliage in appropriate green shades, cartoon-style appearance but realistic texture quality
- Parks and green spaces with grass texture, pathways, organized landscaping elements
- Topographical variation if city is hilly: elevated areas with terracing, slopes with buildings following terrain
- Vegetation details: bushes, garden areas, tree-lined streets with appropriate seasonal coloring for current date

Miniature People & Vehicles:
- Tiny human figures at 2-3mm scale scattered naturally throughout streets and squares (approximately 20-30 people visible)
- Miniature vehicles: cars, trams, buses appropriate to {city.name} - simplified forms but recognizable, proper colors (approximately 5-10 vehicles)
- If city has waterways: small boats, tourist vessels, gondolas, ferries at appropriate scale
- Density: populated but not crowded, creating authentic lived-in feeling without clutter

CURRENT WEATHER INTEGRATION:
Weather condition: {weather.description}
Temperature: {weather.format_temperature('C')}

Atmospheric Condition to Apply:
{atmospheric_condition}

Lighting Adaptation:
- Time of day atmosphere: {weather.time_of_day}
- {window_lights}
- Overall scene brightness and color temperature adapting to weather mood and conditions
- Shadow quality matching weather: soft for cloudy/rainy, defined for sunny, minimal for foggy

TEXT OVERLAY SYSTEM - CRITICAL TYPOGRAPHY REQUIREMENTS:
All text elements must be clearly legible with high contrast against the background.

1. CITY NAME (Primary Header):
   Content: "{city.name}, {city.country}"
   Typography: BOLD SANS-SERIF font (Montserrat Bold style or similar), ALL CAPITALS
   Color: Dark gray #3D4A5C
   Size: Large 72-80pt equivalent
   Position: Top-center of image, 80-100px from top edge
   Style: Generous letter-spacing for modern clean aesthetic

2. WEATHER ICON (Visual Weather Indicator):
   Content: Simple line-art weather icon representing: {weather.emoji}
   Style: Minimalist outlined icon design with 3-4px stroke weight
   Color: Dark gray #3D4A5C matching text
   Size: Approximately 120x120px
   Position: Directly below city name, horizontally centered, 20px gap from name

3. DATE (Temporal Information):
   Content: "{weather.format_date('%B %d, %Y')}"
   Typography: Regular sans-serif font (Montserrat Regular style or similar), sentence case
   Color: Dark gray #3D4A5C
   Size: Small 28-32pt equivalent
   Position: To the right of weather icon, vertically aligned with top of icon
   Alignment: Left-aligned starting 15px from icon's right edge

4. TEMPERATURE (Weather Data):
   Content: "{weather.format_temperature('C')}"
   Typography: Regular sans-serif font (Montserrat Regular style or similar)
   Color: Dark gray #3D4A5C
   Size: Medium 48-52pt equivalent
   Position: Below date text, left-aligned with date
   Spacing: 10px gap below date line

Text Hierarchy and Layout Rules:
- Text elements may subtly overlap the tops of the tallest buildings to suggest depth integration
- All text must remain clearly legible - no buildings obscuring critical text information
- Text occupies approximately the top 25% of the image composition
- Diorama model occupies the remaining 75% of the image composition
- Maintain visual balance between text information and miniature city model

OUTPUT SPECIFICATIONS:
- Exact dimensions: Square 1080x1080 pixels
- High quality rendering with anti-aliasing and smooth textures
- Professional finish suitable for social media posting on Instagram, Twitter, TikTok
- Consistent lighting across entire scene matching weather conditions
- Polished miniature model aesthetic with realistic PBR materials"""

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
