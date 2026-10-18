"""
V4.1 FIXED - absorption.json 호환
- selected 없으면 tickers에서 score 높은 3개 자동 선택
- 주말에도 journal_data.json 강제 생성
"""
import json, os
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
    with open(path,'r',encoding='utf-8') as f:
        return json.load(f)

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
    print(f"=== V4.1 FIXED DAILY PNL {datetime.now(timezone.utc)} ===")
    abs_path = "docs/absorption.json"
    if not os.path.exists(abs_path):
        abs_path = "absorption.json"
    absorption = load_json(abs_path)
    if not absorption:
        print(f"No file at {abs_path}")
        # create dummy for test
        absorption = {"date": datetime.utcnow().strftime("%Y-%m-%d"), "macro": {"dxy":101.84, "bias":"NEUTRAL"}, "tickers":[]}

    # get selected - compatible with both formats
    selected = absorption.get('selected')
    if not selected:
        # fallback: top 3 by score from tickers
        tickers = absorption.get('tickers', [])
        if tickers:
            sorted_t = sorted(tickers, key=lambda x: x.get('score',0), reverse=True)
            # take 3: 2 bottom + 1 top logic simplified: just top 3 for now
            selected = []
            for t in sorted_t[:3]:
                status = t.get('status','NEUTRAL')
                side = "LONG" if status == "BOTTOM" else "SHORT" if status == "TOP" else "LONG"
                # if score low for short, keep as short
                if t['ticker'] == 'XLE':
                    side = "SHORT"
                selected.append({
                    "ticker": t['ticker'],
                    "micro": MICRO_MAP.get(t['ticker'], t['ticker']),
                    "side": side,
                    "score": t.get('score',0),
                    "close": None,  # will fetch
                    "sl_pct": 0.8,
                    "tp_pct": 1.6
                })
        else:
            # hardcoded fallback from screenshot
            selected = [
                {"ticker":"CPER","micro":MICRO_MAP["CPER"],"side":"LONG","score":6.7,"close":39.5,"sl_pct":0.8,"tp_pct":1.6},
                {"ticker":"SPY","micro":MICRO_MAP["SPY"],"side":"LONG","score":6.6,"close":763.25,"sl_pct":0.8,"tp_pct":1.6},
                {"ticker":"XLE","micro":MICRO_MAP["XLE"],"side":"SHORT","score":2.8,"close":68.24,"sl_pct":0.8,"tp_pct":1.6},
            ]

    print(f"Selected tickers: {[s['ticker'] for s in selected]}")

    journal_path = "docs/journal_data.json"
    journal = load_json(journal_path)
    if not journal:
        journal = {"weeks": {}}

    week_key = absorption.get('date') or absorption.get('generated_at','')[:10] or datetime.utcnow().strftime("%Y-%m-%d")
    week_key = week_key[:10]

    if week_key not in journal["weeks"]:
        journal["weeks"][week_key] = {
            "date": week_key,
            "bias": absorption.get('bias') or absorption.get('macro',{}).get('bias',''),
            "dxy": absorption.get('macro',{}).get('dxy',''),
            "trades": []
        }
        for sel in selected:
            ticker = sel.get('ticker')
            # get entry price
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
            shares = int(risk_krw / (per_share * fx)) if per_share else 0
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
                "pnl_usd": 0
            })
        print(f"New week {week_key} created with {len(journal['weeks'][week_key]['trades'])} trades")

    today = datetime.now(timezone.utc)
    weekday = today.weekday()

    for trade in journal["weeks"][week_key]["trades"]:
        if trade["status"] != "OPEN":
            continue
        ticker = trade["ticker"]
        price = get_price(ticker)
        if not price:
            print(f"No price for {ticker}, keep entry")
            continue

        entry = trade["entry"]
        sl = trade["sl"]
        tp = trade["tp"]
        side = trade["side"]
        high = price["high"]
        low = price["low"]
        close = price["close"]

        trade["current"] = close
        trade["last_check"] = price["date"]

        exited = False
        if side == "LONG":
            if low <= sl:
                trade["exit"] = sl
                trade["exit_reason"] = "SL"
                exited = True
            elif high >= tp:
                trade["exit"] = tp
                trade["exit_reason"] = "TP"
                exited = True
        else:
            if high >= sl:
                trade["exit"] = sl
                trade["exit_reason"] = "SL"
                exited = True
            elif low <= tp:
                trade["exit"] = tp
                trade["exit_reason"] = "TP"
                exited = True

        if not exited and weekday == 4:
            trade["exit"] = close
            trade["exit_reason"] = "TIME_FRIDAY"
            exited = True

        if exited:
            trade["status"] = "CLOSED"
            trade["exit_date"] = price["date"]
            dir_mult = 1 if side=="LONG" else -1
            pnl_usd = (trade["exit"] - entry) * trade["shares"] * dir_mult
            fx = 1350
            pnl_krw = pnl_usd * fx
            trade["pnl_usd"] = round(pnl_usd,2)
            trade["pnl_krw"] = round(pnl_krw,0)
            print(f"{ticker} {side} CLOSED {trade['exit_reason']} exit {trade['exit']} PnL {pnl_krw}")
        else:
            dir_mult = 1 if side=="LONG" else -1
            pnl_usd = (close - entry) * trade["shares"] * dir_mult
            trade["pnl_usd"] = round(pnl_usd,2)
            trade["pnl_krw"] = round(pnl_usd * 1350,0)
            print(f"{ticker} OPEN current {close} unreal {trade['pnl_krw']}")

    os.makedirs("docs", exist_ok=True)
    with open(journal_path, "w", encoding="utf-8") as f:
        json.dump(journal, f, ensure_ascii=False, indent=2)
    print(f"Saved {journal_path}")

    total_closed = sum(1 for t in journal["weeks"][week_key]["trades"] if t["status"]=="CLOSED")
    total_pnl = sum(t.get("pnl_krw",0) for t in journal["weeks"][week_key]["trades"])
    print(f"WEEK {week_key} {total_closed}/{len(journal['weeks'][week_key]['trades'])} closed, total {total_pnl} KRW")

if __name__ == "__main__":
    main()
