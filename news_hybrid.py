"""
news_hybrid.py - Finnhub (1순위) + GDELT (백업) 하이브리드 뉴스 컬렉터

기존 finnhub_sentiment.py 대체용
- Finnhub 성공하면 그대로 사용
- 0개, 에러, Rate Limit이면 GDELT로 자동 폴백
"""

import requests
from datetime import datetime, timedelta

def get_finnhub_score(ticker, api_key):
    """Finnhub 시도 - 기존 로직 그대로"""
    try:
        url = f"https://finnhub.io/api/v1/news-sentiment?symbol={ticker}&token={api_key}"
        r = requests.get(url, timeout=10)
        if r.status_code == 429:
            print(f"[Finnhub] {ticker} Rate Limit -> GDELT 백업으로")
            return None
        data = r.json()
        # Finnhub는 buzz, sentiment, companyNewsScore 줌
        buzz = data.get('buzz', {}).get('articlesInLastWeek', 0)
        sentiment = data.get('sentiment', {}).get('bearishPercent', 0.5)
        score = data.get('companyNewsScore', 0)
        
        if buzz == 0 and score == 0:
            return None  # 데이터 없음 -> 백업으로
        
        # 0~10점으로 정규화 (기존 로직 유지)
        # score가 -1~1 범위면 0~10으로 변환
        normalized = max(0, min(10, (score + 1) * 5)) if score != 0 else 5.0
        return {
            'source': 'finnhub',
            'buzz': buzz,
            'score': normalized,
            'raw': data
        }
    except Exception as e:
        print(f"[Finnhub] {ticker} 에러 {e} -> GDELT 백업으로")
        return None

def get_gdelt_score(ticker, micro_name=""):
    """GDELT 백업 - 무료, 키 없음"""
    try:
        # GDELT DOC 2.0 API - 최근 7일
        query = f"{ticker} OR {micro_name}" if micro_name else ticker
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            'query': query,
            'mode': 'artlist',
            'maxrecords': 20,
            'format': 'json',
            'timespan': '7d'
        }
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        articles = data.get('articles', [])
        
        if not articles:
            return {
                'source': 'gdelt',
                'buzz': 0,
                'score': 5.0,  # 중립
                'raw': data
            }
        
        # GDELT는 tone 정보 있으면 평균, 없으면 기사 수로 점수
        # 간단히: 기사 수로 buzz 계산, 제목에 bullish/bearish 키워드로 점수
        buzz = len(articles)
        
        # 간단 키워드 센티멘트 (VADER 없이도 동작)
        bullish_kw = ['surge', 'rally', 'gain', 'bull', 'up', 'high', 'rise', 'buy']
        bearish_kw = ['drop', 'fall', 'bear', 'down', 'low', 'sell', 'crash', 'slump']
        
        score_sum = 0
        for art in articles:
            title = art.get('title', '').lower()
            b = sum(1 for k in bullish_kw if k in title)
            be = sum(1 for k in bearish_kw if k in title)
            if b > be:
                score_sum += 7  # bullish
            elif be > b:
                score_sum += 3  # bearish
            else:
                score_sum += 5  # neutral
        
        avg_score = score_sum / buzz if buzz else 5.0
        
        return {
            'source': 'gdelt',
            'buzz': buzz,
            'score': max(0, min(10, avg_score)),
            'raw': data
        }
    except Exception as e:
        print(f"[GDELT] {ticker} 에러 {e}")
        return {
            'source': 'gdelt_failed',
            'buzz': 0,
            'score': 5.0,  # 실패시 중립
            'raw': {}
        }

def get_news_score(ticker, micro_name="", finnhub_key=None):
    """
    하이브리드 메인 함수
    scoring_engine.py에서 이 함수만 호출하면 됨
    """
    # 1순위: Finnhub
    if finnhub_key:
        finnhub_result = get_finnhub_score(ticker, finnhub_key)
        if finnhub_result is not None:
            print(f"[{ticker}] Finnhub 성공: {finnhub_result['buzz']}개, 점수 {finnhub_result['score']:.1f}")
            return finnhub_result
    
    # 2순위: GDELT 백업
    gdelt_result = get_gdelt_score(ticker, micro_name)
    print(f"[{ticker}] GDELT 백업: {gdelt_result['buzz']}개, 점수 {gdelt_result['score']:.1f}")
    return gdelt_result

# 테스트
if __name__ == "__main__":
    # 키 없이 테스트 (GDELT만)
    for t in ["USO", "DBA", "QQQ"]:
        result = get_news_score(t, f"Micro {t}", finnhub_key=None)
        print(f"{t}: {result}\n")
    
    # 키 있으면 테스트
    # import os
    # key = os.getenv("FINNHUB_KEY")
    # result = get_news_score("USO", "Micro WTI", key)
