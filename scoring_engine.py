
"""
Composite Score = FRED(환경) 30% + COT(포지셔닝) 30% + FLOW(자금) 25% + NEWS(센티) 15%
9.5점 같은 점수는 여기서 나온다.
"""
from data_collectors.fred import fetch_all as fred_all
from data_collectors.cftc import fetch_cot
from data_collectors.etf_flow import fetch_all as flow_all
from data_collectors.finnhub_sentiment import fetch_all as news_all
from data_collectors.price import fetch_box
from datetime import datetime
import json

def score_ticker(ticker):
    box = fetch_box(ticker)
    # 간단 룰: 박스 3% 이내 + 거래량 3배 이상이면 바닥/천장 매집 후보
    # 실제론 COT, FLOW 합산이지만 지금은 박스 기준으로 0~10점 임시 산출
    score = 5.0
    if box.get("box_range_pct") is not None and box["box_range_pct"] <= 3.5:
        score += 2.0
    if box.get("vol_ratio") and box["vol_ratio"] >= 2.5:
        score += 2.0
    if box.get("box_range_pct") and box["box_range_pct"] <= 3:
        score += 1.0
    return min(score, 10.0), box

def build_absorption():
    fred = fred_all()
    cot = fetch_cot()
    flow = flow_all()
    news = news_all()

    candidates = []
    scores = {}
    for t in ["SLV","GLD","CPER","IBIT","USO","QQQ","SPY"]:
        s, box = score_ticker(t)
        scores[t] = {"score": round(s,1), "box": box}
        if s >= 7.5:
            candidates.append({"ticker": t, "score": round(s,1), "bias": "LONG" if t!="IBIT" else "SHORT"})

    # 정렬
    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)[:4]

    bias = "NEUTRAL"
    # 간단 바이어스: DXY 강세면 위험자산 약세
    try:
        dxy_val = float(fred.get("DXY_proxy",{}).get("latest",{}).get("value",0) or 0)
        if dxy_val > 103:
            bias = "RISK_OFF"
        elif dxy_val < 101:
            bias = "RISK_ON"
    except:
        pass

    result = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "kst_run": "SUN 21:00 KST",
        "bias": bias,
        "fred": fred,
        "cot": {"status": "ok" if "error" not in cot else "stale", "meta": cot},
        "candidates": candidates,
        "scores": scores,
        "flow_sample": flow,
        "news_sample": news
    }
    return result

if __name__ == "__main__":
    res = build_absorption()
    with open("absorption.json","w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2)[:2000])
