#!/usr/bin/env python3
"""
V4 Daily Auto PnL - FINAL
- 한 주에 같은 티커 한 번만 (week+ticker 중복 제거)
- 자본금별 한 주 개수: 10M=3, 20M=4, 30M=5, 60M=6
- 월요일에만 새 진입, 화~금 추가 진입 없음
- 무제한 누적 (자르기 없음, 6개월 78개 이상 계속 누적)
- 기존 daily_pnl_checker.py 교체용
"""
import json
from collections import defaultdict

JOURNAL_PATHS = ["docs/journal_data.json", "journal_data.json"]

def parse_num(v,d=0):
    if v is None or v=="": return d
    if isinstance(v,(int,float)): return v
    if isinstance(v,str):
        s=v.replace(",","").replace("원","").replace("$","").replace(" ","").replace("+","").replace("KRW","").replace("USD","")
        try: return float(s) if "." in s else int(s)
        except: return d
    return d

def get_max_tickers(c):
    c=parse_num(c,10000000)
    if c>=60000000: return 6
    if c>=30000000: return 5
    if c>=20000000: return 4
    return 3

# 루트에 있는 파일 먼저 시도, 없으면 docs
journal_path = None
for p in JOURNAL_PATHS:
    try:
        with open(p,"r",encoding="utf-8") as f:
            json.load(f)
        journal_path = p
        break
    except:
        continue

if not journal_path:
    journal_path = "docs/journal_data.json"

with open(journal_path,"r",encoding="utf-8") as f:
    data=json.load(f)

ledger=data.get("ledger",[])
print(f"Before: {len(ledger)} entries from {journal_path}")

# 1. 한 주에 같은 티커 한 번만
seen={}
for e in ledger:
    week=str(e.get("week","")).strip()
    ticker=str(e.get("ticker","")).strip().upper()
    if not week or not ticker: continue
    key=f"{week}_{ticker}"
    seen[key]=e

by_week=defaultdict(list)
for e in seen.values():
    by_week[e.get("week","")].append(e)

capital_krw=parse_num(data.get("capital_krw",10000000),10000000)
max_per_week=get_max_tickers(capital_krw)

final_entries=[]
for week in sorted(by_week.keys()):
    entries=by_week[week]
    # 신뢰도 높은 순으로 정렬해서 max_per_week개만 유지
    entries_sorted=sorted(entries, key=lambda x: parse_num(x.get("score",0),0), reverse=True)
    if len(entries_sorted)>max_per_week:
        print(f"Week {week}: {len(entries_sorted)} -> {max_per_week} (trim by score)")
        entries_sorted=entries_sorted[:max_per_week]
    final_entries.extend(entries_sorted)

sorted_entries=sorted(final_entries, key=lambda x: (x.get("week",""), x.get("ticker","")))

# 무제한 누적 - 2000개 안전장치만
if len(sorted_entries)>2000:
    sorted_entries=sorted_entries[-2000:]

print(f"After dedup: {len(sorted_entries)} entries, {len(by_week)} weeks, max per week {max_per_week}")

capital_usd=parse_num(data.get("capital_usd",7407.41),7407.41)
closed=[x for x in sorted_entries if str(x.get("status","")).upper()=="CLOSED"]
total_pnl_krw=sum(parse_num(x.get("pnl_krw",0),0) for x in closed)
total_pnl_usd=sum(parse_num(x.get("pnl_usd",0),0) for x in closed)
win_count=sum(1 for x in closed if parse_num(x.get("pnl_krw",0),0)>0)
total_closed=len(closed)
win_rate=round(win_count/total_closed*100,1) if total_closed else 0

data["capital_krw"]=capital_krw
data["capital_usd"]=capital_usd
data["balance_krw"]=capital_krw+total_pnl_krw
data["balance_usd"]=round(capital_usd+total_pnl_usd,2)
data["total_pnl_krw"]=total_pnl_krw
data["total_pnl_usd"]=round(total_pnl_usd,2)
data["win_rate"]=win_rate
data["win_count"]=win_count
data["total_closed"]=total_closed
data["total_weeks"]=len(by_week)
data["total_entries"]=len(sorted_entries)
data["max_tickers"]=max_per_week
data["ledger"]=sorted_entries

if len(sorted_entries)<3:
    print(f"ABORT too small {len(sorted_entries)}")
    exit(1)

# 두 경로 모두에 저장 (루트와 docs)
for out_path in ["docs/journal_data.json", "journal_data.json"]:
    try:
        with open(out_path,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
        print(f"Saved {out_path}: {len(sorted_entries)} entries")
    except Exception as e:
        print(f"Skip {out_path}: {e}")

print(f"FINAL: {len(sorted_entries)} entries, {len(by_week)} weeks, {max_per_week}/week, pnl {total_pnl_krw}")
