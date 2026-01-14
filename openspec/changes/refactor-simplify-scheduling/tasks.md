## 1. State Management Refactor

- [x] 1.1 Create new `RecentlyPosted` dataclass to track cities posted in last 24h
- [x] 1.2 Implement `load_recent()` method to load from JSON file
- [x] 1.3 Implement `save_recent()` method to persist to JSON file
- [x] 1.4 Implement `add_posted(city_id)` method to add city with timestamp
- [x] 1.5 Implement `cleanup_old()` method to remove entries older than 24h
- [x] 1.6 Implement `get_excluded_ids()` method to return list of recently posted city IDs
- [x] 1.7 Remove old `DailySchedule` class and related methods

## 2. Scheduler Refactor

- [x] 2.1 Create new `select_random_city()` function that picks ONE city
- [x] 2.2 Add `excluded_ids` parameter to exclude recently posted cities
- [x] 2.3 Keep weighted random selection logic
- [x] 2.4 Remove `select_daily_cities()` function (no longer needed)
- [x] 2.5 Remove `calculate_posting_times()` function (no longer needed)

## 3. Main Script Refactor

- [x] 3.1 Remove `should_post_now()` function (no longer needed)
- [x] 3.2 Update main flow: load recent → select city → post → save recent
- [x] 3.3 Remove schedule-based city filtering
- [x] 3.4 Remove time-window checking logic
- [x] 3.5 Simplify `process_city()` to always post (no time checks)
- [x] 3.6 Update `--force` flag behavior (now ignores recently-posted exclusions)

## 4. GitHub Actions Workflow

- [x] 4.1 Simplify state commit step (only track recently_posted.json)
- [x] 4.2 Update workflow description/comments
- [ ] 4.3 Test workflow with manual trigger

## 5. Configuration Cleanup

- [ ] 5.1 Remove `posting_times` field from cities.yaml documentation
- [ ] 5.2 Update global `default_posting_times` in cities.yaml (mark as deprecated/unused)

## 6. Testing & Validation

- [x] 6.1 Test locally with `--dry-run` flag
- [x] 6.2 Verify random city selection excludes recent posts
- [ ] 6.3 Run actual post test via GitHub Actions
- [ ] 6.4 Verify posts succeed without timing issues
