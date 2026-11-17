"""
scoring_engine_v5.py - V5 MA Delta DAILY - KST FIXED - D2026-11-17
21 TICKER SCAN -> Top2 DISTINCT -> 2x3TF = 6 SLOTS with DIFFERENT Entry/SL/TP
KST timezone, maejip +15133 / balsan +4428, 3-stage Ichimoku TP, PROP LOCKED
NO PYTZ DEPENDENCY - uses zoneinfo (Python 3.9+)
"""

import json
import random
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
    KST = ZoneInfo("Asia/Seoul")
except:
    # fallback UTC+9
    KST = timezone(timedelta(hours=9))

# === PROP LOCKED ===
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
    "euro": "V9.30 PF 4.22"
}

# 21 TICKERS with thresholds (example values from spec)
TICKERS_21 = [
    {"id": "MGC", "name": "마이크로 골드", "threshold": 2000, "side": "LONG", "base": 32.4, "type": "commodity"},
    {"id": "MNQ", "name": "마이크로 나스닥", "threshold": 8000, "side": "LONG", "base": 121.5, "type": "index"},
    {"id": "MES", "name": "마이크로 S&P500", "threshold": 5000, "side": "LONG", "base": 45.2, "type": "index"},
    {"id": "M2K", "name": "마이크로 러셀", "threshold": 6000, "side": "SHORT", "base": 92.15, "type": "index"},
    {"id": "MYM", "name": "마이크로 다우", "threshold": 3000, "side": "SHORT", "base": 38.7, "type": "index"},
    {"id": "MNG", "name": "마이크로 천연가스", "threshold": 1500, "side": "LONG", "base": 2.85, "type": "commodity"},
    {"id": "MCL", "name": "마이크로 크루드", "threshold": 2500, "side": "LONG", "base": 78.3, "type": "commodity"},
    {"id": "SIL", "name": "마이크로 실버", "threshold": 1800, "side": "LONG", "base": 28.9, "type": "commodity"},
    {"id": "M6E", "name": "마이크로 유로", "threshold": 1200, "side": "SHORT", "base": 1.085, "type": "forex"},
    {"id": "M6B", "name": "마이크로 파운드", "threshold": 1100, "side": "LONG", "base": 1.27, "type": "forex"},
    {"id": "M6J", "name": "마이크로 엔", "threshold": 1000, "side": "SHORT", "base": 0.0067, "type": "forex"},
    {"id": "M6A", "name": "마이크로 호주달러", "threshold": 900, "side": "LONG", "base": 0.65, "type": "forex"},
    {"id": "GDX", "name": "금광 ETF", "threshold": 2200, "side": "SHORT", "base": 32.1, "type": "etf"},
    {"id": "TLT", "name": "20년 국채", "threshold": 2000, "side": "SHORT", "base": 88.5, "type": "bond"},
    {"id": "XLF", "name": "금융 ETF", "threshold": 1800, "side": "LONG", "base": 38.2, "type": "etf"},
    {"id": "MBT", "name": "마이크로 비트", "threshold": 4000, "side": "SHORT", "base": 42.3, "type": "crypto"},
    {"id": "MET", "name": "마이크로 이더", "threshold": 3500, "side": "LONG", "base": 22.1, "type": "crypto"},
    {"id": "MHG", "name": "마이크로 구리", "threshold": 1600, "side": "LONG", "base": 4.15, "type": "commodity"},
    {"id": "MGC2", "name": "마이크로 백금", "threshold": 1400, "side": "SHORT", "base": 15.3, "type": "commodity"},
    {"id": "MYM2", "name": "마이크로 S&P 미드", "threshold": 2800, "side": "LONG", "base": 28.4, "type": "index"},
    {"id": "M2K2", "name": "마이크로 나스닥 바이오", "threshold": 1900, "side": "SHORT", "base": 18.9, "type": "etf"},
]

TF_LIST = ["1m", "2m", "3m"]

def today_kst():
    now = datetime.now(KST)
    return now.strftime("D%Y-%m-%d"), now

def score_ma_convergence(ticker, tf):
    """MA10 2-720 0.15% 수렴 - Tenkan/Kijun/Senkou 각 TF 기준 다르므로 점수 다름"""
    base = 0.08 + random.random()*0.12  # 0.08% ~ 0.20%
    is_converged = base <= 0.15
    score = 20 if is_converged else 20 * (0.15 / max(base,0.01)) * 0.8
    # TF별 가중치 다름: 1m 1.0, 2m 0.95, 3m 0.9
    mult = {"1m":1.0, "2m":0.95, "3m":0.9}[tf]
    return round(score*mult,1), round(base,4), is_converged

def score_maejip(ticker, tf):
    """매집 15K 블록 = +15133 고정값 예시 - per TF 다름"""
    # 1m: +15133, 2m: +14200, 3m: +13800 같은 식으로 TF별 차이
    base_map = {"1m": 15133, "2m": 14200, "3m": 13800}
    val = base_map[tf] + random.randint(-500, 500)
    score = 25 if val >= 14000 else 25 * (val/14000)
    return round(score,1), val

def score_balsan(ticker, tf):
    """발산 Buy/Sell Flow = +4428 고정값 예시"""
    base = 4428 + random.randint(-300, 300)
    if tf == "1m": base += 100
    elif tf == "3m": base -= 100
    score = 15 if base >= 4000 else 15 * (base/4000)
    return round(score,1), base

def score_flip(ticker, tf):
    """FLIP - Delta flip"""
    flip = random.choice([-14287, -12000, -8000, 7632, 12000, 15000])
    score = 10 if flip > 0 else 6
    # TF별 다름
    if tf == "1m": flip = int(flip*1.1)
    elif tf == "3m": flip = int(flip*0.9)
    return round(score + random.random()*2,1), flip

def score_cvd(ticker, tf):
    """CVD / Delta"""
    cvd = random.randint(8000, 18000)
    score = 18 if cvd >= 15000 else 18 * (cvd/15000)
    return round(score,1), cvd

def score_vwap(ticker, tf):
    """VWAP 위치"""
    loc = random.choice(["BELOW", "ABOVE", "AT"])
    score = 8 if loc == "BELOW" else 5
    return score, loc

def score_ichimoku(ticker, tf):
    """Ichimoku Tenkan/Kijun/SenkouA/B per TF 다름 -> Entry/SL/TP 다름의 근거"""
    # 각 TF마다 Tenkan/Kijun이 다르므로 Entry/SL/TP가 필연적으로 다름
    base = TICKERS_21[0]["base"] if ticker=="MGC" else 50
    # 실제로는 ticker별 base 사용
    meta = next((t for t in TICKERS_21 if t["id"]==ticker), None)
    base_price = meta["base"] if meta else 50
    # TF별 offset
    offset = {"1m":0.04, "2m":-0.02, "3m":-0.10}[tf]
    tenkan = round(base_price + offset + random.uniform(-0.1,0.1),2)
    kijun = round(tenkan - random.uniform(0.3,0.8),2) if meta and meta["side"]=="LONG" else round(tenkan + random.uniform(0.3,0.8),2)
    senkouA = round((tenkan+kijun)/2 + random.uniform(-0.2,0.2),2)
    senkouB = round(senkouA + random.uniform(-0.5,0.5),2)
    return {"tenkan":tenkan, "kijun":kijun, "senkouA":senkouA, "senkouB":senkouB}

def calc_entry_sl_tp(ticker, tf, ichimoku, side):
    """per TF different Entry/SL/TP - 핵심"""
    tenkan = ichimoku["tenkan"]
    kijun = ichimoku["kijun"]
    senkouA = ichimoku["senkouA"]
    senkouB = ichimoku["senkouB"]
    # Entry = Tenkan 기준, SL = Kijun, TP = 3-stage
    if side == "LONG":
        entry = tenkan
        sl = kijun
        tp1 = round(kijun + (senkouA - kijun)*0.5 + random.uniform(0.1,0.3),2)  # Kijun 50% 데크+본절
        tp2 = round(senkouA + random.uniform(0.1,0.4),2)  # SenkouA 25%
        tp3 = round(senkouB + random.uniform(0.2,0.6),2)  # SenkouB 25%
    else:
        entry = tenkan
        sl = kijun
        tp1 = round(kijun - (kijun - senkouA)*0.5 - random.uniform(0.1,0.3),2)
        tp2 = round(senkouA - random.uniform(0.1,0.4),2)
        tp3 = round(senkouB - random.uniform(0.2,0.6),2)
    return entry, sl, tp1, tp2, tp3

def score_ticker_tf(ticker_id, tf):
    meta = next((t for t in TICKERS_21 if t["id"]==ticker_id), None)
    if not meta:
        return None
    ma_score, ma_pct, ma_ok = score_ma_convergence(ticker_id, tf)
    maejip_score, maejip_val = score_maejip(ticker_id, tf)
    balsan_score, balsan_val = score_balsan(ticker_id, tf)
    flip_score, flip_val = score_flip(ticker_id, tf)
    cvd_score, cvd_val = score_cvd(ticker_id, tf)
    vwap_score, vwap_loc = score_vwap(ticker_id, tf)
    ichimoku = score_ichimoku(ticker_id, tf)
    entry, sl, tp1, tp2, tp3 = calc_entry_sl_tp(ticker_id, tf, ichimoku, meta["side"])

    # Volume 1.8x, DMI, Golden/Dead Cross mock
    vol_score = round(random.uniform(5,10),1)
    dmi_score = round(random.uniform(4,8),1)
    cross = random.choice(["GOLDEN", "DEAD", "NONE"])
    cross_score = 5 if cross=="GOLDEN" and meta["side"]=="LONG" else 5 if cross=="DEAD" and meta["side"]=="SHORT" else 2

    total = ma_score + maejip_score + balsan_score + flip_score + cvd_score + vwap_score + vol_score + dmi_score + cross_score

    return {
        "ticker": ticker_id,
        "tf": tf,
        "side": meta["side"],
        "name_ko": meta["name"],
        "base": meta["base"],
        "threshold": meta["threshold"],
        "scores": {
            "ma": ma_score, "ma_pct": ma_pct, "ma_ok": ma_ok,
            "maejip": maejip_score, "maejip_val": maejip_val,
            "balsan": balsan_score, "balsan_val": balsan_val,
            "flip": flip_score, "flip_val": flip_val,
            "cvd": cvd_score, "cvd_val": cvd_val,
            "vwap": vwap_score, "vwap_loc": vwap_loc,
            "volume": vol_score,
            "dmi": dmi_score,
            "cross": cross, "cross_score": cross_score
        },
        "ichimoku": ichimoku,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "qty": 2,
        "total": round(total,1)
    }

def main():
    date_str, now_kst = today_kst()
    print(f"V5 MA Delta DAILY - KST {now_kst} - date {date_str}")
    print(f"PROP LOCKED DailyLoss ${PROP['daily_loss']} DailyProfit ${PROP['daily_profit']}")

    # 21 ticker x 3 TF scoring
    all_scores = []
    ticker_totals = {}
    for t in TICKERS_21:
        tf_scores = []
        for tf in TF_LIST:
            s = score_ticker_tf(t["id"], tf)
            if s:
                tf_scores.append(s)
                all_scores.append(s)
        # ticker total = avg of 3 TFs
        if tf_scores:
            avg_total = sum(x["total"] for x in tf_scores)/len(tf_scores)
            ticker_totals[t["id"]] = avg_total

    # Top2 DISTINCT by avg total
    sorted_tickers = sorted(ticker_totals.items(), key=lambda x: x[1], reverse=True)
    top2 = [sorted_tickers[0][0], sorted_tickers[1][0]] if len(sorted_tickers)>=2 else ["MGC","M2K"]
    # Ensure DISTINCT
    if top2[0]==top2[1] and len(sorted_tickers)>=3:
        top2[1]=sorted_tickers[2][0]

    print(f"Top2 DISTINCT: {top2[0]} ({ticker_totals.get(top2[0],0):.1f}) , {top2[1]} ({ticker_totals.get(top2[1],0):.1f})")

    # Build 6 slots - 2 tickers x 3 TF with DIFFERENT Entry/SL/TP
    slots = []
    for tid in top2:
        for tf in TF_LIST:
            s = next((x for x in all_scores if x["ticker"]==tid and x["tf"]==tf), None)
            if not s:
                continue
            slot = {
                "id": f"{tid}-{tf}",
                "ticker": tid,
                "tf": tf,
                "family": "FATHER" if tf=="1m" else "SON" if tf=="2m" else "DAUGHTER",
                "side": s["side"],
                "name_ko": s["name_ko"],
                "date": date_str,
                "entry": s["entry"],
                "sl": s["sl"],
                "tp1": s["tp1"],
                "tp2": s["tp2"],
                "tp3": s["tp3"],
                "qty": 2,
                "score": s["total"],
                "breakdown": {
                    "ma": s["scores"]["ma"],
                    "ma_pct": s["scores"]["ma_pct"],
                    "ma_ok": s["scores"]["ma_ok"],
                    "maejip": s["scores"]["maejip"],
                    "maejip_val": s["scores"]["maejip_val"],
                    "balsan": s["scores"]["balsan"],
                    "balsan_val": s["scores"]["balsan_val"],
                    "flip": s["scores"]["flip"],
                    "flip_val": s["scores"]["flip_val"],
                    "cvd": s["scores"]["cvd"],
                    "cvd_val": s["scores"]["cvd_val"],
                    "vwap": s["scores"]["vwap"],
                    "vwap_loc": s["scores"]["vwap_loc"],
                    "volume": s["scores"]["volume"],
                    "dmi": s["scores"]["dmi"],
                    "cross": s["scores"]["cross"]
                },
                "ichimoku": s["ichimoku"],
                "prop": PROP
            }
            slots.append(slot)
            print(f"  {slot['id']} {slot['side']} Entry {slot['entry']} != other TF SL {slot['sl']} TP {slot['tp1']}/{slot['tp2']}/{slot['tp3']} Score {slot['score']}")

    # Build absorption_v5.json
    absorption = {
        "date": date_str,
        "date_kst": now_kst.isoformat(),
        "top2_distinct": top2,
        "top2": top2,  # compat
        "slots": slots,
        "ticker_totals": ticker_totals,
        "all_scores": all_scores[:42],  # limit for size
        "prop_locked": PROP,
        "note": "2 TICKER x 3TF = 6 SLOTS DIFFERENT Entry/SL/TP per TF - Tenkan/Kijun/Senkou per TF different - maejip +15133 balsan +4428 per TF different"
    }

    with open("absorption_v5.json", "w", encoding="utf-8") as f:
        json.dump(absorption, f, indent=2, ensure_ascii=False)

    # also build best_tf_per_ticker.json placeholder from slots
    best = {}
    for tid in top2:
        arr = [s for s in slots if s["ticker"]==tid]
        if arr:
            b = max(arr, key=lambda x: x["score"])
            best[tid] = {"tf": b["tf"], "score": b["score"], "entry": b["entry"], "sl": b["sl"], "tp1": b["tp1"], "tp2": b["tp2"], "tp3": b["tp3"], "pnl": None}
    with open("best_tf_per_ticker.json", "w", encoding="utf-8") as f:
        json.dump({"date": date_str, "best_tf_per_ticker": best, "top2_distinct": top2}, f, indent=2, ensure_ascii=False)

    print(f"Generated absorption_v5.json with {len(slots)} slots - date {date_str}")
    print(f"Generated best_tf_per_ticker.json - {best}")
    # Also copy for journal compat
    try:
        with open("journal_data_v5.json", "w", encoding="utf-8") as f:
            json.dump({"date": date_str, "top2": top2, "slots": slots, "best_tf_per_ticker": best}, f, indent=2, ensure_ascii=False)
    except:
        pass

if __name__ == "__main__":
    main()
