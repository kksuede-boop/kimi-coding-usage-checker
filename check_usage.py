#!/usr/bin/env python3
"""
Kimi Coding Plan Usage Checker
Uses Playwright with its own independent Chromium browser + persistent profile.
Does NOT touch user's Chrome at all.
First run: opens a Chromium window for one-time login.
Subsequent runs: headless, fully automated.
Outputs structured JSON with quota, rate limit, member info, and recent usage history.
"""

import json
import sys
import os
import re
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Persistent browser profile (independent from user's Chrome)
PROFILE_DIR = Path.home() / ".kimi-coding-checker" / "chromium-profile"
CONSOLE_URL = "https://www.kimi.com/code/console?from=kfc_overview_topbar"

# Auth detection: "API Keys" heading only appears on authenticated console
AUTH_SELECTOR = "text=API Keys"


def ensure_dirs():
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def extract_usage_data(page) -> dict:
    """Extract all key usage data from the console page."""
    result = {
        "status": "success",
        "quota": {},
        "rate_limit": {},
        "member": {},
        "recent_requests": []
    }

    # Wait for authenticated content to fully render
    page.wait_for_selector(AUTH_SELECTOR, timeout=15000)
    # Wait for all dynamic content to render (SPA needs time)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # Use JavaScript to extract page text and table data
    data = page.evaluate("""() => {
        const result = { tables: [] };
        const main = document.querySelector('main') || document.body;
        result.fullText = main.innerText;

        const tables = document.querySelectorAll('table');
        tables.forEach((table, idx) => {
            const tableData = { index: idx, headers: [], rows: [] };
            const headerCells = table.querySelectorAll('thead th, thead td, tr:first-child th');
            headerCells.forEach(cell => tableData.headers.push(cell.innerText.trim()));
            const bodyRows = table.querySelectorAll('tbody tr');
            bodyRows.forEach(row => {
                const cells = row.querySelectorAll('td');
                const rowData = [];
                cells.forEach(cell => rowData.push(cell.innerText.trim()));
                if (rowData.length > 0) tableData.rows.push(rowData);
            });
            result.tables.push(tableData);
        });

        return result;
    }""")

    full_text = data.get("fullText", "")

    if os.environ.get("KIMI_DEBUG"):
        print("=== RAW PAGE TEXT (first 3000 chars) ===", file=sys.stderr)
        print(full_text[:3000], file=sys.stderr)
        print("=== END ===", file=sys.stderr)

    lines = [l.strip() for l in full_text.split('\n') if l.strip()]

    # --- Extract Weekly usage ---
    for i, line in enumerate(lines):
        if 'Weekly usage' in line:
            search_range = lines[max(0, i-3):min(len(lines), i+6)]
            for nearby in search_range:
                pct_match = re.match(r'^(\d+)%$', nearby)
                if pct_match and not result["quota"].get("weekly_usage_percent"):
                    result["quota"]["weekly_usage_percent"] = int(pct_match.group(1))
                reset_match = re.search(r'Resets in (\d+)\s*(hours?|minutes?|seconds?)', nearby)
                if reset_match and not result["quota"].get("resets_in_value"):
                    result["quota"]["resets_in_value"] = int(reset_match.group(1))
                    result["quota"]["resets_in_unit"] = reset_match.group(2)
            break

    # --- Extract Rate limit ---
    for i, line in enumerate(lines):
        if 'Rate limit' in line:
            search_range = lines[max(0, i-3):min(len(lines), i+6)]
            for nearby in search_range:
                pct_match = re.match(r'^(\d+)%$', nearby)
                if pct_match:
                    result["rate_limit"]["usage_percent"] = int(pct_match.group(1))
                reset_match = re.search(r'Resets in (\d+)\s*(hours?|minutes?|seconds?)', nearby)
                if reset_match:
                    result["rate_limit"]["resets_in_value"] = int(reset_match.group(1))
                    result["rate_limit"]["resets_in_unit"] = reset_match.group(2)
            break

    # --- Extract Member info ---
    for line in lines:
        member_match = re.search(r'\b(Free|Andante|Moderato|Allegretto|Allegro|Pro|Enterprise)\b', line)
        if member_match:
            if 'Subscribe' not in line and '/' not in line and '\xa5' not in line:
                result["member"]["level"] = member_match.group(1)
                break

    # --- Extract Model access ---
    for line in lines:
        model_match = re.search(r'(K\d+\.?\d*)\s*(Flagship model|Standard model)?', line)
        if model_match:
            model_name = model_match.group(1)
            model_type = model_match.group(2) or ""
            result["member"]["model_access"] = f"{model_name} {model_type}".strip()
            break

    # --- Extract Usage history table ---
    # The usage history table has "Datetime" in headers, distinguishing from API Keys table
    tables = data.get("tables", [])
    for table in tables:
        headers = table.get("headers", [])
        header_text = " ".join(headers).lower()
        if "datetime" in header_text or "call type" in header_text:
            for row in table.get("rows", []):
                if len(row) >= 5:
                    record = {
                        "request_id": row[0],
                        "name": row[1],
                        "source": row[2],
                        "call_type": row[3],
                        "datetime": row[4],
                        "status": row[5] if len(row) > 5 else ""
                    }
                    result["recent_requests"].append(record)
            break

    # --- Total record count ---
    total_match = re.search(r'(\d+)\s*records?\s*in\s*total', full_text)
    if total_match:
        result["total_records"] = int(total_match.group(1))

    return result


def check_usage(headless=True) -> dict:
    """
    Use Playwright's own Chromium with persistent profile.
    Completely independent from user's Chrome browser.
    """
    ensure_dirs()

    with sync_playwright() as p:
        # Launch Playwright's bundled Chromium with persistent context
        # This is a SEPARATE browser from the user's Chrome
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=headless,
            # Do NOT use channel="chrome" - we want Playwright's own Chromium
            locale="en-US",  # Force English locale for consistent page text
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(CONSOLE_URL, wait_until="networkidle", timeout=30000)

        # Wait for page to stabilize
        page.wait_for_timeout(3000)

        # Check auth state
        logged_in = False
        try:
            page.wait_for_selector(AUTH_SELECTOR, timeout=8000)
            logged_in = True
        except PlaywrightTimeout:
            logged_in = False

        if not logged_in:
            if headless:
                context.close()
                return {
                    "status": "login_required",
                    "message": "Not logged in. Run with --no-headless for first-time login."
                }
            else:
                print("Please log in to Kimi in the browser window.", file=sys.stderr)
                print("Waiting for login (timeout: 180s)...", file=sys.stderr)
                try:
                    # User might need to navigate after login
                    page.wait_for_selector(AUTH_SELECTOR, timeout=180000)
                    print("Login successful! Session saved.", file=sys.stderr)
                except PlaywrightTimeout:
                    context.close()
                    return {"status": "error", "message": "Login timeout (180s)."}
        else:
            print("Logged in (using saved session).", file=sys.stderr)

        # Extract data
        data = extract_usage_data(page)
        context.close()
        return data


def main():
    parser = argparse.ArgumentParser(
        description="Check Kimi Coding Plan usage (uses independent Playwright Chromium)"
    )
    parser.add_argument("--no-headless", action="store_true",
                        help="Show browser window (needed for first-time login)")
    parser.add_argument("--login", action="store_true",
                        help="Force re-login (clear saved browser profile)")
    parser.add_argument("--output", choices=["json", "text"], default="json",
                        help="Output format (default: json)")

    args = parser.parse_args()

    if args.login:
        import shutil
        if PROFILE_DIR.exists():
            shutil.rmtree(PROFILE_DIR, ignore_errors=True)
        print("Cleared saved profile. Will prompt for login.", file=sys.stderr)

    headless = not args.no_headless

    result = check_usage(headless=headless)

    if args.output == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result.get("status") != "success":
            print(f"Error: {result.get('message', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)

        print("=== Kimi Coding Plan Usage ===")
        print()

        quota = result.get("quota", {})
        if quota:
            pct = quota.get("weekly_usage_percent", "?")
            reset_val = quota.get("resets_in_value", "?")
            reset_unit = quota.get("resets_in_unit", "hours")
            print(f"Weekly Quota: {pct}% used, resets in {reset_val} {reset_unit}")

        rate = result.get("rate_limit", {})
        if rate:
            pct = rate.get("usage_percent", "?")
            reset_val = rate.get("resets_in_value", "?")
            reset_unit = rate.get("resets_in_unit", "")
            print(f"Rate Limit:  {pct}% used, resets in {reset_val} {reset_unit}")

        member = result.get("member", {})
        if member:
            print(f"Member Level: {member.get('level', '?')}")
            print(f"Model Access: {member.get('model_access', '?')}")

        total = result.get("total_records")
        if total:
            print(f"Total API Requests: {total}")

        recent = result.get("recent_requests", [])
        if recent:
            print(f"\nRecent Requests (showing {min(5, len(recent))} of {len(recent)}):")
            for r in recent[:5]:
                print(f"  [{r.get('status', '')}] {r.get('source', '')} @ {r.get('datetime', '')}")


if __name__ == "__main__":
    main()
