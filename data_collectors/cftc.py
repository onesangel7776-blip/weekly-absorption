
import requests, io, csv

# CFTC Legacy Futures Only - 매주 금요일 발표, 실제 데이터는 화요일 기준
# 공식: https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm
# 여기선 가장 가벼운 최신 파일 하나만 긁는다. 실패하면 STALE 처리

COT_URL = "https://www.cftc.gov/dea/newcot/FinFutWk.txt"  # Financial Futures (Gold/Silver 포함)

def fetch_cot():
    try:
        r = requests.get(COT_URL, timeout=15)
        r.raise_for_status()
        # FinFutWk는 고정폭 텍스트라 간단 파싱만, 여기선 길이로 정상 여부만 체크
        lines = r.text.splitlines()
        # Gold, Silver, Copper, Bitcoin 관련 줄만 필터
        keywords = ["GOLD", "SILVER", "COPPER", "BITCOIN"]
        filtered = [l for l in lines if any(k in l for k in keywords)][:20]
        return {"raw_lines": len(lines), "samples": filtered, "source": COT_URL}
    except Exception as e:
        return {"error": str(e), "source": COT_URL}

if __name__ == "__main__":
    print(fetch_cot())
