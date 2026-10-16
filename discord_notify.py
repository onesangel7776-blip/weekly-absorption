import json, os, requests
try:
    with open('absorption.json') as f:
        data=json.load(f)
    sel = data.get('selected',[])
    sel_txt = ', '.join([f"{s['ticker']} {s['side']} {s['score']}" for s in sel]) if sel else 'No trade - NEUTRAL'
    macro = data.get('macro',{})
    msg = f"**21 COMMAND CENTER {data.get('date')}** {macro.get('bias')} DXY {macro.get('dxy')} US10Y {macro.get('us10y')}%\nBOTTOM {data['summary']['bottom_count']} TOP {data['summary']['top_count']}\nSELECTED: {sel_txt}\nhttps://onesangel7776-blip.github.io/weekly-absorption/"
    url = os.getenv('DISCORD_WEBHOOK_URL')
    if url:
        requests.post(url, json={'content': msg}, timeout=10)
        print("Discord sent")
except Exception as e:
    print(f"Discord skip: {e}")
