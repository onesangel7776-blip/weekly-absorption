
# sync_to_pages.py FINAL FIX - V4 + V5 모두 docs로 복사
import json, os, shutil

FILES_TO_SYNC = [
    ("journal_data.json", ["docs/journal_data.json", "docs/v5-ma-delta/journal_data.json"]),
    ("journal_data_v5.json", ["docs/journal_data_v5.json", "docs/v5-ma-delta/journal_data_v5.json", "docs/journal_data.json"]),
    ("absorption_v5.json", ["docs/absorption_v5.json", "docs/v5-ma-delta/absorption_v5.json", "docs/absorption.json"]),
    ("absorption.json", ["docs/absorption.json"]),
    ("best_tf_per_ticker.json", ["docs/best_tf_per_ticker.json", "docs/v5-ma-delta/best_tf_per_ticker.json"]),
    ("best_tf_per_ticker_v5.json", ["docs/best_tf_per_ticker.json", "docs/v5-ma-delta/best_tf_per_ticker.json"]),
]

def sync():
    print("=== sync_to_pages FINAL FIX V4+V5 ===")
    for src, dsts in FILES_TO_SYNC:
        if not os.path.exists(src):
            alt_paths = [f"docs/{src}", f"data/{src}", f"backup/{src}"]
            found = None
            for ap in alt_paths:
                if os.path.exists(ap):
                    found = ap
                    break
            if not found:
                print(f"[SKIP] {src} not found")
                continue
            src = found
        
        try:
            with open(src, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"[FOUND] {src}")
        except Exception as e:
            print(f"[ERR] load {src}: {e}")
            continue
        
        for dst in dsts:
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, 'w', encoding='utf-8') as out:
                    json.dump(data, out, ensure_ascii=False, indent=2)
                print(f"[SYNCED] {src} -> {dst}")
            except Exception as e:
                print(f"[ERR] {dst}: {e}")

if __name__ == "__main__":
    sync()
