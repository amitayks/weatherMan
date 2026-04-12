"""Caption generator — notability → Gemini → post (always).

Single Gemini call per caption. Validation is diagnostic only: stylistic
slips (cliché, missing temperature, missing condition) are *recorded* in
the glitch log and the caption is posted anyway. The period-voice fallback
runs only when Gemini returns nothing at all (empty response or exception).

Entry point: ``CaptionGenerator.generate(city, weather, platform, memory,
glitch_log)``. Never raises; always returns a usable caption string.
"""

import logging
import re
from typing import Optional

from google import genai
from google.genai import types

from .config import CityConfig, get_config
from .weather import WeatherData
from .notability import score_notability
from .caption_memory import CaptionMemory
from .caption_prompts import (
    FORBIDDEN_CLICHES,
    build_period_fallback,
    build_system_prompt,
    build_user_prompt,
    roll_parameters,
)
from .glitch_log import GlitchLog


logger = logging.getLogger("caption_generator")


SUPPORTED_PLATFORMS = ("twitter", "instagram", "tiktok")


# Temperature references: number + anchor (°, celsius, fahrenheit) OR the word "degree".
_TEMP_PATTERN = re.compile(
    r"\d+\s*(?:°|celsius|fahrenheit)|degree",
    re.IGNORECASE,
)

# Qualitative temperature descriptors that count as a temperature reference.
_TEMP_WORDS = {
    "muggy", "freezing", "crisp", "balmy", "sweltering", "chilly",
    "frigid", "icy", "scorching", "brisk", "frosty", "sultry", "steamy",
    "sticky", "humid", "minus",
}

# Condition synonyms — accepted as evidence the caption references weather.
_CONDITION_SYNONYMS = {
    "sun", "sunny", "sunlight", "sunshine", "cloud", "cloudy", "clouds",
    "overcast", "rain", "raining", "rainy", "drizzle", "shower", "storm",
    "stormy", "thunder", "lightning", "snow", "snowy", "snowfall",
    "fog", "foggy", "mist", "misty", "haze", "hazy", "clear", "sky",
    "breeze", "breezy", "gust", "wind", "windy",
}


class CaptionGenerator:
    """Generates period-voice captions for Twitter / Instagram / TikTok."""

    MODEL = "gemini-2.5-pro"
    # Gemini 2.5 Pro spends tokens on internal thinking; the budget must hold
    # (thinking + caption) or the caption comes back empty.
    MAX_OUTPUT_TOKENS = 2048
    THINKING_BUDGET = 512
    TIMEOUT_MS = 30_000
    TEMPERATURE = 0.9

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_config().google_ai_api_key
        if not self.api_key:
            raise ValueError("Google AI API key not configured")
        self.client = genai.Client(api_key=self.api_key)

    def generate(
        self,
        city: CityConfig,
        weather: WeatherData,
        platform: str,
        memory: Optional[CaptionMemory] = None,
        glitch_log: Optional[GlitchLog] = None,
    ) -> str:
        """Return a caption for the given platform. Never raises.

        Style slips are logged to ``glitch_log`` (if provided) but do not block
        posting. Only hard failures (empty Gemini response or exception) trigger
        the period-voice template fallback.
        """
        platform_key = platform.lower()
        if platform_key not in SUPPORTED_PLATFORMS:
            logger.warning("Unknown platform %r; using fallback", platform)
            return build_period_fallback(
                city_name=city.name,
                temperature_c=weather.temperature_c,
                main_condition=weather.main_condition,
                description=weather.description,
            )

        recent_angles = memory.get_recent_angles(city.id, n=5) if memory else []
        notability = score_notability(weather, recent_angles=recent_angles)
        params = roll_parameters()
        recent_history = memory.get_recent(city.id, n=10) if memory else []
        character = getattr(city, "character", "") or None

        system_prompt = build_system_prompt(platform_key)
        user_prompt = build_user_prompt(
            notability=notability,
            params=params,
            recent_history=recent_history,
            character=character,
        )

        caption = self._try_generate(system_prompt, user_prompt, platform_key)

        if caption is None:
            # Hard failure: empty response, timeout, or exception.
            if glitch_log is not None:
                glitch_log.record(
                    city=city.id,
                    platform=platform_key,
                    caption="",
                    slip="hard_failure",
                    angle=notability.primary_angle,
                    main_condition=weather.main_condition,
                    temp_c=weather.temperature_c,
                    params=params,
                )
            logger.info("Hard failure from Gemini — using period-voice fallback for %s/%s",
                        city.id, platform_key)
            return build_period_fallback(
                city_name=city.name,
                temperature_c=weather.temperature_c,
                main_condition=weather.main_condition,
                description=weather.description,
            )

        # Sensor-only validation: record the slip but return the caption anyway.
        slip, detail = self._diagnose(caption, weather)
        if slip is not None and glitch_log is not None:
            glitch_log.record(
                city=city.id,
                platform=platform_key,
                caption=caption,
                slip=slip,
                detail=detail,
                angle=notability.primary_angle,
                main_condition=weather.main_condition,
                temp_c=weather.temperature_c,
                params=params,
            )

        if memory is not None:
            first_three = " ".join(caption.split()[:3])
            memory.add_entry(
                city_id=city.id,
                angle=notability.primary_angle,
                literary_form=params["literary_form"],
                narrator=params["narrator"],
                tone=params["tone"],
                first_three_words=first_three,
            )

        return caption

    # ── internals ──────────────────────────────────────────────────────

    def _try_generate(
        self,
        system_prompt: str,
        user_prompt: str,
        platform: str,
    ) -> Optional[str]:
        """Single Gemini call. Returns cleaned caption text or None on any failure."""
        try:
            logger.debug("--- Gemini request [%s] ---", platform)
            logger.debug("SYSTEM:\n%s", system_prompt)
            logger.debug("USER:\n%s", user_prompt)

            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=self.MAX_OUTPUT_TOKENS,
                temperature=self.TEMPERATURE,
                thinking_config=types.ThinkingConfig(thinking_budget=self.THINKING_BUDGET),
                http_options=types.HttpOptions(timeout=self.TIMEOUT_MS),
            )
            response = self.client.models.generate_content(
                model=self.MODEL,
                contents=user_prompt,
                config=config,
            )

            text = self._extract_text(response)
            if not text:
                logger.warning("Empty caption from Gemini for %s", platform)
                return None

            logger.debug("RESPONSE:\n%s", text)
            return text.strip().strip('"').strip("'").strip()

        except Exception as e:
            logger.warning("Gemini generate failed for %s: %s", platform, e)
            return None

    def _extract_text(self, response) -> str:
        """Pull text out of the google-genai response object, tolerant of shape."""
        if getattr(response, "text", None):
            return response.text
        candidates = getattr(response, "candidates", None) or []
        for cand in candidates:
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                if getattr(part, "text", None):
                    return part.text
        return ""

    def _diagnose(
        self,
        caption: str,
        weather: WeatherData,
    ) -> tuple[Optional[str], str]:
        """Return (slip_code, detail) if the caption has a style issue, else (None, "").

        Checks: forbidden clichés, temperature reference, condition reference.
        Length is intentionally not checked — the user's posting accounts accept
        arbitrary lengths, and trimming Gemini's output would damage the voice.
        """
        lower = caption.lower()

        for cliche in FORBIDDEN_CLICHES:
            if cliche in lower:
                logger.info("Caption contained banned cliché: %r", cliche)
                return "cliche", cliche.strip()

        has_temp = bool(_TEMP_PATTERN.search(lower)) or any(w in lower for w in _TEMP_WORDS)
        if not has_temp:
            logger.info("Caption lacks temperature reference")
            return "missing_temp", ""

        has_condition = any(s in lower for s in _CONDITION_SYNONYMS)
        if not has_condition:
            desc_tokens = [
                t.lower().strip(",.;:")
                for t in weather.description.split()
                if len(t) > 3
            ]
            if desc_tokens:
                has_condition = any(t in lower for t in desc_tokens)
        if not has_condition:
            logger.info(
                "Caption lacks condition reference for %r",
                weather.description,
            )
            return "missing_condition", weather.description

        return None, ""
