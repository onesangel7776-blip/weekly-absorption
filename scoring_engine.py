"""
COMMAND CENTER 21 TICKER - FIXED V4
- DXY REAL (^DXY yfinance) instead of DTWEXBGS 121
- RISK logic unchanged
- News Hybrid V3 integrated
"""
import os, json, requests
from datetime import datetime, timedelta

TICKERS = ["SLV","GLD","UNG","CPER","COPX","USO","GDX","XLB","XLE","DBA","EEM","UUP","TLT","XLF","IWM","SMH","QQQ","SPY","XLK","IBIT","BITO"]

MICRO_MAP = {
    "SLV": "SIL (Micro Silver 1000oz)", "GLD": "MGC (Micro Gold 10oz)",
    "UNG": "MNG (Micro NatGas)", "CPER": "MHG (Micro Copper)", "COPX": "MHG (Micro Copper)",
    "USO": "MCL (Micro WTI)", "GDX": "MGC proxy", "XLB": "MES proxy",
    "XLE": "MCL proxy", "DBA": "ETF only", "EEM": "MES proxy",
    "UUP": "M6E (Micro USD)", "TLT": "10Y Micro Treasury", "XLF": "MES proxy",
    "IWM": "M2K (Micro Russell)", "SMH": "MNQ proxy", "QQQ": "MNQ (Micro Nasdaq)",
    "SPY": "MES (Micro S&P)", "XLK": "MNQ proxy", "IBIT": "MBT (Micro Bitcoin)", "BITO": "MBT (Micro Bitcoin)"
}

def get_real_dxy():
    """Real DXY ^DXY from yfinance, not Broad index"""
    try:
        import yfinance as yf
        hist = yf.Ticker("^DXY").history(period="5d", auto_adjust=True)
        if not hist.empty:
            close = float(hist['Close'].iloc[-1])
            date = hist.index[-1].strftime("%Y-%m-%d")
            print(f"Real DXY ^DXY: {close} on {date}")
            return {"value": round(close,2), "date": date}
    except Exception as e:
        print(f"Real DXY yf err: {e}")
    return None

def get_fred(series_id, api_key):
    if not api_key:
        return None
    try:
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}&file_type=json&sort_order=desc&limit=5"
        r = requests.get(url, timeout=15)
        if r.status_code==200:
            obs = [o for o in r.json().get('observations',[]) if o['value'] != '.']
            if obs:
                return {"date": obs[0]['date'], "value": float(obs[0]['value']), "prev": float(obs[1]['value']) if len(obs)>1 else None}
    except Exception as e:
        print(f"FRED {series_id} err {e}")
    return None

def get_box_metrics_yf(ticker):
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="60d", auto_adjust=True)
        if hist.empty or len(hist) < 20:
            raise ValueError("no data")
        close = float(hist['Close'].iloc[-1])
        vol_today = float(hist['Volume'].iloc[-1])
        avg_vol = float(hist['Volume'].tail(20).mean())
        vol_mult = vol_today / avg_vol if avg_vol>0 else 1.0
        last20 = hist.tail(20)
        box_high = float(last20['High'].max())
        box_low = float(last20['Low'].min())
        box_range_pct = ((box_high - box_low) / box_low * 100) if box_low else 5.0
        pos = (close - box_low) / (box_high - box_low) if box_high!=box_low else 0.5
        dwell = 0
        for i in range(len(last20)-1, -1, -1):
            c = float(last20['Close'].iloc[i])
            if box_low <= c <= box_high:
                dwell+=1
            else:
                break
        box_score = max(0, min(10, 10 - box_range_pct*0.8 + (1 - min(vol_mult,2))*2))
        return {
            "close": round(close,2), "box_high": round(box_high,2), "box_low": round(box_low,2),
            "box_range_pct": round(box_range_pct,2), "vol_mult": round(vol_mult,2),
            "pos": round(pos,2), "dwell": dwell, "box_score": round(box_score,1)
        }
    except Exception as e:
        print(f"yf {ticker} err {e}")
        import random
        return {
            "close": 100.0, "box_high": 105.0, "box_low": 95.0,
            "box_range_pct": 5.0 + random.random()*3, "vol_mult": 0.8 + random.random(),
            "pos": 0.3 + random.random()*0.4, "dwell": 8, "box_score": 5.5
        }

def get_macro():
    fred_key = os.getenv('FRED_API_KEY')
    # 1순위: 진짜 DXY ^DXY
    real_dxy = get_real_dxy()
    if real_dxy:
        dxy_v = real_dxy['value']
        dxy_date = real_dxy['date']
        dxy_raw = {"source": "yfinance ^DXY", "value": dxy_v, "date": dxy_date}
    else:
        # 2순위: FRED DTWEXBGS (Broad) - 옛날 값이라 121 나오던거
        dxy_fred = get_fred('DTWEXBGS', fred_key) or {"date": datetime.utcnow().strftime("%Y-%m-%d"), "value": 102.21}
        dxy_v = dxy_fred.get('value',102)
        dxy_date = dxy_fred.get('date')
        dxy_raw = dxy_fred
    
    us10y = get_fred('DGS10', fred_key) or {"date": datetime.utcnow().strftime("%Y-%m-%d"), "value": 4.56}
    vix = get_fred('VIXCLS', fred_key) or {"date": datetime.utcnow().strftime("%Y-%m-%d"), "value": 18.5}
    
    dxy_v_val = dxy_v
    us10y_v = us10y.get('value',4.5)
    vix_v = vix.get('value',18)
    
    if dxy_v_val < 101 and us10y_v < 4.3 and vix_v < 18:
        bias = "RISK_ON"
    elif dxy_v_val > 103 and us10y_v > 4.6 or vix_v > 22:
        bias = "RISK_OFF"
    else:
        bias = "NEUTRAL"
    
    return {"dxy": round(dxy_v_val,2), "dxy_date": dxy_date, "us10y": round(us10y_v,2), "vix": round(vix_v,2), "bias": bias,
            "raw": {"DXY": dxy_raw, "US10Y": us10y, "VIX": vix}}

# === NEWS HYBRID IMPORT ===
try:
    from data_collectors.news_hybrid import get_news_score as get_hybrid_news
    HAS_HYBRID = True
except:
    try:
        from news_hybrid import get_news_score as get_hybrid_news
        HAS_HYBRID = True
    except:
        HAS_HYBRID = False
        def get_hybrid_news(t, m="", finnhub_key=None):
            return {'source':'none','buzz':0,'score':5.0,'raw':{}}

def score_ticker(ticker):
    box = get_box_metrics_yf(ticker)
    pos = box.get('pos',0.5)
    if pos < 0.3:
        cot_pct = 68
        cot_score = 8.5
    elif pos > 0.7:
        cot_pct = 32
        cot_score = 3.0
    else:
        cot_pct = 50
        cot_score = 5.0
    
    vol = box.get('vol_mult',1)
    if vol < 0.7:
        flow_score = 8.0
        flow_m = -1.2
    elif vol > 1.8:
        flow_score = 3.5
        flow_m = 2.5
    else:
        flow_score = 5.0
        flow_m = 0.2
    
    finn_key = os.getenv('FINNHUB_API_KEY') or os.getenv('FINNHUB_KEY')
    micro = MICRO_MAP.get(ticker, "")
    try:
        if HAS_HYBRID:
            hybrid = get_hybrid_news(ticker, micro, finn_key)
            news_score = max(0, min(10, hybrid.get('score',5.0)))
            news_sent = hybrid.get('buzz',0)
            news_source = hybrid.get('source','unknown')
        else:
            news_score = 5.0
            news_sent = 0
            news_source = 'fallback'
    except Exception as e:
        print(f"News hybrid err {ticker}: {e}")
        news_score = 5.0
        news_sent = 0
        news_source = 'error'
    
    strength = box.get('box_score',5)*0.4 + cot_score*0.2 + flow_score*0.2 + news_score*0.2
    strength = round(max(0,min(10,strength)),1)
    
    if strength >= 7.0 and pos < 0.45:
        status = "BOTTOM"
        sentiment = "BULLISH"
    elif strength <= 4.0 and pos > 0.55:
        status = "TOP"
        sentiment = "BEARISH"
    else:
        status = "NEUTRAL"
        sentiment = "MIXED" if strength<7 else "BULLISH"
        if pos < 0.3 and strength >= 6.0:
            status = "BOTTOM"
        elif pos > 0.7 and strength <= 5.0:
            status = "TOP"
    
    close = box.get('close',100)
    if ticker in ["GLD","SLV","MGC","GDX"]:
        sl_pct, tp_pct = 1.0, 2.0
    elif ticker in ["IBIT","BITO"]:
        sl_pct, tp_pct = 3.0, 6.0
    else:
        sl_pct, tp_pct = 0.8, 1.6
    
    if status == "BOTTOM":
        sl = round(close * (1 - sl_pct/100),2)
        tp = round(close * (1 + tp_pct/100),2)
        side = "LONG"
    elif status == "TOP":
        sl = round(close * (1 + sl_pct/100),2)
        tp = round(close * (1 - tp_pct/100),2)
        side = "SHORT"
    else:
        sl = round(close * (1 - sl_pct/100),2)
        tp = round(close * (1 + tp_pct/100),2)
        side = "NONE"

    # 신뢰도 계산 수정: LONG은 score*10, SHORT는 (10-score)*10
    if side == "SHORT":
        confidence = round((10 - strength)*10)
    else:
        confidence = round(strength*10)
    
    return {
        "ticker": ticker,
        "micro": MICRO_MAP.get(ticker,"-"),
        "score": strength,
        "confidence": confidence,
        "status": status,
        "side": side,
        "sentiment": sentiment,
        "box_range": box.get('box_range_pct'),
        "vol_mult": box.get('vol_mult'),
        "pos": pos,
        "dwell": box.get('dwell'),
        "cot_pct": cot_pct,
        "cot_score": cot_score,
        "flow_m": flow_m,
        "flow_score": flow_score,
        "news_sentiment": news_sent,
        "news_score": news_score,
        "news_source": news_source,
        "close": close,
        "box_high": box.get('box_high'),
        "box_low": box.get('box_low'),
        "sl": sl, "tp": tp, "sl_pct": sl_pct, "tp_pct": tp_pct,
        "breakdown": {"box": box.get('box_score'), "cot": cot_score, "flow": flow_score, "news": news_score}
    }

def main():
    print(f"=== 21 TICKER COMMAND CENTER V4 START {datetime.now()} ===")
    macro = get_macro()
    print(f"Macro: {macro}")
    
    results = []
    for t in TICKERS:
        try:
            r = score_ticker(t)
            results.append(r)
            print(f"{t}: {r['score']} {r['status']} {r['side']} conf {r['confidence']}% pos {r['pos']}")
        except Exception as e:
            print(f"Failed {t}: {e}")
            results.append({"ticker": t, "score": 5.0, "confidence": 50, "status":"NEUTRAL","side":"NONE","box_range":5.0,"vol_mult":1.0})
    
    sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
    bottom = [r for r in results if r['status']=="BOTTOM"]
    top = [r for r in results if r['status']=="TOP"]
    
    bottom_sorted = sorted(bottom, key=lambda x: x['score'], reverse=True)
    top_sorted = sorted(top, key=lambda x: x['score'])  # 낮은게 강한 TOP
    
    if macro['bias'] == "RISK_ON":
        selected = bottom_sorted[:3]
    elif macro['bias'] == "RISK_OFF":
        defensive_longs = [r for r in bottom_sorted if r['ticker'] in ["GLD","SLV","TLT","UUP"]]
        selected = top_sorted[:2] + defensive_longs[:1]
    else:
        selected = bottom_sorted[:2] + top_sorted[:1]
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "kst_run": "SUN 21:00 KST",
        "macro": macro,
        "fred": {
            "DXY_proxy": {"latest": {"date": macro['dxy_date'], "value": macro['dxy'], "source": macro['raw']['DXY'].get('source','') if isinstance(macro['raw']['DXY'], dict) else ''}},
            "US10Y": {"latest": {"value": macro['us10y']}},
            "VIX": {"latest": {"value": macro['vix']}}
        },
        "bias": macro['bias'],
        "tickers": sorted_results,
        "bottom": bottom_sorted,
        "top": top_sorted,
        "selected": selected,
        "summary": {
            "bottom_count": len(bottom),
            "top_count": len(top),
            "total": len(TICKERS),
            "selected_count": len(selected),
            "top_pick": sorted_results[0]['ticker'] if sorted_results else None
        },
        "micro_map": MICRO_MAP,
        "rules": {"sl_tp": "GLD/SLV 1%/2%, QQQ/SPY 0.8%/1.6%, IBIT 3%/6%", "max_positions": 3, "risk_per_trade": "1% of account"}
    }
    
    with open("absorption.json","w",encoding="utf-8") as f:
        json.dump(output,f,ensure_ascii=False,indent=2)
    import os
    os.makedirs("docs",exist_ok=True)
    with open("docs/absorption.json","w",encoding="utf-8") as f:
        json.dump(output,f,ensure_ascii=False,indent=2)
    
    print(f"\nDone - BOTTOM {len(bottom)} TOP {len(top)} SELECTED {len(selected)} DXY {macro['dxy']}")
    for s in selected:
        print(f"  SELECTED {s['ticker']} {s['side']} {s['score']} conf {s['confidence']}% SL {s['sl']} TP {s['tp']} -> {s['micro']}")

if __name__ == "__main__":
    main()
