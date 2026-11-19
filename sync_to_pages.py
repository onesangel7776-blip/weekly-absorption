
# sync_to_pages.py V4/V5 SEPARATE FIX - V5가 V4 덮어쓰기 금지
import json, os

FILES_TO_SYNC = [
    # V4 - V4 전용 (주간 스윙)
    ("journal_data.json", ["docs/journal_data.json"]),
    ("absorption.json", ["docs/absorption.json"]),
    # V5 - V5 전용 (5티커 15슬롯) - V4 절대 건드리지 않음
    ("journal_data_v5.json", ["docs/journal_data_v5.json", "docs/v5-ma-delta/journal_data_v5.json", "docs/v5-ma-delta/journal_data.json"]),
    ("absorption_v5.json", ["docs/absorption_v5.json", "docs/v5-ma-delta/absorption_v5.json", "docs/v5-ma-delta/absorption.json"]),
    ("best_tf_per_ticker.json", ["docs/best_tf_per_ticker.json", "docs/v5-ma-delta/best_tf_per_ticker.json"]),
    ("best_tf_per_ticker_v5.json", ["docs/best_tf_per_ticker.json", "docs/v5-ma-delta/best_tf_per_ticker.json"]),
]

def sync():
    print("=== sync_to_pages V4/V5 SEPARATE FIX ===")
    for src, dsts in FILES_TO_SYNC:
        src_path = src
        if not os.path.exists(src_path):
            # 다른 위치에서 찾기
            alt = [f"docs/{src}", f"data/{src}", f"backup/{src}", f"docs/v5-ma-delta/{src}"]
            found = None
            for a in alt:
                if os.path.exists(a):
                    found = a
                    break
            if not found:
                print(f"[SKIP] {src} not found anywhere")
                continue
            src_path = found
        
        try:
            with open(src_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"[FOUND] {src_path} -> {len(str(data))} chars")
        except Exception as e:
            print(f"[ERR] {src_path}: {e}")
            continue
        
        for dst in dsts:
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, 'w', encoding='utf-8') as out:
                    json.dump(data, out, ensure_ascii=False, indent=2)
                print(f"[SYNCED] {src_path} -> {dst}")
            except Exception as e:
                print(f"[ERR] {dst}: {e}")

if __name__ == "__main__":
    sync()
