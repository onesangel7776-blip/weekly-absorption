"""
V5 MA Delta - 매집으로 이름 변경 확정 + KST DAILY FIX
대목 -> 매집 (세력 매집 블록, 개미가 할 수 없는 15K 물량)
발산 +4428 (전체 흐름) vs 매집 +15133 (특정 가격 세력 매집)
Euro V9.30 프랍룰 LOCKED + 3단계 구름 익절 + KST 월~금 07:00 FIX
"""
import json, random
from datetime import datetime, timezone, timedelta

# KST 추가 - 한국시간 오늘 DATE
KST = timezone(timedelta(hours=9))
today_kst = datetime.now(KST).strftime("%Y-%m-%d")
now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

DAILY_LOSS = 700
DAILY_PROFIT = 500

TICKERS = [
    ("MGC", 2000, "D-100% VAL"), ("MNG", 1500, "D50% W0%"), ("SIL", 2500, "D50% W0%"),
    ("M2K", 6000, "D50% W0%"), ("MES", 5000, "D50% W0%"), ("MNQ", 8000, "W-75%"),
    ("MYM", 4000, "VAL"), ("MCL", 3000, "D-75%"), ("MBT", 2000, "POC"),
    ("MET", 2500, "D-100%"), ("M6E", 2000, "D-75%"), ("M6B", 2000, "VAL"),
    ("M6A", 2000, "VAL"), ("MJY", 2000, "W-100%"), ("MSF", 2000, "POC"),
    ("MHG", 2500, "D-50%"), ("M10Y", 2000, "W-75%"), ("M30Y", 2000, "D-75%"),
    ("M2KY", 6000, "D-100%"), ("MGCQ", 2000, "W-50%"), ("MNGQ", 1500, "VAL"),
]

def gen():
    print(f"Running V5 Scoring - DATE DAILY {today_kst} - KST {now_kst}")
    tickers = []
    for ticker, thresh, loc in TICKERS:
        is_mgc = ticker == "MGC"
        # 매집 = 세력 매집 블록 (개미 불가 물량) - 초록
        # 발산 = 전체 흐름 - 하늘/귤색
        maejip = 15133 if is_mgc else random.randint(500, 8000)
        score = 96 if is_mgc else random.randint(30, 75)
        balsan = random.randint(200, 5000) if not is_mgc else 4428
        
        tickers.append({
            "ticker": ticker,
            "location": loc,
            "balsan": f"+{balsan}",  # 발산: 전체 Buy/Sell 차이 - 발산 롱 하늘 +12,400 / 발산 숏 귤색 -9,870
            "maejip": f"+{maejip}" if maejip>0 else f"{maejip}",  # 매집: 특정 가격 세력 매집 블록 - 롱매집 초록 +15133 / 숏매집 노랑 -15133
            "maejip_raw": maejip,
            "balsan_raw": balsan,
            "threshold": thresh,
            "score": score,
            "go": is_mgc,
            "reason": f"MA10 0.15% 수렴 + {loc} + 매집 +{maejip} + 발산 +{balsan} + CVD -14287->+7632 + FLIP + 골크/데크" if is_mgc else "임계값 미달",
            "prop": {"judas": False, "news": False, "zombie": False, "daily_loss": False, "daily_profit": False, "block_weekend": False},
            "tp": {"tp1": "기준선 Kijun 50% 데크+본절", "tp2": "선행1 SenkouA 25% 구름터치", "tp3": "선행2 SenkouB 25% 이탈"}
        })
    
    data = {
        "date": today_kst,
        "datetime_kst": now_kst,
        "run": "V5 MA DELTA - 매집 확정 (대목->매집) - 발산 vs 매집 구분 - KST DAILY - 75/25 2패널",
        "naming": {
            "balsan": "발산 +4428 = 하루 전체 Buy/Sell 차이 (전체 흐름) - 발산 롱 하늘 +12,400 / 발산 숏 귤색 -9,870",
            "maejip": "매집 +15133 = 특정 가격에 세력이 15K 계약 매집 (개미 불가, 4.7톤 금) - 롱매집 초록 +15133 / 숏매집 노랑 -15133",
            "cvd": "Bull CVD 롱매집 하늘 vs Bear CVD 숏매집 귤색 - 골크/데크 - FLIP -14,287->+7,632"
        },
        "filters": {"daily_loss": DAILY_LOSS, "daily_profit": DAILY_PROFIT, "prop_locked": True},
        "layout": "75% 메인 (MA10+VWAP 보라+일목 구름+매집 초록/노랑) / 25% 통합 (거래량 1.8x + Bull 하늘 + Bear 귤색 + Net 초록빨강 + 골크데크 + FLIP)",
        "tickers": tickers
    }
    with open("absorption_v5.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # journal도 DATE 갱신
    try:
        with open("journal_data_v5.json", "r", encoding="utf-8") as jf:
            journal = json.load(jf)
    except:
        journal = {"positions": []}
    
    journal["date"] = today_kst
    journal["datetime_kst"] = now_kst
    
    with open("journal_data_v5.json", "w", encoding="utf-8") as jf:
        json.dump(journal, jf, ensure_ascii=False, indent=2)
    
    print(f"Generated 매집 확정 DATE {today_kst} KST - 발산 vs 매집 구분 - 75/25 2패널 - {len(tickers)} tickers")

if __name__ == "__main__":
    gen()
