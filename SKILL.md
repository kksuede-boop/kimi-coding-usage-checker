---
name: kimi-coding-usage-checker
description: Check Kimi Coding Plan usage statistics (quota, rate limit, member level) via Playwright browser automation. Use when the user asks about Kimi coding plan quota, remaining usage, rate limits, or subscription status.
version: 1.1.0
---

# Kimi Coding Plan Usage Checker

Automated tool to check Kimi Coding Plan (kimi.com/code) usage status. Uses its own independent Chromium browser - does NOT touch user's Chrome.

## Prerequisites

- Python 3.9+
- Playwright with Chromium: `pip install playwright && python -m playwright install chromium`

## Steps

1. **First run** - login once in Playwright's Chromium window:
   ```bash
   python <skill-directory>/check_usage.py --no-headless --output json
   ```
   Log in to kimi.com. Session is saved in `~/.kimi-coding-checker/chromium-profile/`.

2. **Subsequent runs** - fully automated headless:
   ```bash
   python <skill-directory>/check_usage.py --output json
   ```

3. Parse the JSON output:
   ```json
   {
     "status": "success",
     "quota": {
       "weekly_usage_percent": 27,
       "resets_in_value": 138,
       "resets_in_unit": "hours"
     },
     "rate_limit": {
       "usage_percent": 21,
       "resets_in_value": 17,
       "resets_in_unit": "minutes"
     },
     "member": {
       "level": "Moderato",
       "model_access": "K2.6"
     },
     "total_records": 100,
     "recent_requests": [...]
   }
   ```

4. Report key metrics to user in natural language.

## Arguments

| Argument | Description |
|----------|-------------|
| `--no-headless` | Show browser window (needed for first-time login) |
| `--login` | Force re-login (clears saved browser profile) |
| `--output json` | Output as JSON (default) |
| `--output text` | Output as human-readable text |

## Pitfalls

- Does NOT require closing user's Chrome - uses independent Chromium instance.
- If session expires, run `--login --no-headless` to re-authenticate.
- Debug: set `KIMI_DEBUG=1` env var to dump raw page text to stderr.
- GitHub repo: https://github.com/kksuede-boop/kimi-coding-usage-checker

## Verification

- `status` is `"success"`
- `quota.weekly_usage_percent` is 0-100
- `member.level` is non-empty (Andante/Moderato/Allegretto/Allegro)
