#!/usr/bin/env python3
"""
V5 Daily Auto PnL - VIRTUAL V2 - TP/SL + MaxLoss $2000 추가
- 50K Prop MaxLoss $2000 = balance 48000 밑으로 가면 계좌 정지
- DailyLoss $700 / DailyProfit $500 / News/Judas BLOCK 기존 유지
"""
import json, os, random
from collections import defaultdict

JOURNAL_PATHS = [
    "absorption_v5.json",
    "journal_data_v5.json",
    "docs/v5-ma-delta/journal_data_v5.json",
    "docs/journal_data_v5.json",
    "docs/v5-ma-delta/absorption_v5.json",
]

MAX_LOSS_USD = -2000  # 50K Prop 전체 손실 제한
MAX_BALANCE_FLOOR = 48000  # 50000-2000

def parse_num(v, d=0):
    if v is None or v == "": return d
    if isinstance(v, (int,float)): return v
    if isinstance(v, str):
        s = v.replace(",","").replace("원","").replace("$","").replace(" ","").replace("+","").replace("KRW","").replace("USD","").replace("만","")
        try: return float(s) if "." in s else int(s)
        except: return d
    return d

def get_max_tickers_v5(balance_usd):
    if balance_usd >= 95000: return 10
    if balance_usd >= 85000: return 9
    if balance_usd >= 75000: return 8
    if balance_usd >= 65000: return 7
    if balance_usd >= 55000: return 6
    return 5

def simulate_pnl(slot):
    score = parse_num(slot.get("score",0),0)
    win_prob = 0.6 if score >= 106 else 0.5
    is_win = random.random() < win_prob
    if random.random() < 0.08:
        return 0,0,"BLOCKED_NEWS" if random.random()<0.5 else "BLOCKED_JUDAS"
    if is_win:
        r = random.random()
        if r < 0.5: pnl_usd = random.uniform(80,130); status="TP1"
        elif r < 0.75: pnl_usd = random.uniform(120,170); status="TP2"
        else: pnl_usd = random.uniform(150,220); status="TP3"
    else:
        pnl_usd = -random.uniform(40,120); status="SL"
    return round(pnl_usd,2), round(pnl_usd*1350,0), status

data=None; journal_path=None
for p in JOURNAL_PATHS:
    if os.path.exists(p):
        try:
            with open(p,"r",encoding="utf-8") as f:
                jd=json.load(f)
                slots=jd.get("slots") or jd.get("ledger") or jd.get("positions")
                if slots and len(slots)>0:
                    data=jd; journal_path=p; break
        except: continue
if not data:
    print("No valid journal"); exit(1)

ledger = data.get("slots") or data.get("ledger") or data.get("positions") or []
capital_usd=50000.0; capital_krw=67500000
existing_cap_usd=parse_num(data.get("capital_usd",0),0)
existing_cap_krw=parse_num(data.get("capital_krw",0),0)
if existing_cap_usd>=40000: capital_usd=existing_cap_usd
if existing_cap_krw>=50000000: capital_krw=existing_cap_krw

seen={}
for e in ledger:
    week=str(e.get("date","") or e.get("week","") or "").strip()
    ticker=str(e.get("ticker","")).strip().upper().split()[0]
    tf=str(e.get("tf","") or e.get("timeframe","") or "").strip()
    if not week or not ticker: continue
    key=f"{week}_{ticker}_{tf}" if tf else f"{week}_{ticker}"
    seen[key]=e

by_week=defaultdict(list)
for e in seen.values():
    w=str(e.get("date","") or e.get("week","") or "").strip()
    by_week[w].append(e)

temp_all=[]
for week in sorted(by_week.keys()): temp_all.extend(by_week[week])
temp_pnl_usd=sum(parse_num(x.get("pnl",x.get("pnl_usd",0)),0) for x in temp_all)
temp_balance_usd=capital_usd+temp_pnl_usd
max_tickers=get_max_tickers_v5(temp_balance_usd)
max_slots=max_tickers*3

print(f"Balance USD {temp_balance_usd} (PnL {temp_pnl_usd}) -> max {max_tickers} tickers={max_slots} slots")
print(f"MaxLoss check: floor {MAX_BALANCE_FLOOR}, current {temp_balance_usd}")

final_entries=[]
running_total_pnl = 0
# 이전 주차 누적부터 시작 (이미 저장된 pnl 합)
# running_total은 by_week 순서대로 누적
account_blown = False

for week in sorted(by_week.keys()):
    if account_blown:
        print(f"Week {week}: ACCOUNT BLOWN (MaxLoss $2000) - all BLOCKED")
        for e in by_week[week]:
            e["pnl"]=0; e["pnl_usd"]=0; e["pnl_krw"]=0; e["status"]="BLOCKED_MAXLOSS"
            final_entries.append(e)
        continue

    entries=sorted(by_week[week], key=lambda x: parse_num(x.get("score",0),0), reverse=True)
    if len(entries)>max_slots: entries=entries[:max_slots]

    daily_pnl=0
    for e in entries:
        # 전체 MaxLoss 체크 먼저
        if capital_usd + running_total_pnl < MAX_BALANCE_FLOOR:
            e["pnl"]=0; e["pnl_usd"]=0; e["pnl_krw"]=0; e["status"]="BLOCKED_MAXLOSS"
            account_blown=True
            final_entries.append(e)
            print(f"  {e.get('ticker')} {e.get('tf')} BLOCKED_MAXLOSS - balance {capital_usd+running_total_pnl} < {MAX_BALANCE_FLOOR}")
            continue

        cur_pnl=parse_num(e.get("pnl",e.get("pnl_usd",0)),0)
        cur_status=str(e.get("status","")).upper()
        if cur_pnl==0 and cur_status not in ("BLOCKED_NEWS","BLOCKED_JUDAS","BLOCKED_DAILYLOSS","BLOCKED_DAILYPROFIT","BLOCKED_MAXLOSS"):
            pnl_usd,pnl_krw,status=simulate_pnl(e)
            # MaxLoss 예측 체크
            if running_total_pnl + daily_pnl + pnl_usd <= MAX_LOSS_USD:
                e["pnl"]=0; e["pnl_usd"]=0; e["pnl_krw"]=0; e["status"]="BLOCKED_MAXLOSS"
                account_blown=True
                final_entries.append(e)
                print(f"  {e.get('ticker')} {e.get('tf')} BLOCKED_MAXLOSS - total would be {running_total_pnl+daily_pnl+pnl_usd} <= {MAX_LOSS_USD}")
                continue
            # Daily 체크
            if daily_pnl + pnl_usd < -700:
                e["pnl"]=0; e["pnl_usd"]=0; e["pnl_krw"]=0; e["status"]="BLOCKED_DAILYLOSS"
            elif daily_pnl + pnl_usd > 500:
                e["pnl"]=0; e["pnl_usd"]=0; e["pnl_krw"]=0; e["status"]="BLOCKED_DAILYPROFIT"
            else:
                e["pnl"]=pnl_usd; e["pnl_usd"]=pnl_usd; e["pnl_krw"]=pnl_krw; e["status"]=status
                daily_pnl+=pnl_usd
        else:
            daily_pnl+=cur_pnl
        final_entries.append(e)
    running_total_pnl += daily_pnl

sorted_entries=sorted(final_entries, key=lambda x: (str(x.get("date","") or x.get("week","")), str(x.get("ticker",""))))
if len(sorted_entries)>5000: sorted_entries=sorted_entries[-5000:]

total_pnl_usd=sum(parse_num(x.get("pnl",x.get("pnl_usd",0)),0) for x in sorted_entries)
total_pnl_krw=sum(parse_num(x.get("pnl_krw",x.get("pnl",0)),0) for x in sorted_entries)

data["capital_krw"]=capital_krw; data["capital_usd"]=capital_usd
data["balance_krw"]=capital_krw+total_pnl_krw
data["balance_usd"]=round(capital_usd+total_pnl_usd,2)
data["total_pnl_krw"]=total_pnl_krw; data["total_pnl_usd"]=round(total_pnl_usd,2)
data["max_tickers"]=max_tickers; data["max_slots"]=max_slots
data["ledger"]=sorted_entries; data["slots"]=sorted_entries; data["positions"]=sorted_entries
data["max_loss_usd"]=MAX_LOSS_USD; data["max_loss_floor"]=MAX_BALANCE_FLOOR
data["account_blown"]=account_blown

for out_path in ["docs/v5-ma-delta/journal_data_v5.json","docs/journal_data_v5.json","journal_data_v5.json","docs/v5-ma-delta/absorption_v5.json"]:
    try:
        with open(out_path,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
        print(f"Saved {out_path}: {len(sorted_entries)}")
    except: pass

print(f"FINAL VIRTUAL V2: {len(sorted_entries)} entries, {max_tickers} tickers, pnl {total_pnl_usd}, balance {data['balance_usd']}, blown={account_blown}")
