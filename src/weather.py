"""OpenWeatherMap API integration for fetching current weather data."""

import requests
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import pytz

from .config import CityConfig, get_config


# Weather condition to emoji mapping
WEATHER_ICONS = {
    "clear sky": "☀️",
    "few clouds": "🌤️",
    "scattered clouds": "⛅",
    "broken clouds": "🌥️",
    "overcast clouds": "☁️",
    "shower rain": "🌧️",
    "rain": "🌧️",
    "light rain": "🌦️",
    "moderate rain": "🌧️",
    "heavy rain": "⛈️",
    "thunderstorm": "⛈️",
    "snow": "🌨️",
    "light snow": "🌨️",
    "heavy snow": "❄️",
    "mist": "🌫️",
    "fog": "🌫️",
    "haze": "🌫️",
    "dust": "🌪️",
    "smoke": "🌫️",
    "drizzle": "🌧️",
}

# Weather condition keywords for prompt enhancement
WEATHER_ATMOSPHERE = {
    "clear": "bright sunshine, crisp shadows, blue sky",
    "clouds": "soft diffused light, cloudy sky, gentle shadows",
    "rain": "wet streets, rain droplets, puddle reflections, grey sky",
    "drizzle": "light mist, wet surfaces, overcast atmosphere",
    "thunderstorm": "dramatic dark clouds, lightning in the distance, stormy atmosphere",
    "snow": "snow-covered roofs and streets, soft white blanket, winter wonderland",
    "mist": "mysterious fog, soft diffused light, atmospheric haze",
    "fog": "thick fog partially obscuring buildings, moody atmosphere",
    "haze": "hazy atmosphere, soft sunlight filtering through",
}


@dataclass
class WeatherData:
    """Weather data container."""
    city_name: str
    country: str
    temperature_c: float
    temperature_f: float
    feels_like_c: float
    feels_like_f: float
    humidity: int
    description: str
    main_condition: str
    icon_code: str
    wind_speed: float  # m/s
    clouds_percent: int
    timestamp: datetime
    sunrise: datetime
    sunset: datetime
    
    @property
    def emoji(self) -> str:
        """Get weather emoji based on description."""
        desc_lower = self.description.lower()
        for key, emoji in WEATHER_ICONS.items():
            if key in desc_lower:
                return emoji
        # Fallback based on main condition
        main_lower = self.main_condition.lower()
        if "clear" in main_lower:
            return "☀️"
        elif "cloud" in main_lower:
            return "☁️"
        elif "rain" in main_lower:
            return "🌧️"
        elif "snow" in main_lower:
            return "🌨️"
        return "🌡️"
    
    @property
    def atmosphere_prompt(self) -> str:
        """Get atmospheric description for image generation prompt."""
        main_lower = self.main_condition.lower()
        for key, atmosphere in WEATHER_ATMOSPHERE.items():
            if key in main_lower or key in self.description.lower():
                return atmosphere
        return "pleasant weather, natural lighting"
    
    @property
    def is_daytime(self) -> bool:
        """Check if current time is between sunrise and sunset."""
        return self.sunrise <= self.timestamp <= self.sunset
    
    @property
    def time_of_day(self) -> str:
        """Get time of day description for prompt."""
        if not self.is_daytime:
            return "nighttime scene with city lights glowing, stars in the sky"
        
        hour = self.timestamp.hour
        if 5 <= hour < 8:
            return "early morning golden hour, warm sunrise light"
        elif 8 <= hour < 11:
            return "bright morning light, crisp atmosphere"
        elif 11 <= hour < 14:
            return "midday sun, strong overhead lighting"
        elif 14 <= hour < 17:
            return "afternoon light, warm tones"
        elif 17 <= hour < 20:
            return "golden hour sunset, warm orange and pink sky"
        else:
            return "twilight, city transitioning to night"
    
    def format_temperature(self, unit: str = "C") -> str:
        """Format temperature string."""
        if unit.upper() == "F":
            return f"{self.temperature_f:.0f}°F"
        return f"{self.temperature_c:.0f}°C"
    
    def format_date(self, format_str: str = "%B %d, %Y") -> str:
        """Format date string."""
        return self.timestamp.strftime(format_str)


class WeatherAPI:
    """OpenWeatherMap API client."""
    
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_config().openweather_api_key
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key not configured")
    
    def get_weather(self, city: CityConfig) -> Optional[WeatherData]:
        """Fetch current weather for a city."""
        try:
            params = {
                "lat": city.coordinates.lat,
                "lon": city.coordinates.lon,
                "appid": self.api_key,
                "units": "metric",  # Get Celsius
            }
            
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Parse timestamps with city's timezone
            tz = city.tz
            now = datetime.now(tz)
            sunrise = datetime.fromtimestamp(data["sys"]["sunrise"], tz)
            sunset = datetime.fromtimestamp(data["sys"]["sunset"], tz)
            
            # Convert Celsius to Fahrenheit
            temp_c = data["main"]["temp"]
            feels_like_c = data["main"]["feels_like"]
            
            return WeatherData(
                city_name=city.name,
                country=city.country,
                temperature_c=temp_c,
                temperature_f=(temp_c * 9/5) + 32,
                feels_like_c=feels_like_c,
                feels_like_f=(feels_like_c * 9/5) + 32,
                humidity=data["main"]["humidity"],
                description=data["weather"][0]["description"],
                main_condition=data["weather"][0]["main"],
                icon_code=data["weather"][0]["icon"],
                wind_speed=data["wind"]["speed"],
                clouds_percent=data["clouds"]["all"],
                timestamp=now,
                sunrise=sunrise,
                sunset=sunset,
            )
            
        except requests.RequestException as e:
            print(f"Error fetching weather for {city.name}: {e}")
            return None
        except (KeyError, ValueError) as e:
            print(f"Error parsing weather data for {city.name}: {e}")
            return None


def get_weather_for_city(city: CityConfig) -> Optional[WeatherData]:
    """Convenience function to get weather for a city."""
    api = WeatherAPI()
    return api.get_weather(city)
