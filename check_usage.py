#!/usr/bin/env python3
"""
Kimi Coding Plan Usage Checker
Uses Playwright persistent context to check Kimi Coding Plan usage.
Preserves full login state (cookies + localStorage + sessionStorage) across runs.
Outputs structured JSON with quota, rate limit, member info, and recent usage history.
"""

import json
import sys
import os
import re
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Persistent browser profile directory (preserves full auth state)
PROFILE_DIR = Path.home() / ".kimi-coding-checker" / "browser-profile"
CONSOLE_URL = "https://www.kimi.com/code/console?from=kfc_overview_topbar"

# Default Chrome user data directory on Windows
CHROME_USER_DATA = Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"

# Selector that ONLY appears on the authenticated console page
# "Create API Key" button is unique to the logged-in console
AUTH_SELECTOR = "text=Create API Key"
# The login button text indicates NOT authenticated
LOGIN_BUTTON = "text=Log in"


def ensure_dirs():
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def extract_usage_data(page) -> dict:
    """Extract all key usage data from the console page using JS evaluation."""
    result = {
        "status": "success",
        "quota": {},
        "rate_limit": {},
        "member": {},
        "recent_requests": []
    }

    # Wait for the authenticated content to fully render
    page.wait_for_selector(AUTH_SELECTOR, timeout=15000)
    page.wait_for_timeout(2000)  # SPA render time

    # Use JavaScript to extract structured data from the page DOM
    data = page.evaluate("""() => {
        const result = { tables: [] };
        const main = document.querySelector('main') || document.body;
        result.fullText = main.innerText;

        // Extract all tables
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

    # Debug output
    if os.environ.get("KIMI_DEBUG"):
        print("=== RAW PAGE TEXT (first 2000 chars) ===", file=sys.stderr)
        print(full_text[:2000], file=sys.stderr)
        print("=== END ===", file=sys.stderr)

    # Parse line by line for quota/rate info
    lines = [l.strip() for l in full_text.split('\n') if l.strip()]

    # Find Weekly usage quota
    for i, line in enumerate(lines):
        if line == 'Weekly usage' or 'Weekly usage' in line:
            # Search nearby lines for percentage and reset time
            search_range = lines[max(0, i-3):min(len(lines), i+6)]
            for nearby in search_range:
                pct_match = re.match(r'^(\d+)%$', nearby)
                if pct_match and "quota" not in str(result["quota"].get("weekly_usage_percent")):
                    result["quota"]["weekly_usage_percent"] = int(pct_match.group(1))
                reset_match = re.search(r'Resets in (\d+)\s*(hours?|minutes?|seconds?)', nearby)
                if reset_match:
                    result["quota"]["resets_in_value"] = int(reset_match.group(1))
                    result["quota"]["resets_in_unit"] = reset_match.group(2)
            break

    # Find Rate limit info (search after quota section)
    found_quota = False
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

    # Find member info
    for line in lines:
        member_match = re.search(r'\b(Free|Andante|Moderato|Allegretto|Allegro|Pro|Enterprise)\b', line)
        if member_match:
            # Skip if it's in a pricing section context
            if 'Subscribe' not in line and '/' not in line and '\xa5' not in line:
                result["member"]["level"] = member_match.group(1)
                break

    # Find model access
    for line in lines:
        model_match = re.search(r'(K\d+\.?\d*)\s*(Flagship model|Standard model)?', line)
        if model_match:
            model_name = model_match.group(1)
            model_type = model_match.group(2) or ""
            result["member"]["model_access"] = f"{model_name} {model_type}".strip()
            break

    # Extract usage history from tables
    tables = data.get("tables", [])
    for table in tables:
        headers = table.get("headers", [])
        header_text = " ".join(headers).lower()
        if "request" in header_text or "source" in header_text or "status" in header_text:
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

    # Total record count
    total_match = re.search(r'(\d+)\s*records?\s*in\s*total', full_text)
    if total_match:
        result["total_records"] = int(total_match.group(1))

    return result


def check_usage(headless=True, use_chrome_profile=False) -> dict:
    """Main function: use persistent context to check Kimi Coding Plan usage."""
    ensure_dirs()

    with sync_playwright() as p:
        # Determine which user data directory to use
        if use_chrome_profile:
            # Use the user's actual Chrome profile (Chrome must be closed!)
            user_data_dir = str(CHROME_USER_DATA)
            if not CHROME_USER_DATA.exists():
                return {"status": "error",
                        "message": f"Chrome user data not found at: {CHROME_USER_DATA}"}
            print(f"Using Chrome profile: {user_data_dir}", file=sys.stderr)
        else:
            user_data_dir = str(PROFILE_DIR)

        # Launch persistent context
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
                channel="chrome",
                viewport={"width": 1280, "height": 900},
                args=["--disable-blink-features=AutomationControlled"]
            )
        except Exception as e:
            if "already running" in str(e).lower() or "lock" in str(e).lower():
                return {"status": "error",
                        "message": "Chrome is running. Close Chrome first, or use without --chrome-profile."}
            raise

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(CONSOLE_URL, wait_until="domcontentloaded", timeout=30000)

        # Wait for page to stabilize
        page.wait_for_timeout(3000)

        # Check auth state: "Create API Key" only exists on authenticated console
        logged_in = False
        try:
            page.wait_for_selector(AUTH_SELECTOR, timeout=8000)
            logged_in = True
        except PlaywrightTimeout:
            logged_in = False

        if not logged_in:
            if headless:
                context.close()
                return {"status": "login_required",
                        "message": "Not logged in. Run with --no-headless to log in interactively."}
            else:
                # Visible mode - wait for user to log in
                print("Not logged in. Please log in to Kimi in the browser window.", file=sys.stderr)
                print("After login, navigate to: " + CONSOLE_URL, file=sys.stderr)
                print("Waiting for login (timeout: 180s)...", file=sys.stderr)
                try:
                    page.wait_for_selector(AUTH_SELECTOR, timeout=180000)
                    print("Login successful!", file=sys.stderr)
                except PlaywrightTimeout:
                    context.close()
                    return {"status": "error", "message": "Login timeout (180s)."}
        else:
            if not headless:
                print("Already logged in.", file=sys.stderr)

        # Extract data
        data = extract_usage_data(page)
        context.close()
        return data


def main():
    parser = argparse.ArgumentParser(description="Check Kimi Coding Plan usage")
    parser.add_argument("--no-headless", action="store_true",
                        help="Show browser window (needed for first login)")
    parser.add_argument("--chrome-profile", action="store_true",
                        help="Use existing Chrome profile (Chrome must be closed)")
    parser.add_argument("--login", action="store_true",
                        help="Force re-login (delete saved browser profile)")
    parser.add_argument("--output", choices=["json", "text"], default="json",
                        help="Output format (default: json)")

    args = parser.parse_args()

    if args.login:
        import shutil
        if PROFILE_DIR.exists():
            shutil.rmtree(PROFILE_DIR, ignore_errors=True)
        print("Cleared browser profile. Will prompt for login.", file=sys.stderr)

    headless = not args.no_headless

    result = check_usage(headless=headless, use_chrome_profile=args.chrome_profile)

    if args.output == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result.get("status") == "error" or result.get("status") == "login_required":
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
