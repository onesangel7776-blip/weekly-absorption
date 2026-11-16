# scoring_engine_v5.py - V5 MA Delta DAILY 3-TRACK + 21 TICKER BEST TF TRACKING
# 1m/2m/3m 각각 50K 프랍 계정 독립 + 동일 티커 2개 3분봉 동시 진입 + 최적 분봉 추적
# KST 07:00 갱신, PROP LOCKED, maejip/balsan 구분

import json
import os
import random
from datetime import datetime
import pytz

# ================= CONFIG =================
KST = pytz.timezone("Asia/Seoul")
TODAY_KST = datetime.now(KST).strftime("%Y-%m-%d")
DATETIME_KST = datetime.now(KST).isoformat()

PROP_LOCKED = True
SAME_TICKER_ACROSS_TF = True  # 같은 Top2 티커를 1m/2m/3m 모두 동일 진입 - 튜닝용
PROP_PER_FAMILY = {
    "Father": {"tf": "1m", "capital": 50000, "daily_loss": 700, "daily_profit": 500, "color": "#ffcc00", "owner": "나"},
    "Son": {"tf": "2m", "capital": 50000, "daily_loss": 700, "daily_profit": 500, "color": "#00aaff", "owner": "아들"},
    "Daughter": {"tf": "3m", "capital": 50000, "daily_loss": 700, "daily_profit": 500, "color": "#aa66ff", "owner": "딸"}
}

TICKER_THRESHOLDS = {
    "MGC": 2000, "MNQ": 8000, "MNG": 1500, "M2K": 6000, "MES": 5000,
    "MCL": 3000, "M6E": 2000, "M6A": 2000, "M6B": 2000,
    "MYM": 4000, "MET": 2500, "M6B": 2000, "MGA": 2000, "MJY": 2000, "MSF": 2000,
    "MBT": 2000, "SIL": 2500, "MGC": 2000, "MING": 1500, "MNG": 1500
}
# 21 TICKER FULL LIST
TICKERS_21 = ["MGC","MNG","M2K","MES","MNQ","MYM","MCL","MBT","MET","M6E","M6B","MGA","MJY","MSF","MNG","MING","SIL","CPER","XLE","DBA","MCL"]

# ================= BEST TF TRACKING - 21개 티커별 최적 분봉 =================
def load_journal_for_best_tf():
    """journal_data_v5.json에서 21개 티커별 1m/2m/3m 누적 P&L 계산해서 최적 분봉 추적"""
    journal_paths = [
        "./docs/v5-ma-delta/journal_data_v5.json",
        "./docs/journal_data_v5.json",
        "./journal_data_v5.json"
    ]
    all_positions = []
    for p in journal_paths:
        try:
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_positions = data
                    elif isinstance(data, dict):
                        all_positions = data.get("positions", [])
                    break
        except:
            continue
    
    # 21개 티커별 TF별 P&L 집계
    best_tf_per_ticker = {}
    ticker_tf_stats = {}
    
    for ticker in TICKERS_21:
        ticker_tf_stats[ticker] = {
            "1m": {"pnl": 0, "wins": 0, "count": 0, "win_rate": 0},
            "2m": {"pnl": 0, "wins": 0, "count": 0, "win_rate": 0},
            "3m": {"pnl": 0, "wins": 0, "count": 0, "win_rate": 0}
        }
    
    for pos in all_positions:
        ticker = pos.get("ticker")
        tf = pos.get("tf")
        pnl = pos.get("pnlKrw", pos.get("pnl", 0))
        if ticker in ticker_tf_stats and tf in ["1m","2m","3m"]:
            ticker_tf_stats[ticker][tf]["pnl"] += pnl
            ticker_tf_stats[ticker][tf]["count"] += 1
            if pnl > 0:
                ticker_tf_stats[ticker][tf]["wins"] += 1
    
    # 최적 분봉 결정
    for ticker, tf_data in ticker_tf_stats.items():
        best_tf = "1m"
        best_pnl = -999999999
        best_win_rate = 0
        for tf in ["1m","2m","3m"]:
            pnl = tf_data[tf]["pnl"]
            count = tf_data[tf]["count"]
            wins = tf_data[tf]["wins"]
            win_rate = (wins / count * 100) if count > 0 else 0
            tf_data[tf]["win_rate"] = round(win_rate, 1)
            # P&L과 승률 종합으로 최적 결정
            score = pnl * 0.7 + win_rate * 1000 * 0.3  # P&L 70% + 승률 30%
            if score > best_pnl or (count == 0 and best_pnl == -999999999):
                best_pnl = score
                best_tf = tf
                best_win_rate = win_rate
        
        best_tf_per_ticker[ticker] = {
            "best_tf": best_tf,
            "best_pnl": ticker_tf_stats[ticker][best_tf]["pnl"],
            "best_win_rate": ticker_tf_stats[ticker][best_tf]["win_rate"],
            "stats": ticker_tf_stats[ticker]
        }
    
    return best_tf_per_ticker, ticker_tf_stats

# ================= SCORING =================
def calc_score(ticker, mock_delta, ma_convergence):
    """V5 Score: MA 10개 수렴 0.15% + 매집/발산 + CVD + 위치 + FLIP"""
    threshold = TICKER_THRESHOLDS.get(ticker, 2000)
    maejip = mock_delta.get("maejip", 0)
    balsan = mock_delta.get("balsan", 0)
    location = mock_delta.get("location", "VAL")
    
    # Base score from maejip vs threshold
    base = min(100, abs(maejip) / threshold * 40)
    # Balsan bonus
    balsan_bonus = min(20, abs(balsan) / 1000 * 5)
    # Location bonus: VAL/POC best
    loc_bonus = 15 if location in ["VAL","POC"] else 8 if location in ["VAH","D-100"] else 5
    # MA convergence bonus (mock)
    ma_bonus = ma_convergence * 100
    
    score = base + balsan_bonus + loc_bonus + ma_bonus
    score = max(0, min(100, score + random.uniform(-5, 10)))
    
    return round(score, 1)

def get_mock_data(ticker):
    balsan = random.randint(-9000, 9000)
    threshold = TICKER_THRESHOLDS.get(ticker, 2000)
    maejip = random.randint(threshold, threshold*4)
    if balsan < 0:
        maejip = -maejip
    return {
        "balsan": balsan,
        "maejip": maejip,
        "maejip_raw": balsan,
        "delta": balsan,
        "buy_vol": random.randint(5000, 20000),
        "sell_vol": random.randint(5000, 20000),
        "location": random.choice(["VAL","VAH","POC","D-100","D+100","W-100"]),
        "cvd": balsan,
        "flip": f"{random.randint(-15000, -5000)}→{random.randint(5000, 15000)}",
        "ma_convergence": random.uniform(0.05, 0.25)
    }

# ================= MAIN =================
def main():
    print("="*70)
    print(f"COMMAND CENTER V5 - SCORING ENGINE DAILY 3-TRACK - {TODAY_KST}")
    print(f"SAME_TICKER_ACROSS_TF: {SAME_TICKER_ACROSS_TF} - 동일 Top2 티커 1m/2m/3m 동시 진입")
    print(f"PROP_PER_FAMILY: 1m=나 50K, 2m=아들 50K, 3m=딸 50K 각각 $700/$500 독립")
    print(f"PROP_LOCKED: {PROP_LOCKED}")
    print("="*70)
    
    # Best TF tracking
    best_tf_per_ticker, ticker_tf_stats = load_journal_for_best_tf()
    print(f"\n[BEST TF TRACKING] 21개 티커별 최적 분봉:")
    for ticker in TICKERS_21[:5]:  # Top5만 출력
        best = best_tf_per_ticker.get(ticker, {})
        print(f"  {ticker}: best_tf={best.get('best_tf','1m')} pnl={best.get('best_pnl',0)} win_rate={best.get('best_win_rate',0)}%")
    
    # Scoring 21 tickers
    tickers_data = []
    for ticker in TICKERS_21:
        mock = get_mock_data(ticker)
        score = calc_score(ticker, mock, mock["ma_convergence"])
        go = score >= 80
        
        # Best TF info
        best_info = best_tf_per_ticker.get(ticker, {})
        
        tickers_data.append({
            "ticker": ticker,
            "score": score,
            "go": go,
            "balsan": mock["balsan"],
            "maejip": mock["maejip"],
            "maejip_raw": mock["balsan"],
            "delta": mock["delta"],
            "location": mock["location"],
            "cvd": mock["cvd"],
            "flip": mock["flip"],
            "reason": f"{'매집 확정' if abs(mock['maejip'])>TICKER_THRESHOLDS.get(ticker,2000) else '발산'} DAILY",
            "threshold": TICKER_THRESHOLDS.get(ticker, 2000),
            "best_tf": best_info.get("best_tf", "1m"),
            "best_pnl": best_info.get("best_pnl", 0),
            "best_win_rate": best_info.get("best_win_rate", 0),
            "stats_per_tf": best_info.get("stats", {})
        })
    
    # Sort by score
    tickers_data_sorted = sorted(tickers_data, key=lambda x: x["score"], reverse=True)
    top2 = [t for t in tickers_data_sorted if t["go"]][:2]
    
    print(f"\n[TOP2 TODAY {TODAY_KST}] SAME ACROSS TF:")
    for t in top2:
        print(f"  {t['ticker']} Score {t['score']} 발산 {t['balsan']} 매집 {t['maejip']} {t['location']} best_tf={t['best_tf']}")
    
    if SAME_TICKER_ACROSS_TF:
        print(f"\n[3-TRACK SAME TICKER] 1m/2m/3m 모두 동일 2개 티커 진입:")
        print(f"  Father 1m (나 50K): {[t['ticker'] for t in top2]} - $700/$500 독립")
        print(f"  Son 2m (아들 50K): {[t['ticker'] for t in top2]} - $700/$500 독립")
        print(f"  Daughter 3m (딸 50K): {[t['ticker'] for t in top2]} - $700/$500 독립")
        print(f"  총 6포지션 (2개 x 3계좌), 각 계좌 독립 $700/$500")
    
    # Build absorption_v5.json
    absorption = {
        "date": TODAY_KST,
        "datetime_kst": DATETIME_KST,
        "datetime_utc": datetime.now(pytz.UTC).isoformat(),
        "tickers": tickers_data_sorted,
        "top2_today": top2,
        "same_ticker_across_tf": SAME_TICKER_ACROSS_TF,
        "prop_per_family": PROP_PER_FAMILY,
        "best_tf_per_ticker": best_tf_per_ticker,
        "prop_locked": PROP_LOCKED,
        "maejip_balsan_naming": "대목→매집, 발산 vs 매집 구분",
        "tp_structure": {
            "TP1": "50% Tenkan<Kijun deck+본절",
            "TP2": "25% SenkouA 구름 터치",
            "TP3": "25% SenkouB 구름 탈출"
        },
        "prop_rules": {
            "daily_loss": 700,
            "daily_profit": 500,
            "session": "18:00-16:10 EST",
            "pre_close": "60m",
            "block_weekend": True,
            "judas_kst": ["15:30-16:15", "21:00-21:45"],
            "news": "±30",
            "zombie": "0.7x+CVD",
            "eod": "23:50 KST",
            "consistency": "40%"
        },
        "total_slots": 63,
        "family_tracks": ["Father 1m", "Son 2m", "Daughter 3m"],
        "final_goal": "프랍은 프랍대로 자본충전, 돈 쌓이면 미국 증권거래소 직결 - 21개 티커별 최적 분봉으로 AI 실시간 매매 진화"
    }
    
    # Save to multiple paths for GitHub Pages fallback
    paths = [
        "./absorption_v5.json",
        "./docs/absorption_v5.json",
        "./docs/v5-ma-delta/absorption_v5.json"
    ]
    for p in paths:
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(absorption, f, ensure_ascii=False, indent=2)
            print(f"[SAVE] {p} DATE {TODAY_KST}")
        except Exception as e:
            print(f"[SAVE ERROR] {p} {e}")
    
    print("\n[DONE] scoring_engine_v5.py - 21개 티커별 최적 분봉 추적 + 3계좌 독립 프랍룰")
    print("[ENTRY.HTML]에서 1m ONLY / 2m ONLY / 3m ONLY 필터로 각각 수익 비교 → 최적 분봉 튜닝")
    return absorption

if __name__ == "__main__":
    main()
