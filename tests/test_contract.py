import copy,unittest
from datetime import datetime
from public_contract import CN,current_article
class ContractTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,10,19,9,0,tzinfo=CN)
  self.article={'author':'易茅时价','biz':'MzYyMTQ3NTQ1OQ==','mid':'2247530009','idx':'1','published_timestamp':str(int(datetime(2026,10,19,6,0,tzinfo=CN).timestamp())),'body':'Public original text. '*10,'tables':[[['Product','100','99','-1'] for _ in range(100)]]}
 def test_native_identity_permalink_without_invented_sn(self):
  result=current_article(self.article,'易茅时价',self.now)
  self.assertEqual(result['date'],'2026-10-19');self.assertNotIn('&sn=',result['source_url']);self.assertIn('mid=2247530009',result['source_url']);self.assertEqual(result['link_identity_method'],'native_biz_mid_idx')
 def test_wrong_identity_stale_or_missing_timestamp_rejected(self):
  for key,value in [('author','other'),('biz','other'),('mid','not-a-mid'),('idx','0'),('published_timestamp',True),('published_timestamp','1790028000')]:
   with self.subTest(key=key):
    d=copy.deepcopy(self.article);d[key]=value
    with self.assertRaises(ValueError):current_article(d,'易茅时价',self.now)
 def test_future_publication_rejected(self):
  self.article['published_timestamp']=str(int(datetime(2026,10,19,10,0,tzinfo=CN).timestamp()))
  with self.assertRaises(ValueError):current_article(self.article,'易茅时价',self.now)
 def test_private_input_permalink_is_never_copied(self):
  self.article['source_url']='https://evil.test/?pass_ticket=private'
  self.assertNotIn('private',current_article(self.article,'易茅时价',self.now)['source_url'])
 def test_incomplete_sized_original_is_not_published(self):
  self.article['tables'][0].pop()
  with self.assertRaises(ValueError):current_article(self.article,'易茅时价',self.now)
if __name__=='__main__':unittest.main()
