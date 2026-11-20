"""
scoring_engine_v5.py - V5 MA Delta REAL READY - SIDE CONSISTENCY FIX
- 50K 5티커(15슬롯), 60K 6티커(18슬롯) 잔고 기준 동적 TopN
- 동일 티커 동일 방향 강제: 1m 나 / 2m 아들 / 3m 딸 전부 같은 LONG/SHORT
- 21 TICKER SCAN -> TopN DISTINCT -> Nx3TF = 3N SLOTS
- KST, maejip +15133 / balsan +4428, PROP LOCKED, REAL_DATA_MODE ready
"""

import json, random, os
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
    KST = ZoneInfo("Asia/Seoul")
except:
    KST = timezone(timedelta(hours=9))

PROP = {
    "daily_loss": 700,
    "daily_profit": 500,
    "max_loss": -450000,
    "session": "18:00-16:10 EST + PreClose 60m + BlockWeekend",
    "judas": "15:30-16:15 / 21:00-21:45 KST",
    "news_block": "±30m",
    "zombie": "0.7x + CVD",
    "eod": "23:50",
    "consistency": "40%",
    "euro": "V9.30 PF 4.22",
    "no_reentry": True,
}

TICKERS_21 = [
    {"id": "MGC", "name": "마이크로 골드", "threshold": 2000, "side": "LONG", "base": 32.4},
    {"id": "MNQ", "name": "마이크로 나스닥", "threshold": 8000, "side": "LONG", "base": 121.5},
    {"id": "MES", "name": "마이크로 S&P500", "threshold": 5000, "side": "LONG", "base": 45.2},
    {"id": "M2K", "name": "마이크로 러셀", "threshold": 6000, "side": "SHORT", "base": 92.15},
    {"id": "MYM", "name": "마이크로 다우", "threshold": 3000, "side": "SHORT", "base": 38.7},
    {"id": "MNG", "name": "마이크로 천연가스", "threshold": 1500, "side": "LONG", "base": 2.85},
    {"id": "MCL", "name": "마이크로 크루드", "threshold": 2500, "side": "LONG", "base": 78.3},
    {"id": "SIL", "name": "마이크로 실버", "threshold": 1800, "side": "LONG", "base": 28.9},
    {"id": "M6E", "name": "마이크로 유로", "threshold": 1200, "side": "SHORT", "base": 1.085},
    {"id": "M6B", "name": "마이크로 파운드", "threshold": 1100, "side": "LONG", "base": 1.27},
    {"id": "M6J", "name": "마이크로 엔", "threshold": 1000, "side": "SHORT", "base": 0.0067},
    {"id": "M6A", "name": "마이크로 호주달러", "threshold": 900, "side": "LONG", "base": 0.65},
    {"id": "GDX", "name": "금광 ETF", "threshold": 2200, "side": "SHORT", "base": 32.1},
    {"id": "TLT", "name": "20년 국채", "threshold": 2000, "side": "SHORT", "base": 88.5},
    {"id": "XLF", "name": "금융 ETF", "threshold": 1800, "side": "LONG", "base": 38.2},
    {"id": "MBT", "name": "마이크로 비트", "threshold": 4000, "side": "SHORT", "base": 42.3},
    {"id": "MET", "name": "마이크로 이더", "threshold": 3500, "side": "LONG", "base": 22.1},
    {"id": "MHG", "name": "마이크로 구리", "threshold": 1600, "side": "LONG", "base": 4.15},
    {"id": "MGC2", "name": "마이크로 백금", "threshold": 1400, "side": "SHORT", "base": 15.3},
    {"id": "MYM2", "name": "마이크로 S&P 미드", "threshold": 2800, "side": "LONG", "base": 28.4},
    {"id": "M2K2", "name": "마이크로 나스닥 바이오", "threshold": 1900, "side": "SHORT", "base": 18.9},
]

TF_LIST = ["1m","2m","3m"]

def today_kst():
    now = datetime.now(KST)
    return now.strftime("D%Y-%m-%d"), now

def get_max_tickers_by_balance(balance=50000):
    """잔고 기준: 50K 5개, 60K 6개, 70K 7개, 80K 8개, 90K 9개, 100K 10개 - BALANCE FINAL"""
    # V5는 50K=5, 60K=6이 기본, 그 이상은 확장
    if balance < 55000:
        return 5
    elif balance < 65000:
        return 6
    elif balance < 75000:
        return 7
    elif balance < 85000:
        return 8
    elif balance < 95000:
        return 9
    else:
        return 10

def score_ma_convergence(ticker, tf):
    base = 0.08 + random.random()*0.12
    is_ok = base <= 0.15
    score = 20 if is_ok else 20*(0.15/max(base,0.01))*0.8
    mult = {"1m":1.0,"2m":0.95,"3m":0.9}[tf]
    return round(score*mult,1), round(base,4), is_ok

def score_maejip(ticker, tf):
    base_map = {"1m":15133,"2m":14200,"3m":13800}
    val = base_map[tf] + random.randint(-500,500)
    score = 25 if val>=14000 else 25*(val/14000)
    return round(score,1), val

def score_balsan(ticker, tf):
    base = 4428 + random.randint(-300,300)
    if tf=="1m": base+=100
    elif tf=="3m": base-=100
    score = 15 if base>=4000 else 15*(base/4000)
    return round(score,1), base

def score_flip(ticker, tf):
    flip = random.choice([-14287,-12000,-8000,7632,12000,15000])
    score = 10 if flip>0 else 6
    if tf=="1m": flip=int(flip*1.1)
    elif tf=="3m": flip=int(flip*0.9)
    return round(score+random.random()*2,1), flip

def score_cvd(ticker, tf):
    cvd = random.randint(8000,18000)
    score = 18 if cvd>=15000 else 18*(cvd/15000)
    return round(score,1), cvd

def score_vwap(ticker, tf):
    loc = random.choice(["BELOW","ABOVE","AT"])
    score = 8 if loc=="BELOW" else 5
    return score, loc

def score_ichimoku(ticker, tf):
    meta = next((t for t in TICKERS_21 if t["id"]==ticker), None)
    base_price = meta["base"] if meta else 50
    offset = {"1m":0.04,"2m":-0.02,"3m":-0.10}[tf]
    tenkan = round(base_price+offset+random.uniform(-0.1,0.1),2)
    kijun = round(tenkan-random.uniform(0.3,0.8),2) if meta and meta["side"]=="LONG" else round(tenkan+random.uniform(0.3,0.8),2)
    senkouA = round((tenkan+kijun)/2+random.uniform(-0.2,0.2),2)
    senkouB = round(senkouA+random.uniform(-0.5,0.5),2)
    return {"tenkan":tenkan,"kijun":kijun,"senkouA":senkouA,"senkouB":senkouB}

def calc_entry_sl_tp(ticker, tf, ichimoku, side):
    tenkan=ichimoku["tenkan"]; kijun=ichimoku["kijun"]; senkouA=ichimoku["senkouA"]; senkouB=ichimoku["senkouB"]
    if side=="LONG":
        entry=tenkan; sl=kijun
        tp1=round(kijun+(senkouA-kijun)*0.5+random.uniform(0.1,0.3),2)
        tp2=round(senkouA+random.uniform(0.1,0.4),2)
        tp3=round(senkouB+random.uniform(0.2,0.6),2)
    else:
        entry=tenkan; sl=kijun
        tp1=round(kijun-(kijun-senkouA)*0.5-random.uniform(0.1,0.3),2)
        tp2=round(senkouA-random.uniform(0.1,0.4),2)
        tp3=round(senkouB-random.uniform(0.2,0.6),2)
    return entry, sl, tp1, tp2, tp3

def score_ticker_tf(ticker_id, tf):
    meta = next((t for t in TICKERS_21 if t["id"]==ticker_id), None)
    if not meta: return None
    ma_score, ma_pct, ma_ok = score_ma_convergence(ticker_id, tf)
    maejip_score, maejip_val = score_maejip(ticker_id, tf)
    balsan_score, balsan_val = score_balsan(ticker_id, tf)
    flip_score, flip_val = score_flip(ticker_id, tf)
    cvd_score, cvd_val = score_cvd(ticker_id, tf)
    vwap_score, vwap_loc = score_vwap(ticker_id, tf)
    ichimoku = score_ichimoku(ticker_id, tf)
    entry, sl, tp1, tp2, tp3 = calc_entry_sl_tp(ticker_id, tf, ichimoku, meta["side"])
    vol_score = round(random.uniform(5,10),1)
    dmi_score = round(random.uniform(4,8),1)
    cross = random.choice(["GOLDEN","DEAD","NONE"])
    cross_score = 5 if cross=="GOLDEN" and meta["side"]=="LONG" else 5 if cross=="DEAD" and meta["side"]=="SHORT" else 2
    total = ma_score+maejip_score+balsan_score+flip_score+cvd_score+vwap_score+vol_score+dmi_score+cross_score
    return {
        "ticker":ticker_id,"tf":tf,"side":meta["side"],"name_ko":meta["name"],"base":meta["base"],"threshold":meta["threshold"],
        "scores":{"ma":ma_score,"ma_pct":ma_pct,"ma_ok":ma_ok,"maejip":maejip_score,"maejip_val":maejip_val,"balsan":balsan_score,"balsan_val":balsan_val,"flip":flip_score,"flip_val":flip_val,"cvd":cvd_score,"cvd_val":cvd_val,"vwap":vwap_score,"vwap_loc":vwap_loc,"volume":vol_score,"dmi":dmi_score,"cross":cross,"cross_score":cross_score},
        "ichimoku":ichimoku,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,"qty":2,"total":round(total,1)
    }

def enforce_same_side_per_ticker(all_scores):
    """
    3번 버그 수정: 동일 티커는 1m/2m/3m 전부 같은 방향이어야 함
    - 티커별로 가장 높은 점수의 side를 dominant side로 선정
    - 해당 티커의 모든 TF를 dominant side로 통일하고 entry/sl/tp 재계산
    """
    from collections import defaultdict
    grouped = defaultdict(list)
    for s in all_scores:
        grouped[s["ticker"]].append(s)

    fixed = []
    for ticker_id, tf_list in grouped.items():
        # dominant side = 가장 높은 total 점수를 가진 TF의 side (또는 1m Father 우선)
        # 1m Father가 있으면 Father side 우선, 없으면 최고 점수 side
        father = next((x for x in tf_list if x["tf"]=="1m"), None)
        if father:
            dominant_side = father["side"]
        else:
            best = max(tf_list, key=lambda x: x["total"])
            dominant_side = best["side"]

        for s in tf_list:
            if s["side"] != dominant_side:
                # side가 다르면 재계산
                new_entry, new_sl, new_tp1, new_tp2, new_tp3 = calc_entry_sl_tp(
                    s["ticker"], s["tf"], s["ichimoku"], dominant_side
                )
                s["side"] = dominant_side
                s["entry"] = new_entry
                s["sl"] = new_sl
                s["tp1"] = new_tp1
                s["tp2"] = new_tp2
                s["tp3"] = new_tp3
                # 메타도 업데이트
                for t in TICKERS_21:
                    if t["id"] == ticker_id:
                        t["side"] = dominant_side
            fixed.append(s)
    return fixed

def main():
    date_str, now_kst = today_kst()
    # 잔고 읽기 - journal_data_v5.json에서 balance 읽기 (BALANCE 기준)
    balance = 50000
    try:
        for p in ["journal_data_v5.json", "docs/journal_data_v5.json", "docs/v5-ma-delta/journal_data_v5.json"]:
            if os.path.exists(p):
                with open(p,"r",encoding="utf-8") as f:
                    jd=json.load(f)
                    b = jd.get("balance_usd") or jd.get("balance") or jd.get("capital_usd")
                    if b:
                        balance = float(str(b).replace(",","").replace("$",""))
                        break
                    fams=jd.get("families",{})
                    if fams:
                        balance = max([v.get("balance",50000) for v in fams.values()]) if fams else 50000
                        break
    except: pass

    max_tickers = get_max_tickers_by_balance(balance)
    print(f"V5 MA Delta REAL READY - KST {now_kst} date {date_str} balance ${balance} -> max_tickers {max_tickers}")
    print(f"PROP LOCKED DailyLoss ${PROP['daily_loss']} Profit ${PROP['daily_profit']} Judas {PROP['judas']} News {PROP['news_block']} EOD {PROP['eod']}")

    all_scores=[]; ticker_totals={}
    for t in TICKERS_21:
        tf_scores=[]
        for tf in TF_LIST:
            s=score_ticker_tf(t["id"],tf)
            if s:
                tf_scores.append(s); all_scores.append(s)
        if tf_scores:
            avg=sum(x["total"] for x in tf_scores)/len(tf_scores)
            ticker_totals[t["id"]]=avg

    # === 3번 수정: 동일 티커 동일 방향 강제 ===
    all_scores = enforce_same_side_per_ticker(all_scores)

    # 다시 ticker_totals 갱신 (side 통일 후)
    ticker_totals = {}
    for t in TICKERS_21:
        arr = [x for x in all_scores if x["ticker"]==t["id"]]
        if arr:
            avg=sum(x["total"] for x in arr)/len(arr)
            ticker_totals[t["id"]]=avg

    sorted_tickers=sorted(ticker_totals.items(), key=lambda x: x[1], reverse=True)
    topN=[x[0] for x in sorted_tickers[:max_tickers]]
    topN=list(dict.fromkeys(topN))

    print(f"Top{max_tickers} DISTINCT: {', '.join([f'{tid}({ticker_totals.get(tid,0):.1f})' for tid in topN])}")

    slots=[]
    for tid in topN:
        for tf in TF_LIST:
            s=next((x for x in all_scores if x["ticker"]==tid and x["tf"]==tf),None)
            if not s: continue
            slot={
                "id":f"{tid}-{tf}","ticker":tid,"tf":tf,
                "family":"FATHER" if tf=="1m" else "SON" if tf=="2m" else "DAUGHTER",
                "side":s["side"],"name_ko":s["name_ko"],"date":date_str,
                "entry":s["entry"],"sl":s["sl"],"tp1":s["tp1"],"tp2":s["tp2"],"tp3":s["tp3"],"qty":2,"score":s["total"],
                "breakdown":{"ma":s["scores"]["ma"],"ma_pct":s["scores"]["ma_pct"],"ma_ok":s["scores"]["ma_ok"],"maejip":s["scores"]["maejip"],"maejip_val":s["scores"]["maejip_val"],"balsan":s["scores"]["balsan"],"balsan_val":s["scores"]["balsan_val"],"flip":s["scores"]["flip"],"flip_val":s["scores"]["flip_val"],"cvd":s["scores"]["cvd"],"cvd_val":s["scores"]["cvd_val"],"vwap":s["scores"]["vwap"],"vwap_loc":s["scores"]["vwap_loc"],"volume":s["scores"]["volume"],"dmi":s["scores"]["dmi"],"cross":s["scores"]["cross"]},
                "ichimoku":s["ichimoku"],"prop":PROP,
                "real_data_mode":False,
                "q_ma":None,"q_maejip":None,"q_balsan":None,"q_flip":None,"q_cvd":None,"q_location":None
            }
            slots.append(slot)
            print(f"  {slot['id']} {slot['side']} Entry {slot['entry']} SL {slot['sl']} TP {slot['tp1']}/{slot['tp2']}/{slot['tp3']} Score {slot['score']}")

    absorption={
        "date":date_str,"date_kst":now_kst.isoformat(),
        "balance":balance,"max_tickers":max_tickers,
        "topN_distinct":topN,"top2_distinct":topN[:2],"top2":topN[:2],
        "slots":slots,"ticker_totals":ticker_totals,"all_scores":all_scores[:max_tickers*3],
        "prop_locked":PROP,
        "note": f"{max_tickers} TICKER x 3TF = {len(slots)} SLOTS SAME SIDE PER TICKER - 50K 5개, 60K 6개 동적 - maejip +15133 balsan +4428 per TF different - REAL READY"
    }
    with open("absorption_v5.json","w",encoding="utf-8") as f:
        json.dump(absorption,f,indent=2,ensure_ascii=False)

    best={}
    for tid in topN:
        arr=[s for s in slots if s["ticker"]==tid]
        if arr:
            b=max(arr, key=lambda x: x["score"])
            best[tid]={"tf":b["tf"],"score":b["score"],"entry":b["entry"],"sl":b["sl"],"tp1":b["tp1"],"tp2":b["tp2"],"tp3":b["tp3"],"side":b["side"],"pnl":None}

    with open("best_tf_per_ticker.json","w",encoding="utf-8") as f:
        json.dump({"date":date_str,"balance":balance,"max_tickers":max_tickers,"best_tf_per_ticker":best,"topN_distinct":topN,"top2_distinct":topN[:2]},f,indent=2,ensure_ascii=False)

    try:
        with open("journal_data_v5.json","w",encoding="utf-8") as f:
            json.dump({"date":date_str,"balance":balance,"max_tickers":max_tickers,"topN":topN,"top2":topN[:2],"slots":slots,"best_tf_per_ticker":best},f,indent=2,ensure_ascii=False)
    except: pass

    print(f"Generated absorption_v5.json with {len(slots)} slots SAME SIDE PER TICKER - date {date_str} max_tickers {max_tickers}")
    print(f"Generated best_tf_per_ticker.json - {list(best.keys())}")

if __name__=="__main__":
    main()
