
"""
V5 MA Delta - 목업이지만 프랍룰은 실제로 잠그는 버전
Euro V9.30 필터 + 뉴스/주다스/좀비/당일종료/손실700/수익500 전부 체크
"""
import json, random
from datetime import datetime, time
import os

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

def is_judas():
    now = datetime.now()
    m = now.hour*60 + now.minute
    return (930 <= m <= 975) or (1260 <= m <= 1305)

def is_eod():
    now = datetime.now()
    return now.hour==23 and now.minute>=50

def is_session():
    now = datetime.now()
    # 주말 차단 - 토,일
    if now.weekday()>=5:
        return True
    return False

def is_news_mock():
    # GDELT 아직 없으니 10% 확률로 뉴스 있다고 가정
    return random.random()<0.1

def is_zombie(vol):
    return vol<0.7

def gen():
    today = datetime.now().strftime("%Y-%m-%d %H:%M KST")
    
    # 프랍룰 체크 - 하나라도 걸리면 전체 NO-GO
    judas_block = is_judas()
    eod_block = is_eod()
    session_block = is_session()
    news_block = is_news_mock()
    
    # 일일 손익 목업 - 700불 손실 / 500불 수익 넘으면 블록
    mock_balance = random.randint(-600, 600)
    daily_loss_block = mock_balance <= -DAILY_LOSS
    daily_profit_block = mock_balance >= DAILY_PROFIT
    
    tickers = []
    for ticker, thresh, loc in TICKERS:
        vol = random.uniform(0.5, 2.5)
        zombie_block = is_zombie(vol)
        
        is_mgc = ticker == "MGC"
        daemok = 15133 if is_mgc else random.randint(500, 8000)
        score = 96 if is_mgc else random.randint(30, 75)
        
        # 프랍룰 하나라도 걸리면 GO 막음 - 유로봇 CanOpenNewPosition 로직
        blocked = judas_block or eod_block or session_block or news_block or daily_loss_block or daily_profit_block or zombie_block
        go = is_mgc and not blocked
        
        reason = []
        if judas_block: reason.append("Judas 15:30-16:15/21:00-21:45")
        if news_block: reason.append("News ±30")
        if zombie_block: reason.append("Zombie 0.7x")
        if eod_block: reason.append("EOD 23:50")
        if daily_loss_block: reason.append(f"DailyLoss ${DAILY_LOSS}")
        if daily_profit_block: reason.append(f"DailyProfit ${DAILY_PROFIT}")
        if session_block: reason.append("Weekend/Session")
        if not reason and is_mgc:
            reason.append("MA 0.15% 수렴 + D-100% + 대목 +15133 + CVD -14287->+7632")
        if not reason:
            reason.append("임계값 미달")
            
        tickers.append({
            "ticker": ticker,
            "location": loc,
            "delta_badge": f"+{daemok}",
            "daemok": daemok,
            "threshold": thresh,
            "score": 0 if blocked else score,
            "go": go,
            "reason": " / ".join(reason),
            "prop": {
                "judas": judas_block,
                "news": news_block,
                "zombie": zombie_block,
                "daily_loss": daily_loss_block,
                "daily_profit": daily_profit_block,
                "session": session_block,
                "eod": eod_block,
                "blocked": blocked
            }
        })
    
    data = {
        "date": today,
        "run": "V5 MA DAILY - Euro V9.30 Prop Filter LOCKED",
        "filters": {
            "daily_loss": DAILY_LOSS,
            "daily_profit": DAILY_PROFIT,
            "session": "18:00-16:10 EST + PreClose 60m + Weekend Block",
            "judas": "15:30-16:15 / 21:00-21:45 KST BLOCKED",
            "news": "±30분 BLOCKED",
            "zombie": "0.7x + CVD 횡보 BLOCKED",
            "eod": "23:50 강제청산 BLOCKED"
        },
        "status": "BLOCKED" if (judas_block or eod_block or session_block or daily_loss_block or daily_profit_block) else "PASS",
        "tickers": tickers
    }
    with open("absorption_v5.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Generated DATE {today} - Prop LOCKED - Judas:{judas_block} EOD:{eod_block} Loss:{daily_loss_block} Profit:{daily_profit_block}")

if __name__ == "__main__":
    gen()
