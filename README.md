
# weekly-absorption - 하이브리드 자동+수동

## 구조
- 자동: GitHub Actions 일요일 21:00 KST (cron 0 12 * * 0 UTC) -> absorption.json -> docs/index.html + Discord
- 수동: mcp_server.py -> "SLV 왜 9.5점이야?" 4레이어 분해

## 오늘 해야할 3개 (30분 컷)
1. FRED 키 발급: https://fred.stlouisfed.org -> My Account -> API Keys -> 발급 -> GitHub Secrets에 FRED_API_KEY 등록
2. Finnhub 키 발급: https://finnhub.io/register -> Free -> GitHub Secrets에 FINNHUB_KEY 등록
3. (선택) Discord Webhook: 디스코드 채널 설정 -> 연동 -> 웹후크 생성 -> URL 복사 -> GitHub Secrets DISCORD_WEBHOOK_URL 등록

## 로컬 테스트
pip install requests
export FRED_API_KEY=xxx
export FINNHUB_KEY=xxx
python scoring_engine.py
python mcp_server.py SLV

## GitHub에 올리기
git init
git add .
git commit -m "init"
git remote add origin <your repo>
git push -u origin main

그 다음 GitHub repo Settings -> Pages -> Source: main / docs 폴더 -> 저장
Settings -> Secrets and variables -> Actions -> New secret 3개 등록

## 비용
$0/mo, Actions 2000분 무료, Pages 무료, No Server
