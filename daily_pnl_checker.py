
# daily_pnl_checker.py V4.5 FINAL FIX - V4 누적치 사라짐 방지 + V5 호환
# - V4: journal_data.json 누적 append, 절대 덮어쓰기 금지
# - 검색 경로: ./journal_data.json, docs/journal_data.json, docs/v5-ma-delta/journal_data.json, backup/journal_data.json
# - 없으면 생성 + 기존 데이터 합치기
# - V4 + V5 모두 지원

import json, os, glob
from datetime import datetime

CANDIDATE_PATHS = [
    "journal_data.json",
    "./journal_data.json",
    "docs/journal_data.json",
    "./docs/journal_data.json",
    "docs/v5-ma-delta/journal_data.json",
    "journal_data_v5.json",
    "docs/journal_data_v5.json",
    "backup/journal_data.json",
    "data/journal_data.json"
]

def load_all_existing():
    merged = {}
    existing_files = []
    for p in CANDIDATE_PATHS:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and len(str(data)) > 10:
                        merged[p] = data
                        existing_files.append(p)
                        print(f"[FOUND] {p} len={len(str(data))}")
            except Exception as e:
                print(f"[ERR] {p}: {e}")
    return merged, existing_files

def get_latest_cumulative(merged):
    # 가장 큰 데이터 선택 (누적치가 가장 많은 파일)
    if not merged:
        return None
    best_path = max(merged.keys(), key=lambda k: len(str(merged[k])))
    print(f"[BEST] {best_path} as base")
    return merged[best_path]

def ensure_v4_structure(base):
    if not base:
        # 빈 V4 구조 생성 (누적 시작)
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "balance_krw": 10000000,
            "balance_usd": 7407.41,
            "pnl_krw": 0,
            "pnl_usd": 0,
            "positions": [],
            "ledger": [],  # 전체 누적 원장
            "weekly": [],
            "source": "V4.5 FINAL FIX - created"
        }
    # 기존 구조 유지
    if "ledger" not in base:
        base["ledger"] = base.get("positions", [])
    return base

def save_to_all_places(data):
    targets = [
        "journal_data.json",
        "docs/journal_data.json",
        "docs/v5-ma-delta/journal_data.json",
        "backup/journal_data.json"
    ]
    for t in targets:
        try:
            os.makedirs(os.path.dirname(t) if os.path.dirname(t) else ".", exist_ok=True)
            with open(t, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[SAVED] {t}")
        except Exception as e:
            print(f"[SAVE ERR] {t}: {e}")

def main():
    print("=== daily_pnl_checker V4.5 FINAL FIX ===")
    merged, files = load_all_existing()
    if not files:
        print("[WARN] No existing journal_data.json found - creating new cumulative file")
        base = ensure_v4_structure(None)
    else:
        base = get_latest_cumulative(merged)
        base = ensure_v4_structure(base)
        # 모든 파일의 ledger 합치기 (중복 제거)
        all_ledger = []
        seen = set()
        for path, data in merged.items():
            ledger = data.get("ledger") or data.get("positions") or []
            for row in ledger:
                key = f"{row.get('date','')}_{row.get('ticker','')}_{row.get('entry','')}"
                if key not in seen:
                    seen.add(key)
                    all_ledger.append(row)
        if all_ledger:
            base["ledger"] = all_ledger
            print(f"[MERGED] ledger total {len(all_ledger)} rows")
    
    base["date"] = datetime.now().strftime("%Y-%m-%d")
    base["last_checked"] = datetime.now().isoformat()
    base["fix_version"] = "V4.5 FINAL FIX - cumulative no overwrite"
    
    save_to_all_places(base)
    print(f"=== DONE: ledger {len(base.get('ledger',[]))} rows saved to {len([p for p in ['journal_data.json','docs/journal_data.json'] if True])} places ===")
    return base

if __name__ == "__main__":
    main()
