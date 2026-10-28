import copy,json,os,runpy,tempfile,unittest
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch
from public_contract import CN
from publish_contract import validate_report

class PublishTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,10,28,12,tzinfo=CN)
  self.data={'status':'publisher_today_verified_completeness_unverified','checked_at':self.now.isoformat(),'article':{'source':'茅粉鲁智深','author':'茅粉鲁智深','biz':'Mzg4MzMyMTExMQ==','date':'2026-10-28','published_timestamp':str(int(self.now.timestamp()))}}
 def test_current_report_and_timezone_conversion(self):
  self.assertEqual(validate_report(self.data,self.now),'data/maofen.json')
  self.data['checked_at']='2026-10-28T04:00:00+00:00'
  self.assertEqual(validate_report(self.data,self.now),'data/maofen.json')
 def test_stale_or_future_success_and_identity_rejected(self):
  for section,key,value in [('article','date','2026-10-27'),('article','published_timestamp',str(int((self.now-timedelta(days=1)).timestamp()))),('article','published_timestamp',True),('article','published_timestamp',str(int((self.now+timedelta(hours=1)).timestamp()))),('article','author','other'),(None,'checked_at','2026-10-27T12:00:00+08:00'),(None,'checked_at','2026-10-28T12:00:00'),(None,'status','no_today_verified_quotes')]:
   with self.subTest(key=key,value=value):
    d=copy.deepcopy(self.data);(d[section] if section else d)[key]=value
    with self.assertRaises(ValueError):validate_report(d,self.now)
 def test_failed_result_cannot_read_token_or_make_network_request(self):
  script=Path(__file__).resolve().parents[1]/'publish.py'
  with tempfile.TemporaryDirectory() as folder:
   Path(folder,'result.json').write_text(json.dumps({'status':'no_today_verified_quotes'}))
   previous=os.getcwd()
   try:
    os.chdir(folder)
    with patch('urllib.request.urlopen') as network,patch.dict(os.environ,{},clear=True):
     with self.assertRaises(ValueError):runpy.run_path(str(script))
     network.assert_not_called()
   finally:os.chdir(previous)
