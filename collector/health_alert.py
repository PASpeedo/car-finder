#!/usr/bin/env python3
"""Report GitHub collector failures through the already-connected Telegram bot.

Does not log bot tokens, email contents, or chat IDs.
"""
import os, json, sys
from telegram_notify import read, STATE, recover_chat
from pathlib import Path
from urllib import request, parse, error

def api(token,method,data):
    req=request.Request("https://api.telegram.org/bot"+token+"/"+method,
        data=parse.urlencode(data).encode(),headers={"Content-Type":"application/x-www-form-urlencoded"})
    try:
        with request.urlopen(req,timeout=20) as r:return json.load(r).get("result")
    except (error.URLError,error.HTTPError,ValueError):
        print("Could not send Telegram health warning")
        return None

def main():
    token=os.environ.get("TELEGRAM_BOT_TOKEN","")
    chat=os.environ.get("TELEGRAM_CHAT_ID","")
    if not token:
        print("Health warning unavailable: Telegram not configured")
        return
    if not chat:
        chat=recover_chat(token,read(STATE,{}))
    if not chat:
        updates=api(token,"getUpdates",{"timeout":"0","limit":"100"})
        ids={str(m["chat"]["id"]) for x in (updates or []) for m in [x.get("message",{})]
             if m.get("chat",{}).get("type")=="private" and m.get("chat",{}).get("id") is not None}
        if len(ids)!=1:
            print("Cannot route health warning safely: expected one Telegram private chat")
            return
        chat=next(iter(ids))
    url=os.environ.get("GITHUB_SERVER_URL","https://github.com")+"/"+os.environ.get("GITHUB_REPOSITORY","PASpeedo/car-finder")+"/actions/runs/"+os.environ.get("GITHUB_RUN_ID","")
    result=api(token,"sendMessage",{"chat_id":chat,"text":"🚨 Speedy ERROR: A Craigslist scan, test, publish, or Telegram notification step failed. Check the failed GitHub Actions run:\n"+url})
    if result is None:
        print("ERROR: Could not deliver Telegram failure alert",file=sys.stderr)
        sys.exit(1)
    print("Telegram failure alert delivered")

if __name__=="__main__":main()
