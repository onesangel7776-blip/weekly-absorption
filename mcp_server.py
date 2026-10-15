
"""
MCP 뼈대 - 수동 모드: "SLV 왜 9.5점이야?" 같은 질문에 COT/ETF/뉴스 까서 설명

실행: python mcp_server.py
나중에 Claude/Meta AI MCP로 연결하면 tool로 노출 가능
"""

from data_collectors.fred import fetch_all as fred_all
from data_collectors.cftc import fetch_cot
from data_collectors.finnhub_sentiment import fetch_news_sentiment
from data_collectors.price import fetch_box
import json

def explain_ticker(ticker="SLV"):
    fred = fred_all()
    box = fetch_box(ticker)
    cot = fetch_cot()
    news = fetch_news_sentiment(ticker)

    explanation = f"""
=== {ticker} 왜 9.5점이야? (4레이어 분해) ===

[LAYER 1] FRED 환경:
- DXY: {fred.get('DXY_proxy')}
- US10Y: {fred.get('US10Y')}
- VIX: {fred.get('VIX')}
-> DXY가 102~103이면 위험자산 중립, 101 이하면 RISK_ON

[LAYER 2] COT 포지셔닝:
- {cot.get('source')} 에서 {ticker} 관련 라인 {len(cot.get('samples',[]))}개 감지
- 천장/바닥은 COT가 극단에 있을 때 (상업적 헤저 vs 투기세력 역전)

[LAYER 3] PRICE BOX:
- 22일 박스: {box.get('box_low')} ~ {box.get('box_high')} ({box.get('box_range_pct')}%)
- 거래량 비율: {box.get('vol_ratio')}x (3x 이상이면 흡수)
- 체류일: 22일 박스 안에 몇 일 있었는지 -> 98퍼타일은 22일 중 21일 이상

[LAYER 4] NEWS SENTIMENT:
- 최근 뉴스 {news.get('count')}개, 점수 {news.get('sentiment_score')}
- 샘플: {news.get('samples')}

=> 종합: 박스 3% 이내 + 거래량 급증 + COT 극단 + DXY 약세 겹치면 9.5점
"""
    return explanation

if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv)>1 else "SLV"
    print(explain_ticker(ticker))
