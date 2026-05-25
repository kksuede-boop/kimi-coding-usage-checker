# Kimi Coding Plan Usage Checker

A Playwright-based automation tool to check [Kimi Coding Plan](https://www.kimi.com/code) usage statistics. **Designed for AI agents** — minimal model involvement, just run the script and parse JSON output.

## For AI Agents: Quick Integration

### One-time setup (run these commands in order)

```bash
git clone https://github.com/kksuede-boop/kimi-coding-usage-checker.git ~/kimi-coding-usage-checker
cd ~/kimi-coding-usage-checker
pip install playwright
python -m playwright install chromium
```

### First-time login (requires human interaction ONCE)

```bash
python ~/kimi-coding-usage-checker/check_usage.py --no-headless
```

> Tell the user: "A Chromium window has opened. Please log in to kimi.com, then the window will close automatically."

### Regular usage (fully automated, no human needed)

```bash
python ~/kimi-coding-usage-checker/check_usage.py --output json
```

### Handle the output

```python
import json, subprocess

result = subprocess.run(
    ["python", "~/kimi-coding-usage-checker/check_usage.py", "--output", "json"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)

if data["status"] == "success":
    # Report to user
    print(f"Weekly quota: {data['quota']['weekly_usage_percent']}% used")
    print(f"Rate limit: {data['rate_limit']['usage_percent']}% used")
    print(f"Member: {data['member']['level']}")
elif data["status"] == "login_required":
    # Tell user to run --no-headless once
    print("Session expired. Please run with --no-headless to re-login.")
```

### Error handling for agents

| `status` value | What to do |
|---|---|
| `success` | Parse and report data normally |
| `login_required` | Tell user: "Kimi session expired, please run `python .../check_usage.py --no-headless` to re-login" |
| `error` | Report the `message` field to user |

---

## Features

- Weekly quota usage percentage and reset countdown
- Rate limit status
- Member tier and model access level
- Recent API request history (with total count)
- Uses independent Chromium — **does NOT touch user's Chrome**
- Headless after one-time login

## Output Schema

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
      "request_id": "170bb4c1-...",
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
2. Maintains persistent profile at `~/.kimi-coding-checker/chromium-profile/`
3. First run: visible Chromium window for one-time login
4. After login: all subsequent runs are headless and fully automated
5. Forces `locale=en-US` for consistent English page parsing

## Architecture (for other developers)

```
User/Agent
    |
    v
python check_usage.py --output json   (shell command)
    |
    v
Playwright Chromium (headless, independent instance)
    |
    v
kimi.com/code/console  (navigates, waits for render)
    |
    v
JavaScript evaluation (extracts innerText + table data)
    |
    v
Python regex parsing (structured extraction)
    |
    v
JSON to stdout  (agent reads this)
```

No model/LLM is involved in the runtime. The script does everything deterministically.

## Requirements

- Python 3.9+
- Playwright (`pip install playwright`)
- Chromium (`python -m playwright install chromium`)

## License

MIT
