## ADDED Requirements

### Requirement: Random City Selection Per Run
The system SHALL select ONE random city each time the workflow runs, using weighted random selection from enabled cities, excluding cities posted within the last 24 hours.

#### Scenario: Normal selection with available cities
- **WHEN** the workflow runs
- **AND** there are enabled cities not posted in the last 24 hours
- **THEN** the system selects one random city using weighted selection
- **AND** posts to that city immediately

#### Scenario: All cities recently posted
- **WHEN** the workflow runs
- **AND** all enabled cities have been posted within the last 24 hours
- **THEN** the system clears the recently-posted list
- **AND** selects any random city using weighted selection

### Requirement: Recently Posted Tracking
The system SHALL maintain a list of cities posted within the last 24 hours to prevent duplicate posts.

#### Scenario: City added after successful post
- **WHEN** a post succeeds for a city
- **THEN** the city ID and timestamp are added to the recently-posted list
- **AND** the list is persisted to `state/recently_posted.json`

#### Scenario: Old entries cleaned up
- **WHEN** the recently-posted list is loaded
- **THEN** entries older than 24 hours are automatically removed

### Requirement: Immediate Posting
The system SHALL post immediately when triggered, without time-window validation.

#### Scenario: Workflow triggered by cron
- **WHEN** the GitHub Actions cron job runs (every 4 hours)
- **THEN** the system posts immediately without checking time windows

#### Scenario: Workflow triggered manually
- **WHEN** a user manually triggers the workflow
- **THEN** the system posts immediately

## REMOVED Requirements

### Requirement: Daily Schedule Pre-Selection
**Reason**: Over-engineered for the use case; causes timing failures with GitHub Actions delays
**Migration**: Replace with per-run random selection

### Requirement: Time Window Validation
**Reason**: GitHub Actions delays cause posts to miss the 30-minute tolerance windows
**Migration**: Remove entirely; post immediately when triggered

### Requirement: Posting Times Configuration
**Reason**: No longer needed since posts happen immediately on cron trigger
**Migration**: Remove `posting_times` field from city configs (optional cleanup)
