# quantower_delta_collector_v5_3TRACK.py
import json, os
from datetime import datetime, date

ABSORPTION_PATH="./absorption_v5.json"
PROP_DAILY_LOSS=-700
PROP_DAILY_PROFIT=500

FAMILIES={
    "FATHER":{"tf":"1m","daily_loss":0,"daily_profit":0,"traded_tickers_today":set(),"date":None},
    "SON":{"tf":"2m","daily_loss":0,"daily_profit":0,"traded_tickers_today":set(),"date":None},
    "DAUGHTER":{"tf":"3m","daily_loss":0,"daily_profit":0,"traded_tickers_today":set(),"date":None},
}

def reset_if_new_day():
    today=date.today().isoformat()
    for fam in FAMILIES.values():
        if fam["date"]!=today:
            fam["daily_loss"]=0; fam["daily_profit"]=0; fam["traded_tickers_today"]=set(); fam["date"]=today

def load_top2_distinct():
    if os.path.exists(ABSORPTION_PATH):
        with open(ABSORPTION_PATH,'r',encoding='utf-8') as f:
            d=json.load(f); top2=d.get("top2_distinct")
            if top2 and len(top2)>=2: return [t["ticker"] for t in top2]
    return ["M2K","MNQ"]

def can_enter(fam_name,ticker,score):
    reset_if_new_day()
    fam=FAMILIES[fam_name]
    if ticker in fam["traded_tickers_today"]: return False,f"NO RE-ENTRY {ticker}"
    if fam["daily_loss"]<=PROP_DAILY_LOSS: return False,"Daily Loss Hit"
    if fam["daily_profit"]>=PROP_DAILY_PROFIT: return False,"Daily Profit Cap"
    if score<80: return False,f"Score {score}<80"
    return True,"OK"

def enter_position(fam_name,ticker,tf,entry,sl,tp,qty,score):
    ok,reason=can_enter(fam_name,ticker,score)
    if not ok:
        print(f"[BLOCK] {fam_name} {ticker}-{tf} {reason}"); return None
    FAMILIES[fam_name]["traded_tickers_today"].add(ticker)
    pos={"family":fam_name,"ticker":ticker,"tf":tf,"entry":entry,"sl":sl,"tp":tp,"qty":qty,"score":score,"timestamp":datetime.now().isoformat()}
    print(f"[ENTER] {fam_name} {ticker}-{tf} @{entry}"); return pos

def main_3track_daily():
    top2=load_top2_distinct()
    print(f"Top2 {top2} -> 6 positions (2 tickers x 3 TF)")
    mock={"M2K":{"entry":2148.5,"sl":2139,"tp":2185,"qty":2,"score":100},"MNQ":{"entry":21000,"sl":20950,"tp":21150,"qty":1,"score":98}}
    positions=[]
    for ticker in top2:
        md=mock.get(ticker,{"entry":100,"sl":99,"tp":102,"qty":1,"score":90})
        for fam in ["FATHER","SON","DAUGHTER"]:
            tf=FAMILIES[fam]["tf"]
            p=enter_position(fam,ticker,tf,md["entry"],md["sl"],md["tp"],md["qty"],md["score"])
            if p: positions.append(p)
    print(f"Total {len(positions)}")
    if positions:
        with open(f"./journal_data_v5_{date.today().isoformat()}.json",'w',encoding='utf-8') as f: json.dump(positions,f,indent=2,ensure_ascii=False)

if __name__=="__main__": main_3track_daily()
