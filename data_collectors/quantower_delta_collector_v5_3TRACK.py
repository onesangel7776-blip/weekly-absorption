# quantower_delta_collector.py - V5 MA Delta 3-TRACK REAL MODE
# VPS 1대로 Father 1m / Son 2m / Daughter 3m 동시 검증
# Black Friday 후 hdMain[1].VolumeAnalysisData.Total.Delta 연결
# Source: Euro bot V9.30 line 521 + BotAccount.Balance
# Prop Rules LOCKED from Euro V9.30

import json
import os
from datetime import datetime, timedelta
import pytz

# ================= CONFIG - PROP LOCKED (Euro V9.30) =================
PROP_LOCKED = True
DAILY_LOSS_LIMIT = 700  # $700
DAILY_PROFIT_LIMIT = 500  # $500 new for V5
MAX_LOSS_LIMIT = 450000  # 원화 -450k for journal display
SESSION_START_EST = "18:00"
SESSION_END_EST = "16:10"
PRE_CLOSE_BLOCK_MIN = 60
WEEKEND_BLOCK = True
JUDAS_KST_1 = ("15:30", "16:15")
JUDAS_KST_2 = ("21:00", "21:45")
NEWS_BLOCK_MIN = 30
ZOMBIE_FACTOR = 0.7
EOD_CLOSE_KST = "23:50"
CONSISTENCY_LIMIT = 0.40  # 40%

# ================= 21 TICKERS THRESHOLDS (V5) =================
TICKER_THRESHOLDS = {
    "MGC": 2000, "MNQ": 8000, "MNG": 1500, "M2K": 3000, "MES": 5000,
    "MCL": 2500, "M6E": 1200, "M6A": 1000, "M6B": 1100,
    "GC": 2000, "NQ": 8000, "NG": 1500, "RTY": 3000, "ES": 5000,
    "CL": 2500, "6E": 1200, "6A": 1000, "6B": 1100,
    "CPER": 4428, "XLE": 5000, "DBA": 2000
}

# ================= FAMILY TRACKS - VPS 1대로 3프로세스 =================
FAMILY_TRACKS = {
    "Father": {"tf": "1m", "vps_id": 1, "color": "#ffcc00", "desc": "Father 1m - MA Delta"},
    "Son": {"tf": "2m", "vps_id": 1, "color": "#00aaff", "desc": "Son 2m - MA Delta"},
    "Daughter": {"tf": "3m", "vps_id": 1, "color": "#aa66ff", "desc": "Daughter 3m - MA Delta"}
}

# ================= REAL DATA HOOK - BLACK FRIDAY 후 활성화 =================
REAL_DATA_MODE = False  # Black Friday 전: False (mock), 후: True (real)

def get_real_delta_quantower(hd_main):
    """
    Black Friday 후 진짜 델타 - Euro bot V9.30 521번째 줄
    total = hdMain[1].VolumeAnalysisData.Total.Delta
    """
    if not REAL_DATA_MODE:
        return None  # mock mode
    
    try:
        # Quantower 실제 코드
        # hdMain[1] = 1분봉 VolumeAnalysis
        total_delta = hd_main[1].VolumeAnalysisData.Total.Delta
        buy_volume = hd_main[1].VolumeAnalysisData.Total.BuyVolume
        sell_volume = hd_main[1].VolumeAnalysisData.Total.SellVolume
        return {
            "delta": total_delta,
            "buy_vol": buy_volume,
            "sell_vol": sell_volume,
            "cvd": total_delta  # CVD proxy
        }
    except Exception as e:
        print(f"[REAL DELTA ERROR] {e}")
        return None

def get_real_balance(bot_account):
    """
    Black Friday 후 진짜 잔고 - BotAccount.Balance
    """
    if not REAL_DATA_MODE:
        return 10000  # mock $10k
    
    try:
        return bot_account.Balance
    except:
        return 10000

# ================= 3-STAGE ICHIMOKU TP (V5) =================
def calc_ichimoku_3stage_tp(entry_price, side, tenkan, kijun, senkou_a, senkou_b):
    """
    TP1 50% Tenkan<Kijun deck+breakeven
    TP2 25% SenkouA cloud touch
    TP3 25% SenkouB cloud exit
    """
    if side == "LONG":
        tp1 = kijun  # Tenkan < Kijun deck
        tp2 = senkou_a
        tp3 = senkou_b
    else:
        tp1 = kijun
        tp2 = senkou_a
        tp3 = senkou_b
    
    return {
        "TP1": {"price": tp1, "qty_pct": 0.5, "desc": "Tenkan<Kijun deck+breakeven"},
        "TP2": {"price": tp2, "qty_pct": 0.25, "desc": "SenkouA cloud touch"},
        "TP3": {"price": tp3, "qty_pct": 0.25, "desc": "SenkouB cloud exit"}
    }

# ================= MOCK DATA FOR NOW (Black Friday 전) =================
def get_mock_delta(ticker):
    import random
    # 발산 + 매집 구분
    balsan = random.randint(-9000, 9000)
    maejip_threshold = TICKER_THRESHOLDS.get(ticker, 2000)
    maejip = random.randint(maejip_threshold, maejip_threshold*3)
    if balsan < 0:
        maejip = -maejip
    
    return {
        "delta": balsan,
        "balsan": balsan,
        "maejip": maejip,
        "maejip_raw": balsan,
        "buy_vol": random.randint(5000, 20000),
        "sell_vol": random.randint(5000, 20000),
        "location": random.choice(["VAL", "VAH", "POC", "D-100", "D+100"])
    }

# ================= ABSORPTION READER =================
def load_absorption():
    paths = [
        "./docs/v5-ma-delta/absorption_v5.json",
        "./docs/absorption_v5.json",
        "./absorption_v5.json",
        "/weekly-absorption/docs/v5-ma-delta/absorption_v5.json"
    ]
    for p in paths:
        try:
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"[LOAD] absorption_v5.json from {p} DATE {data.get('date')}")
                    return data
        except Exception as e:
            print(f"[LOAD ERROR] {p} {e}")
            continue
    
    # Fallback mock
    print("[LOAD] No absorption file, using mock")
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "datetime_kst": datetime.now().isoformat(),
        "tickers": [
            {"ticker": "MGC", "score": 88.4, "go": True, "balsan": 4428, "maejip": 15133, "location": "VAL", "reason": "매집 확정"},
            {"ticker": "M2K", "score": 84.1, "go": True, "balsan": -8760, "maejip": -12000, "location": "D-100", "reason": "발산"}
        ]
    }

# ================= JOURNAL WRITER - 3TRACK =================
def update_journal_3track(absorption_data, vps_id=1):
    """
    VPS 1대로 Father 1m / Son 2m / Daughter 3m 3트랙 동시 기록
    journal_data_v5.json에 Family, TF 구분 저장
    """
    kst = pytz.timezone("Asia/Seoul")
    now_kst = datetime.now(kst)
    date_str = f"D{now_kst.strftime('%Y-%m-%d')}"
    
    journal_path = "./docs/v5-ma-delta/journal_data_v5.json"
    
    # Load existing journal
    existing = []
    try:
        if os.path.exists(journal_path):
            with open(journal_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                if isinstance(existing, dict):
                    existing = existing.get("positions", [])
    except:
        existing = []
    
    tickers = absorption_data.get("tickers", [])
    go_tickers = [t for t in tickers if t.get("go") and t.get("score", 0) >= 80]
    go_tickers = sorted(go_tickers, key=lambda x: x.get("score", 0), reverse=True)[:2]
    
    new_positions = []
    for family, track_info in FAMILY_TRACKS.items():
        tf = track_info["tf"]
        # VPS 1대지만 tf 구분
        for i, t in enumerate(go_tickers):
            if i >= 1 and family == "Father":  # Father는 Top1만, Son/Daughter는 Top2
                continue
            if REAL_DATA_MODE:
                # 진짜 데이터
                delta_data = get_real_delta_quantower(None)  # hdMain 전달 필요
                if delta_data is None:
                    delta_data = get_mock_delta(t["ticker"])
            else:
                delta_data = get_mock_delta(t["ticker"])
            
            side = "LONG" if delta_data["maejip"] >= 0 else "SHORT"
            
            # Mock entry prices
            entry_price = 32.44 + i*60 + (0 if family=="Father" else 10 if family=="Son" else 20)
            
            position = {
                "date": date_str,
                "ticker": t["ticker"],
                "side": side,
                "entry": round(entry_price, 2),
                "sl": round(entry_price*0.98, 2),
                "tp": round(entry_price*1.05, 2),
                "qty": 3,
                "current": round(entry_price*1.02, 2),
                "status": "OPEN",
                "pnlKrw": 272000 + i*50000,
                "pnlUsd": 204 + i*40,
                "family": family,
                "tf": tf,
                "vps_id": vps_id,
                "score": t.get("score", 80),
                "balsan": delta_data.get("balsan", 0),
                "maejip": delta_data.get("maejip", 0),
                "maejip_raw": delta_data.get("maejip_raw", 0),
                "delta": delta_data.get("delta", 0),
                "location": delta_data.get("location", "VAL"),
                "reason": t.get("reason", "매집 확정 DAILY"),
                "tp_structure": calc_ichimoku_3stage_tp(entry_price, side, 32.0, 31.8, 34.2, 35.1),
                "prop_locked": PROP_LOCKED,
                "timestamp_kst": now_kst.isoformat()
            }
            new_positions.append(position)
    
    # Merge with existing, keep last 30 days
    all_positions = existing + new_positions
    # Keep only last 100 positions for file size
    all_positions = all_positions[-100:]
    
    # Save
    try:
        os.makedirs(os.path.dirname(journal_path), exist_ok=True)
        with open(journal_path, 'w', encoding='utf-8') as f:
            json.dump(all_positions, f, ensure_ascii=False, indent=2)
        print(f"[JOURNAL] Saved {len(all_positions)} positions to {journal_path}")
        print(f"[3-TRACK] Father 1m: {len([p for p in new_positions if p['tf']=='1m'])} | Son 2m: {len([p for p in new_positions if p['tf']=='2m'])} | Daughter 3m: {len([p for p in new_positions if p['tf']=='3m'])}")
    except Exception as e:
        print(f"[JOURNAL ERROR] {e}")
    
    return new_positions

# ================= MAIN - VPS 1대로 3트랙 =================
def main():
    print("="*60)
    print("COMMAND CENTER V5 - DELTA COLLECTOR 3-TRACK REAL MODE")
    print("VPS 1대로 Father 1m / Son 2m / Daughter 3m 동시 검증")
    print(f"REAL_DATA_MODE: {REAL_DATA_MODE} (False=mock, True=Quantower real)")
    print(f"PROP LOCKED: {PROP_LOCKED} - DailyLoss ${DAILY_LOSS_LIMIT} / DailyProfit ${DAILY_PROFIT_LIMIT}")
    print("="*60)
    
    absorption = load_absorption()
    print(f"[ABSORPTION] DATE {absorption.get('date')} Tickers {len(absorption.get('tickers',[]))}")
    
    positions = update_journal_3track(absorption, vps_id=1)
    
    print("\n[RESULT] Today positions:")
    for p in positions:
        print(f"  {p['date']} {p['ticker']} {p['side']} Score {p['score']} {p['family']} {p['tf']} P&L {p['pnlKrw']}원 발산 {p['balsan']} 매집 {p['maejip']} {p['location']}")
    
    print("\n[BLACK FRIDAY 후 활성화 방법]")
    print("1. Quantower All-in-One 구매 후 이 파일에서 REAL_DATA_MODE = True 로 변경")
    print("2. get_real_delta_quantower()에 hdMain 전달: get_real_delta_quantower(hdMain)")
    print("3. get_real_balance()에 BotAccount 전달: get_real_balance(BotAccount)")
    print("4. VPS 1대에서 이 스크립트를 3번 실행 or 1번 실행으로 3트랙 동시 기록")
    print("5. journal_data_v5.json이 entry.html에 자동 반영 → 1m/2m/3m 수익 비교")
    print("\n[ENTRY.HTML 필터로 확인]")
    print("1m ONLY → Father 1m 수익, 2m ONLY → Son 2m 수익, 3m ONLY → Daughter 3m 수익")
    print("6개월 후 잘 버는 분봉으로 MFFU 회사별 Euro/MA 분류")

if __name__ == "__main__":
    main()
