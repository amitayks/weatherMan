# Design: Instagram Highlights Integration

## Context

Instagram's official Graph API supports posting to feed and stories, but does **not** support highlights management. To add stories to highlights programmatically, we must use Instagram's private API - the same endpoints their mobile app uses.

### Stakeholders
- **Primary**: Project maintainer (needs minimal manual intervention)
- **Secondary**: Instagram followers (benefit from organized content)

### Constraints
- Must not require storing TOTP secret (user wants to keep using their authenticator app)
- Must handle session expiry gracefully without breaking core posting
- Must minimize detection risk (low frequency, realistic patterns)

## Goals / Non-Goals

### Goals
- Automatically add stories to country-specific highlights
- Automatically create highlights for new countries (rate-limited)
- Persist sessions to minimize login frequency
- Provide manual login flow with user-provided 2FA code
- Graceful degradation when session expires

### Non-Goals
- Automatic 2FA code generation
- Modifying existing stories
- Analytics/insights from highlights
- Custom highlight covers or names

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    EVERY 4 HOURS (Automated)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Generate │───►│ Post to  │───►│ Post to  │───►│ Highlight│  │
│  │ Image    │    │ Twitter  │    │ Instagram│    │ Logic    │  │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘  │
│                                   (Official API)       │        │
│                                                        ▼        │
│                                        ┌───────────────────────┐│
│                                        │ Session valid?        ││
│                                        └───────────┬───────────┘│
│                                             YES    │    NO      │
│                                    ┌───────────────┴─────┐      │
│                                    ▼                     ▼      │
│                          ┌─────────────────┐      ⚠️ Skip       │
│                          │ Country has     │      + Notify      │
│                          │ highlight?      │                    │
│                          └────────┬────────┘                    │
│                            YES    │    NO                       │
│                       ┌───────────┴───────────┐                 │
│                       ▼                       ▼                 │
│               ┌─────────────┐      ┌─────────────────────┐      │
│               │ Add story   │      │ Created < 2 today?  │      │
│               │ to highlight│      └──────────┬──────────┘      │
│               └─────────────┘           YES   │   NO            │
│                                    ┌──────────┴──────┐          │
│                                    ▼                 ▼          │
│                          ┌──────────────┐    ⏭️ Skip creation   │
│                          │Create highlight│   (post next time)  │
│                          │"🇯🇵 Country"  │                      │
│                          │+ add story    │                      │
│                          │+ save ID      │                      │
│                          └──────────────┘                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  WHEN NOTIFIED (Manual Trigger)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User clicks "Run workflow" in GitHub Actions                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Inputs:                                                 │   │
│  │  - 2FA code from authenticator app: [______]             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Load     │───►│ Login    │───►│ Submit   │───►│ Save     │  │
│  │ Creds    │    │ Request  │    │ 2FA Code │    │ Session  │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Design

```
src/
├── platforms/
│   ├── instagram.py              # Existing - Official Graph API
│   ├── instagram_private.py      # NEW - Private API client
│   └── instagram_login.py        # NEW - Login + 2FA flow
├── highlights.py                 # NEW - Highlight management
└── main.py                       # Modified - Call highlights after story

state/
├── recently_posted.json          # Existing - Track posted cities
└── highlights_mapping.json       # NEW - Track highlights & rate limits

.github/workflows/
├── post-weather.yml              # Modified - Add highlights step
└── instagram-login.yml           # NEW - Manual login workflow
```

### State File Structure

```json
// state/highlights_mapping.json
{
  "highlights": {
    "Japan": {
      "highlight_id": "17907771728171896",
      "title": "🇯🇵 Japan",
      "created_at": "2026-01-28T12:00:00Z",
      "story_count": 15
    },
    "France": {
      "highlight_id": "17907771728171897",
      "title": "🇫🇷 France",
      "created_at": "2026-01-29T08:00:00Z",
      "story_count": 8
    }
  },
  "rate_limit": {
    "date": "2026-01-28",
    "created_today": 2
  }
}
```

## Decisions

### Decision 1: Session Storage in GitHub Secrets

**What**: Store Instagram session data (cookies, user ID) as encrypted JSON in GitHub Secrets.

**Why**:
- GitHub Secrets are encrypted at rest
- Can be updated programmatically via GitHub API
- Persists across workflow runs
- No additional infrastructure needed

**Alternatives considered**:
- GitHub Actions Cache: Can be evicted, less secure
- Commit to repo (encrypted): Clutters git history
- External KV store: Additional complexity and cost

### Decision 2: Manual 2FA Code Input

**What**: User manually enters 2FA code when triggering login workflow.

**Why**:
- User explicitly requested to keep using their authenticator app
- No need to store TOTP secret (additional security risk)
- Login only needed ~monthly (when session expires)

**Trade-off**: Requires user action within 30-second window when code refreshes.

### Decision 3: Automatic Highlight Creation with Rate Limiting

**What**: Automatically create highlights for new countries, limited to 2 per day.

**Why**:
- Manual creation of 200 highlights is tedious
- Creating highlights when content exists is natural user behavior
- Rate limiting (2/day) avoids suspicious burst of activity
- ~100 days to cover all countries - gradual, natural rollout

**Implementation**:
```python
def can_create_highlight_today(state):
    today = datetime.now().strftime("%Y-%m-%d")
    if state["rate_limit"]["date"] != today:
        # New day, reset counter
        state["rate_limit"] = {"date": today, "created_today": 0}
    return state["rate_limit"]["created_today"] < 2
```

**Trade-off**: Countries without highlights won't have stories added until highlight is created (on a future post when under rate limit).

### Decision 4: State File for Highlight Mapping

**What**: Store highlight IDs and rate limit tracking in `state/highlights_mapping.json`.

**Why**:
- Follows existing pattern (`state/recently_posted.json`)
- Automatically committed to repo by workflow
- No need to configure highlight IDs manually
- Persists across workflow runs

**Alternatives considered**:
- `cities.yaml`: Would require manual configuration, defeats auto-creation
- GitHub Secrets: Too many secrets (200 countries), harder to inspect
- Database: Overkill for simple key-value storage

### Decision 5: Highlight Naming Convention

**What**: Highlights named as "{flag emoji} {country name}" (e.g., "🇯🇵 Japan").

**Why**:
- Visually distinctive with flag emoji
- Easy to identify country at a glance
- Consistent across all highlights
- Flag emojis render well on Instagram

### Decision 6: Graceful Degradation

**What**: If highlights fail, continue with normal posting and notify user.

**Why**:
- Highlights are a "nice to have" enhancement
- Core posting must never be blocked by highlights issues
- User can address session issues at their convenience

## API Endpoints

### Private API Base
```
https://i.instagram.com/api/v1
```

### Authentication
```
POST /accounts/login/
POST /accounts/two_factor_login/
GET /accounts/current_user/  (session validation)
```

### Highlights
```
POST /highlights/create_reel/
POST /highlights/{highlight_id}/edit_reel/
GET /highlights/{user_id}/highlights_tray/
```

### Required Headers
```
User-Agent: Instagram {version} Android (...)
X-CSRFToken: {csrf_token}
Cookie: sessionid={session_id}; csrftoken={csrf_token}; ...
```

## Security Considerations

### Stored Secrets
| Secret | Purpose | Risk Level |
|--------|---------|------------|
| INSTAGRAM_USERNAME | Login | Low (public info) |
| INSTAGRAM_PASSWORD | Login | High (encrypted in GitHub) |
| INSTAGRAM_SESSION | API calls | Medium (expires, can be revoked) |
| GH_TOKEN | Update secrets | Medium (scoped to repo) |

### Detection Avoidance
- **Frequency**: 1 highlight add per 4 hours (6/day) - well below suspicious thresholds
- **Pattern**: Consistent timing mimics scheduled posting tools
- **Session reuse**: Same session from different IPs is normal mobile behavior
- **No scraping**: Only writing to own account, no data extraction

## Risks / Trade-offs

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Account ban | Very Low | High | Low frequency, graceful degradation |
| API endpoint changes | Medium | Medium | Isolated module, easy to disable |
| Session expiry at bad time | Low | Low | Notification system, manual re-login |
| 2FA code timing | Low | Low | User enters fresh code, 30s window |

## Migration Plan

### Phase 1: Infrastructure
1. Create GitHub Secrets (username, password)
2. Create GH_TOKEN with repo scope
3. Initialize empty `state/highlights_mapping.json`

### Phase 2: Implementation
1. Implement private API client
2. Implement login flow with 2FA
3. Implement highlight management with rate limiting
4. Implement state file management
5. Add country flag emoji mapping
6. Add to main workflow

### Phase 3: Testing
1. Test manual login workflow
2. Test session persistence
3. Test highlight creation (new country)
4. Test highlight addition (existing country)
5. Test rate limiting (skip creation when at limit)
6. Test graceful degradation

### Phase 4: Rollout
1. Deploy to production
2. Perform initial login (manual trigger with 2FA)
3. Monitor first few runs for highlight creation
4. Verify state file is being updated and committed
5. Over ~100 days, all countries will have highlights

### Rollback
- Remove highlights step from workflow
- Core posting unaffected
- State file can remain (harmless)
- No data migration needed

## Open Questions

1. ~~Should TOTP secret be stored for automatic 2FA?~~ **Resolved**: No, user wants manual input
2. ~~How many countries should have highlights initially?~~ **Resolved**: Start with 0, auto-create as we post
3. ~~Should we retry failed highlight additions?~~ **Resolved**: No, skip and try next run
4. Should we track story count per highlight? **Proposed**: Yes, useful for analytics
