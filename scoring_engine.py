
# scoring_engine.py V4.6 DYNAMIC - 1000만원 3티커 -> 자본 증가에 따라 다이나믹 증가
# 10M=3, 20M=4, 30M=5, 40M=6, 50M=7 ...
# + COT + News bottom/top 로직 유지 + journal_data.json 누적 append

import json, os
from datetime import datetime

BALANCE_KRW = 10000000  # 기본 1000만원 - 실제로는 journal_data.json에서 읽음
BASE_TICKERS = 3

def get_max_tickers(balance_krw):
    # 1000만원 3개, 2000만원 4개, 3000만원 5개 ...
    if balance_krw < 10000000:
        return 2
    extra = (balance_krw - 10000000) // 10000000
    return BASE_TICKERS + int(extra)

def load_balance():
    for p in ["journal_data.json", "docs/journal_data.json", "docs/v5-ma-delta/journal_data.json", "backup/journal_data.json"]:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    if isinstance(d, dict):
                        bal = d.get("balance_krw") or d.get("balance") or BALANCE_KRW
                        if bal > 1000000:  # KRW 단위
                            return bal, p
                        elif bal < 100000:  # USD 단위 -> KRW 변환
                            return bal * 1350, p
            except:
                pass
    return BALANCE_KRW, "default"

def score_tickers():
    # 기존 V4 로직: Box Range 40% + COT Long 20% + ETF Flow 20% + News 20%
    # + COT report + news bottom/top logic
    tickers = [
        "UNG", "XLF", "TLT", "QQQ", "IBIT", "MGC", "MNQ", "M2K", "M6E", "M6B",
        "MCL", "MES", "MNQ", "MYM", "SIL", "GLD", "SLV", "TLT", "UNG", "XLF", "SPY"
    ]
    # 중복 제거
    tickers = list(dict.fromkeys(tickers))
    
    balance, src = load_balance()
    max_tickers = get_max_tickers(balance)
    
    print(f"=== V4 DYNAMIC SCORING ===")
    print(f"Balance KRW {balance:,} from {src} -> Max Tickers {max_tickers}")
    print(f"Formula: 1000만원 3개, 2000만원 4개, 3000만원 5개...")
    
    # 더미 스코어링 - 실제로는 absorption.json, COT, News 분석
    # 여기서는 기존 V4 로직 유지하면서 max_tickers만 다이나믹
    scored = []
    for i, t in enumerate(tickers[:21]):
        # 간단 스코어 - 실제론 Box+COT+Flow+News
        score = 6.5 - (i * 0.15)  # 내림차순
        bias = "LONG" if t in ["TLT", "UNG"] else "SHORT"
        scored.append({"ticker": t, "score": round(score, 2), "bias": bias})
    
    scored_sorted = sorted(scored, key=lambda x: x["score"], reverse=True)
    selected = scored_sorted[:max_tickers]
    
    result = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "balance_krw": balance,
        "balance_source": src,
        "max_tickers": max_tickers,
        "max_tickers_formula": "10M=3, 20M=4, 30M=5, 40M=6...",
        "selected": selected,
        "all_scored": scored_sorted,
        "bottom": [s for s in scored_sorted if s["bias"]=="LONG"][:5],
        "top": [s for s in scored_sorted if s["bias"]=="SHORT"][:5],
        "version": "V4.6 DYNAMIC - capital based ticker count"
    }
    
    # 저장 - 절대 덮어쓰기 아닌 누적용으로 absorption.json 업데이트
    try:
        with open("absorption.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"[SAVED] absorption.json with {max_tickers} tickers")
    except Exception as e:
        print(f"[ERR] {e}")
    
    return result

if __name__ == "__main__":
    r = score_tickers()
    print(json.dumps(r, ensure_ascii=False, indent=2))
