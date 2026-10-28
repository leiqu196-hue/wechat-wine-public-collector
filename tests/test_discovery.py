import unittest
from datetime import date
from discovery_contract import current_titles,listing_diagnostic

class DiscoveryTests(unittest.TestCase):
 def test_current_article_after_first_three_and_padded_date(self):
  rows=[{'title':'广告'}]*3+[{'title':'2026年10月028日'}, {'title':'2026年10月28日茅台行情价'}, {'title':'10月28日行情'}]
  self.assertEqual(len(current_titles(rows,date(2026,10,28))),2)
 def test_day_month_and_year_boundaries(self):
  rows=[{'title':t} for t in ['11月1日','1月11日','2025年1月1日',None,'01月01日']]
  self.assertEqual(current_titles(rows,date(2026,1,1)),[rows[-1]])
 def test_empty_stale_changed_markup_and_verification_are_distinct(self):
  for rows,verify,markup,reason in [([],False,True,'empty_listing'),([],False,False,'listing_markup_missing'),([],True,False,'verification_required'),([{'title':'10月27日'}],False,True,'no_current_title_in_bounded_listing')]:
   with self.subTest(reason=reason):
    d=listing_diagnostic(rows,date(2026,10,28),'search_listing',verify,markup)
    self.assertEqual(d['reason'],reason)
    self.assertEqual(d['current_candidates'],0)
 def test_diagnostics_bounded_and_exclude_urls(self):
  d=listing_diagnostic([{'title':'a'*200,'url':'secret'}]*40,date(2026,10,28),'album_candidates')
  self.assertEqual(len(d['titles']),20);self.assertEqual(len(d['titles'][0]),160);self.assertNotIn('secret',str(d))
