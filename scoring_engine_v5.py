
"""
V5 MA Delta Daily - 고정 버전 (pytz 없이)
Euro bot V9.30 필터 + 티커별 임계값 + DATE 일일매매
"""
import json, random
from datetime import datetime

# 유로봇에서 뽑은 필터 상수
DAILY_LOSS = 700
DAILY_PROFIT = 500
SESSION_START = "18:00"
SESSION_END = "16:10"
PRE_CLOSE_MIN = 60

# 21개 티커별 임계값 - MGC +2000, MNQ +8000
TICKERS = [
    ("MGC", 2000, "D-100% VAL"),
    ("MNG", 1500, "D50% W0%"),
    ("SIL", 2500, "D50% W0%"),
    ("M2K", 6000, "D50% W0%"),
    ("MES", 5000, "D50% W0%"),
    ("MNQ", 8000, "W-75%"),
    ("MYM", 4000, "VAL"),
    ("MCL", 3000, "D-75%"),
    ("MBT", 2000, "POC"),
    ("MET", 2500, "D-100%"),
    ("M6E", 2000, "D-75%"),
    ("M6B", 2000, "VAL"),
    ("M6A", 2000, "VAL"),
    ("MJY", 2000, "W-100%"),
    ("MSF", 2000, "POC"),
    ("MHG", 2500, "D-50%"),
    ("M10Y", 2000, "W-75%"),
    ("M30Y", 2000, "D-75%"),
    ("M2KY", 6000, "D-100%"),
    ("MGCQ", 2000, "W-50%"),
    ("MNGQ", 1500, "VAL"),
]

def gen():
    today = datetime.now().strftime("%Y-%m-%d")
    tickers = []
    for ticker, thresh, loc in TICKERS:
        # MGC만 오늘 GO 예시, 나머지는 랜덤
        is_mgc = ticker == "MGC"
        daemok = 15133 if is_mgc else random.randint(500, 8000)
        delta = f"+{daemok}" if daemok>1000 else f"+{random.randint(200,1500)}"
        score = 87 if is_mgc else random.randint(30, 65)
        cvd = 7632 if is_mgc else random.randint(-5000, 5000)
        tickers.append({
            "ticker": ticker,
            "location": loc,
            "delta_badge": delta,
            "daemok": daemok,
            "cvd_now": cvd,
            "threshold": thresh,
            "score": score,
            "go": is_mgc,
            "reason": "MA 0.15% 수렴 + D-100% + 대목 +15133 + CVD -14287->+7632" if is_mgc else "임계값 미달",
            "prop": {
                "judas": False,
                "news": False,
                "zombie": False,
                "daily_loss": False,
                "daily_profit": False,
                "session": False,
                "eod": False
            }
        })
    
    data = {
        "date": today,
        "run": "V5 MA DELTA DAILY - Euro V9.30 Filter Imported",
        "filters": {
            "daily_loss": DAILY_LOSS,
            "daily_profit": DAILY_PROFIT,
            "session": f"{SESSION_START}-{SESSION_END} EST + PreClose {PRE_CLOSE_MIN}m",
            "judas": "15:30-16:15 / 21:00-21:45 KST",
            "news": "±30분",
            "zombie": "0.7x + CVD 횡보",
            "eod": "23:50"
        },
        "tickers": tickers
    }
    with open("absorption_v5.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Generated absorption_v5.json DATE {today} - 21 tickers - MGC GO")

if __name__ == "__main__":
    gen()
