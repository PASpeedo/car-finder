"""Conservative, offline Porsche listing triage. No paid APIs or scraped data."""
import re
from statistics import median
from urllib.parse import urlparse

MODEL = re.compile(r"\b(?:911|930|964|993|carrera|targa)\b", re.I)
AUTO_CUE = re.compile(r"\b(?:911|930|964|993)\b.{0,25}\b(?:sc|coupe|targa|carrera|turbo|air.cooled|convertible)\b|\b(?:sc|coupe|targa|carrera|turbo)\b.{0,25}\b(?:911|930|964|993)\b",re.I)
PORSCHE = re.compile(r"\b(?:porsche|porshe|porche|porsch)\b", re.I)
PARTS = re.compile(r"\b(?:parts? only|parting out|diecast|scale model|poster|engine only|wheels? only|transmission only|toy|repair manual)\b", re.I)
DEALER = re.compile(r"\b(?:dealership|licensed dealer|dealer(?:s)? fees?|dealer inventory|financ(?:e|ing) available|buy here pay here|doc(?:umentation)? fee|stock\s*(?:#|number)|trade[- ]?ins? welcome|all credit accepted|cash or finance)\b", re.I)
URGENCY = re.compile(r"\b(?:must sell|need gone|moving|relocating|estate sale|quick sale|no time to finish|or best offer|obo)\b", re.I)
PROJECT = re.compile(r"\b(?:project|roller|non.running|does not run|doesn't run|not running|barn find|restoration|needs rebuild)\b", re.I)
RISK = re.compile(r"\b(?:no title|lost title|salvage|flood|wire transfer|deposit to hold)\b", re.I)
DRIVER = re.compile(r"\b(?:runs and drives|running and driving|daily driver|starts and drives|drives great)\b", re.I)
YEAR = re.compile(r"\b(19(?:6[5-9]|[7-9]\d))\b")
PRICE = re.compile(r"(?:\$|USD\s*)(\d{1,3}(?:,\d{3})+|\d{4,6})(?!\d)",re.I)
MODEL_YEAR = (1965, 1997)
MAX_PRICE = 20000

def year_from(text):
    m=YEAR.search(text)
    return int(m.group(1)) if m else None

def price_from(text):
    m=PRICE.search(text)
    return int(m.group(1).replace(",","")) if m else None

def classify(item):
    """Triage source-provided information. No unverified claim of market discount."""
    x=dict(item)
    title=str(x.get("title") or "")
    description=str(x.get("description") or "")
    text=(title+" "+description).strip()
    url=str(x.get("url") or "")
    path=urlparse(url).path.lower()
    flags=[]
    year=x.get("year")
    if year is None:year=year_from(title)
    price=x.get("price")
    if price is None:price=price_from(title)
    x.update(year=year,price=price,score=0,flags=flags,source_confidence="email_only")
    if "/ctd/" in path or DEALER.search(text) or x.get("seller_type")=="dealer":
        x.update(status="excluded_dealer",seller_type="dealer");return x
    if PARTS.search(title):
        x["status"]="excluded_parts";return x
    if year is not None and not MODEL_YEAR[0]<=int(year)<=MODEL_YEAR[1]:
        x["status"]="excluded_year";return x
    if price is not None and (int(price)<=0 or int(price)>MAX_PRICE):
        x["status"]="excluded_price";return x
    # Owner category in the URL is a useful source indicator, not proof.
    x["seller_type"]="owner_category" if "/cto/" in path else "unknown"
    flags.append("seller identity unverified")
    likely911=bool(MODEL.search(text) and (PORSCHE.search(text) or AUTO_CUE.search(title)))
    if not likely911:
        flags.append("911 identity unverified")
    elif not PORSCHE.search(text):
        flags.append("Porsche make inferred; verify photos")
    if price is None:flags.append("price not in email")
    if year is None:flags.append("year not in email")
    if URGENCY.search(text):flags.append("urgency wording")
    if PROJECT.search(text):flags.append("project car")
    if DRIVER.search(text):flags.append("advertised running")
    if RISK.search(text):flags.append("possible title/scam risk")
    x["status"]="review" if likely911 else "verify_model"
    x["score"]=min(70, (25 if x["status"]=="review" else 0)+(10 if year else 0)+(8 if price else 0)+(8 if x["seller_type"]=="owner_category" else 0)+(8 if URGENCY.search(text) else 0)+(5 if PROJECT.search(text) else 0))
    # Never return an 'exceptional' score from title alone.
    if RISK.search(text):x["score"]=0
    return x

def assess_comparables(item, comps):
    """Manual verified sales only, comparable by generation, body and year window.

    Never infer value for a project from 'driver' sales. This reference is
    informational, not an independent appraisal.
    """
    text=str(item.get("title") or "").lower()
    year=item.get("year")
    try: year=int(year)
    except (ValueError,TypeError): year=None
    def family(y):
        if y is None:return None
        if y<=1973:return "early911"
        if y<=1989:return "gbody"
        if y<=1994:return "964"
        return "993"
    body=next((v for v in ("targa","cabriolet","coupe") if v in text),None)
    condition_text=(text+" "+str(item.get("description") or "")).lower()
    is_project=bool(PROJECT.search(condition_text))
    if year is None or body is None or is_project:
        return {"status":"insufficient_vehicle_match","comps":0,"median_sold_price":None,"discount_pct":None}
    available=[]
    for c in comps:
        if c.get("verified_sold") is not True or c.get("condition")!="driver" or c.get("body")!=body:continue
        try:
            cy=int(c.get("year"))
            sold=int(c.get("sold_price"))
        except (ValueError,TypeError):continue
        if sold<=0 or abs(year-cy)>3 or family(cy)!=family(year):continue
        if not c.get("source_url"):continue
        available.append(sold)
    if len(available)<3:
        return {"status":"insufficient_data","comps":len(available),"median_sold_price":None,"discount_pct":None}
    market=median(available)
    price=item.get("price")
    if price is None:
        return {"status":"price_unknown","comps":len(available),"median_sold_price":market,"discount_pct":None}
    try:price=int(price)
    except (TypeError,ValueError):price=None
    return {"status":"rough_reference_only","comps":len(available),
            "median_sold_price":market,"discount_pct":round((1-price/market)*100,1) if price else None}
