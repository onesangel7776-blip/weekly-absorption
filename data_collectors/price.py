
import requests

def fetch_box(ticker):
    # 3% Box + 3x Vol 로직을 위한 최근 데이터
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=3mo&interval=1d"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        r.raise_for_status()
        j = r.json()["chart"]["result"][0]
        closes = [c for c in j["indicators"]["quote"][0]["close"] if c]
        vols = [v for v in j["indicators"]["quote"][0]["volume"] if v]
        if len(closes) < 22: 
            return {"ticker": ticker, "error": "not enough data"}
        # 최근 22일 체류, 3% 박스, 거래대금 3x 체크용 기초값
        recent = closes[-22:]
        box_high = max(recent)
        box_low = min(recent)
        box_range_pct = (box_high - box_low) / box_low * 100 if box_low else None
        avg_vol = sum(vols[-22:]) / 22 if vols else None
        last_vol = vols[-1] if vols else None
        return {
            "ticker": ticker,
            "box_high": box_high,
            "box_low": box_low,
            "box_range_pct": round(box_range_pct,2) if box_range_pct else None,
            "avg_vol_22": avg_vol,
            "last_vol": last_vol,
            "vol_ratio": round(last_vol/avg_vol,2) if avg_vol and last_vol else None
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}

if __name__ == "__main__":
    for t in ["SLV","GLD","CPER","IBIT"]:
        print(fetch_box(t))
