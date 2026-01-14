## Why

The current scheduling system is over-engineered and unreliable. It pre-selects 6 cities at midnight with specific UTC posting times, but GitHub Actions delays cause the workflow to miss the 30-minute tolerance windows, resulting in zero posts. The complexity of time-window matching is unnecessary for our use case.

## What Changes

- **BREAKING**: Remove pre-scheduled daily city selection (6 cities at midnight)
- **BREAKING**: Remove time-window-based posting logic
- Simplify to: each cron run picks ONE random city and posts immediately
- Add simple "recently posted" tracking to prevent repeats within 24 hours
- Remove complex state management (DailySchedule class)

## Impact

- Affected specs: `scheduling` (new capability spec)
- Affected code:
  - `src/scheduler.py` - Simplify to single city selection with recent-exclusion
  - `src/state_manager.py` - Replace DailySchedule with simple RecentlyPosted tracking
  - `src/main.py` - Remove time-window checks, post immediately
  - `.github/workflows/post-weather.yml` - Minor adjustments (remove state commit complexity)
  - `config/cities.yaml` - Remove `posting_times` field from cities (no longer used)
