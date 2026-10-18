"""
NEWS HYBRID COLLECTOR - Finnhub Primary + GDELT Backup
- Finnhub 1순위: /news-sentiment -> companyNewsScore (0-10)
- GDELT 2순위: 기사 수 기반
- Fallback: 5점 neutral
"""
import os, requests
from datetime import datetime, timedelta

def get_finnhub_score(ticker, api_key):
    if not api_key:
        return None
    try:
        # 1) sentiment endpoint
        url = f"https://finnhub.io/api/v1/news-sentiment?symbol={ticker}&token={api_key}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            j = r.json()
            # companyNewsScore is 0-10? Sometimes 0-1, convert
            score = j.get('companyNewsScore')
            buzz = j.get('buzz', {})
            articles = buzz.get('articlesInLastWeek', 0) if isinstance(buzz, dict) else 0
            if score is not None:
                # finnhub score sometimes 0-1, normalize to 0-10
                if score <= 1.0 and score > 0:
                    score = score * 10
                # clamp 0-10
                score = max(0, min(10, float(score)))
                # if buzz is high, slightly boost?
                return {'source': 'finnhub', 'score': round(score,1), 'buzz': articles, 'raw': j}
            else:
                # no sentiment but has buzz -> neutral 5 + buzz info
                if articles > 0:
                    return {'source': 'finnhub', 'score': 5.0, 'buzz': articles, 'raw': j}
        # 429 = rate limit
        if r.status_code == 429:
            print(f"Finnhub 429 rate limit for {ticker}")
            return {'source': 'finnhub_ratelimit', 'score': 5.0, 'buzz': 0, 'raw': {'status':429}}
    except Exception as e:
        print(f"Finnhub err {ticker}: {e}")
    return None

def get_gdelt_score(ticker, micro=""):
    try:
        # GDELT doc 2.0 - last 7 days article count
        query = ticker
        if micro:
            query = f"{ticker} OR {micro}"
        # use 7 days
        url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=TimelineVol&timespan=7d&format=json"
        r = requests.get(url, timeout=12)
        if r.status_code == 200:
            j = r.json()
            # timeline vol gives counts
            timeline = j.get('timeline', [{}])[0].get('data', [])
            total_vol = sum([d.get('value',0) for d in timeline]) if timeline else 0
            # score mapping: high vol = higher attention, neutral 5-7
            # If vol > 100 => 7, >50 =>6, else 5
            if total_vol > 100:
                score = 7.0
            elif total_vol > 50:
                score = 6.0
            elif total_vol > 10:
                score = 5.5
            else:
                score = 5.0
            return {'source': 'gdelt', 'score': score, 'buzz': total_vol, 'raw': {'vol': total_vol}}
    except Exception as e:
        print(f"GDELT err {ticker}: {e}")
        return {'source': 'gdelt_failed', 'score': 5.0, 'buzz': 0, 'raw': {'error': str(e)}}
    return None

def get_news_score(ticker, micro="", finnhub_key=None):
    # 1순위 Finnhub
    key = finnhub_key or os.getenv('FINNHUB_API_KEY') or os.getenv('FINNHUB_KEY')
    if key:
        fin = get_finnhub_score(ticker, key)
        if fin and fin.get('source') in ('finnhub','finnhub_ratelimit','finnhub_empty'):
            return fin
        if fin and fin.get('score') is not None:
            return fin
    
    # 2순위 GDELT
    gd = get_gdelt_score(ticker, micro)
    if gd:
        return gd
    
    # Fallback
    return {'source': 'fallback_neutral', 'score': 5.0, 'buzz': 0, 'raw': {}}

if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv)>1 else "SPY"
    print(get_news_score(t))
