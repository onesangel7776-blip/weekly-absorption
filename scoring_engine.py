
"""
weekly-absorption - 하이브리드 자동+수동
Strength Score = 40% Box + 20% COT + 20% Flow + 20% News
매일 21:00 KST 자동 실행 -> absorption.json -> docs/index.html + Discord
"""
import os
import json
from datetime import datetime
from data_collectors.box_collector import get_box_metrics
from data_collectors.cot_collector import get_cot_metrics, normalize_cot_score
from data_collectors.flow_collector import get_flow_metrics
from data_collectors.news_collector import get_news_metrics

TICKERS = ["SLV","GLD","UNG","CPER","COPX","USO","GDX","XLB","XLE","DBA","EEM","UUP","TLT","XLF","IWM","SMH","QQQ","SPY","XLK","IBIT","BITO"]

# DXY, US10Y는 FRED에서 가져오기
def get_macro_bias():
    try:
        import requests
        fred_key = os.getenv("FRED_API_KEY")
        dxy = 102.21
        us10y = 4.56
        bias = "TIGHTENING"
        if fred_key:
            # FRED: DXY (DTWEXBGS), US10Y (DGS10)
            try:
                r = requests.get(f"https://api.stlouisfed.org/fred/series/observations?series_id=DTWEXBGS&api_key={fred_key}&file_type=json&sort_order=desc&limit=1", timeout=10)
                if r.status_code==200:
                    obs = r.json().get('observations',[])
                    if obs and obs[0]['value']!='.':
                        dxy = float(obs[0]['value'])
            except:
                pass
            try:
                r = requests.get(f"https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key={fred_key}&file_type=json&sort_order=desc&limit=1", timeout=10)
                if r.status_code==200:
                    obs = r.json().get('observations',[])
                    if obs and obs[0]['value']!='.':
                        us10y = float(obs[0]['value'])
            except:
                pass
        # Bias 판정: DXY 하락 + 금리 하락 = EASING
        if dxy < 101 and us10y < 4.3:
            bias = "EASING"
        elif dxy > 103 and us10y > 4.6:
            bias = "TIGHTENING"
        else:
            bias = "NEUTRAL"
        return {"dxy": round(dxy,2), "us10y": round(us10y,2), "bias": bias}
    except Exception as e:
        print(f"[MACRO] error {e}")
        return {"dxy": 102.21, "us10y": 4.56, "bias": "TIGHTENING"}

def score_ticker(ticker):
    print(f"\n=== Scoring {ticker} ===")
    box = get_box_metrics(ticker)
    if not box:
        print(f"  Box failed for {ticker}")
        box = {"box_range_pct": 5.0, "box_score": 5.0, "vol_mult": 1.0, "dwell": 0}
    cot = get_cot_metrics(ticker)
    cot_score = normalize_cot_score(cot.get("cot_pct",50)) if "cot_pct" in cot else cot.get("cot_score",5.0)
    flow = get_flow_metrics(ticker)
    news = get_news_metrics(ticker)
    
    # 최종 점수: 40/20/20/20
    strength = (
        box.get("box_score",5)*0.4 +
        cot_score*0.2 +
        flow.get("flow_score",5)*0.2 +
        news.get("news_score",5)*0.2
    )
    strength = round(max(0,min(10,strength)),1)
    
    # 상태 판정
    if strength >= 7.0:
        status = "BOTTOM"
        sentiment = "BULLISH" if strength>=7.5 else "MIXED"
    elif strength <= 4.0:
        status = "TOP"
        sentiment = "BEARISH"
    else:
        status = "NEUTRAL"
        sentiment = "MIXED"
    
    return {
        "ticker": ticker,
        "score": strength,
        "status": status,
        "sentiment": sentiment,
        "box_range": box.get("box_range_pct"),
        "vol_mult": box.get("vol_mult"),
        "dwell": box.get("dwell"),
        "cot_pct": cot.get("cot_pct"),
        "flow_m": flow.get("flow_m"),
        "news_sentiment": news.get("sentiment"),
        "news_count": news.get("count"),
        "breakdown": {
            "box_score": box.get("box_score"),
            "cot_score": round(cot_score,2),
            "flow_score": flow.get("flow_score"),
            "news_score": news.get("news_score")
        },
        "close": box.get("close"),
        "details": {
            "box_high": box.get("box_high"),
            "box_low": box.get("box_low")
        }
    }

def main():
    print(f"Starting scoring at {datetime.now()}")
    macro = get_macro_bias()
    print(f"Macro: {macro}")
    results = []
    for t in TICKERS:
        try:
            r = score_ticker(t)
            results.append(r)
        except Exception as e:
            print(f"Failed {t}: {e}")
            results.append({"ticker": t, "score": 5.0, "status": "NEUTRAL", "sentiment": "MIXED", "box_range": 5.0, "vol_mult": 1.0, "dwell": 0, "cot_pct": 50, "flow_m": 0, "news_sentiment": 0})
    
    # 정렬: 점수 높은 순
    results_sorted = sorted(results, key=lambda x: x['score'], reverse=True)
    
    bottom = [r for r in results_sorted if r['score']>=7.0]
    top = [r for r in results_sorted if r['score']<=4.0]
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "macro": macro,
        "tickers": results_sorted,
        "summary": {
            "bottom_count": len(bottom),
            "top_count": len(top),
            "top_pick": results_sorted[0]['ticker'] if results_sorted else None
        }
    }
    
    # 저장: 루트와 docs 둘 다
    with open("absorption.json","w",encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    os.makedirs("docs", exist_ok=True)
    with open("docs/absorption.json","w",encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("\n=== FINAL RANKING ===")
    for r in results_sorted:
        print(f"{r['ticker']:4} {r['score']:4} {r['status']:7} Box:{r['breakdown']['box_score']} COT:{r['breakdown']['cot_score']} Flow:{r['breakdown']['flow_score']} News:{r['breakdown']['news_score']}")
    
    print("\nSaved to absorption.json and docs/absorption.json")
    return output

if __name__ == "__main__":
    main()
