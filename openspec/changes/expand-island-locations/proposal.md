# Proposal: Expand Island Locations

**Change ID:** `expand-island-locations`
**Status:** Proposal
**Created:** 2026-01-10

## Overview

Expand the WeatherNews city list from the current 35 major cities to include 200 unique island and remote locations from around the world. These locations will showcase truly unique destinations that many people have never visited, providing exotic and visually stunning weather content for social media.

## Goals

1. **Expand Location Coverage**: Increase total locations from 35 to 200+ by adding 165+ island and remote destinations
2. **Global Diversity**: Include islands from all major regions (Pacific, Caribbean, Mediterranean, Indian Ocean, Arctic, etc.)
3. **Visual Uniqueness**: Select locations with distinctive landmarks, architecture, and natural features that create compelling miniature diorama scenes
4. **Maintain Quality**: Ensure each location has 12-20 detailed landmark descriptions for variety in image generation
5. **Phased Rollout**: Start with 200 locations and provide framework for future expansion

## Why

The current city list focuses on major metropolitan areas (Tokyo, New York, Paris, etc.). While these are popular, they lack the exotic appeal of remote islands and unique destinations. By adding island locations:

- **Unique Visual Content**: Islands offer distinctive natural features (volcanic landscapes, coral reefs, unique rock formations)
- **Unexplored Destinations**: Most users have never visited these locations, creating novelty and discovery
- **Diverse Weather Patterns**: Islands have unique microclimates and weather phenomena
- **Travel Inspiration**: Content appeals to wanderlust and travel planning audiences
- **Reduced Competition**: Less saturated content space compared to major cities

This expansion addresses user feedback requesting more diverse and exotic weather content beyond major metropolitan areas.

## Scope

### In Scope

- Curating list of 200 unique island and remote locations worldwide
- Creating detailed landmark lists (12-20 items) for each location
- Updating `cities.yaml` configuration with new locations
- Ensuring geographic coordinates and timezone accuracy
- Adding region-appropriate hashtags for each location
- Documenting location selection criteria

### Out of Scope

- Modifying core image generation algorithms (existing system handles varied locations)
- Changing posting schedule logic (existing timezone-aware system works)
- Updating social media platform integrations (no changes needed)
- Implementing location-specific weather data sources (OpenWeatherMap covers all locations)

## User Impact

### Content Creators (Primary Users)

- **Benefit**: Access to 200 unique locations for daily content creation
- **Effort**: Minimal - just enable desired locations in configuration
- **Change**: Significantly expanded location options in `cities.yaml`

### Social Media Audiences

- **Benefit**: More diverse and exotic weather content
- **Discovery**: Exposure to unique destinations they may not know about
- **Engagement**: Higher engagement from novelty and visual variety

## Success Criteria

1. ✅ Successfully add 165+ new island locations to configuration
2. ✅ Each location has 12-20 detailed, visually descriptive landmarks
3. ✅ All locations have accurate coordinates, timezones, and country information
4. ✅ Geographic distribution across all major island regions
5. ✅ Image generation successfully creates recognizable scenes for new locations
6. ✅ No regression in existing 35 city configurations
7. ✅ Documentation includes location selection rationale

## Related Changes

- None (this is a data expansion change, not an architectural change)

## Open Questions

None - implementation approach is straightforward as it leverages existing configuration structure.

## Implementation Notes

The implementation will follow a phased approach:

**Phase 1: Location Research & Curation** (Research existing island destinations)
**Phase 2: Landmark Documentation** (Detailed research on each location's iconic features)
**Phase 3: Configuration Updates** (Update cities.yaml with all new locations)
**Phase 4: Validation & Testing** (Verify image generation quality)

See `tasks.md` and `design.md` for detailed implementation approach.
