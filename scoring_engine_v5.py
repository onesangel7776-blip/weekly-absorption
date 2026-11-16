# scoring_engine_v5.py - V5 MA Delta BEST TF + DISTINCT Top2
import json, os
from collections import defaultdict
from datetime import datetime

JOURNAL_PATH = "./journal_data_v5.json"
ABSORPTION_PATH = "./absorption_v5.json"
BEST_TF_PATH = "./best_tf_per_ticker.json"
TICKERS_21 = ["M2K","MNQ","MES","MYM","MGC","SIL","MCL","6E","6J","6A","6B","ZN","ZB","NG","GC","SI","CL","NQ","ES","YM","RTY"]
TFS = ["1m","2m","3m"]

def load_journal():
    if not os.path.exists(JOURNAL_PATH):
        import random
        data=[]
        for i in range(515):
            t=TICKERS_21[i%21]; tf=TFS[i%3]
            pnl=random.randint(-500,800)
            data.append({"ticker":t,"tf":tf,"pnl":pnl,"family":["FATHER","SON","DAUGHTER"][i%3],"score":random.randint(70,100),"win":pnl>0})
        return data
    with open(JOURNAL_PATH,'r',encoding='utf-8') as f: return json.load(f)

def aggregate_best_tf(journal):
    per_ticker_tf=defaultdict(lambda:defaultdict(list))
    for r in journal:
        ticker=r.get("ticker"); tf=r.get("tf","1m"); pnl=float(r.get("pnl",0))
        per_ticker_tf[ticker][tf].append(pnl)
    best_map={}; counts={"1m":0,"2m":0,"3m":0}
    for ticker,tf_dict in per_ticker_tf.items():
        sum_by_tf={}
        for tf in TFS:
            vals=tf_dict.get(tf,[]); s=sum(vals)
            wr=sum(1 for v in vals if v>0)/len(vals)*100 if vals else 0
            sum_by_tf[tf]={"sum":s,"count":len(vals),"win_rate":round(wr,1)}
        best_tf=max(sum_by_tf.items(), key=lambda x:x[1]["sum"])[0]
        best_map[ticker]={"best_tf":best_tf,"best_pnl":sum_by_tf[best_tf]["sum"],"per_tf":sum_by_tf,"final":f"{ticker}={best_tf}"}
        counts[best_tf]+=1
    return best_map,counts

def get_top2_distinct(journal,best_map):
    slots=[{"ticker":r.get("ticker","M2K"),"tf":r.get("tf","1m"),"score":int(r.get("score",80))} for r in journal]
    slots_sorted=sorted(slots, key=lambda x:(x["score"],best_map.get(x["ticker"],{}).get("best_pnl",0)), reverse=True)
    seen=set(); sel=[]
    for s in slots_sorted:
        if s["ticker"] in seen: continue
        seen.add(s["ticker"]); sel.append(s)
        if len(sel)>=2: break
    return sel

def main():
    journal=load_journal()
    best_map,counts=aggregate_best_tf(journal)
    top2=get_top2_distinct(journal,best_map)
    print(f"BEST TF counts {counts}")
    print(f"Top2 DISTINCT {[(t['ticker']+'-'+t['tf']+'('+str(t['score'])+')') for t in top2]}")
    with open(BEST_TF_PATH,'w',encoding='utf-8') as f: json.dump(best_map,f,indent=2,ensure_ascii=False)
    abs_data={}
    if os.path.exists(ABSORPTION_PATH):
        try:
            with open(ABSORPTION_PATH,'r',encoding='utf-8') as f: abs_data=json.load(f)
        except: pass
    abs_data["best_tf_per_ticker"]=best_map; abs_data["best_counts"]=counts
    abs_data["top2_distinct"]=[{"ticker":t["ticker"],"tf":t["tf"],"score":t["score"]} for t in top2]
    abs_data["generated_at"]=datetime.now().isoformat()
    with open(ABSORPTION_PATH,'w',encoding='utf-8') as f: json.dump(abs_data,f,indent=2,ensure_ascii=False)

if __name__=="__main__": main()
