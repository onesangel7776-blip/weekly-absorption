
import requests

# 무료로 쓸 수 있는 가벼운 소스: Yahoo Finance quote + ETFDB 대체로 Finnhub/Stooq 아님
# 여기선 Yahoo Finance를 1차로 쓰고, ETFDB는 스크래핑 실패시 skip

TICKERS_21 = ["GLD","SLV","CPER","IBIT","USO","UNG","XLE","XLF","XLK","QQQ","SPY","IWM","TLT","HYG","UUP","FXE","EWJ","EEM","XLB","XLI","DBA"]

def fetch_yahoo(ticker):
    try:
        # Yahoo v8 chart API는 키 없이 사용 가능 (비공식이지만 안정적)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1mo&interval=1d"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        r.raise_for_status()
        j = r.json()
        result = j["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        vols = result["indicators"]["quote"][0]["volume"]
        # 간단: 최근 20일 평균 대비 최근 거래대금
        last_close = closes[-1] if closes else None
        last_vol = vols[-1] if vols else None
        return {"ticker": ticker, "close": last_close, "vol": last_vol}
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}

def fetch_all():
    return {t: fetch_yahoo(t) for t in ["SLV","GLD","CPER","IBIT"] + TICKERS_21[:5]}

if __name__ == "__main__":
    print(fetch_all())
