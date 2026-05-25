---
name: kimi-coding-usage-checker
description: Check Kimi Coding Plan usage statistics (quota, rate limit, member level) via Playwright browser automation. Use when the user asks about Kimi coding plan quota, remaining usage, rate limits, or subscription status.
version: 1.2.0
---

# Kimi Coding Plan Usage Checker

Query Kimi Coding Plan usage via headless browser. Zero model involvement at runtime — just execute one shell command and parse JSON stdout.

## Setup (one-time, run in order)

```bash
# 1. Clone the tool
git clone https://github.com/kksuede-boop/kimi-coding-usage-checker.git ~/.kimi-coding-usage-checker-tool

# 2. Install dependencies
pip install playwright && python -m playwright install chromium

# 3. First-time login (opens a Chromium window, user logs in once)
python ~/.kimi-coding-usage-checker-tool/check_usage.py --no-headless
```

> When running step 3, tell the user: "A browser window will open. Please log in to your Kimi account at kimi.com, then wait for the window to close automatically."

## Steps (regular usage)

1. Execute the script:
   ```bash
   python ~/.kimi-coding-usage-checker-tool/check_usage.py --output json
   ```

2. Capture stdout. The output is a single JSON object. Parse it.

3. Check `status` field:
   - If `"success"` → report data to user (see "How to report" below)
   - If `"login_required"` → tell user: "Kimi session expired. I'll open a browser for you to re-login." Then run: `python ~/.kimi-coding-usage-checker-tool/check_usage.py --no-headless --login`
   - If `"error"` → report the `message` field to user

4. **How to report** (template):
   ```
   Kimi Coding Plan 用量：
   - 周用量：{quota.weekly_usage_percent}% 已用，{quota.resets_in_value} {quota.resets_in_unit}后重置
   - 速率限制：{rate_limit.usage_percent}% 已用，{rate_limit.resets_in_value} {rate_limit.resets_in_unit}后重置
   - 会员等级：{member.level}
   - 模型权限：{member.model_access}
   - 总请求数：{total_records}
   ```

## Output Schema

```json
{
  "status": "success | login_required | error",
  "message": "(only when status != success)",
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
      "request_id": "uuid",
      "name": "api-key-name",
      "source": "claude-code/0.1.0",
      "call_type": "Model Inference",
      "datetime": "2026-05-25 15:28:45",
      "status": "Success"
    }
  ]
}
```

## Important Notes

- Does NOT touch user's Chrome browser. Uses its own independent Chromium instance.
- Session is stored at `~/.kimi-coding-checker/chromium-profile/` — persists across runs.
- The script takes ~8 seconds to run (browser launch + page load + extraction).
- All stderr output is informational/debug. Only stdout is the JSON result.
- Set env `KIMI_DEBUG=1` to dump raw page text to stderr for troubleshooting.

## Pitfalls

- If setup step 2 is missing, you'll get `ModuleNotFoundError: playwright`. Run `pip install playwright && python -m playwright install chromium`.
- If `status` is `login_required` after a long period, the Kimi session has expired. Re-run with `--no-headless --login`.
- Do NOT run with `--no-headless` in a headless environment (CI, cron, SSH without display). It requires a GUI.
- The script forces `locale=en-US` to ensure English page text for consistent parsing.

## Verification

After running, verify:
- Exit code is 0
- stdout is valid JSON
- `status` is `"success"`
- `quota.weekly_usage_percent` is a number 0-100
- `member.level` is non-empty
