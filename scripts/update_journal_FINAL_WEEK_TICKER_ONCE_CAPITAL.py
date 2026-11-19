#!/usr/bin/env python3
"""
V4-AUTO 최종 - BALANCE 기준 - 무제한 누적 + 한주에 같은 티커 한번만 + 자본금별 개수
- 규칙:
  1. 한주에 같은 티커는 한번만 매매 (week+ticker 중복이면 최신 1개만)
  2. 자본금별 한주 매매 개수: 10M=3, 20M=4, 30M=5, 60M=6 - balance 기준으로 자동 증가
  3. 월요일에만 3~6개 진입, 화~금 추가 진입 없음 (이 스크립트는 추가 안 함, 유지보수만)
  4. 무제한 누적 (자르기 없음, 2000개 안전장치만)
  5. V4 페이지가 자본금 늘어난 걸 아는 방법: balance = capital + total_pnl
"""
import json
from collections import defaultdict

JOURNAL_PATH = "docs/journal_data.json"

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

with open(JOURNAL_PATH,"r",encoding="utf-8") as f:
    data=json.load(f)

ledger=data.get("ledger",[])
print(f"Before: {len(ledger)} entries")

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
capital_usd=parse_num(data.get("capital_usd",7407.41),7407.41)

# Balance 기준으로 max_tickers 결정 - V4 페이지가 자본금 늘어난 걸 아는 방법
temp_all=[]
for w in sorted(by_week.keys()):
    temp_all.extend(by_week[w])
temp_closed=[x for x in temp_all if str(x.get("status","")).upper()=="CLOSED"]
temp_pnl_krw=sum(parse_num(x.get("pnl_krw",0),0) for x in temp_closed)
temp_balance_krw=capital_krw+temp_pnl_krw
max_per_week=get_max_tickers(temp_balance_krw)
print(f"Balance {temp_balance_krw} -> max per week {max_per_week} (capital {capital_krw} + pnl {temp_pnl_krw})")

final_entries=[]
for week in sorted(by_week.keys()):
    entries=by_week[week]
    entries_sorted=sorted(entries, key=lambda x: parse_num(x.get("score",0),0), reverse=True)
    if len(entries_sorted)>max_per_week:
        print(f"Week {week}: {len(entries_sorted)} -> {max_per_week} (trim by score)")
        entries_sorted=entries_sorted[:max_per_week]
    final_entries.extend(entries_sorted)

sorted_entries=sorted(final_entries, key=lambda x: (x.get("week",""), x.get("ticker","")))
if len(sorted_entries)>2000:
    sorted_entries=sorted_entries[-2000:]
    print("Trimmed to 2000 for safety")

print(f"After: {len(sorted_entries)} entries, {len(by_week)} weeks, max per week {max_per_week}")

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

with open(JOURNAL_PATH,"w",encoding="utf-8") as f:
    json.dump(data,f,ensure_ascii=False,indent=2)

print(f"FINAL: {len(sorted_entries)} entries, {len(by_week)} weeks, {max_per_week}/week, pnl {total_pnl_krw}, balance {data['balance_krw']}")
print("Rules:")
print(f"  - Same week same ticker: only once (week+ticker dedup)")
print(f"  - Per week max: {max_per_week} (10M=3,20M=4,30M=5,60M=6) - balance based")
print(f"  - Unlimited accumulate: no cut")
