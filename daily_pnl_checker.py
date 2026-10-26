"""
V4.3 ORIGINAL INTENT RESTORED
- 21개 티커 -> 점수 높은 3개 뽑아서 월요일 아침 OPEN
- fallback 삭제 (absorption.json 없으면 에러로 멈춤)
- 경로는 docs/absorption.json 하나만 사용
- week_key = absorption date 기준 월요일 주차 (ISO week) -> 월요일이면 무조건 새 주차 생성
- 기존 주차 CLOSED는 절대 삭제 안 함
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

def load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path,'r',encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"load_json {path} fail {e}")
        return None

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
    print(f"=== V4.3 ORIGINAL INTENT {datetime.now(timezone.utc)} ===")
    
    # 1. absorption load - 오직 docs/absorption.json 하나만, 없으면 에러
    abs_path = "docs/absorption.json"
    absorption = load_json(abs_path)
    if not absorption:
        print(f"ERROR: {abs_path} 없음. 21개 스캐너가 먼저 돌아야 함. fallback 안 씀.")
        sys.exit(1)

    # 21개 중에 3개 뽑기 - selected가 있으면 그걸 쓰고, 없으면 점수순으로
    selected = absorption.get('selected')
    if not selected:
        tickers = absorption.get('tickers', [])
        if not tickers or len(tickers) < 3:
            print(f"ERROR: tickers가 21개가 아님. 현재 {len(tickers)}개")
            sys.exit(1)
        # 점수 높은 3개 = 원래 의도
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
    
    print(f"Selected 3 from 21: {[s['ticker'] for s in selected]} from {abs_path}")

    # 2. journal load
    journal_path = "docs/journal_data.json"
    journal = load_json(journal_path) or {"weeks": {}}
    if "weeks" not in journal:
        journal["weeks"] = {}

    # week_key = 다음 월요일 날짜 (일요일 스캔 -> 월요일 포지션 = 원래 의도)
    # absorption date가 일요일이면 +1일 해서 월요일로
    abs_date_str = (absorption.get('date') or absorption.get('generated_at','')[:10])
    try:
        abs_date = datetime.strptime(abs_date_str[:10], "%Y-%m-%d")
        # 일요일이면 월요일로, 그 외도 월요일 기준으로
        if abs_date.weekday() == 6: # Sunday
            week_key_date = abs_date + timedelta(days=1)
        else:
            # 이번 주 월요일로 정규화
            week_key_date = abs_date - timedelta(days=abs_date.weekday())
        week_key = week_key_date.strftime("%Y-%m-%d")
    except:
        week_key = abs_date_str[:10]

    print(f"week_key = {week_key} (absorption {abs_date_str} -> Monday)")

    # 3. 새 주차 생성 - 월요일이면 무조건 새로, 같은 주라도 OPEN이 0개면 새로
    should_create_new = False
    if week_key not in journal["weeks"]:
        should_create_new = True
    else:
        # 기존 주차에 OPEN이 하나도 없으면 새로 만들어야 함 (지난 주 다 CLOSED)
        open_cnt = sum(1 for t in journal["weeks"][week_key]["trades"] if t["status"] == "OPEN")
        if open_cnt == 0:
            # 날짜를 하루 더 밀어서 새 키로 (중복 방지)
            # 실제로는 다음 주 월요일로 가야 하지만, 여기서는 강제 재생성
            print(f"Week {week_key} exists but OPEN=0 -> will recreate")
            should_create_new = True
            # 기존 CLOSED는 유지, trades 비우고 다시 채울지? 여기서는 새로 덮지 않고, 기존 유지 + 새 주차로
            # 간단히 week_key를 오늘 날짜로 변경해서 새 주차 생성
            if datetime.now(timezone.utc).weekday() == 0: # Monday
                week_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                should_create_new = True

    if should_create_new and week_key not in journal["weeks"]:
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
        print(f"NEW WEEK {week_key} created with {[t['ticker'] for t in journal['weeks'][week_key]['trades']]}")
    else:
        print(f"Week {week_key} already exists with OPEN, keeping it")

    # 4. P&L update - OPEN만 갱신
    today = datetime.now(timezone.utc)
    weekday = today.weekday()
    for wk, wdata in journal["weeks"].items():
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

    # 5. 저장
    os.makedirs("docs", exist_ok=True)
    for out_path in ["docs/journal_data.json", "journal_data.json"]:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(journal, f, ensure_ascii=False, indent=2)

    total_closed = sum(1 for w in journal["weeks"].values() for t in w["trades"] if t["status"]=="CLOSED")
    total_open = sum(1 for w in journal["weeks"].values() for t in w["trades"] if t["status"]=="OPEN")
    print(f"TOTAL {len(journal['weeks'])} weeks, CLOSED {total_closed}, OPEN {total_open} - V4.3 DONE")

if __name__ == "__main__":
    main()
