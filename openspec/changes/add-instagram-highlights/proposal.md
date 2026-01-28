# Proposal: Add Instagram Highlights Integration

**Change ID:** `add-instagram-highlights`
**Status:** Proposal
**Created:** 2026-01-28

## Overview

Automatically add posted Instagram stories to country-specific highlights, creating a visual timeline of weather updates for each country. Over time, each country's highlight will showcase the variety of cities, weather patterns, and unique geographical features across different seasons.

## Why

Currently, Instagram stories disappear after 24 hours. By automatically adding each story to a country-specific highlight:

- **Persistent Content**: Weather updates remain accessible beyond the 24-hour story limit
- **Country Timelines**: Each country builds a visual history showing weather diversity across its cities
- **Geographic Showcase**: Highlights demonstrate the variety of landscapes and weather within each country
- **User Engagement**: Followers can browse historical weather art for countries they're interested in
- **Content Discovery**: New followers can explore past content organized by country

## What Changes

- Add Instagram Private API integration for highlights management
- Implement secure session persistence using GitHub Secrets
- Create manual login workflow with user-provided 2FA code
- **Automatic highlight creation** when posting to a new country for the first time
- **Rate-limited creation** (max 2 new highlights per day) to avoid suspicious patterns
- State file to track highlight IDs and creation counts
- Implement graceful degradation (continue posting if highlights fail)

## Technical Approach

### Why Private API?

The official Instagram Graph API does **not** support highlights. This feature requires using Instagram's private/internal API, which involves:

- Reverse-engineered endpoints (`/highlights/create_reel/`, `/highlights/{id}/edit_reel/`)
- Session-based authentication (cookies, not OAuth tokens)
- Careful implementation to minimize detection risk

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Account ban | Very low frequency (1 action per 4 hours), mimics normal user behavior |
| ToS violation | Accept risk for non-critical feature; graceful degradation ensures core posting continues |
| API changes | Isolated module; easy to disable if Instagram changes endpoints |
| Session expiry | Manual re-login workflow; user notified when session expires |

### Session Management

- Sessions persist for 30-90 days
- Stored encrypted in GitHub Secrets
- Validated before each use
- Manual re-login only when expired (~monthly)

### Manual 2FA Flow

When session expires:
1. Workflow notifies user (GitHub issue or workflow failure)
2. User triggers manual "Instagram Login" workflow
3. User inputs 2FA code from their authenticator app
4. Workflow logs in and saves new session

This allows users to keep using their existing authenticator app normally.

## Impact

- **Affected specs**: New capability (instagram-highlights)
- **Affected code**:
  - `src/platforms/instagram_private.py` (new)
  - `src/platforms/instagram_login.py` (new)
  - `src/highlights.py` (new)
  - `state/highlights_mapping.json` (new - tracks highlight IDs and rate limits)
  - `.github/workflows/instagram-login.yml` (new)
  - `.github/workflows/post-weather.yml` (modified)

## Success Criteria

1. Stories automatically added to country-specific highlights
2. Highlights automatically created for new countries (rate-limited to 2/day)
3. Session persists between workflow runs (no login spam)
4. Manual 2FA login works within 30-second code window
5. Core posting continues if highlights feature fails
6. User notified when re-login needed
7. Each country maintains its own highlight timeline
8. All ~200 countries have highlights within ~3 months of rollout

## Out of Scope

- Automatic 2FA (user wants to keep using their authenticator app)
- Highlight cover image customization
- Deleting old stories from highlights
- Custom highlight names per country (uses standard format)

## Open Questions

1. ~~Should we create highlights automatically for new countries, or require manual creation?~~
   - **Resolved**: Automatic creation with rate limiting (max 2/day)
2. What should the highlight naming convention be?
   - **Decision**: Country flag emoji + country name (e.g., "🇯🇵 Japan", "🇫🇷 France")
3. What's the daily rate limit for new highlight creation?
   - **Decision**: 2 per day - balances coverage speed vs. natural activity pattern
