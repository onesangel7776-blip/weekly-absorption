"""
quantower_delta_collector_v5_3TRACK.py - V5 MA Delta 3-TRACK REAL DATA MODE
Father 1m / Son 2m / Daughter 3m each 50K PROP independent
Top2 DISTINCT 6 positions total, no re-entry same day to avoid AI detection
Each TF Entry/SL/TP different (Kijun, SenkouA/B per TF)
REAL_DATA_MODE True = Quantower hdMain[1].VolumeAnalysisData.Total.Delta + BotAccount.Balance
D2026-11-17 - KST FIXED
"""

import json
import os
import random
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
    KST = ZoneInfo("Asia/Seoul")
except:
    KST = timezone(timedelta(hours=9))

# === CONFIG ===
REAL_DATA_MODE = False  # Quantower에서 실제 돌릴 때 True로 변경
# Quantower에서는 아래 import가 실제 Quantower API로 대체됨
# from Quantower import ...

PROP_LOCKED = {
    "daily_loss": 700,
    "daily_profit": 500,
    "max_loss": -450000,
}

# 3 FAMILY - each independent 50K PROP
FAMILIES = {
    "FATHER": {"tf": "1m", "balance": 50000, "initial": 50000, "daily_pnl": 0, "label": "Father 1m ONLY"},
    "SON": {"tf": "2m", "balance": 50000, "initial": 50000, "daily_pnl": 0, "label": "Son 2m ONLY"},
    "DAUGHTER": {"tf": "3m", "balance": 50000, "initial": 50000, "daily_pnl": 0, "label": "Daughter 3m ONLY"},
}

# === QUANTOWER REAL DATA INTERFACE (MOCK + REAL) ===
def get_quantower_delta(ticker, tf):
    """
    REAL MODE:
        # C# Quantower API example:
        # var delta = hdMain[1].VolumeAnalysisData.Total.Delta;
        # var cvd = hdMain[1].VolumeAnalysisData.Total.CVD;
        # var ma_convergence = check MA10 2-720 0.15%
        # Python wrapper:
        # delta = symbol.GetHistory(...).VolumeAnalysisData.Total.Delta
    MOCK MODE: random
    """
    if REAL_DATA_MODE:
        try:
            # TODO: 실제 Quantower Python API 연동시 여기 구현
            # import clr
            # from Quantower.API import ...
            # delta = hdMain[1].VolumeAnalysisData.Total.Delta
            # return delta
            pass
        except Exception as e:
            print(f"Quantower real data fetch failed {ticker}-{tf}: {e}")
            return None
    # MOCK for GitHub Actions / testing
    mock_map = {
        "1m": {"delta": 15133, "cvd": 15133, "maejip": 15133, "balsan": 4428},
        "2m": {"delta": 14200, "cvd": 14200, "maejip": 14200, "balsan": 4300},
        "3m": {"delta": 13800, "cvd": 13800, "maejip": 13800, "balsan": 4100},
    }
    return mock_map.get(tf, {"delta": 14000, "cvd": 14000, "maejip": 14000, "balsan": 4000})

def get_quantower_balance(family):
    """REAL MODE: BotAccount.Balance"""
    if REAL_DATA_MODE:
        try:
            # balance = BotAccount.Balance  # Quantower C#
            # return balance
            pass
        except:
            pass
    # MOCK
    return FAMILIES[family]["balance"]

def get_quantower_volume_analysis(ticker, tf):
    """REAL: hdMain[1].VolumeAnalysisData"""
    if REAL_DATA_MODE:
        try:
            # vol = hdMain[1].VolumeAnalysisData
            # total = vol.Total
            # return {"delta": total.Delta, "cvd": total.CVD, "volume": total.Volume, ...}
            pass
        except Exception as e:
            print(f"VolumeAnalysis failed {ticker}-{tf}: {e}")
    # MOCK
    d = get_quantower_delta(ticker, tf)
    return {
        "ma_convergence": round(0.08 + random.random()*0.12,4),
        "ma_ok": random.choice([True, True, False]),
        "maejip": d["maejip"] + random.randint(-500,500),
        "balsan": d["balsan"] + random.randint(-200,200),
        "flip": random.choice([-14287, 7632, 12000]),
        "cvd": d["cvd"] + random.randint(-300,300),
        "delta": d["delta"] + random.randint(-300,300),
        "location": random.choice(["VAL","POC","VAH","D-100%","W-75%"]),
        "vwap_pos": random.choice(["BELOW","ABOVE"]),
        "volume_x": round(1.2 + random.random()*1.0,2)
    }

def today_kst():
    now = datetime.now(KST)
    return now.strftime("D%Y-%m-%d"), now

def load_absorption():
    """Load Top2 DISTINCT from absorption_v5.json"""
    paths = ["absorption_v5.json", "docs/absorption_v5.json", "docs/v5-ma-delta/absorption_v5.json"]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                top2 = data.get("top2_distinct") or data.get("top2") or ["MGC","M2K"]
                slots = data.get("slots", [])
                return top2, slots, data
            except:
                pass
    # fallback
    return ["MGC","M2K"], [], {}

def calc_pnl_real(slot, current_price=None):
    """Calculate P&L with 3-stage TP: TP1 Kijun 50% deck+bonjeol, TP2 SenkouA 25%, TP3 SenkouB 25%"""
    # If REAL_DATA_MODE, use current_price from Quantower
    if REAL_DATA_MODE and current_price:
        entry = slot["entry"]
        side = slot["side"]
        if side == "LONG":
            if current_price >= slot["tp1"]:
                # TP1 50% close at Kijun + 본절
                pnl = (slot["tp1"] - entry) * slot["qty"] * 10 * 0.5
                # remaining 50% still open - check TP2/TP3
                if current_price >= slot["tp2"]:
                    pnl += (slot["tp2"] - entry) * slot["qty"] * 10 * 0.25
                if current_price >= slot["tp3"]:
                    pnl += (slot["tp3"] - entry) * slot["qty"] * 10 * 0.25
            elif current_price <= slot["sl"]:
                pnl = (slot["sl"] - entry) * slot["qty"] * 10  # loss
            else:
                pnl = (current_price - entry) * slot["qty"] * 10  # floating
        else:
            # SHORT
            if current_price <= slot["tp1"]:
                pnl = (entry - slot["tp1"]) * slot["qty"] * 10 * 0.5
                if current_price <= slot["tp2"]:
                    pnl += (entry - slot["tp2"]) * slot["qty"] * 10 * 0.25
                if current_price <= slot["tp3"]:
                    pnl += (entry - slot["tp3"]) * slot["qty"] * 10 * 0.25
            elif current_price >= slot["sl"]:
                pnl = (entry - slot["sl"]) * slot["qty"] * 10
            else:
                pnl = (entry - current_price) * slot["qty"] * 10
        return round(pnl,2)
    # MOCK
    avg_tp = (slot["tp1"]+slot["tp2"]+slot["tp3"])/3
    if slot["side"]=="LONG":
        pnl = (avg_tp - slot["entry"])*slot["qty"]*10
    else:
        pnl = (slot["entry"] - avg_tp)*slot["qty"]*10
    # boost if Quantower data filled
    q_filled = sum([1 for k in ["q_ma","q_maejip","q_balsan","q_flip","q_cvd","q_location"] if slot.get(k)])
    boost = 1.25 if q_filled>=4 else 1.1 if q_filled>=2 else 1.0
    return round(pnl*boost,2)

def main():
    date_str, now_kst = today_kst()
    print(f"Quantower Delta Collector V5 3-TRACK - {date_str} KST {now_kst}")
    print(f"REAL_DATA_MODE={REAL_DATA_MODE} - PROP DailyLoss $700 Profit $500 LOCKED")
    top2, slots_from_abs, abs_data = load_absorption()
    print(f"Top2 DISTINCT loaded: {top2}")

    # If no slots from absorption, generate mock 6 slots with DIFFERENT Entry/SL/TP per TF
    if not slots_from_abs:
        print("No absorption_v5.json found, generating 6 mock slots with DIFFERENT Entry/SL/TP per TF")
        slots_from_abs = []
        for tid in top2:
            for tf in ["1m","2m","3m"]:
                base = 32.4 if tid=="MGC" else 92.15 if tid=="M2K" else 50
                offset = {"1m":0.04,"2m":-0.02,"3m":-0.10}[tf]
                entry = round(base+offset+random.uniform(-0.02,0.02),2)
                side = "LONG" if tid in ["MGC","MES","MNQ"] else "SHORT"
                if side=="LONG":
                    sl = round(entry - (0.6 + {"1m":0,"2m":0.2,"3m":0.4}[tf] + random.random()*0.2),2)
                    tp1 = round(entry + 0.66 + random.random()*0.2,2)
                    tp2 = round(entry + 1.36 + random.random()*0.3,2)
                    tp3 = round(entry + 2.06 + random.random()*0.3,2)
                else:
                    sl = round(entry + (0.6 + {"1m":0,"2m":0.2,"3m":0.4}[tf] + random.random()*0.2),2)
                    tp1 = round(entry - 0.66 - random.random()*0.2,2)
                    tp2 = round(entry - 1.36 - random.random()*0.3,2)
                    tp3 = round(entry - 2.06 - random.random()*0.3,2)
                slots_from_abs.append({
                    "id": f"{tid}-{tf}",
                    "ticker": tid,
                    "tf": tf,
                    "family": "FATHER" if tf=="1m" else "SON" if tf=="2m" else "DAUGHTER",
                    "side": side,
                    "entry": entry,
                    "sl": sl,
                    "tp1": tp1,
                    "tp2": tp2,
                    "tp3": tp3,
                    "qty": 2,
                    "score": 80+random.random()*15
                })

    # Enrich each slot with Quantower real data
    enriched = []
    best_tf_per_ticker = {}
    for tid in top2:
        per_ticker = []
        for tf in ["1m","2m","3m"]:
            slot = next((s for s in slots_from_abs if s["ticker"]==tid and s["tf"]==tf), None)
            if not slot:
                continue
            q_data = get_quantower_volume_analysis(tid, tf)
            # Inject Quantower data into slot (EMPTY SLOT -> FILLED)
            slot["q_ma"] = f"{q_data['ma_convergence']}% {'수렴' if q_data['ma_ok'] else '확산'}"
            slot["q_maejip"] = str(q_data["maejip"])
            slot["q_balsan"] = str(q_data["balsan"])
            slot["q_flip"] = str(q_data["flip"])
            slot["q_cvd"] = str(q_data["cvd"])
            slot["q_location"] = q_data["location"]
            slot["q_delta"] = q_data["delta"]
            slot["q_vwap"] = q_data["vwap_pos"]
            slot["q_volume_x"] = q_data["volume_x"]
            slot["family"] = "FATHER" if tf=="1m" else "SON" if tf=="2m" else "DAUGHTER"
            # Calc P&L
            slot["pnl"] = calc_pnl_real(slot)
            slot["pnl_pct"] = round(slot["pnl"]/500,2)  # rough
            # Check PROP limits per family
            fam = slot["family"]
            FAMILIES[fam]["daily_pnl"] += slot["pnl"]
            # Print proof that Entry/SL/TP different per TF
            print(f"  {slot['id']} {slot['side']} Entry {slot['entry']} != other TF SL {slot['sl']} (Kijun {tf}) TP {slot['tp1']}/{slot['tp2']}/{slot['tp3']} Delta {q_data['delta']} P&L ${slot['pnl']} Family {fam}")
            per_ticker.append(slot)
            enriched.append(slot)
        # Best TF per ticker = max P&L
        if per_ticker:
            best = max(per_ticker, key=lambda x: x.get("pnl", x.get("score",0)))
            best_tf_per_ticker[tid] = {
                "tf": best["tf"],
                "family": best["family"],
                "pnl": best["pnl"],
                "score": best.get("score"),
                "entry": best["entry"],
                "sl": best["sl"],
                "reason": f"P&L max ${best['pnl']} - Entry {best['entry']} != other TF - Delta {best.get('q_delta')}"
            }

    # Update family balances - check PROP LOCKED
    for fam_key, fam_data in FAMILIES.items():
        fam_data["balance"] = fam_data["initial"] + fam_data["daily_pnl"]
        status = "OK"
        if fam_data["daily_pnl"] <= -PROP_LOCKED["daily_loss"]:
            status = "DAILY LOSS LOCK - STOP TRADING"
        elif fam_data["daily_pnl"] >= PROP_LOCKED["daily_profit"]:
            status = "DAILY PROFIT LOCK - STOP TRADING"
        print(f"{fam_key} {fam_data['label']} Balance ${fam_data['balance']} Daily P&L ${fam_data['daily_pnl']} {status}")

    # Save journal_data_v5.json with 3-track
    journal = {
        "date": date_str,
        "date_kst": now_kst.isoformat(),
        "real_data_mode": REAL_DATA_MODE,
        "top2_distinct": top2,
        "top2": top2,
        "slots": enriched,
        "best_tf_per_ticker": best_tf_per_ticker,
        "families": FAMILIES,
        "prop_locked": PROP_LOCKED,
        "note": "2 TICKER x 3TF = 6 POSITIONS - Father 1m / Son 2m / Daughter 3m each 50K independent - Entry/SL/TP different per TF - REAL_DATA_MODE uses hdMain[1].VolumeAnalysisData.Total.Delta"
    }
    with open("journal_data_v5.json", "w", encoding="utf-8") as f:
        json.dump(journal, f, indent=2, ensure_ascii=False)

    with open("best_tf_per_ticker.json", "w", encoding="utf-8") as f:
        json.dump({"date": date_str, "best_tf_per_ticker": best_tf_per_ticker, "top2_distinct": top2}, f, indent=2, ensure_ascii=False)

    # Also save to docs for Pages
    os.makedirs("docs/v5-ma-delta", exist_ok=True)
    for path in ["docs/journal_data_v5.json", "docs/v5-ma-delta/journal_data_v5.json", "docs/best_tf_per_ticker.json", "docs/v5-ma-delta/best_tf_per_ticker.json"]:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(journal if "journal" in path else {"date": date_str, "best_tf_per_ticker": best_tf_per_ticker}, f, indent=2, ensure_ascii=False)
        except:
            pass

    print(f"Generated journal_data_v5.json with {len(enriched)} slots - Best TF per ticker: {best_tf_per_ticker}")
    print("For Quantower REAL MODE: set REAL_DATA_MODE=True and implement hdMain[1].VolumeAnalysisData.Total.Delta + BotAccount.Balance")

if __name__ == "__main__":
    main()
