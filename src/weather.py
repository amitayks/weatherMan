"""OpenWeatherMap API integration for fetching current weather data."""

import requests
from dataclasses import dataclass, field
from typing import Optional, Literal
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
class ForecastEntry:
    """Single 3-hour forecast entry from OpenWeatherMap."""
    timestamp: datetime
    temperature_c: float
    feels_like_c: float
    humidity: int
    main_condition: str
    description: str
    clouds_percent: int
    wind_speed: float
    precipitation_mm: float  # rain + snow over this 3h window


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
    forecast_entries: list[ForecastEntry] = field(default_factory=list)
    
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
    
    @property
    def precipitation_next_6h(self) -> float:
        """Sum of precipitation_mm for the next 2 forecast entries (~6 hours)."""
        return sum(e.precipitation_mm for e in self.forecast_entries[:2])

    @property
    def temp_trend_6h(self) -> Literal["rising", "falling", "steady"]:
        """Direction of temperature change over the next ~6 hours."""
        if len(self.forecast_entries) < 2:
            return "steady"
        future_temp = self.forecast_entries[1].temperature_c
        delta = future_temp - self.temperature_c
        if abs(delta) < 2:
            return "steady"
        return "rising" if delta > 0 else "falling"

    @property
    def next_condition_change(self) -> Optional[tuple]:
        """First forecast entry whose main_condition differs from current, or None."""
        for entry in self.forecast_entries:
            if entry.main_condition != self.main_condition:
                return (entry.timestamp, entry.main_condition)
        return None

    @property
    def max_temp_24h(self) -> float:
        """Max temperature across current + forecast entries."""
        if not self.forecast_entries:
            return self.temperature_c
        return max(self.temperature_c, *(e.temperature_c for e in self.forecast_entries))

    @property
    def min_temp_24h(self) -> float:
        """Min temperature across current + forecast entries."""
        if not self.forecast_entries:
            return self.temperature_c
        return min(self.temperature_c, *(e.temperature_c for e in self.forecast_entries))

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
    FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_config().openweather_api_key
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key not configured")

    def get_forecast(self, city: CityConfig) -> list[ForecastEntry]:
        """Fetch 24-hour forecast (8 × 3-hour entries) for a city.

        Returns empty list on failure so callers can degrade gracefully.
        """
        try:
            params = {
                "lat": city.coordinates.lat,
                "lon": city.coordinates.lon,
                "appid": self.api_key,
                "units": "metric",
                "cnt": 8,
            }
            response = requests.get(self.FORECAST_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            tz = city.tz
            entries: list[ForecastEntry] = []
            for item in data.get("list", []):
                try:
                    ts = datetime.fromtimestamp(item["dt"], tz)
                    main = item.get("main", {})
                    weather = (item.get("weather") or [{}])[0]
                    clouds = item.get("clouds", {}) or {}
                    wind = item.get("wind", {}) or {}
                    rain = item.get("rain", {}) or {}
                    snow = item.get("snow", {}) or {}

                    precip = float(rain.get("3h", 0) or 0) + float(snow.get("3h", 0) or 0)

                    entries.append(ForecastEntry(
                        timestamp=ts,
                        temperature_c=float(main.get("temp", 0)),
                        feels_like_c=float(main.get("feels_like", main.get("temp", 0))),
                        humidity=int(main.get("humidity", 0)),
                        main_condition=weather.get("main", ""),
                        description=weather.get("description", ""),
                        clouds_percent=int(clouds.get("all", 0)),
                        wind_speed=float(wind.get("speed", 0)),
                        precipitation_mm=precip,
                    ))
                except (KeyError, ValueError, TypeError) as e:
                    print(f"Skipping malformed forecast entry for {city.name}: {e}")
                    continue

            return entries

        except requests.RequestException as e:
            print(f"Error fetching forecast for {city.name}: {e}")
            return []
        except (KeyError, ValueError) as e:
            print(f"Error parsing forecast for {city.name}: {e}")
            return []
    
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
    """Convenience function to get weather (current + forecast) for a city."""
    api = WeatherAPI()
    weather = api.get_weather(city)
    if weather is None:
        return None
    weather.forecast_entries = api.get_forecast(city)
    return weather
