## Why

The current post captions for Twitter, Instagram, and TikTok are dry, formulaic readouts of weather data ("🌡️ 25°C / ☁️ Light Rain / 💧 Humidity: 77%"). They read like dashboard output, not like something a human wrote. The images we post are AI-generated literary miniatures — the text accompanying them should match that aesthetic.

We want captions that stand out, catch the eye, and read like elevated prose — short literary vignettes about the weather — while still conveying the actual conditions. We want each post to feel freshly written, not assembled from a template.

## What Changes

- **BREAKING** Replace template-based `build_tweet_text()`, `build_caption()`, `build_description()` methods with AI-generated literary captions via Gemini 2.5 Pro.
- Add a new **notability scoring** layer that analyzes current weather + near-term forecast and picks the single most interesting "angle" for the post (e.g., *rain-clearing-soon*, *sticky-heat*, *first-frost*, *perfect-day*).
- Add a **forecast data fetch** (OpenWeatherMap `/data/2.5/forecast` endpoint, free tier) so captions can reference what's coming next, not just the current snapshot.
- Add a **variable-parameters rotation** per call (literary form, narrator persona, tone, sensory device, seed phrase) so every generation produces a different composition even with identical weather.
- Add an **anti-repetition memory** per city (last N posts' angles/voices/openers) that feeds into generation to steer away from recent patterns.
- Add a **platform-specific voice adaptation**: one Gemini call per platform (Twitter terse, Instagram full, TikTok engaging) — 3 calls per post.
- Add a **template-based fallback**: if Gemini fails or returns invalid output, fall back to a minimal clean template so posts never fail entirely.
- Keep Instagram and TikTok hashtags appended to captions (outside the AI-generated body). Twitter remains hashtag-free.

## Capabilities

### New Capabilities
- `caption-generation`: Orchestrates the full pipeline — fetch forecast, score notability, pick angle, roll variable parameters, invoke Gemini per platform, apply fallback, and return final caption text ready for posting.
- `notability-scoring`: Analyzes weather + forecast data and produces a ranked list of "angles" (notable signals) with a primary angle and supporting facts selected.
- `weather-forecast`: Extends the existing weather capture to include near-term (next 24h) forecast data from OpenWeatherMap.

### Modified Capabilities
<!-- No existing specs exist yet in openspec/specs/; all platform behavior today lives only in code. -->

## Impact

**Code**:
- `src/platforms/twitter.py`: replace `build_tweet_text()` with call into caption generator.
- `src/platforms/instagram.py`: replace `build_caption()` (keep hashtag appending).
- `src/platforms/tiktok.py`: replace `build_description()` (keep hashtag appending).
- `src/weather.py`: extend `WeatherData` with forecast fields; add forecast fetch.
- New module `src/caption_generator.py`: orchestrates notability scoring + Gemini call.
- New module `src/notability.py`: weather analysis / angle picking.
- New module `src/caption_memory.py`: per-city recent-post history.
- New module `src/caption_prompts.py`: system prompt, few-shot examples, variable parameter taxonomy.

**Config**:
- `config/cities.yaml`: optional per-city `character` hint (e.g., "laid-back Caribbean island", "crisp alpine town") passed to Gemini as context.
- New state file `state/caption_history.json` tracking last ~10 posts per city (angle, voice, opener).

**Dependencies**: no new packages — `google-genai` already used for image generation.

**Runtime cost**: ~$3.50/month added for Gemini 2.5 Pro (450 calls × ~4.7k tokens input + ~200 tokens output). Image generation cost (~$6/month) unchanged.

**Failure behavior**: any Gemini failure falls back to a minimal template caption; posting never fails because of caption generation.
