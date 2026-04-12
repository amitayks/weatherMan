## ADDED Requirements

### Requirement: Platform-specific caption generation

The system SHALL generate one caption per enabled platform (Twitter, Instagram, TikTok) via separate Gemini API calls, each tuned to that platform's length and tone.

#### Scenario: Twitter caption generated
- **WHEN** a post is being built for a city with Twitter enabled
- **THEN** the system calls Gemini once with a Twitter-specific prompt
- **AND** the returned caption is strictly no longer than 260 characters (leaving 20-char safety margin below the 280-char Twitter limit)
- **AND** the caption contains no hashtags
- **AND** the caption contains at least the current temperature and a reference to current conditions

#### Scenario: Instagram caption generated
- **WHEN** a post is being built for a city with Instagram enabled
- **THEN** the system calls Gemini once with an Instagram-specific prompt
- **AND** the returned caption body is between 100 and 260 characters (matching the Twitter-range budget: social readers do not reward long paragraphs)
- **AND** the system appends the existing standard hashtag block after two blank lines
- **AND** the final caption fits within Instagram's 2200-character limit

#### Scenario: TikTok caption generated
- **WHEN** a post is being built for a city with TikTok enabled
- **THEN** the system calls Gemini once with a TikTok-specific prompt
- **AND** the returned caption body is between 80 and 180 characters
- **AND** the system appends up to 8 platform-standard hashtags after the body
- **AND** the final description fits within TikTok's 150-character title limit for the truncated title

### Requirement: Literary quality floor

The system SHALL enforce a 17th-century aphoristic voice by constructing a prompt in that same register — prose after the manner of Bacon (for brevity), Browne (for gravity), and Johnson (for balance).

#### Scenario: Voice-in-voice system prompt
- **WHEN** the Gemini request is assembled
- **THEN** the system prompt itself is written in the target period voice (not modern instructions about a period voice), to prime the model for register consistency
- **AND** it names the target explicitly as composing "after Bacon for his brevity, after Browne for his gravity, after Johnson for his balance"
- **AND** it permits period flavor (inversion, "six-and-twenty", "betwixt", "of an evening", semicolon-joined balance, mild aphorism)
- **AND** the validator-enforced `FORBIDDEN_CLICHES` list contains at least 30 entries spanning four categories:
  - **Modern Hallmark clichés** — e.g. "dance of clouds", "Mother Nature", "kiss of the sun"
  - **Fake-archaic costume-party tokens** — e.g. "verily", "hath", "doth", "thee", "thou", "'tis", "o'er", "yonder"
  - **Modern-literary clichés** — e.g. "held its breath", "bruised sky", "dappled light", "a quiet hum"
  - **Period kitsch** (Victorian greeting-card) — e.g. "feathered friends", "gentle zephyr", "old sol", "bosom of nature"
- **AND** fake-archaic word-sized tokens are stored with surrounding spaces (e.g. `" hath "`) to avoid false positives in legitimate words (e.g. "Mathilda", "though")
- **AND** it includes at least 6 few-shot examples of good captions with short rationales, themselves written in the target voice

#### Scenario: Caption references concrete weather facts
- **WHEN** a caption is returned
- **THEN** the caption text contains at least the numeric temperature in Celsius OR a specific qualitative temperature word rooted in the data (e.g., "25 degrees", "muggy", "freezing")
- **AND** at least one reference to the current sky/precipitation condition

### Requirement: Variable-parameters rotation

The system SHALL pass a rotating set of parameters to Gemini on each call so that identical weather produces distinct compositions across calls.

#### Scenario: Parameters are rolled per call
- **WHEN** a caption generation request is built
- **THEN** the system randomly selects one value from each of the following rotation dimensions, chosen to fit the aphoristic period voice:
  - `literary_form` from {aphorism, periodic_sentence, gazette_notice, moral_observation, epistolary_fragment, balanced_antithesis, character_sketch, sermon_miniature}
  - `narrator` from {omniscient_correspondent, the_city_itself, a_disinterested_observer, a_passing_traveller, the_almanack, the_chronicler, the_gazetteer, the_parson_at_his_window}
  - `tone` from {sober, dryly_ironic, contemplative, skeptical, reverent, wistful, judicious, didactic, magisterial, melancholic, mildly_satirical}
  - `sensory_device` from {one_telling_figure, balanced_antithesis, mild_personification, a_progress_of_particulars, led_by_the_ear, led_by_the_hand}
  - `seed_noun` from a curated list of at least 200 concrete nouns (e.g., "a brass bell", "an unread letter", "the color of old parchment", "a patient sky")
- **AND** these parameters are included in the per-call user prompt accompanied by a short gloss (e.g., `tone: dryly_ironic — wit without smile`), so the model reads the label as instruction rather than guessing at period jargon

#### Scenario: Seed noun influences composition
- **WHEN** a seed noun is passed
- **THEN** the prompt instructs Gemini to weave the seed noun's image into the caption

### Requirement: Anti-repetition memory

The system SHALL track recent caption metadata per city and use it to avoid repeating angles, voices, or openers.

#### Scenario: Recent history recorded
- **WHEN** a caption is successfully generated and posted
- **THEN** the system appends an entry to the city's caption history with: timestamp, primary angle, literary_form, narrator, tone, first 3 words of caption
- **AND** the history retains only the last 10 entries per city

#### Scenario: Recent history steers generation
- **WHEN** a new caption is being requested for a city with history
- **THEN** the last 10 history entries are included in the user prompt as context
- **AND** the prompt instructs Gemini to avoid reusing the same angle, literary_form, narrator, and opener words from these recent entries

### Requirement: Sensor-model posting (no retries, no style gating)

The system SHALL make exactly one Gemini call per caption and SHALL return that caption for posting even if it contains a stylistic slip. Stylistic slips are recorded in the glitch log as a learning signal; they do not block posting.

#### Scenario: Single Gemini call per caption
- **WHEN** `generate()` is invoked for a (city, platform) pair
- **THEN** the Gemini API is called exactly once
- **AND** no retry with a correction hint is attempted

#### Scenario: Style slip is posted and logged
- **WHEN** the returned caption contains a forbidden cliché, lacks a temperature reference, or lacks a condition reference
- **THEN** the caption IS returned unchanged for posting
- **AND** the system appends one record to the glitch log with: timestamp, city_id, platform, caption, slip code (`cliche` | `missing_temp` | `missing_condition`), optional detail (e.g. the matched cliché string), primary angle, rotation parameters, `main_condition`, `temp_c`

#### Scenario: Caption length is not checked
- **WHEN** the returned caption exceeds the previous 260-character target
- **THEN** the system does NOT trim or reject it — verified posting accounts accept long posts, and trimming would damage the voice

### Requirement: Period-voice fallback on hard failure only

The system SHALL use the period-voice fallback template only when Gemini produces no usable output at all (empty response, exception, timeout). Style-only slips never trigger the fallback.

#### Scenario: Empty Gemini response
- **WHEN** the Gemini API call returns an empty response, raises an exception, or times out
- **THEN** the system returns a period-voice fallback caption produced by `build_period_fallback(city, temperature, main_condition, description)`
- **AND** appends one glitch-log record with slip code `hard_failure`
- **AND** does NOT record anything to the anti-repetition `CaptionMemory` (the fallback is not an AI output worth steering away from)

### Requirement: Glitch log retention and storage

The system SHALL persist glitches in an append-only JSONL file at `state/caption_glitches.jsonl` with bounded retention.

#### Scenario: File format
- **WHEN** a glitch is recorded
- **THEN** it is appended as a single JSON object on a new line
- **AND** the line contains: `ts`, `city`, `platform`, `caption`, `slip`, `detail`, `length`, `angle`, `main_condition`, `temp_c`, `params`

#### Scenario: Retention
- **WHEN** a glitch is recorded
- **THEN** entries older than 60 days are pruned from the file before the new entry is appended (single atomic rewrite via temp file)

#### Scenario: GitHub Actions cron compatibility
- **WHEN** the cron workflow runs `python -m src.main`
- **THEN** `state/caption_glitches.jsonl` is committed alongside `state/recently_posted.json` and `state/caption_history.json` in the same `[skip ci]` auto-commit step

### Requirement: Model and cost controls

The system SHALL use Gemini 2.5 Pro by default with cost-protecting guardrails.

#### Scenario: Default model configured
- **WHEN** the caption generator is initialized
- **THEN** the Gemini model is `gemini-2.5-pro`

#### Scenario: Token cap enforced
- **WHEN** a Gemini request is sent
- **THEN** the `max_output_tokens` parameter is set to 400 (generous for even longest Instagram body)

#### Scenario: Request timeout enforced
- **WHEN** a Gemini request is sent
- **THEN** the request has a timeout of 30 seconds per call
