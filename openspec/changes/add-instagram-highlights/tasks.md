# Tasks: Instagram Highlights Integration

## Prerequisites

- [ ] 0.1 Create GitHub Personal Access Token (GH_TOKEN) with `repo` scope
- [ ] 0.2 Add GH_TOKEN to repository secrets
- [ ] 0.3 Add INSTAGRAM_USERNAME to repository secrets
- [ ] 0.4 Add INSTAGRAM_PASSWORD to repository secrets
- [ ] 0.5 Create empty `state/highlights_mapping.json` with initial structure

## 1. Instagram Private API Client

- [ ] 1.1 Create `src/platforms/instagram_private.py` with base client class
- [ ] 1.2 Implement session management (save/load/validate)
- [ ] 1.3 Implement proper headers (User-Agent, CSRF token, cookies)
- [ ] 1.4 Implement `create_highlight(title, story_media_id)` method
- [ ] 1.5 Implement `add_story_to_highlight(highlight_id, story_media_id)` method
- [ ] 1.6 Implement `get_highlights()` method for validation
- [ ] 1.7 Add error handling and logging

## 2. Login Flow with Manual 2FA

- [ ] 2.1 Create `src/platforms/instagram_login.py` with login functionality
- [ ] 2.2 Implement initial login request (username/password)
- [ ] 2.3 Implement 2FA submission endpoint
- [ ] 2.4 Implement session extraction from response
- [ ] 2.5 Implement GitHub Secrets update via API (save session)
- [ ] 2.6 Add challenge detection and user-friendly error messages

## 3. Highlight Management Module

- [ ] 3.1 Create `src/highlights.py` with main highlight logic
- [ ] 3.2 Implement state file loading/saving (`state/highlights_mapping.json`)
- [ ] 3.3 Implement country-to-highlight ID lookup from state
- [ ] 3.4 Implement rate limit checking (max 2 creations per day)
- [ ] 3.5 Implement rate limit counter reset on new day
- [ ] 3.6 Implement `get_or_create_highlight(country, story_id)` function
- [ ] 3.7 Implement `add_to_country_highlight(country, story_id)` function
- [ ] 3.8 Add session validation before highlight operations
- [ ] 3.9 Implement graceful degradation (skip on failure, don't raise)
- [ ] 3.10 Add notification mechanism for session expiry

## 4. Country Flag Emoji Mapping

- [ ] 4.1 Create country-to-flag-emoji mapping utility
- [ ] 4.2 Implement `get_highlight_title(country)` returning "🇯🇵 Japan" format
- [ ] 4.3 Handle edge cases (countries without standard flag emojis)

## 5. State File Management

- [ ] 5.1 Define state file schema (highlights, rate_limit)
- [ ] 5.2 Implement atomic read/write operations
- [ ] 5.3 Implement highlight ID storage after creation
- [ ] 5.4 Implement story count tracking per highlight
- [ ] 5.5 Ensure state file is committed after updates (in workflow)

## 6. GitHub Workflows

- [ ] 6.1 Create `.github/workflows/instagram-login.yml` with workflow_dispatch
- [ ] 6.2 Add 2FA code input parameter to login workflow
- [ ] 6.3 Modify `.github/workflows/post-weather.yml` to call highlights
- [ ] 6.4 Add `continue-on-error: true` for highlights step
- [ ] 6.5 Add step to commit `state/highlights_mapping.json` changes
- [ ] 6.6 Add notification step when session expired (create issue or similar)

## 7. Integration with Main Flow

- [ ] 7.1 Modify `src/main.py` to return story media ID after posting
- [ ] 7.2 Extract country from city configuration
- [ ] 7.3 Call highlights module after successful Instagram story post
- [ ] 7.4 Pass country and story_id to highlight function
- [ ] 7.5 Ensure main flow continues regardless of highlight result

## 8. Testing

- [ ] 8.1 Test manual login workflow with 2FA code
- [ ] 8.2 Verify session is saved to GitHub Secrets
- [ ] 8.3 Test session validation (valid session)
- [ ] 8.4 Test session validation (expired session - should notify)
- [ ] 8.5 Test highlight creation (new country, under rate limit)
- [ ] 8.6 Test highlight creation skipped (over rate limit)
- [ ] 8.7 Test highlight addition (existing country)
- [ ] 8.8 Test rate limit reset on new day
- [ ] 8.9 Test state file persistence
- [ ] 8.10 Test graceful degradation (API failure doesn't break posting)
- [ ] 8.11 Test full end-to-end flow

## 9. Documentation

- [ ] 9.1 Document initial setup steps (secrets creation)
- [ ] 9.2 Document manual login process (how to trigger, timing for 2FA)
- [ ] 9.3 Document troubleshooting (session expiry, 2FA timing, rate limits)
- [ ] 9.4 Document state file format and location
- [ ] 9.5 Update README with highlights feature description

## Completion Checklist

- [ ] All tasks marked complete
- [ ] Manual login workflow tested and working
- [ ] Highlights being created automatically (rate-limited)
- [ ] Stories being added to existing highlights
- [ ] Graceful degradation verified
- [ ] State file being committed properly
- [ ] Documentation complete
