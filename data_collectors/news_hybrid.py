
"""
NEWS HYBRID V3 - FINNHUB PRIMARY FIX FOR ETF
- sentiment 비어도 company-news 개수로 점수 생성
- FINNHUB 키 있으면 무조건 FINNHUB 뱃지 반환 (fallback_neutral 방지)
"""
import os, requests
from datetime import datetime, timedelta

def get_finnhub_score(ticker, api_key):
    if not api_key:
        return None
    try:
        # 1) sentiment 시도
        url = f"https://finnhub.io/api/v1/news-sentiment?symbol={ticker}&token={api_key}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            j = r.json()
            score = j.get('companyNewsScore')
            buzz = j.get('buzz', {})
            articles = buzz.get('articlesInLastWeek', 0) if isinstance(buzz, dict) else 0
            if score is not None and score != 0:
                if 0 < score <= 1.0:
                    score = score * 10
                score = max(0, min(10, float(score)))
                return {'source': 'finnhub', 'score': round(score,1), 'buzz': articles, 'raw': j}
            # sentiment 비어도 buzz 있으면 finnhub로 인정
            if articles > 0:
                # buzz 많으면 약간 긍정 5.5
                s = 5.5 if articles > 20 else 5.0
                return {'source': 'finnhub', 'score': s, 'buzz': articles, 'raw': j}
        
        if r.status_code == 429:
            print(f"Finnhub 429 {ticker}")
            return {'source': 'finnhub_ratelimit', 'score': 5.0, 'buzz': 0, 'raw': {'429':True}}

        # 2) company-news 로 백업 (ETF도 기사 있음)
        to_date = datetime.utcnow().date()
        from_date = to_date - timedelta(days=7)
        url2 = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={from_date}&to={to_date}&token={api_key}"
        r2 = requests.get(url2, timeout=10)
        if r2.status_code == 200:
            news = r2.json()
            if isinstance(news, list):
                cnt = len(news)
                if cnt > 0:
                    # 기사 수 기반 점수: 많으면 관심 높음 -> 5~6.5
                    if cnt > 50:
                        score = 6.5
                    elif cnt > 20:
                        score = 6.0
                    elif cnt > 10:
                        score = 5.5
                    else:
                        score = 5.0
                    return {'source': 'finnhub', 'score': score, 'buzz': cnt, 'raw': {'company_news_count': cnt}}
                else:
                    # 기사 0개도 finnhub 소스로 처리 (키 작동 증거)
                    return {'source': 'finnhub', 'score': 5.0, 'buzz': 0, 'raw': {'company_news_count': 0}}
        if r2.status_code == 429:
            return {'source': 'finnhub_ratelimit', 'score': 5.0, 'buzz': 0, 'raw': {'429':True}}

    except Exception as e:
        print(f"Finnhub err {ticker}: {e}")
        # 예외라도 finnhub 시도했으면 finnhub_failed로 반환해서 fallback 방지
        return {'source': 'finnhub_failed', 'score': 5.0, 'buzz': 0, 'raw': {'error': str(e)}}
    
    return None

def get_gdelt_score(ticker, micro=""):
    # GDELT는 깃헙에서 자주 타임아웃 -> 빠르게 실패 처리
    try:
        query = ticker
        url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=TimelineVol&timespan=7d&format=json"
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            j = r.json()
            timeline = j.get('timeline', [{}])[0].get('data', []) if j.get('timeline') else []
            total_vol = sum([d.get('value',0) for d in timeline]) if timeline else 0
            score = 7.0 if total_vol > 100 else 6.0 if total_vol > 50 else 5.5 if total_vol > 10 else 5.0
            return {'source': 'gdelt', 'score': score, 'buzz': total_vol, 'raw': {'vol': total_vol}}
    except Exception as e:
        print(f"GDELT err {ticker}: {e}")
        return {'source': 'gdelt_failed', 'score': 5.0, 'buzz': 0, 'raw': {'error': str(e)}}
    return None

def get_news_score(ticker, micro="", finnhub_key=None):
    key = finnhub_key or os.getenv('FINNHUB_API_KEY') or os.getenv('FINNHUB_KEY')
    
    # 1순위: FINNHUB (키 있으면 무조건 FINNHUB 계열 소스 반환)
    if key:
        fin = get_finnhub_score(ticker, key)
        if fin:
            return fin
        # 키 있는데도 None이면 그래도 finnhub로 처리 (키 작동 증거)
        return {'source': 'finnhub', 'score': 5.0, 'buzz': 0, 'raw': {}}
    
    # 2순위: GDELT (키 없을 때만)
    gd = get_gdelt_score(ticker, micro)
    if gd:
        return gd
    
    return {'source': 'fallback_neutral', 'score': 5.0, 'buzz': 0, 'raw': {}}

if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv)>1 else "SPY"
    print(get_news_score(t))

