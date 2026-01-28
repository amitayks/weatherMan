# Instagram Highlights Capability

## ADDED Requirements

### Requirement: Country-Specific Highlights

The system SHALL automatically add each posted Instagram story to a country-specific highlight, creating a persistent timeline of weather updates organized by country.

#### Scenario: Story added to existing country highlight
- **GIVEN** a story was successfully posted to Instagram for city "Tokyo" in country "Japan"
- **AND** Japan has an existing highlight ID in the state file
- **AND** a valid Instagram session exists
- **WHEN** the highlight addition is triggered
- **THEN** the story is added to Japan's highlight
- **AND** the story appears in the highlight alongside previous Japan weather stories
- **AND** the story count for Japan is incremented in the state file

#### Scenario: Country has no highlight yet (under rate limit)
- **GIVEN** a story was posted for city "Paris" in country "France"
- **AND** France has no highlight ID in the state file
- **AND** fewer than 2 highlights have been created today
- **AND** a valid Instagram session exists
- **WHEN** the highlight addition is triggered
- **THEN** the system creates a new highlight titled "🇫🇷 France"
- **AND** adds the story to the new highlight
- **AND** saves the highlight ID to the state file
- **AND** increments the daily creation counter

#### Scenario: Country has no highlight (rate limit reached)
- **GIVEN** a story was posted for city "Berlin" in country "Germany"
- **AND** Germany has no highlight ID in the state file
- **AND** 2 highlights have already been created today
- **WHEN** the highlight addition is triggered
- **THEN** the system skips highlight creation for this story
- **AND** logs that rate limit was reached
- **AND** the main posting workflow continues successfully
- **AND** the story will be added when Germany's highlight is created on a future run

### Requirement: Automatic Highlight Creation

The system SHALL automatically create new highlights for countries that don't have one yet, using the country flag emoji and name as the title.

#### Scenario: New highlight created with correct title
- **GIVEN** a story needs to be added for country "Japan"
- **AND** Japan has no existing highlight
- **AND** the daily rate limit has not been reached
- **WHEN** a highlight is created
- **THEN** the highlight title is "🇯🇵 Japan"
- **AND** the first story is added to the highlight
- **AND** the highlight ID is stored in the state file

#### Scenario: Highlight title for country without standard flag
- **GIVEN** a story needs to be added for a territory or region without a standard country flag
- **WHEN** a highlight is created
- **THEN** the system uses a generic globe emoji "🌍" or appropriate regional flag
- **AND** the highlight is created successfully

### Requirement: Rate-Limited Highlight Creation

The system SHALL limit new highlight creation to a maximum of 2 per day to avoid suspicious activity patterns during initial rollout.

#### Scenario: First highlight of the day
- **GIVEN** no highlights have been created today
- **AND** a new country needs a highlight
- **WHEN** the highlight is created
- **THEN** the daily counter is set to 1
- **AND** the current date is recorded in the state file

#### Scenario: Second highlight of the day
- **GIVEN** 1 highlight has been created today
- **AND** a new country needs a highlight
- **WHEN** the highlight is created
- **THEN** the daily counter is incremented to 2
- **AND** creation is allowed

#### Scenario: Rate limit reached
- **GIVEN** 2 highlights have been created today
- **AND** a new country needs a highlight
- **WHEN** highlight creation is attempted
- **THEN** creation is skipped
- **AND** a message is logged indicating rate limit reached
- **AND** the story is not added to any highlight
- **AND** the workflow continues successfully

#### Scenario: Rate limit resets on new day
- **GIVEN** 2 highlights were created yesterday
- **AND** it is now a new calendar day
- **AND** a new country needs a highlight
- **WHEN** highlight creation is attempted
- **THEN** the daily counter is reset to 0
- **AND** the new date is recorded
- **AND** the highlight is created successfully

### Requirement: Session Persistence

The system SHALL persist Instagram session data between workflow runs to minimize login frequency and avoid suspicious authentication patterns.

#### Scenario: Valid session reused
- **GIVEN** a valid Instagram session exists in GitHub Secrets
- **WHEN** a new workflow run starts
- **THEN** the system loads the existing session
- **AND** validates the session is still active
- **AND** uses the session for highlight operations without re-authenticating

#### Scenario: Session expired
- **GIVEN** an Instagram session exists but has expired
- **WHEN** the system attempts to validate the session
- **THEN** the validation fails
- **AND** the system skips highlight operations
- **AND** the system notifies the user that re-login is required
- **AND** the main posting workflow continues successfully

#### Scenario: No session exists
- **GIVEN** no Instagram session exists in GitHub Secrets
- **WHEN** a workflow run starts
- **THEN** the system skips highlight operations
- **AND** logs that no session is available
- **AND** the main posting workflow continues successfully

### Requirement: Manual Login with 2FA

The system SHALL provide a manual login workflow that allows users to authenticate with their own 2FA code from their authenticator app.

#### Scenario: Successful login with 2FA
- **GIVEN** the user triggers the Instagram Login workflow
- **AND** provides their current 2FA code from their authenticator app
- **WHEN** the login flow executes
- **THEN** the system authenticates with Instagram using username, password, and 2FA code
- **AND** extracts the session data from the response
- **AND** saves the session to GitHub Secrets
- **AND** reports login success

#### Scenario: Invalid 2FA code
- **GIVEN** the user triggers the Instagram Login workflow
- **AND** provides an expired or incorrect 2FA code
- **WHEN** the login flow executes
- **THEN** the system reports the 2FA code was invalid
- **AND** instructs the user to wait for a fresh code and retry
- **AND** does not save any session data

#### Scenario: Login challenged by Instagram
- **GIVEN** the user triggers the Instagram Login workflow
- **AND** Instagram requires additional verification (checkpoint)
- **WHEN** the login flow executes
- **THEN** the system reports that Instagram requires additional verification
- **AND** provides guidance on resolving the challenge
- **AND** does not save any session data

### Requirement: Graceful Degradation

The system SHALL continue normal posting operations even when highlight functionality fails, ensuring core features are never blocked by highlight issues.

#### Scenario: Highlight API failure
- **GIVEN** a story was successfully posted to Instagram
- **AND** a valid session exists
- **WHEN** the highlight API call fails (network error, API change, etc.)
- **THEN** the system logs the error
- **AND** the workflow completes successfully
- **AND** Twitter and Instagram posts remain published
- **AND** the system reports partial success (posts succeeded, highlights failed)

#### Scenario: Session validation failure during posting
- **GIVEN** the posting workflow is running
- **AND** the Instagram session has expired mid-workflow
- **WHEN** the highlight addition is attempted
- **THEN** the system detects the invalid session
- **AND** skips highlight addition
- **AND** notifies the user about session expiry
- **AND** the workflow completes successfully with posts published

### Requirement: Session Security

The system SHALL store Instagram session data securely using GitHub's encrypted secrets infrastructure.

#### Scenario: Session stored securely
- **GIVEN** a successful login has occurred
- **WHEN** the session is saved
- **THEN** the session data is encrypted using GitHub's public key
- **AND** stored in GitHub Secrets as INSTAGRAM_SESSION
- **AND** is only accessible during workflow execution
- **AND** is not visible in workflow logs

#### Scenario: Session updated after login
- **GIVEN** a valid session already exists in GitHub Secrets
- **AND** the user performs a new login
- **WHEN** the new session is saved
- **THEN** the old session is replaced with the new session
- **AND** subsequent workflow runs use the new session

### Requirement: State File Management

The system SHALL maintain a state file tracking highlight IDs and rate limit counters, persisted to the repository.

#### Scenario: State file created on first run
- **GIVEN** no state file exists
- **WHEN** the highlights module runs for the first time
- **THEN** an empty state file is created with default structure
- **AND** the file is committed to the repository

#### Scenario: State file updated after highlight creation
- **GIVEN** a new highlight was created for country "Italy"
- **WHEN** the operation completes
- **THEN** the state file is updated with Italy's highlight ID
- **AND** the creation timestamp is recorded
- **AND** the story count is set to 1
- **AND** the daily creation counter is incremented
- **AND** the changes are committed to the repository

#### Scenario: State file updated after story addition
- **GIVEN** a story was added to an existing highlight
- **WHEN** the operation completes
- **THEN** the story count for that country is incremented
- **AND** the changes are committed to the repository

### Requirement: Highlight Timeline Building

The system SHALL build country-specific highlight timelines that showcase weather diversity across cities and seasons over time.

#### Scenario: Multiple cities same country
- **GIVEN** Japan has cities Tokyo, Osaka, and Kyoto configured
- **AND** Japan has a single highlight
- **WHEN** stories are posted for each city over time
- **THEN** all stories are added to the same Japan highlight
- **AND** the highlight shows a timeline of weather across all Japanese cities
- **AND** viewers can see geographic and weather diversity within Japan

#### Scenario: Timeline grows over seasons
- **GIVEN** a country highlight has been active for multiple months
- **WHEN** a viewer browses the highlight
- **THEN** they see weather updates spanning different seasons
- **AND** the timeline demonstrates the country's weather variety throughout the year
