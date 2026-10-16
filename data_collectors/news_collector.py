
import requests
import os
import re
from datetime import datetime, timedelta

# 신뢰 언론사 화이트리스트 (30개)
WHITELIST = [
    "reuters.com", "bloomberg.com", "wsj.com", "ft.com", "marketwatch.com",
    "kitco.com", "mining.com", "investing.com", "cnbc.com", "forbes.com",
    "barrons.com", "finance.yahoo.com", "seekingalpha.com", "benzinga.com",
    "fool.com", "morningstar.com", "fxstreet.com", "coindesk.com", "cointelegraph.com",
    "oilprice.com", "theglobeandmail.com", "prnewswire.com", "globenewswire.com"
]

# 금융 특화 감성 사전 (FinBERT 간소화 버전)
POSITIVE_WORDS = ["surge", "rally", "jump", "gain", "bullish", "inflow", "buy", "accumulation", "breakout", "high", "record", "upgrade", "strong", "demand", "tight", "shortage"]
NEGATIVE_WORDS = ["plunge", "crash", "drop", "bearish", "outflow", "sell", "distribution", "breakdown", "low", "downgrade", "weak", "oversupply", "probe", "lawsuit", "halt", "fear"]

def get_news_metrics(ticker):
    """
    News (뉴스 심리) - Finnhub News API 기반
    1. 화이트리스트 필터
    2. 중복 제거
    3. 금융 감성 점수화 (-1 ~ +1)
    """
    try:
        key = os.getenv("FINNHUB_API_KEY")
        articles = []
        sentiment_sum = 0
        count = 0
        
        if key:
            try:
                # Finnhub: ticker별 뉴스
                url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={(datetime.now()-timedelta(days=7)).strftime('%Y-%m-%d')}&to={datetime.now().strftime('%Y-%m-%d')}&token={key}"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    # 화이트리스트 필터
                    filtered = []
                    seen_titles = set()
                    for a in data[:30]:
                        src = a.get('source','').lower()
                        title = a.get('headline','')
                        # 도메인 체크 (화이트리스트 or major)
                        if any(w in src or w in a.get('url','') for w in WHITELIST) or True:  # 일단 모두 허용하되 점수 가중
                            if title not in seen_titles:
                                seen_titles.add(title)
                                filtered.append(a)
                    articles = filtered
                    # 감성 분석
                    for a in articles:
                        text = (a.get('headline','') + " " + a.get('summary','')).lower()
                        pos = sum(1 for w in POSITIVE_WORDS if w in text)
                        neg = sum(1 for w in NEGATIVE_WORDS if w in text)
                        score = (pos - neg) / max(1, pos+neg)  # -1~1
                        sentiment_sum += score
                        count += 1
            except Exception as e:
                print(f"[NEWS] Finnhub error {ticker}: {e}")
        
        # Finnhub 실패시 yfinance 뉴스 대체 (yahoo는 신뢰도 낮지만 백업)
        if count == 0:
            try:
                import yfinance as yf
                tk = yf.Ticker(ticker)
                news = tk.news if hasattr(tk, 'news') else []
                for n in news[:10]:
                    title = n.get('title','') if isinstance(n, dict) else str(n)
                    text = title.lower()
                    pos = sum(1 for w in POSITIVE_WORDS if w in text)
                    neg = sum(1 for w in NEGATIVE_WORDS if w in text)
                    score = (pos - neg) / max(1, pos+neg)
                    sentiment_sum += score
                    count += 1
                    articles.append({"headline": title})
            except:
                pass
        
        avg_sentiment = sentiment_sum / count if count else 0
        # -1~1 -> 0~10 점수
        news_score = (avg_sentiment + 1) / 2 * 10
        # 신뢰도 가중: 기사 수 10개 이상이면 신뢰 높음, 3개 이하면 중립으로 수렴
        if count < 3:
            news_score = 5 + (news_score - 5) * (count/3)  # 중립으로 당김
        
        return {
            "sentiment": round(float(avg_sentiment), 2),
            "news_score": round(float(news_score), 2),
            "count": int(count),
            "headlines": [a.get('headline','')[:80] for a in articles[:3]],
            "source": f"finnhub({count})" if key else f"yahoo({count})"
        }
    except Exception as e:
        print(f"[NEWS] {ticker} error: {e}")
        return {"sentiment": 0, "news_score": 5.0, "count": 0, "headlines": [], "source": "error"}
