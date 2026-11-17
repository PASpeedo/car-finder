"""Synthetic Craigslist email parsing tests; no private emails or network."""
import sys, unittest
from pathlib import Path
from email.message import EmailMessage
sys.path.insert(0,str(Path(__file__).parent/"collector"))
from craigslist_email import parse_email, classify

URL="https://sfbay.craigslist.org/eby/cto/d/oakland-1984-porsche-911/7890123456.html"

def make_message(body,html=False,sender="alerts@craigslist.org"):
    e=EmailMessage()
    e["From"]=sender
    e["To"]="owner@example.net"
    e["Subject"]="Craigslist Saved Search"
    e.set_content("See Craigslist listings")
    if html:e.add_alternative(body,subtype="html")
    else:e.set_content(body)
    return e.as_bytes()

class EmailParsingTests(unittest.TestCase):
    def test_plain_text_url(self):
        x=parse_email(make_message("1984 Porsche 911 $19,000 "+URL))
        self.assertEqual(len(x),1)
        self.assertEqual(x[0]["url"],URL)
    def test_html_anchor(self):
        x=parse_email(make_message('<a href="'+URL+'">1984 Porsche 911 $18,000</a>',True))
        self.assertEqual(len(x),1)
        self.assertIn("Porsche",x[0]["title"])
        self.assertEqual(classify(x[0])["price"],18000)
    def test_html_listing_photo(self):
        picture="https://images.craigslist.org/00A0A_photo_300x300.jpg"
        doc='<a href="'+URL+'"><img src="'+picture+'">1984 Porsche 911 $17,500</a>'
        x=parse_email(make_message(doc,True))
        self.assertEqual(len(x),1)
        self.assertEqual(x[0].get("image_url"),picture)
    def test_untrusted_sender(self):
        x=parse_email(make_message(URL,sender="noreply@example.com"))
        self.assertEqual(x,[])
    def test_dealer_link(self):
        x=parse_email(make_message(URL.replace("/cto/","/ctd/")))
        self.assertEqual(classify(x[0])["status"],"excluded_dealer")

if __name__=="__main__":unittest.main()
