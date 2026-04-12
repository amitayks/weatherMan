## ADDED Requirements

### Requirement: Fetch 24-hour forecast alongside current weather

The system SHALL fetch a near-term forecast from OpenWeatherMap whenever it fetches current weather for a city.

#### Scenario: Forecast endpoint called
- **WHEN** `get_weather_for_city(city)` is invoked
- **THEN** the system calls `https://api.openweathermap.org/data/2.5/forecast` with the city's coordinates, `units=metric`, and `cnt=8` (8 × 3-hour intervals = 24 hours)
- **AND** the call uses the same `OPENWEATHER_API_KEY`
- **AND** the call has a timeout of 10 seconds

#### Scenario: Forecast failure does not block current weather
- **WHEN** the forecast endpoint fails (timeout, 5xx, network error)
- **THEN** the system logs the failure
- **AND** returns a `WeatherData` object with current weather populated and an empty forecast list
- **AND** downstream code (notability scorer) tolerates an empty forecast gracefully

### Requirement: Extended WeatherData model

`WeatherData` SHALL include forecast entries and derived forecast-based fields.

#### Scenario: forecast_entries field
- **WHEN** a `WeatherData` object is returned
- **THEN** it has a `forecast_entries: list[ForecastEntry]` field
- **AND** each `ForecastEntry` contains: `timestamp`, `temperature_c`, `feels_like_c`, `humidity`, `main_condition`, `description`, `clouds_percent`, `wind_speed`, `precipitation_mm` (sum of rain + snow for that 3h window, defaulting to 0)

#### Scenario: Derived convenience fields
- **WHEN** a `WeatherData` object has forecast entries
- **THEN** it exposes the following computed properties:
  - `precipitation_next_6h: float` (sum of `precipitation_mm` for next 2 entries, or 0 if empty)
  - `temp_trend_6h: Literal["rising","falling","steady"]` (steady if delta < 2°C, else direction of next-6h delta)
  - `next_condition_change: Optional[tuple[datetime, str]]` (first forecast entry where `main_condition` differs from current, or None)
  - `max_temp_24h: float`, `min_temp_24h: float` (over forecast entries)

#### Scenario: Empty forecast handled
- **WHEN** `forecast_entries` is empty
- **THEN** all derived properties return safe defaults (0, "steady", None, current temp for max/min)

### Requirement: Forecast parsing robustness

The forecast fetch SHALL tolerate missing optional fields in the API response.

#### Scenario: Rain field missing
- **WHEN** a forecast entry from the API has no `rain` or `snow` key
- **THEN** the entry's `precipitation_mm` is 0

#### Scenario: Partial entries
- **WHEN** a forecast entry is missing any optional field (clouds, wind)
- **THEN** the entry uses sensible defaults (clouds_percent=0, wind_speed=0) rather than failing the fetch
