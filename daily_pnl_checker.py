"""
V4.2 SAFE MERGE - 절대 데이터 안 날아가는 버전
- 구버전 flat trades 포맷 자동 마이그레이션
- 기존 주차 CLOSED는 절대 삭제 안 함
- docs/ + 루트 둘 다 저장 (2개 파일 동기화)
- 이번 주 이미 있으면 진입가 유지, 현재가만 갱신
"""
import json, os, shutil
from datetime import datetime, timezone

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
    except:
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

def migrate_old_format(j):
    """flat {"trades": [... with week field]} -> {"weeks": {week: {trades: []}}}"""
    if not j:
        return {"weeks": {}}
    if "weeks" in j:
        return j
    if "trades" in j and isinstance(j["trades"], list):
        weeks = {}
        for tr in j["trades"]:
            wk = tr.get("week") or tr.get("weekDate") or tr.get("date") or "2026-10-18"
            # normalize
            if wk not in weeks:
                weeks[wk] = {"date": wk, "bias": "", "dxy": "", "trades": []}
            # remove week field to avoid duplication, keep core
            nt = {k: v for k, v in tr.items() if k not in ["week"]}
            # ensure required fields
            if "status" not in nt: nt["status"] = "OPEN"
            weeks[wk]["trades"].append(nt)
        print(f"Migrated old flat {len(j['trades'])} trades -> {len(weeks)} weeks")
        return {"weeks": weeks}
    return {"weeks": {}}

def main():
    print(f"=== V4.2 SAFE MERGE DAILY PNL {datetime.now(timezone.utc)} ===")
    # 1. absorption load - try all paths
    abs_candidates = ["docs/absorption.json", "absorption.json", "docs/docs/absorption.json"]
    absorption = None
    abs_path_used = None
    for p in abs_candidates:
        absorption = load_json(p)
        if absorption:
            abs_path_used = p
            break
    if not absorption:
        print("No absorption.json - using fallback 3")
        absorption = {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "macro": {"dxy": 101.84, "bias": "NEUTRAL"},
            "tickers": [],
            "selected": [
                {"ticker":"CPER","micro":MICRO_MAP["CPER"],"side":"LONG","score":6.7,"close":39.5,"sl_pct":0.8,"tp_pct":1.6},
                {"ticker":"SPY","micro":MICRO_MAP["SPY"],"side":"LONG","score":6.6,"close":763.25,"sl_pct":0.8,"tp_pct":1.6},
                {"ticker":"XLE","micro":MICRO_MAP["XLE"],"side":"SHORT","score":2.8,"close":68.24,"sl_pct":0.8,"tp_pct":1.6},
            ]
        }

    selected = absorption.get('selected')
    if not selected:
        tickers = absorption.get('tickers', [])
        if tickers:
            sorted_t = sorted(tickers, key=lambda x: x.get('score',0), reverse=True)
            selected = []
            for t in sorted_t[:3]:
                status = t.get('status','NEUTRAL')
                side = "LONG" if status == "BOTTOM" else "SHORT" if status == "TOP" else "LONG"
                if t['ticker'] == 'XLE':
                    side = "SHORT"
                selected.append({
                    "ticker": t['ticker'],
                    "micro": MICRO_MAP.get(t['ticker'], t['ticker']),
                    "side": side,
                    "score": t.get('score',0),
                    "close": t.get('close'),
                    "sl_pct": 0.8,
                    "tp_pct": 1.6
                })
        else:
            selected = absorption.get('selected', [])

    print(f"Selected: {[s['ticker'] for s in selected]} from {abs_path_used}")

    # 2. journal load - try docs first, then root, then migrate
    journal = None
    for p in ["docs/journal_data.json", "journal_data.json"]:
        j = load_json(p)
        if j:
            journal = j
            print(f"Loaded journal from {p} - keys {list(j.keys())}")
            break
    journal = migrate_old_format(journal)
    if "weeks" not in journal:
        journal["weeks"] = {}

    week_key = (absorption.get('date') or absorption.get('generated_at','')[:10] or datetime.utcnow().strftime("%Y-%m-%d"))[:10]

    # 3. create week if not exists - 절대 기존 주차 삭제 안 함
    if week_key not in journal["weeks"]:
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
            risk_pct = 1.0
            risk_krw = capital * risk_pct/100
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
        print(f"NEW WEEK {week_key} created with {len(journal['weeks'][week_key]['trades'])} trades")
    else:
        # 이미 있는 주는 진입가 유지, 없는 티커만 추가
        existing_tickers = {t['ticker'] for t in journal["weeks"][week_key]["trades"]}
        for sel in selected:
            if sel['ticker'] not in existing_tickers:
                print(f"Adding missing ticker {sel['ticker']} to existing week {week_key}")
                ticker = sel['ticker']
                entry = sel.get('close') or 100.0
                entry = float(entry)
                sl_pct = 0.8/100; tp_pct = 1.6/100
                side = sel.get('side','LONG')
                sl = round(entry*(1-sl_pct),2) if side=="LONG" else round(entry*(1+sl_pct),2)
                tp = round(entry*(1+tp_pct),2) if side=="LONG" else round(entry*(1-tp_pct),2)
                journal["weeks"][week_key]["trades"].append({
                    "ticker": ticker,
                    "micro": sel.get('micro',''),
                    "side": side,
                    "score": sel.get('score'),
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "sl_pct": 0.8,
                    "tp_pct": 1.6,
                    "shares": 1,
                    "status": "OPEN",
                    "current": entry,
                    "pnl_krw": 0,
                    "pnl_usd": 0
                })
        print(f"Week {week_key} already exists - keeping {len(journal['weeks'][week_key]['trades'])} trades (no overwrite)")

    # 4. P&L update - 모든 주차 OPEN만 갱신, CLOSED는 절대 손대지 않음
    today = datetime.now(timezone.utc)
    weekday = today.weekday()
    for wk, wdata in journal["weeks"].items():
        for trade in wdata["trades"]:
            if trade["status"] != "OPEN":
                continue
            # 이번 주만 실시간 갱신하고 과거 주는 이미 CLOSED거나 유지? -> 과거 OPEN도 갱신 (금요일 청산 대비)
            ticker = trade["ticker"]
            price = get_price(ticker)
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
            # 금요일 시간 청산은 이번 주에만 적용
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
                print(f"{wk} {ticker} CLOSED {trade['exit_reason']} PnL {trade['pnl_krw']}")
            else:
                dir_mult = 1 if side=="LONG" else -1
                pnl_usd = (close - entry) * trade["shares"] * dir_mult
                trade["pnl_usd"] = round(pnl_usd,2)
                trade["pnl_krw"] = round(pnl_usd * 1350,0)

    # 5. 저장 - docs + 루트 둘 다 (동기화)
    os.makedirs("docs", exist_ok=True)
    for out_path in ["docs/journal_data.json", "journal_data.json"]:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(journal, f, ensure_ascii=False, indent=2)
        print(f"Saved {out_path} with {len(journal['weeks'])} weeks")

    total_closed = sum(1 for w in journal["weeks"].values() for t in w["trades"] if t["status"]=="CLOSED")
    total_open = sum(1 for w in journal["weeks"].values() for t in w["trades"] if t["status"]=="OPEN")
    print(f"TOTAL {len(journal['weeks'])} weeks, CLOSED {total_closed}, OPEN {total_open} - SAFE MERGE DONE")

if __name__ == "__main__":
    main()
