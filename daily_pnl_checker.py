"""
V4 DAILY PNL CHECKER - 완전 자동 청산
- 매일 21:00 UTC (미장 마감) 실행
- absorption.json SELECTED 3개 읽어서
- yfinance로 실시간 고/저/종가 가져와서 SL/TP 체크
- SL 터지면 SL가에 자동 손절, TP 터지면 TP가에 자동 익절
- 금요일까지 안 터지면 금요일 종가에 시간 청산
- docs/journal_data.json 업데이트 -> journal.html이 자동 표시
"""
import json, os
from datetime import datetime, timezone
import requests

try:
    import yfinance as yf
    HAS_YF = True
except:
    HAS_YF = False

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path,'r',encoding='utf-8') as f:
        return json.load(f)

def get_price(ticker):
    if not HAS_YF:
        return None
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
    print(f"=== V4 DAILY PNL {datetime.now(timezone.utc)} ===")
    abs_path = "docs/absorption.json"
    if not os.path.exists(abs_path):
        abs_path = "absorption.json"
    absorption = load_json(abs_path)
    if not absorption or 'selected' not in absorption:
        print("No absorption.json selected")
        return

    journal_path = "docs/journal_data.json"
    journal = load_json(journal_path)
    if not journal:
        journal = {"weeks": {}}

    week_key = absorption.get('date') or absorption.get('generated_at','')[:10] or datetime.utcnow().strftime("%Y-%m-%d")
    # use monday date? keep as is
    week_key = week_key[:10]

    if week_key not in journal["weeks"]:
        journal["weeks"][week_key] = {
            "date": week_key,
            "bias": absorption.get('bias') or absorption.get('macro',{}).get('bias',''),
            "dxy": absorption.get('macro',{}).get('dxy',''),
            "trades": []
        }
        for sel in absorption.get('selected',[]):
            entry = sel.get('close') or sel.get('entry') or 0
            sl = sel.get('sl') or 0
            tp = sel.get('tp') or 0
            capital = 10000000
            fx = 1350
            risk_pct = 1.0
            risk_krw = capital * risk_pct/100
            per_share = abs(entry - sl) if entry and sl else 1
            shares = int(risk_krw / (per_share * fx)) if per_share else 0
            journal["weeks"][week_key]["trades"].append({
                "ticker": sel.get('ticker'),
                "micro": sel.get('micro',''),
                "side": sel.get('side','LONG'),
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

    # today weekday: 0 Mon ... 4 Fri, 5 Sat, 6 Sun
    today = datetime.now(timezone.utc)
    weekday = today.weekday()
    is_friday_close = weekday == 4  # Friday UTC = Friday US close same day
    # If Saturday/Sunday, treat as Friday close logic for final
    is_weekend = weekday >=5

    for trade in journal["weeks"][week_key]["trades"]:
        if trade["status"] != "OPEN":
            continue
        ticker = trade["ticker"]
        price = get_price(ticker)
        if not price:
            print(f"No price for {ticker}")
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
        else:  # SHORT
            if high >= sl:
                trade["exit"] = sl
                trade["exit_reason"] = "SL"
                exited = True
            elif low <= tp:
                trade["exit"] = tp
                trade["exit_reason"] = "TP"
                exited = True

        if not exited and (is_friday_close or is_weekend):
            # 시간 청산
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
            print(f"{ticker} {side} CLOSED {trade['exit_reason']} exit {trade['exit']} PnL {pnl_krw} KRW / {pnl_usd} USD")
        else:
            # open PnL
            dir_mult = 1 if side=="LONG" else -1
            pnl_usd = (close - entry) * trade["shares"] * dir_mult
            trade["pnl_usd"] = round(pnl_usd,2)
            trade["pnl_krw"] = round(pnl_usd * 1350,0)
            print(f"{ticker} OPEN current {close} unreal {trade['pnl_krw']} KRW")

    # save
    os.makedirs("docs", exist_ok=True)
    with open(journal_path, "w", encoding="utf-8") as f:
        json.dump(journal, f, ensure_ascii=False, indent=2)
    print(f"Saved {journal_path}")

    # also create latest symlink for journal.html
    # write summary for GitHub Action output
    total_closed = sum(1 for t in journal["weeks"][week_key]["trades"] if t["status"]=="CLOSED")
    total_pnl = sum(t.get("pnl_krw",0) for t in journal["weeks"][week_key]["trades"])
    print(f"WEEK {week_key} {total_closed}/{len(journal['weeks'][week_key]['trades'])} closed, total {total_pnl} KRW")

if __name__ == "__main__":
    main()
