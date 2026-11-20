#!/usr/bin/env python3
"""
V5 Daily Auto PnL - FINAL - BALANCE 기준 (V4 동일 로직)
- 한 주에 같은 티커 한 번만 (week+ticker+tf 중복 제거) -> week+ticker로 3TF 묶음 유지
- 잔고 기준: 50K=5티커(15슬롯), 60K=6티커(18슬롯) 자동 증가
- 월요일에만 새 진입, 화~금 추가 진입 없음
- 무제한 누적 (자르기 없음, 2000개 안전장치만)
- V4와 동일: balance = capital + total_pnl
"""
import json
from collections import defaultdict

JOURNAL_PATHS = [
    "docs/v5-ma-delta/journal_data_v5.json",
    "docs/journal_data_v5.json",
    "journal_data_v5.json",
    "docs/v5-ma-delta/journal_data.json",
    "journal_data.json"
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

def get_max_tickers_v5(balance_usd, balance_krw):
    # USD 기준 50K=5, 60K=6 / KRW 기준 6000만원=6
    if balance_usd and balance_usd >= 60000:
        return 6
    if balance_krw and balance_krw >= 60000000:
        return 6
    # V5는 기본 5티커
    return 5

# 저널 파일 찾기
journal_path = None
for p in JOURNAL_PATHS:
    try:
        with open(p, "r", encoding="utf-8") as f:
            json.load(f)
        journal_path = p
        break
    except:
        continue
if not journal_path:
    journal_path = "docs/v5-ma-delta/journal_data_v5.json"

print(f"Using {journal_path}")

with open(journal_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# V5는 ledger 또는 slots 또는 positions 사용
ledger = data.get("ledger") or data.get("slots") or data.get("positions") or data.get("tickers") or []
if isinstance(ledger, dict):
    # absorption_v5.json 형태일 수도 있음
    ledger = ledger.get("slots", []) or []

print(f"Before: {len(ledger)} entries from {journal_path}")

# 1. 한 주에 같은 티커+TF 한 번만 (week_ticker_tf 중복 제거)
seen = {}
for e in ledger:
    week = str(e.get("week", "") or e.get("date", "") or "").strip()
    ticker = str(e.get("ticker", "")).strip().upper().split()[0]  # M2K2 (112) -> M2K2
    tf = str(e.get("tf", "") or e.get("timeframe", "") or "").strip()
    if not week or not ticker:
        continue
    key = f"{week}_{ticker}_{tf}" if tf else f"{week}_{ticker}"
    seen[key] = e

by_week = defaultdict(list)
for e in seen.values():
    w = str(e.get("week", "") or e.get("date", "") or "").strip()
    by_week[w].append(e)

capital_krw = parse_num(data.get("capital_krw", 11250000), 11250000)
capital_usd = parse_num(data.get("capital_usd", 8333), 8333)
# V5는 USD 기반, KRW는 참고
# 임시 전체로 balance 계산
temp_all = []
for week in sorted(by_week.keys()):
    temp_all.extend(by_week[week])
temp_closed = [x for x in temp_all if str(x.get("status","")).upper() in ("CLOSED","CLOSE","EXIT","TP1","TP2","TP3","SL")]
# status가 OPEN이어도 pnl이 있으면 포함
temp_pnl_krw = sum(parse_num(x.get("pnl_krw", x.get("pnl", 0)), 0) for x in temp_closed) if temp_closed else sum(parse_num(x.get("pnl_krw", x.get("pnl",0)),0) for x in temp_all)
temp_pnl_usd = sum(parse_num(x.get("pnl_usd", x.get("pnl",0)),0) for x in temp_closed) if temp_closed else sum(parse_num(x.get("pnl_usd", x.get("pnl",0)),0) for x in temp_all)

temp_balance_krw = capital_krw + temp_pnl_krw
temp_balance_usd = capital_usd + temp_pnl_usd

max_tickers = get_max_tickers_v5(temp_balance_usd, temp_balance_krw)
max_slots = max_tickers * 3  # 1m/2m/3m
print(f"Balance USD {temp_balance_usd} KRW {temp_balance_krw} -> max tickers {max_tickers} = {max_slots} slots (capital USD {capital_usd} + pnl {temp_pnl_usd})")

# 2. 주별로 score 높은 순으로 max_slots개만 유지
final_entries = []
for week in sorted(by_week.keys()):
    entries = by_week[week]
    # score 또는 pnl 기준 정렬
    entries_sorted = sorted(entries, key=lambda x: parse_num(x.get("score", x.get("pnl",0)), 0), reverse=True)
    if len(entries_sorted) > max_slots:
        print(f"Week {week}: {len(entries_sorted)} -> {max_slots} (trim by score)")
        entries_sorted = entries_sorted[:max_slots]
    final_entries.extend(entries_sorted)

sorted_entries = sorted(final_entries, key=lambda x: (str(x.get("week","") or x.get("date","")), str(x.get("ticker",""))))

# 무제한 누적 - 2000개 안전장치만
if len(sorted_entries) > 2000:
    sorted_entries = sorted_entries[-2000:]

print(f"After dedup: {len(sorted_entries)} entries, {len(by_week)} weeks, max {max_tickers} tickers = {max_slots}/week")

closed = [x for x in sorted_entries if str(x.get("status","")).upper() in ("CLOSED","CLOSE","EXIT","TP1","TP2","TP3","SL") or parse_num(x.get("pnl_krw", x.get("pnl",0)),0)!=0]
total_pnl_krw = sum(parse_num(x.get("pnl_krw", x.get("pnl",0)),0) for x in closed)
total_pnl_usd = sum(parse_num(x.get("pnl_usd", x.get("pnl",0)),0) for x in closed)
win_count = sum(1 for x in closed if parse_num(x.get("pnl_krw", x.get("pnl",0)),0)>0)
total_closed = len(closed)
win_rate = round(win_count/total_closed*100,1) if total_closed else 0

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

# 원래 키 유지: ledger 또는 slots 또는 positions
if "ledger" in data:
    data["ledger"] = sorted_entries
elif "slots" in data:
    data["slots"] = sorted_entries
elif "positions" in data:
    data["positions"] = sorted_entries
else:
    data["ledger"] = sorted_entries

if len(sorted_entries) < 3:
    print(f"ABORT too small {len(sorted_entries)}")
    exit(1)

for out_path in ["docs/v5-ma-delta/journal_data_v5.json", "docs/journal_data_v5.json", "journal_data_v5.json"]:
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved {out_path}: {len(sorted_entries)} entries")
    except Exception as e:
        print(f"Skip {out_path}: {e}")

print(f"FINAL V5: {len(sorted_entries)} entries, {len(by_week)} weeks, {max_tickers} tickers={max_slots} slots/week, pnl KRW {total_pnl_krw} USD {total_pnl_usd}, balance USD {data['balance_usd']}")
