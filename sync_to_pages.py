"""
sync_to_pages.py - V5 MA Delta DAILY - KST FIXED - D2026-11-17
Root JSON -> docs/ + docs/v5-ma-delta/ copy for GitHub Pages
Fixes 404: absorption_v5.json not in docs
Copy: absorption_v5.json, journal_data_v5.json, best_tf_per_ticker.json, journal_data.json, absorption.json
"""

import os
import shutil
import json
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
    KST = ZoneInfo("Asia/Seoul")
except:
    KST = timezone(timedelta(hours=9))

def log(msg):
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")
    print(f"[{now}] {msg}")

def ensure_dirs():
    os.makedirs("docs", exist_ok=True)
    os.makedirs("docs/v5-ma-delta", exist_ok=True)

def copy_json(src, dst_list):
    """Copy src to each dst in list, create if src exists, warn if not"""
    if not os.path.exists(src):
        log(f"SKIP {src} not found")
        return False
    try:
        # validate json
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
        # log top2 if present
        top2 = data.get("top2_distinct") or data.get("top2") or data.get("best_tf_per_ticker") or ""
        log(f"FOUND {src} size {os.path.getsize(src)} bytes top2={top2}")
    except Exception as e:
        log(f"WARN {src} invalid json: {e} - still copying")
    
    for dst in dst_list:
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            log(f"COPIED {src} -> {dst}")
        except Exception as e:
            log(f"FAIL copy {src} -> {dst}: {e}")
            return False
    return True

def main():
    log("=== V5 sync_to_pages START ===")
    ensure_dirs()

    # Map: root file -> destinations
    mapping = {
        "absorption_v5.json": ["docs/absorption_v5.json", "docs/v5-ma-delta/absorption_v5.json"],
        "journal_data_v5.json": ["docs/journal_data_v5.json", "docs/v5-ma-delta/journal_data_v5.json"],
        "best_tf_per_ticker.json": ["docs/best_tf_per_ticker.json", "docs/v5-ma-delta/best_tf_per_ticker.json"],
        "journal_data.json": ["docs/journal_data.json", "docs/v5-ma-delta/journal_data.json"],
        "absorption.json": ["docs/absorption.json"],
        "journal_data_v5.json": ["docs/journal_data_v5.json", "docs/v5-ma-delta/journal_data_v5.json"],  # compat
    }

    # Also handle scoring_engine generates in root, but workflow may generate in docs directly
    # So also check reverse: if docs version newer, copy to root? No, root is source of truth per v5-daily.yml
    copied = 0
    for src, dsts in mapping.items():
        # avoid duplicate keys - use set
        if copy_json(src, dsts):
            copied += 1

    # Extra: if absorption_v5.json not in root but in docs/v5-ma-delta (manual edit), copy back
    fallback_sources = [
        ("docs/v5-ma-delta/absorption_v5.json", "absorption_v5.json"),
        ("docs/absorption_v5.json", "absorption_v5.json"),
    ]
    for fsrc, fdst in fallback_sources:
        if not os.path.exists(fdst) and os.path.exists(fsrc):
            try:
                shutil.copy2(fsrc, fdst)
                log(f"FALLBACK COPIED {fsrc} -> {fdst}")
                # then propagate
                copy_json(fdst, ["docs/absorption_v5.json", "docs/v5-ma-delta/absorption_v5.json"])
            except Exception as e:
                log(f"FALLBACK FAIL {fsrc}: {e}")

    # Verify final files exist
    checks = [
        "docs/absorption_v5.json",
        "docs/v5-ma-delta/absorption_v5.json",
        "docs/journal_data_v5.json",
        "docs/v5-ma-delta/journal_data_v5.json",
        "docs/best_tf_per_ticker.json",
    ]
    log("=== VERIFY ===")
    for p in checks:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                date = d.get("date","?")
                slots = len(d.get("slots",[]))
                log(f"OK {p} date={date} slots={slots}")
            except Exception as e:
                log(f"WARN {p} exists but invalid: {e}")
        else:
            log(f"MISSING {p}")

    log(f"=== V5 sync_to_pages DONE copied {copied} types ===")

if __name__ == "__main__":
    main()
