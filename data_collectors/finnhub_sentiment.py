
import os, requests
from datetime import datetime, timedelta

FINNHUB_KEY = os.getenv("FINNHUB_KEY")

def fetch_news_sentiment(ticker="SLV"):
    if not FINNHUB_KEY:
        return {"ticker": ticker, "error": "NO_KEY"}
    try:
        # 최근 7일 뉴스
        today = datetime.utcnow().date()
        from_date = today - timedelta(days=7)
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={from_date}&to={today}&token={FINNHUB_KEY}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        news = r.json()[:10]  # 상위 10개만
        # 간단 점수: 헤드라인에 "high", "record", "surge" vs "crash", "plunge" 카운트
        pos_words = ["high","record","surge","rally","bull","gain","up"]
        neg_words = ["crash","plunge","fear","drop","down","bear","sell"]
        score = 0
        for n in news:
            hl = (n.get("headline","") or "").lower()
            score += sum(1 for w in pos_words if w in hl)
            score -= sum(1 for w in neg_words if w in hl)
        return {"ticker": ticker, "count": len(news), "sentiment_score": score, "samples": [x.get("headline") for x in news[:3]]}
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}

def fetch_all():
    tickers = ["SLV","GLD","CPER","IBIT"]
    return {t: fetch_news_sentiment(t) for t in tickers}

if __name__ == "__main__":
    print(fetch_all())
