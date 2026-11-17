#!/usr/bin/env python3
"""Import Craigslist saved-search alert emails via IMAP, no scraping or paid APIs."""
import email, html, imaplib, json, os, re, sys
from datetime import datetime, timezone
from email.header import decode_header, make_header
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urlunparse

OUTPUT=Path("deals.json")
LIMIT=1000
CL_URL=re.compile(r'https?://(?:[a-z0-9-]+\.)?craigslist\.org/[^\s<>\"\'\)]+',re.I)
P911=re.compile(r'\b(?:porsche|porshe|porche)\b.{0,45}\b(?:911|930|964|993|carrera|targa|turbo)\b|\b(?:911|930|964|993)\b.{0,45}\b(?:porsche|porshe|porche)\b',re.I)
YEAR=re.compile(r'\b(?:19[6-9]\d)\b')
PRICE=re.compile(r'(?:\$|USD\s*)(\d{1,3}(?:,\d{3})+|\d{4,6})(?!\d)',re.I)
DEALER=re.compile(r'\b(?:dealer(?:ship)?|dealer\s+fees?|we\s+finance|financing\s+available|buy\s+here\s+pay\s+here|doc\s+fee|stock\s*#|stock\s+number|trade[- ]?ins?\s+welcome|carfax\s+dealer)\b',re.I)
PARTS=re.compile(r'\b(?:parts?\s+only|parting\s+out|miniature|diecast|poster|scale\s+model|engine\s+only|transmission\s+only|wheels?\s+only)\b',re.I)
URGENT=re.compile(r'\b(?:must\s+sell|need\s+gone|moving|relocating|estate\s+sale|quick\s+sale|no\s+time\s+to\s+finish|or\s+best\s+offer|obo)\b',re.I)
PROJECT=re.compile(r'\b(?:project|roller|non.running|does(?:n.t| not)\s+run|not\s+running|barn\s+find|needs\s+restoration|needs\s+rebuild)\b',re.I)
RISK=re.compile(r'\b(?:no\s+title|lost\s+title|salvage|flood(?:ed)?|wire\s+transfer|deposit\s+to\s+hold)\b',re.I)
DRIVER=re.compile(r'\b(?:runs?\s+and\s+drives?|running\s+and\s+driving|daily\s+driver|starts?\s+and\s+drives?)\b',re.I)
class Links(HTMLParser):
    def __init__(self): super().__init__();self.links=[];self.current=None
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            d=dict(attrs);self.current=[d.get("href",""),""]
    def handle_data(self,data):
        if self.current:self.current[1]+=data
    def handle_endtag(self,tag):
        if tag=="a" and self.current:self.links.append(tuple(self.current));self.current=None
def clean_url(raw):
    raw=html.unescape(raw).rstrip(".,;!'\"")
    try:
        p=urlparse(raw)
        if p.scheme not in ("https","http") or not (p.hostname or "").endswith(".craigslist.org"):return None
        if not re.search(r'/\d{8,}\.html$',p.path):return None
        return urlunparse(("https",p.netloc.lower(),p.path,"","",""))
    except (ValueError,TypeError):return None
def decode_text(msg):
    parts=[]
    for part in msg.walk():
        if part.get_content_type() not in ("text/html","text/plain"):continue
        try: parts.append((part.get_content_type(),part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8","replace")))
        except Exception: continue
    return parts
def parse_email(raw):
    msg=email.message_from_bytes(raw)
    sender=msg.get("From","").lower()
    # Craigslist alerts from the craigslist.org domain only, no forwarded messages.
    if not re.search(r'@(?:[a-z0-9-]+\.)?craigslist\.org\b',sender):return []
    subject=str(make_header(decode_header(msg.get("Subject",""))))
    results={}
    for kind,body in decode_text(msg):
        if kind=="text/html":
            parser=Links()
            try:parser.feed(body)
            except Exception:pass
            pairs=parser.links
        else:pairs=[]
        pairs += [(u,"") for u in CL_URL.findall(body)]
        for url,title in pairs:
            key=clean_url(url)
            if not key:continue
            # Email anchor text often contains listing title; subject is search name.
            title=html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]*>',' ',title))).strip()[:200]
            if not title:title=subject[:160]
            if key not in results or len(title)>len(results[key]["title"]):
                results[key]={"url":key,"title":title,"source":"craigslist-email","first_seen":datetime.now(timezone.utc).isoformat()}
    return list(results.values())
from rules import classify as classify_rule, assess_comparables

def classify(row):
    return classify_rule(row)

def load():
    try:
        data=json.loads(OUTPUT.read_text())
        return data if isinstance(data,list) else []
    except (FileNotFoundError,ValueError):return []
def save(items):
    OUTPUT.write_text(json.dumps(items,indent=2,ensure_ascii=False)+"\n")
def main():
    user=os.getenv("CL_IMAP_USER","").strip()
    pwd=os.getenv("CL_IMAP_APP_PASSWORD","").strip()
    host=os.getenv("CL_IMAP_HOST","imap.gmail.com").strip()
    if not user or not pwd:
        print("Not configured: add CL_IMAP_USER and CL_IMAP_APP_PASSWORD repository secrets.")
        return 0
    items={x["url"]:x for x in load() if isinstance(x,dict) and x.get("url")}
    scanned_emails=0
    extracted_links=0
    raw_craigslist_urls=0
    html_anchor_count=0
    html_email_count=0
    sender_verified_count=0
    shape_count={'listing_id_html':0,'html_links_other':0,'owner_category':0,'dealer_category':0,'non_listing':0}
    with imaplib.IMAP4_SSL(host,993,timeout=30) as imap:
        imap.login(user,pwd)
        status,_=imap.select("INBOX",readonly=True)
        if status!="OK":raise RuntimeError("Cannot access INBOX")
        status,data=imap.uid("SEARCH",None,"(FROM \"craigslist.org\" SINCE \"01-Nov-2026\")")
        if status!="OK":raise RuntimeError("Search failed")
        ids=(data[0] or b"").split()[-250:]
        for uid in ids:
            status,msgs=imap.uid("FETCH",uid,"(RFC822)")
            if status!="OK":continue
            for blob in msgs or []:
                if not isinstance(blob,tuple) or not isinstance(blob[1],bytes):continue
                scanned_emails+=1
                parsed=email.message_from_bytes(blob[1])
                if re.search(r'@(?:[a-z0-9-]+\.)?craigslist\.org\b',parsed.get("From","").lower()):
                    sender_verified_count+=1
                for content_kind,body in decode_text(parsed):
                    urls=CL_URL.findall(body)
                    raw_craigslist_urls+=len(urls)
                    for raw_url in urls:
                        try:
                            parsed_url=urlparse(html.unescape(raw_url))
                            path=parsed_url.path.lower()
                            if path.endswith(".html") and re.search("[0-9]{8,}",path):
                                shape_count["listing_id_html"]+=1
                            elif ".html" in path:
                                shape_count["html_links_other"]+=1
                            else:
                                shape_count["non_listing"]+=1
                            if "/cto/" in path:shape_count["owner_category"]+=1
                            if "/ctd/" in path:shape_count["dealer_category"]+=1
                        except ValueError:pass
                    if content_kind=="text/html":
                        html_email_count+=1
                        p=Links()
                        try:p.feed(body)
                        except Exception:pass
                        html_anchor_count+=len(p.links)
                candidates=parse_email(blob[1])
                extracted_links+=len(candidates)
                for candidate in candidates:
                    old=items.get(candidate["url"])
                    fresh=classify(candidate)
                    if old:
                        # New Craigslist email may change price or reveal better title.
                        if len(candidate.get("title","")) > len(old.get("title","")):
                            old["title"]=candidate["title"]
                        new_price=fresh.get("price")
                        previous=old.get("price")
                        if new_price is not None and new_price!=previous:
                            history=old.setdefault("price_history",[])
                            if previous is not None and not history:
                                history.append({"price":previous,"seen":old.get("first_seen")})
                            history.append({"price":new_price,"seen":datetime.now(timezone.utc).isoformat()})
                            old["price"]=new_price
                            old["price_dropped"]=previous is not None and new_price<previous
                        original_seen=old.get("first_seen")
                        saved_history=old.get("price_history",[])
                        was_drop=old.get("price_dropped",False)
                        revised=classify(old)
                        revised["first_seen"]=original_seen
                        revised["price_history"]=saved_history
                        revised["price_dropped"]=was_drop
                        items[candidate["url"]]=revised
                        continue
                    items[candidate["url"]]=fresh
        imap.logout()
    data=list(items.values())[-LIMIT:]
    try:
        comps=json.loads(Path("comparables.json").read_text())
        if not isinstance(comps,list):comps=[]
    except (FileNotFoundError,ValueError):comps=[]
    for row in data:
        row["market_assessment"]=assess_comparables(row,comps)
    save(data)
    Path("collector_status.json").write_text(json.dumps({
        "last_checked_utc":datetime.now(timezone.utc).isoformat(),
        "records":len(data),
        "emails_scanned":scanned_emails,
        "candidate_links_extracted":extracted_links,
        "craigslist_urls_in_email_bodies":raw_craigslist_urls,
        "html_anchor_links":html_anchor_count,
        "html_parts_seen":html_email_count,
        "verified_sender_messages":sender_verified_count,
        "url_shape_counts":shape_count,
        "review_candidates":sum(x.get("status")=="review" for x in data),
        "source":"Craigslist saved-search email"
    },indent=2)+"\n")
    print("Stored",len(data),"unique candidate URLs; examined",scanned_emails,"emails; extracted",extracted_links,"links.")
    return 0
if __name__=="__main__":sys.exit(main())
