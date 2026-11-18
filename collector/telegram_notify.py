#!/usr/bin/env python3
"""Send no-cost Telegram alerts from Craigslist email candidates.

Set TELEGRAM_BOT_TOKEN in GitHub Actions secrets. Send /start to the bot;
a unique private conversation is detected automatically.
"""
import hashlib, hmac, json, os, re, sys
from pathlib import Path
from urllib import request, parse, error

STATE=Path("telegram_state.json")
FEED=Path("deals.json")
P911=re.compile(r"\b(?:porsche|porshe|porche)\b.{0,45}\b(?:911|930|964|993|carrera|targa|turbo)\b|\b(?:911|930|964|993)\b.{0,45}\b(?:porsche|porshe|porche)\b", re.I)
URGENT=re.compile(r"must sell|need gone|moving|relocating|estate sale|quick sale|no time to finish|\bobo\b",re.I)
RISK=re.compile(r"no title|lost title|salvage|flood|wire transfer|deposit to hold",re.I)

def read(path,default):
    try:
        v=json.loads(path.read_text())
        return v if isinstance(v,type(default)) else default
    except (FileNotFoundError,ValueError):return default

def save(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n")

def telegram(token,method,data):
    payload=parse.urlencode(data).encode()
    req=request.Request("https://api.telegram.org/bot"+token+"/"+method,data=payload,
        headers={"Content-Type":"application/x-www-form-urlencoded"})
    try:
        with request.urlopen(req, timeout=20) as resp: ans=json.load(resp)
    except (error.HTTPError,error.URLError,TimeoutError,ValueError):
        # Never expose exception URLs: they contain the bot token.
        raise RuntimeError("Telegram request failed: check bot token or connectivity") from None
    if not ans.get("ok"):raise RuntimeError("Telegram rejected request")
    return ans["result"]

def chat_for(token):
    override=os.getenv("TELEGRAM_CHAT_ID","").strip()
    if override:
        if not re.fullmatch(r"-?\d+",override):raise RuntimeError("Chat ID must be numeric")
        return override
    identity=telegram(token,"getMe",{})
    username=str(identity.get("username",""))
    print("Telegram authenticated bot:", "@"+username if username else "(unknown)")
    webhook=telegram(token,"getWebhookInfo",{})
    if webhook.get("url"):
        print("Telegram diagnostic: webhook configured; getUpdates cannot receive chat messages.")
        return None
    updates=telegram(token,"getUpdates",{"limit":100,"timeout":0})
    print("Telegram diagnostic: pending updates",len(updates))
    ids=set()
    for u in updates:
        m=u.get("message",{})
        c=m.get("chat",{})
        if c.get("type")=="private" and isinstance(c.get("id"),int) and not m.get("from",{}).get("is_bot"):
            ids.add(str(c["id"]))
    if len(ids)==1:return next(iter(ids))
    print("Telegram setup pending: send /start to your bot." if not ids else
          "Multiple Telegram chats detected; set TELEGRAM_CHAT_ID explicitly.")
    return None

def qualifies(x):
    """Exceptional alert policy: no automatic ungrounded valuation."""
    if x.get("status")!="review" or x.get("seller_type")!="owner_category":return False
    title=str(x.get("title") or "")
    if not P911.search(title) or RISK.search(title):return False
    try:
        year=int(x.get("year"))
        price=int(x.get("price"))
    except (TypeError,ValueError):return False
    if not 1965<=year<=1997 or not 0<price<=20000:return False
    # No market-data confidence yet; use stringent evidence of urgency only.
    # Project cars allowed, but never claim they are good deals from the email.
    return bool(URGENT.search(title))

def main():
    token=os.getenv("TELEGRAM_BOT_TOKEN","").strip()
    if not token:
        print("Telegram not connected yet; notifications skipped.")
        return 0
    chat=chat_for(token)
    if not chat:return 0
    state=read(STATE,{"chat_fingerprint":"","welcome":False,"notified":[]})
    fingerprint=hmac.new(token.encode(),chat.encode(),hashlib.sha256).hexdigest()
    if state.get("chat_fingerprint") and state["chat_fingerprint"]!=fingerprint:
        raise RuntimeError("Telegram destination changed; review telegram_state.json.")
    if not state.get("chat_fingerprint"):state={"chat_fingerprint":fingerprint,"welcome":False,"notified":[]}
    if not state.get("welcome"):
        telegram(token,"sendMessage",{"chat_id":chat,"text":"🏁 Speedy connected! Craigslist candidate notifications are active. Listings are not independently verified."})
        state["welcome"]=True
        save(STATE,state)
        print("Telegram connection confirmed.")
    # GitHub's scheduler can skip triggers without firing any failure step.
    # On the NEXT successful run, report long intervals since the prior scan.
    scan_status=read(Path("collector_status.json"),{})
    gap=scan_status.get("gap_minutes_since_previous")
    current_scan=scan_status.get("last_checked_utc")
    if isinstance(gap,(int,float)) and gap>=60 and current_scan and state.get("last_gap_warned_scan")!=current_scan:
        telegram(token,"sendMessage",{
            "chat_id":chat,
            "text":"⚠️ Speedy missed scheduled checks for about "+str(round(gap))+
                   " minutes. Gmail scanning has now resumed. GitHub's free scheduler can delay or skip runs."
        })
        state["last_gap_warned_scan"]=current_scan
        save(STATE,state)
        print("Telegram: reported delayed schedule (gap minutes)",round(gap))
    sent=set(state.get("notified",[]))
    pending=[x for x in read(FEED,[]) if isinstance(x,dict) and x.get("url") and x["url"] not in sent and qualifies(x)]
    pending.sort(key=lambda x:x.get("first_seen",""))
    for x in pending[:4]:
        price="$"+format(int(x["price"]),",") if x.get("price") is not None else "Not shown in email"
        message="\n".join([
            "🏁 Motivated-seller 911 candidate — NOT an appraised deal",
            str(x.get("title","Porsche"))[:150],
            "Asking: "+price,
            "Seller and condition: unverified",
            "Market value: not yet verified",
            str(x["url"])
        ])
        telegram(token,"sendMessage",{"chat_id":chat,"text":message,"disable_web_page_preview":"true"})
        sent.add(x["url"])
        state["notified"]=list(sent)[-3000:]
        save(STATE,state)
    print("Telegram:",len(pending),"eligible unsent candidates;",min(4,len(pending)),"new alerts delivered.")
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except RuntimeError as e:
        print(str(e),file=sys.stderr)
        sys.exit(1)
