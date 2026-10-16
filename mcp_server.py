
"""
MCP Server - "SLV 왜 9.5점이야?" 4레이어 분해
Usage: python mcp_server.py SLV
"""
import json, sys, os

def explain_ticker(ticker, json_path="absorption.json"):
    ticker=ticker.upper()
    try:
        with open(json_path) as f:
            data=json.load(f)
        found = next((t for t in data['tickers'] if t['ticker']==ticker), None)
        if not found:
            print(f"{ticker} not found in {json_path}")
            return
        print(f"""
=== {ticker} 4레이어 분해 ===
점수: {found['score']} / 상태: {found['status']} / 심리: {found['sentiment']}

1. BOX (40%) - 박스 구간: {found['box_range']}% | 점수 {found['breakdown']['box_score']}
   - 거래량 배수: {found['vol_mult']}x | 체류일: {found['dwell']}D
   - 의미: 박스가 좁을수록 매집 가능성 높음. 3% 이하면 타이트

2. COT (20%) - 투기 포지션: {found['cot_pct']}% Long | 점수 {found['breakdown']['cot_score']}
   - 의미: 70% 이상이면 헤지펀드도 바닥 보고 있음

3. FLOW (20%) - 자금 흐름: {found['flow_m']}M | 점수 {found['breakdown']['flow_score']}
   - 의미: +면 기관 매수, -면 매도

4. NEWS (20%) - 뉴스 심리: {found['news_sentiment']} | 점수 {found['breakdown']['news_score']} (기사 {found.get('news_count',0)}개)
   - 의미: 화이트리스트 23개 언론사 + 중복 제거 + 금융 감성 필터

Macro Bias: {data['macro']['bias']} | DXY {data['macro']['dxy']} US10Y {data['macro']['us10y']}%
생성 시각: {data['generated_at']}

공식: Strength = 40% Box + 20% COT + 20% Flow + 20% News
        """
    except FileNotFoundError:
        print(f"{json_path} 없음. 먼저 python scoring_engine.py 실행")

if __name__=="__main__":
    t = sys.argv[1] if len(sys.argv)>1 else "SLV"
    explain_ticker(t)
