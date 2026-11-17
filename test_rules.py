import unittest
from collector.rules import classify, assess_comparables

def listing(title,url="https://sfbay.craigslist.org/sfc/cto/d/san-francisco-porsche-911/7890123456.html"):
    return {"title":title,"url":url,"description":"","source":"craigslist-email"}

class RulesTests(unittest.TestCase):
    def test_owner_is_unverified(self):
        a=classify(listing("1984 Porsche 911 - $19,000"))
        self.assertEqual(a["seller_type"],"owner_category")
        self.assertEqual(a["status"],"review")
        self.assertLess(a["score"],90)
    def test_dealer_path_excluded(self):
        a=classify(listing("1984 Porsche 911 $15,000","https://sfbay.craigslist.org/sfc/ctd/d/x/7890123456.html"))
        self.assertEqual(a["status"],"excluded_dealer")
    def test_disguised_dealer(self):
        a=classify(listing("Porsche 911 1984 $19,000 dealer fees apply"))
        self.assertEqual(a["status"],"excluded_dealer")
    def test_out_of_budget(self):
        self.assertEqual(classify(listing("1984 Porsche 911 $30,000"))["status"],"excluded_price")
    def test_later_model(self):
        self.assertEqual(classify(listing("1999 Porsche 911 $12,000"))["status"],"excluded_year")
    def test_parts(self):
        self.assertEqual(classify(listing("Porsche 911 engine only $4000"))["status"],"excluded_parts")
    def test_overlooked_911(self):
        a=classify(listing("1982 911 SC Targa $18,000"))
        self.assertEqual(a["status"],"review")
        self.assertIn("Porsche make inferred; verify photos",a["flags"])
    def test_ambiguous_911_goes_to_review_queue(self):
        a=classify(listing("911 bargain $12000"))
        self.assertEqual(a["status"],"verify_model")
    def test_no_comps_no_market_claim(self):
        r=assess_comparables({"title":"1984 Porsche 911 Coupe","year":1984,"price":18000},[])
        self.assertEqual(r["status"],"insufficient_data")
        self.assertIsNone(r["discount_pct"])
    def test_three_verified_comps_only(self):
        comps=[{"year":1983,"body":"coupe","condition":"driver","sold_price":50000,"verified_sold":True,"source_url":"https://example.org/a"},
               {"year":1984,"body":"coupe","condition":"driver","sold_price":55000,"verified_sold":True,"source_url":"https://example.org/b"},
               {"year":1985,"body":"coupe","condition":"driver","sold_price":60000,"verified_sold":True,"source_url":"https://example.org/c"},
               {"year":1984,"body":"coupe","condition":"driver","sold_price":100000,"verified_sold":False,"source_url":"https://example.org/d"}]
        r=assess_comparables({"title":"1984 Porsche 911","price":18000},comps)
        self.assertEqual(r["median_sold_price"],55000)
        self.assertEqual(r["comps"],3)
        self.assertEqual(r["discount_pct"],67.3)

if __name__=="__main__":unittest.main()
