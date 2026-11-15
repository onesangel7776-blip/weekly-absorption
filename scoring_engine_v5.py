"""
Command Center V5 - Scoring Engine
MA Convergence + Delta Divergence + CVD Flip + Location + Daemok
기존 V4는 건들지 않음, V5 전용
"""
import json
from datetime import datetime

TICKERS_21 = [
    "MGC","MNG","SIL","M2K","MES","MNQ","MBT","MYM",
    "MCL","M6E","M6B","M6A","MNQ2","MES2","MYM2",
    "GDX","TLT","IWM","XLE","SPY","DBA"
]

def calc_ma_converge(ma2, ma4, ma8, ma16):
    """이평 수렴 0.15% 이내 체크 - 사진의 MA(2,4,8,16) 겹친 자리"""
    mas = [ma2, ma4, ma8, ma16]
    spread = (max(mas) - min(mas)) / min(mas) * 100
    return 15 if spread < 0.15 else 0, spread

def calc_location_score(location_str):
    """VAL, D-100%, W-75% 극단자리 20점 - 같은 +4000이어도 가는 자리"""
    extreme = ["VAL","D-100","D-75","W-75","W-100"]
    for e in extreme:
        if e in location_str:
            return 20
    return 0

def calc_daemok_score(delta_detail, daemok_val):
    """대목롱 +15133 같이 세력 물량 동반 20점"""
    if "대목" in delta_detail and daemok_val >= 4000:
        return 20
    if daemok_val >= 10000:
        return 20
    if delta_detail.count("Buy") and daemok_val >= 4000:
        return 10
    return 0

def calc_cvd_flip_score(cvd_prev, cvd_now):
    """CVD -14287 -> +7632 플립 15점"""
    if cvd_prev < 0 and cvd_now > 0 and cvd_now > 7000:
        return 15
    if cvd_prev < 0 and cvd_now > 0:
        return 10
    return 0

def calc_vwap_score(close, vwap, side):
    """VWAP 돌파 10점"""
    if side == "LONG" and close > vwap:
        return 10
    if side == "SHORT" and close < vwap:
        return 10
    return 0

def calc_score_15vs5(score_long, score_short):
    """Score 15 vs 5 같은 AI 브리핑 10점"""
    if abs(score_long - score_short) >= 10:
        return 10
    return 0

def calc_vol_score(vol, vol_ma20):
    """Vol 1.8배 폭발 10점 - 사진 Vol(BTC) 34.3 같은"""
    if vol >= vol_ma20 * 1.8:
        return 10
    return 0

def total_score(ticker_data):
    loc = calc_location_score(ticker_data["location"])
    daemok = calc_daemok_score(ticker_data["delta_detail"], ticker_data["daemok"])
    cvd = calc_cvd_flip_score(ticker_data["cvd_prev"], ticker_data["cvd_now"])
    _, ma_spread = calc_ma_converge(ticker_data["ma2"], ticker_data["ma4"], ticker_data["ma8"], ticker_data["ma16"])
    ma_score = 15 if ma_spread < 0.15 else 0
    vwap = calc_vwap_score(ticker_data["close"], ticker_data["vwap"], ticker_data["side"])
    score155 = calc_score_15vs5(ticker_data["score_long"], ticker_data["score_short"])
    vol = calc_vol_score(ticker_data["vol"], ticker_data["vol_ma20"])

    total = loc + daemok + cvd + ma_score + vwap + score155 + vol
    return {
        "ticker": ticker_data["ticker"],
        "location": loc,
        "daemok": daemok,
        "cvd_flip": cvd,
        "ma_converge": ma_score,
        "ma_spread": round(ma_spread,4),
        "vwap": vwap,
        "score155": score155,
        "vol": vol,
        "total": total,
        "go": total >= 80,
        "delta_badge": ticker_data["delta_badge"],
        "cvd_now": ticker_data["cvd_now"]
    }

# Mock run for test
if __name__ == "__main__":
    sample = {
        "ticker": "MGC",
        "location": "VAL D-100%",
        "delta_detail": "Buy 4.5K / Sell 0K 대목롱 +15133",
        "daemok": 15133,
        "cvd_prev": -14287,
        "cvd_now": 7632,
        "ma2": 64871, "ma4": 64910, "ma8": 64935, "ma16": 64891,
        "close": 64950, "vwap": 63787,
        "side": "LONG",
        "score_long": 15, "score_short": 5,
        "vol": 34.3, "vol_ma20": 18,
        "delta_badge": "+4428"
    }
    print(json.dumps(total_score(sample), ensure_ascii=False, indent=2))
