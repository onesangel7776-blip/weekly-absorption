#!/usr/bin/env python3
"""
V5 Daily Auto PnL - FINAL - BALANCE 기준 FIXED V2
- absorption_v5.json을 먼저 읽어서 오늘 데이터로 갱신 (이전 버그: docs/v5-ma-delta/journal_data_v5.json 옛날 파일 읽음)
- 자본금 V5는 $50000 USD 고정 (V4 $8333이 섞인 버그 수정)
- 50K=5티커(15슬롯), 60K=6티커(18슬롯) 잔고 기준
- 무제한 누적 + 동일 티커 동일 방향은 scoring_engine_v5.py에서 이미 처리
"""
import json
import os
from collections import defaultdict

JOURNAL_PATHS = [
    "absorption_v5.json",
    "journal_data_v5.json",
    "docs/v5-ma-delta/journal_data_v5.json",
    "docs/journal_data_v5.json",
    "docs/v5-ma-delta/absorption_v5.json",
]

def parse_num(v, d=0):
    if v is None or v == "":
        return d
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        s = v.replace(",", "").replace("원", "").replace("$", "").replace(" ", "").replace("+", "").replace("KRW", "").replace("USD","").replace("만","")
        try:
            return float(s) if "." in s else int(s)
        except:
            return d
    return d

def get_max_tickers_v5(balance_usd):
    if balance_usd >= 95000: return 10
    if balance_usd >= 85000: return 9
    if balance_usd >= 75000: return 8
    if balance_usd >= 65000: return 7
    if balance_usd >= 55000: return 6
    return 5

# 1. absorption_v5.json을 우선 읽기 (오늘 생성된 최신)
data = None
journal_path = None
for p in JOURNAL_PATHS:
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                jd = json.load(f)
                # slots가 있는 파일만 유효
                slots = jd.get("slots") or jd.get("ledger") or jd.get("positions")
                if slots and len(slots) > 0:
                    data = jd
                    journal_path = p
                    print(f"Using {p} with {len(slots)} slots")
                    break
        except Exception as e:
            print(f"Skip {p}: {e}")
            continue

if not data:
    print("No valid journal found, abort")
    exit(1)

ledger = data.get("slots") or data.get("ledger") or data.get("positions") or []
print(f"Before: {len(ledger)} entries from {journal_path}")

# V5 자본금 고정: $50000
capital_usd = 50000.0
capital_krw = 67500000  # 50000 * 1350
# 기존 파일에 capital이 있으면 그걸 쓰되, 10000 미만이면 V5 자본으로 강제
existing_cap_usd = parse_num(data.get("capital_usd", 0), 0)
existing_cap_krw = parse_num(data.get("capital_krw", 0), 0)
if existing_cap_usd >= 40000:  # 이미 50000이면 유지
    capital_usd = existing_cap_usd
if existing_cap_krw >= 50000000:
    capital_krw = existing_cap_krw

# dedup: date + ticker + tf
seen = {}
for e in ledger:
    week = str(e.get("date", "") or e.get("week", "") or "").strip()
    ticker = str(e.get("ticker", "")).strip().upper().split()[0]
    tf = str(e.get("tf", "") or e.get("timeframe", "") or "").strip()
    if not week or not ticker:
        continue
    key = f"{week}_{ticker}_{tf}" if tf else f"{week}_{ticker}"
    seen[key] = e

by_week = defaultdict(list)
for e in seen.values():
    w = str(e.get("date", "") or e.get("week", "") or "").strip()
    by_week[w].append(e)

# balance 계산: capital + pnl
temp_all = []
for week in sorted(by_week.keys()):
    temp_all.extend(by_week[week])

temp_pnl_usd = sum(parse_num(x.get("pnl", x.get("pnl_usd", 0)), 0) for x in temp_all)
temp_pnl_krw = sum(parse_num(x.get("pnl_krw", x.get("pnl", 0)), 0) for x in temp_all)

temp_balance_usd = capital_usd + temp_pnl_usd
temp_balance_krw = capital_krw + temp_pnl_krw

max_tickers = get_max_tickers_v5(temp_balance_usd)
max_slots = max_tickers * 3

print(f"Balance USD {temp_balance_usd} KRW {temp_balance_krw} -> max tickers {max_tickers} = {max_slots} slots (capital USD {capital_usd} + pnl {temp_pnl_usd})")

# 주별로 score 높은 순으로 max_slots개만
final_entries = []
for week in sorted(by_week.keys()):
    entries = by_week[week]
    entries_sorted = sorted(entries, key=lambda x: parse_num(x.get("score", 0), 0), reverse=True)
    if len(entries_sorted) > max_slots:
        print(f"Week {week}: {len(entries_sorted)} -> {max_slots} (trim by score)")
        entries_sorted = entries_sorted[:max_slots]
    final_entries.extend(entries_sorted)

sorted_entries = sorted(final_entries, key=lambda x: (str(x.get("date","") or x.get("week","")), str(x.get("ticker",""))))

if len(sorted_entries) > 2000:
    sorted_entries = sorted_entries[-2000:]

print(f"After dedup: {len(sorted_entries)} entries, {len(by_week)} weeks, max {max_tickers} tickers = {max_slots}/week")

closed = [x for x in sorted_entries if parse_num(x.get("pnl", x.get("pnl_usd",0)),0)!=0 or str(x.get("status","")).upper() in ("CLOSED","TP1","TP2","TP3","SL")]
total_pnl_usd = sum(parse_num(x.get("pnl", x.get("pnl_usd",0)),0) for x in sorted_entries)
total_pnl_krw = sum(parse_num(x.get("pnl_krw", x.get("pnl",0)),0) for x in sorted_entries)
win_count = sum(1 for x in sorted_entries if parse_num(x.get("pnl",0),0)>0)
total_closed = len([x for x in sorted_entries if parse_num(x.get("pnl",0),0)!=0])
win_rate = round(win_count/total_closed*100,1) if total_closed else 0

# 결과 저장 - 기존 구조 유지 + balance 업데이트
data["capital_krw"] = capital_krw
data["capital_usd"] = capital_usd
data["balance_krw"] = capital_krw + total_pnl_krw
data["balance_usd"] = round(capital_usd + total_pnl_usd, 2)
data["total_pnl_krw"] = total_pnl_krw
data["total_pnl_usd"] = round(total_pnl_usd, 2)
data["win_rate"] = win_rate
data["win_count"] = win_count
data["total_closed"] = total_closed
data["total_weeks"] = len(by_week)
data["total_entries"] = len(sorted_entries)
data["max_tickers"] = max_tickers
data["max_slots"] = max_slots
data["ledger"] = sorted_entries
data["slots"] = sorted_entries
data["positions"] = sorted_entries

if len(sorted_entries) < 3:
    print(f"ABORT too small {len(sorted_entries)}")
    exit(1)

for out_path in ["docs/v5-ma-delta/journal_data_v5.json", "docs/journal_data_v5.json", "journal_data_v5.json", "docs/v5-ma-delta/absorption_v5.json"]:
    try:
        # absorption_v5.json은 slots 키만 있으면 되지만, journal_data_v5.json 형태로 저장
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved {out_path}: {len(sorted_entries)} entries")
    except Exception as e:
        print(f"Skip {out_path}: {e}")

print(f"FINAL V5 FIXED V2: {len(sorted_entries)} entries, {len(by_week)} weeks, {max_tickers} tickers={max_slots} slots/week, pnl USD {total_pnl_usd}, balance USD {data['balance_usd']}, date {data.get('date','')}")
