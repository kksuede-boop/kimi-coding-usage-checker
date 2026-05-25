---
name: kimi-coding-usage-checker
description: Check Kimi Coding Plan usage statistics (quota, rate limit, member level) via Playwright browser automation. Use when the user asks about Kimi coding plan quota, remaining usage, rate limits, or subscription status.
version: 1.0.0
---

# Kimi Coding Plan Usage Checker

Automated tool to check Kimi Coding Plan (kimi.com/code) usage status including weekly quota, rate limits, member level, and recent API request history.

## Prerequisites

- Python 3.9+
- Playwright with Chromium (`pip install playwright && playwright install chromium`)
- Google Chrome installed (uses Chrome channel)
- First run requires one-time manual login (browser window opens)

## Setup (first time only)

```bash
pip install playwright
python -m playwright install chromium
```

## Steps

1. **First run** - Open visible browser for login:
   ```bash
   python <skill-directory>/check_usage.py --no-headless --output json
   ```
   User logs in to kimi.com in the browser. After login, navigate to the console page. The session is saved automatically in a persistent browser profile at `~/.kimi-coding-checker/browser-profile/`.

2. **Subsequent runs** - Headless mode (automated):
   ```bash
   python <skill-directory>/check_usage.py --output json
   ```

3. **Alternative: Use existing Chrome login** (Chrome must be closed):
   ```bash
   python <skill-directory>/check_usage.py --chrome-profile --output json
   ```

4. Parse the JSON output:
   ```json
   {
     "status": "success",
     "quota": {
       "weekly_usage_percent": 23,
       "resets_in_value": 143,
       "resets_in_unit": "hours"
     },
     "rate_limit": {
       "usage_percent": 17,
       "resets_in_value": 11,
       "resets_in_unit": "minutes"
     },
     "member": {
       "level": "Moderato",
       "model_access": "K2.6 Flagship model"
     },
     "total_records": 100,
     "recent_requests": [
       {
         "request_id": "...",
         "name": "hermes260505",
         "source": "claude-code/1.0",
         "call_type": "Model Inference",
         "datetime": "2026-05-25 11:26:38",
         "status": "Success"
       }
     ]
   }
   ```

5. Report key metrics to user:
   - Weekly quota percentage and reset countdown
   - Rate limit current usage and reset time
   - Member tier and model access level
   - Total API request count and recent history

## Arguments

| Argument | Description |
|----------|-------------|
| `--no-headless` | Show browser window (needed for first login) |
| `--chrome-profile` | Use existing Chrome profile directly (Chrome must be closed) |
| `--login` | Force re-login (clears saved persistent profile) |
| `--output json` | Output as JSON (default) |
| `--output text` | Output as human-readable text |

## Error Handling

| Status | Meaning | Action |
|--------|---------|--------|
| `success` | Data extracted OK | Report to user |
| `login_required` | No valid session | Run with `--no-headless` to login |
| `error` | General failure | Check message field for details |

## Pitfalls

- Persistent profile lives at `~/.kimi-coding-checker/browser-profile/`. If login expires, run `--login --no-headless` to re-authenticate.
- `--chrome-profile` requires Chrome to be completely closed (profile lock).
- Playwright Chromium must be installed separately: `python -m playwright install chromium`
- On Windows, Chrome user data is at `%LOCALAPPDATA%\Google\Chrome\User Data`.
- The page is an SPA; script waits 2-3 seconds for rendering after navigation.
- Debug mode: set `KIMI_DEBUG=1` env var to dump raw page text to stderr.

## Verification

After running, check:
- `status` is `"success"`
- `quota.weekly_usage_percent` is 0-100
- `rate_limit.usage_percent` is 0-100
- `member.level` is non-empty (Andante/Moderato/Allegretto/Allegro)
