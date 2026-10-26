"""
V4.4 STABLE - 3주째 주말 버그 완전 제거
- OPEN=0 재 생성 로직 삭제 (중복 주차 원인)
- JSON 깨지면 초기화하지 않고 즉시 실패 (이전 주차 증발 방지)
- week_key는 무조건 월요일 기준으로만 생성
  - absorption이 토/일이면 -> 다음 월요일
  - absorption이 평일이면 -> 그 주의 월요일
- 이미 존재하는 주차는 절대 다시 생성하지 않음
"""
import json, os, sys
from datetime import datetime, timezone, timedelta

try:
    import yfinance as yf
    HAS_YF = True
except:
    HAS_YF = False

MICRO_MAP = {
    "CPER": "MHG (Micro Copper)",
    "SPY": "MES (Micro S&P)",
    "XLE": "MCL proxy",
    "SLV": "SILV Micro",
    "GLD": "MGC Micro Gold",
    "UNG": "MNG Micro NatGas",
    "COPX": "MHG proxy",
    "USO": "MCL Micro Crude",
    "GDX": "MGC proxy",
    "XLB": "MHG proxy",
    "DBA": "Micro Grain",
    "EEM": "MES proxy",
    "UUP": "M6E Micro Euro",
    "TLT": "10Y Micro",
    "XLF": "MES proxy",
    "IWM": "M2K Micro Russell",
    "SMH": "MES proxy",
    "QQQ": "MNQ Micro Nasdaq",
    "XLK": "MNQ proxy",
    "IBIT": "MBT Micro Bitcoin",
    "BITO": "MBT proxy",
}

def load_json_strict(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path,'r',encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"CRITICAL: {path} JSON 파싱 실패 - 절대 초기화하지 않고 종료함. 에러: {e}")
        print("GitHub에서 파일 끝 }} 가 잘렸는지 확인하세요. 복구 파일로 덮어쓰세요.")
        sys.exit(1)

def get_price(ticker):
    if not HAS_YF:
        return {"close": 100.0, "high": 100.8, "low": 99.2, "date": datetime.utcnow().strftime("%Y-%m-%d")}
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d", auto_adjust=True)
        if hist.empty:
            return None
        last = hist.iloc[-1]
        return {
            "close": float(last['Close']),
            "high": float(last['High']),
            "low": float(last['Low']),
            "date": last.name.strftime("%Y-%m-%d") if hasattr(last.name, 'strftime') else str(hist.index[-1].date())
        }
    except Exception as e:
        print(f"yfinance {ticker} fail {e}")
        return None

def main():
    print(f"=== V4.4 STABLE {datetime.now(timezone.utc)} ===")
    
    # 1. absorption load - 하나만
    abs_path = "docs/absorption.json"
    absorption = load_json_strict(abs_path)
    if not absorption:
        print(f"ERROR: {abs_path} 없음. 21개 스캐너 먼저 실행 필요.")
        sys.exit(1)

    selected = absorption.get('selected')
    if not selected:
        tickers = absorption.get('tickers', [])
        if not tickers or len(tickers) < 3:
            print(f"ERROR: tickers가 21개 미만. 현재 {len(tickers)}개")
            sys.exit(1)
        sorted_t = sorted(tickers, key=lambda x: x.get('score',0), reverse=True)
        selected = []
        for t in sorted_t[:3]:
            status = t.get('status','NEUTRAL')
            side = "LONG" if status == "BOTTOM" else "SHORT" if status == "TOP" else "LONG"
            selected.append({
                "ticker": t['ticker'],
                "micro": MICRO_MAP.get(t['ticker'], t['ticker']),
                "side": side,
                "score": t.get('score',0),
                "close": t.get('close'),
                "sl_pct": 0.8,
                "tp_pct": 1.6
            })
    
    print(f"Selected 3: {[s['ticker'] for s in selected]}")

    # 2. journal load - 절대 빈 dict로 초기화하지 않음, 실패하면 종료
    journal_path = "docs/journal_data.json"
    journal = load_json_strict(journal_path)
    if journal is None:
        # 파일이 아예 없으면 새로 시작 (최초 1회만)
        journal = {"weeks": {}}
        print("journal_data.json 없음 -> 새로 생성")
    if "weeks" not in journal:
        journal["weeks"] = {}

    # 3. week_key = 월요일 기준, 토/일은 다음 월요일로
    abs_date_str = (absorption.get('date') or absorption.get('generated_at','')[:10])
    try:
        abs_date = datetime.strptime(abs_date_str[:10], "%Y-%m-%d")
        wd = abs_date.weekday()
        if wd == 5: # Saturday
            week_key_date = abs_date + timedelta(days=2)
        elif wd == 6: # Sunday
            week_key_date = abs_date + timedelta(days=1)
        else: # Mon-Fri -> 그 주의 월요일
            week_key_date = abs_date - timedelta(days=wd)
        week_key = week_key_date.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"week_key 파싱 실패 {e}, absorption date 그대로 사용")
        week_key = abs_date_str[:10]

    print(f"week_key = {week_key} (absorption {abs_date_str} -> Monday)")

    # 4. 새 주차 생성 - week_key가 없을 때만, OPEN=0 로직 완전 삭제
    if week_key not in journal["weeks"]:
        print(f"NEW WEEK 생성: {week_key}")
        journal["weeks"][week_key] = {
            "date": week_key,
            "bias": absorption.get('bias') or absorption.get('macro',{}).get('bias',''),
            "dxy": absorption.get('macro',{}).get('dxy',''),
            "trades": []
        }
        for sel in selected:
            ticker = sel.get('ticker')
            entry = sel.get('close') or sel.get('entry')
            if not entry:
                price = get_price(ticker)
                entry = price['close'] if price else 100.0
            else:
                entry = float(entry)
            sl_pct = sel.get('sl_pct',0.8)/100
            tp_pct = sel.get('tp_pct',1.6)/100
            side = sel.get('side','LONG')
            if side == "LONG":
                sl = round(entry * (1 - sl_pct),2)
                tp = round(entry * (1 + tp_pct),2)
            else:
                sl = round(entry * (1 + sl_pct),2)
                tp = round(entry * (1 - tp_pct),2)
            capital = 10000000
            fx = 1350
            risk_krw = capital * 0.01
            per_share = abs(entry - sl) if entry and sl else 1
            shares = int(risk_krw / (per_share * fx)) if per_share else 1
            if shares == 0:
                shares = 1
            journal["weeks"][week_key]["trades"].append({
                "ticker": ticker,
                "micro": sel.get('micro', MICRO_MAP.get(ticker,'')),
                "side": side,
                "score": sel.get('score'),
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "sl_pct": sel.get('sl_pct',0.8),
                "tp_pct": sel.get('tp_pct',1.6),
                "shares": shares,
                "status": "OPEN",
                "current": entry,
                "exit": None,
                "exit_date": None,
                "exit_reason": None,
                "pnl_krw": 0,
                "pnl_usd": 0,
                "last_check": None
            })
    else:
        print(f"Week {week_key} 이미 존재 -> 새로 만들지 않음, P&L만 갱신")

    # 5. P&L update - OPEN만 갱신
    today = datetime.now(timezone.utc)
    weekday = today.weekday()
    for wk, wdata in list(journal["weeks"].items()):
        for trade in wdata["trades"]:
            if trade["status"] != "OPEN":
                continue
            price = get_price(trade["ticker"])
            if not price:
                continue
            entry = trade["entry"]; sl = trade["sl"]; tp = trade["tp"]; side = trade["side"]
            high = price["high"]; low = price["low"]; close = price["close"]
            trade["current"] = close
            trade["last_check"] = price["date"]
            exited = False
            if side == "LONG":
                if low <= sl:
                    trade["exit"] = sl; trade["exit_reason"] = "SL"; exited = True
                elif high >= tp:
                    trade["exit"] = tp; trade["exit_reason"] = "TP"; exited = True
            else:
                if high >= sl:
                    trade["exit"] = sl; trade["exit_reason"] = "SL"; exited = True
                elif low <= tp:
                    trade["exit"] = tp; trade["exit_reason"] = "TP"; exited = True
            # 금요일 청산은 해당 주차(week_key)일 때만
            if not exited and wk == week_key and weekday == 4:
                trade["exit"] = close
                trade["exit_reason"] = "TIME_FRIDAY"
                exited = True
            if exited:
                trade["status"] = "CLOSED"
                trade["exit_date"] = price["date"]
                dir_mult = 1 if side=="LONG" else -1
                pnl_usd = (trade["exit"] - entry) * trade["shares"] * dir_mult
                trade["pnl_usd"] = round(pnl_usd,2)
                trade["pnl_krw"] = round(pnl_usd * 1350,0)

    # 6. 저장 - 백업도 함께
    os.makedirs("docs", exist_ok=True)
    # 저장 전 검증
    if len(journal["weeks"]) == 0:
        print("CRITICAL: weeks가 0개 -> 저장하지 않고 종료 (데이터 증발 방지)")
        sys.exit(1)
    
    # 백업
    try:
        with open("docs/journal_data_backup.json", "w", encoding="utf-8") as f:
            json.dump(journal, f, ensure_ascii=False, indent=2)
    except:
        pass

    for out_path in ["docs/journal_data.json", "journal_data.json"]:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(journal, f, ensure_ascii=False, indent=2)

    total_closed = sum(1 for w in journal["weeks"].values() for t in w["trades"] if t["status"]=="CLOSED")
    total_open = sum(1 for w in journal["weeks"].values() for t in w["trades"] if t["status"]=="OPEN")
    print(f"TOTAL {len(journal['weeks'])} weeks, CLOSED {total_closed}, OPEN {total_open} - V4.4 DONE")

if __name__ == "__main__":
    main()
