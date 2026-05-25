# Kimi Coding Plan Usage Checker

A Playwright-based automation tool to check [Kimi Coding Plan](https://www.kimi.com/code) usage statistics. Designed to be called by AI agents with minimal model involvement.

## Features

- Checks weekly quota usage percentage and reset countdown
- Shows rate limit status
- Displays member tier and model access level
- Lists recent API request history (with total count)
- Uses independent Chromium browser - **does NOT touch user's Chrome**
- Headless after one-time login setup

## Quick Start

```bash
# Install dependencies
pip install playwright
python -m playwright install chromium

# First run - login in Playwright's Chromium
python check_usage.py --no-headless --output json

# Subsequent runs - fully automated headless
python check_usage.py --output json
```

## Usage as Agent Skill

This tool is designed to be called by AI agents. The agent runs:

```bash
python /path/to/check_usage.py --output json
```

And parses the JSON output to report usage status.

## Output Example

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
  "recent_requests": [
    {
      "request_id": "...",
      "name": "hermes260505",
      "source": "claude-code/0.1.0",
      "call_type": "Model Inference",
      "datetime": "2026-05-25 15:28:45",
      "status": "Success"
    }
  ]
}
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--no-headless` | Show browser (for login) |
| `--login` | Clear saved state and re-login |
| `--output json\|text` | Output format |

## How It Works

1. Uses Playwright's bundled Chromium (not your Chrome)
2. Maintains its own persistent browser profile at `~/.kimi-coding-checker/chromium-profile/`
3. First run opens a visible Chromium window for you to log in to kimi.com
4. After login, the session is preserved - all subsequent runs are headless
5. Forces `locale=en-US` to ensure consistent English page text for parsing

## Requirements

- Python 3.9+
- Playwright (`pip install playwright`)
- Chromium (`python -m playwright install chromium`)

## License

MIT
