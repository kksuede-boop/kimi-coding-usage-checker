# Kimi Coding Plan Usage Checker

A Playwright-based automation tool to check [Kimi Coding Plan](https://www.kimi.com/code) usage statistics. Designed to be called by AI agents with minimal model involvement.

## Features

- Checks weekly quota usage percentage and reset countdown
- Shows rate limit status
- Displays member tier and model access level
- Lists recent API request history
- Supports headless operation after one-time login
- Can use existing Chrome login state directly

## Quick Start

```bash
# Install dependencies
pip install playwright
python -m playwright install chromium

# First run - login in browser
python check_usage.py --no-headless --output json

# Subsequent runs - fully automated
python check_usage.py --output json
```

## Usage as Agent Skill

This tool is designed to be called by AI agents (e.g., QoderWork) to check Kimi Coding Plan usage. The agent runs:

```bash
python /path/to/check_usage.py --output json
```

And parses the JSON output to report usage status to the user.

## Output Example

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
  "recent_requests": [...]
}
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--no-headless` | Show browser (for login) |
| `--chrome-profile` | Use existing Chrome login (Chrome must be closed) |
| `--login` | Clear saved state and re-login |
| `--output json\|text` | Output format |

## How Login Works

1. **Persistent Profile Mode** (default): First run opens a browser for manual login. After login, the browser profile is saved at `~/.kimi-coding-checker/browser-profile/` and reused for subsequent headless runs.

2. **Chrome Profile Mode** (`--chrome-profile`): Directly uses your Chrome's login state. Requires Chrome to be closed since the profile is locked while Chrome runs.

## Requirements

- Python 3.9+
- Playwright (`pip install playwright`)
- Chromium browser (`python -m playwright install chromium`)
- Google Chrome (for `channel="chrome"`)

## License

MIT
