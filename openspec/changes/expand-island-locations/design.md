# Design: Expand Island Locations

**Change ID:** `expand-island-locations`

## Architecture Overview

This change expands the location configuration data without modifying the underlying system architecture. The existing WeatherNews system already supports:

- Dynamic location loading from YAML configuration
- Geographic coordinate-based weather fetching
- Timezone-aware scheduling
- Landmark-based image prompt generation

**Key Insight**: This is a **data-driven expansion** that leverages existing infrastructure.

## Island Selection Criteria

To ensure high-quality, visually compelling content, locations are selected based on:

### 1. Visual Distinctiveness
- Unique natural landmarks (volcanic peaks, rock formations, coral atolls)
- Distinctive architecture (traditional houses, historic forts, colorful buildings)
- Iconic man-made structures (lighthouses, bridges, monuments)
- Recognizable cultural elements (traditional boats, markets, temples)

### 2. Geographic Diversity
- **Pacific Islands**: Polynesia, Micronesia, Melanesia (Hawaii, Bora Bora, Palau, Fiji)
- **Caribbean**: Greater & Lesser Antilles (Jamaica, Barbados, Aruba, St. Lucia)
- **Mediterranean**: Greek islands, Italian islands, Spanish islands (Santorini, Capri, Mallorca)
- **Indian Ocean**: Maldives, Seychelles, Mauritius, Madagascar
- **Atlantic**: Iceland, Azores, Canary Islands, Cape Verde
- **Arctic/Antarctic**: Svalbard, Greenland settlements
- **Southeast Asia**: Bali, Phuket, Langkawi, Boracay

### 3. Weather Interest
- Varied climates (tropical, temperate, arctic)
- Interesting weather phenomena (monsoons, trade winds, midnight sun)
- Seasonal variations that create diverse content

### 4. Cultural Significance
- Historical importance
- Cultural heritage sites
- Indigenous communities with unique traditions
- Tourism destinations with established identity

### 5. Technical Feasibility
- Available weather data from OpenWeatherMap
- Documented landmarks and attractions
- Established geographic coordinates
- Recognized timezone data

## Data Structure

Each island location follows the existing `CityConfig` schema:

```yaml
location_id:
  enabled: true
  weight: 1                    # Selection probability (1-100)
  name: "Island Name"
  name_local: "Local Name"     # Optional
  country: "Country/Territory"
  timezone: "Region/Location"  # IANA timezone
  coordinates:
    lat: 00.0000
    lon: 00.0000
  posting_times:               # Optional, defaults to global
    - "08:00"
    - "18:00"
  platforms:
    twitter: true
    instagram: false
    tiktok: false
  landmarks:                   # 12-20 detailed descriptions
    - Landmark 1 with architectural details and visual characteristics
    - Landmark 2 with specific colors, shapes, materials described
    - [... 10-18 more landmarks ...]
  hashtags:
    - "#IslandName"
    - "#CountryName"
    - "#TravelDestination"
```

### Landmark Description Best Practices

Based on successful patterns from existing cities (Dubai, New York, Jerusalem), landmarks should include:

1. **Specific Visual Details**: Colors, materials, shapes, architectural styles
2. **Distinctive Features**: What makes it recognizable and unique
3. **Scale Indicators**: Size relationships, prominent positioning
4. **Cultural Context**: Traditional vs modern, historical vs contemporary
5. **Natural Elements**: Vegetation, geological features, water bodies

**Example (Good):**
```yaml
- Moai statues massive carved stone heads with elongated faces on volcanic pedestals
- Caldera cliffs dramatic red and black volcanic cliffs rising from turquoise sea
- Whitewashed churches iconic blue-domed chapels with curved bell towers
```

**Example (Avoid - Too Generic):**
```yaml
- Famous statue
- Nice beach
- Historic building
```

## Island Categories & Distribution

Target distribution across categories (approximate):

| Category | Count | Examples |
|----------|-------|----------|
| **Tropical Paradise** | 40 | Maldives, Bora Bora, Seychelles |
| **Mediterranean** | 35 | Santorini, Capri, Ibiza |
| **Caribbean** | 30 | Barbados, Aruba, St. Lucia |
| **Pacific Islands** | 25 | Fiji, Tahiti, Palau |
| **Historic/Cultural** | 20 | Malta, Crete, Rhodes |
| **Arctic/Remote** | 15 | Iceland, Faroe Islands, Svalbard |
| **Southeast Asia** | 20 | Bali, Phuket, Langkawi |
| **Atlantic Islands** | 15 | Azores, Canary Islands, Madeira |
| **Total** | **200** | |

## Implementation Strategy

### Phase 1: Master Location List Creation
Create comprehensive list of 200 locations with:
- Official name and local name
- Country/territory designation
- Geographic coordinates (verified via Google Maps/OpenStreetMap)
- IANA timezone identifier
- Primary landmarks (initial high-level list)

### Phase 2: Detailed Landmark Research
For each location, research and document:
- 12-20 specific landmarks with detailed visual descriptions
- Architectural styles and materials
- Natural features and landscapes
- Cultural elements and traditions
- Color palettes and visual themes

### Phase 3: Configuration Implementation
- Add all locations to `cities.yaml`
- Initially set `enabled: false` for gradual rollout
- Assign appropriate hashtags
- Configure default posting times based on timezone

### Phase 4: Quality Validation
- Generate test images for sample locations
- Verify landmark recognition in generated images
- Adjust descriptions based on image quality
- Enable locations in batches

## Risk Mitigation

### Risk: Landmarks Too Generic
**Mitigation**: Require minimum 12 detailed landmark descriptions per location, with specific visual characteristics.

### Risk: Poor Image Quality
**Mitigation**: Test image generation before enabling location. Iterate on landmark descriptions.

### Risk: Weather Data Unavailable
**Mitigation**: Verify OpenWeatherMap coverage before adding location. Most populated islands are covered.

### Risk: Timezone Errors
**Mitigation**: Use authoritative IANA timezone database. Verify against worldtimeapi.org or similar.

### Risk: Configuration File Too Large
**Mitigation**: Current YAML format is human-readable and git-friendly. 200 locations estimated ~15,000 lines (manageable). Consider splitting into multiple files only if exceeds 20,000 lines.

## Trade-offs

### Decision: Single YAML File vs Multiple Files
**Chosen**: Single `cities.yaml` file
**Rationale**:
- Simpler configuration management
- Easier search and editing
- No breaking changes to existing code
- Performance impact negligible (one-time load at startup)
**Trade-off**: File becomes longer but remains manageable with good organization

### Decision: Manual Curation vs Automated Scraping
**Chosen**: Manual curation of landmark lists
**Rationale**:
- Higher quality, more visually descriptive landmarks
- Better control over prompt engineering
- Ensures cultural sensitivity and accuracy
**Trade-off**: More time-intensive but yields better image generation results

### Decision: All Locations Enabled vs Gradual Rollout
**Chosen**: Add all 200 with `enabled: false`, enable gradually
**Rationale**:
- Test image quality before public posting
- Monitor API costs (Nano Banana)
- Gather user feedback on location selection
**Trade-off**: Delayed benefit but reduced risk

## Success Metrics

1. **Configuration Completeness**: 200 locations with 12+ landmarks each (2,400+ landmark descriptions)
2. **Geographic Coverage**: At least 50 countries/territories represented
3. **Image Quality**: >90% of test generations produce recognizable location scenes
4. **Timezone Accuracy**: 100% correct timezone assignments (verified via automated tests)
5. **Coordinate Accuracy**: GPS coordinates within 1km of actual location center

## Future Considerations

- **Seasonal Variations**: Some islands have dramatic seasonal changes (consider seasonal landmark descriptions)
- **Special Events**: Major festivals or events could be incorporated into landmark lists
- **User Requests**: Framework allows easy addition of user-requested locations
- **Categorization**: Consider adding `category` or `region` field for filtering/selection
