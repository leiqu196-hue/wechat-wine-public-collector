import importlib,json,os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import AsyncMock,patch

class SearchFlowTests(unittest.IsolatedAsyncioTestCase):
 async def exercise(self,rows,state,goto_error=None,launch_error=None):
  page=types.SimpleNamespace(url='https://weixin.sogou.com/weixin',set_default_timeout=lambda value:None,goto=AsyncMock(side_effect=goto_error),evaluate=AsyncMock(side_effect=[rows,state,rows,state]))
  browser=types.SimpleNamespace(new_page=AsyncMock(return_value=page),close=AsyncMock())
  context=types.SimpleNamespace(firefox=types.SimpleNamespace(launch=AsyncMock(return_value=browser,side_effect=launch_error)))
  manager=unittest.mock.MagicMock();manager.__aenter__=AsyncMock(return_value=context);manager.__aexit__=AsyncMock(return_value=False)
  module=types.ModuleType('playwright.async_api');module.async_playwright=lambda:manager
  parent=types.ModuleType('playwright');parent.async_api=module
  search=importlib.import_module('search_collect')
  previous=os.getcwd()
  with tempfile.TemporaryDirectory() as folder:
   try:
    os.chdir(folder)
    with patch.dict(sys.modules,{'playwright':parent,'playwright.async_api':module}),patch.dict(os.environ,{'WINE_SOURCE':'国酒酱香'}):
     if launch_error:
      with self.assertRaises(RuntimeError):await search.main()
     else:self.assertFalse(await search.main())
    result=json.loads(Path('result.json').read_text())
   finally:os.chdir(previous)
  return result,page,browser
 async def test_empty_search_records_both_queries(self):
  result,page,browser=await self.exercise([],{'verification':False,'has_listing':True})
  self.assertEqual([a['reason'] for a in result['attempts']],['empty_listing']*2)
  self.assertEqual(page.goto.await_count,2);browser.close.assert_awaited_once()
 async def test_verification_stops_without_next_query(self):
  result,page,_=await self.exercise([],{'verification':True,'has_listing':False})
  self.assertEqual(result['attempts'][0]['reason'],'verification_required');self.assertEqual(page.goto.await_count,1)
 async def test_navigation_failure_still_writes_diagnostic(self):
  result,_,browser=await self.exercise([],{},goto_error=RuntimeError('network'))
  self.assertEqual(result['attempts'][0]['stage'],'search_runtime');browser.close.assert_awaited_once()
 async def test_launch_failure_still_writes_diagnostic(self):
  result,_,_=await self.exercise([],{},launch_error=RuntimeError('launch'))
  self.assertEqual(result['attempts'][0]['stage'],'collector_runtime')
 async def test_current_original_success_retains_listing_diagnostic(self):
  from public_contract import CN
  from datetime import datetime
  now=datetime.now(CN)
  row={'title':f'{now.month}月{now.day}日行情','url':'https://weixin.sogou.com/link?url=public'}
  page=types.SimpleNamespace(url='https://weixin.sogou.com/weixin',set_default_timeout=lambda v:None,goto=AsyncMock(),evaluate=AsyncMock(side_effect=[[row],{'verification':False,'has_listing':True}]))
  browser=types.SimpleNamespace(new_page=AsyncMock(return_value=page),close=AsyncMock())
  manager=unittest.mock.MagicMock();manager.__aenter__=AsyncMock(return_value=types.SimpleNamespace(firefox=types.SimpleNamespace(launch=AsyncMock(return_value=browser))));manager.__aexit__=AsyncMock(return_value=False)
  module=types.ModuleType('playwright.async_api');module.async_playwright=lambda:manager
  search=importlib.import_module('search_collect')
  article={'author':'国酒酱香','biz':'MzI2MTY5ODk5Ng==','mid':'2247000000','idx':'1','published_timestamp':str(int(now.timestamp())),'body':'public quotation '*20,'tables':[[['产品','100','99','-1']]*63]}
  previous=os.getcwd()
  with tempfile.TemporaryDirectory() as folder:
   try:
    os.chdir(folder)
    with patch.dict(sys.modules,{'playwright.async_api':module}),patch.dict(os.environ,{'WINE_SOURCE':'国酒酱香'}),patch.object(search,'inspect_search_link',AsyncMock(return_value=article)):
     self.assertTrue(await search.main())
    result=json.loads(Path('result.json').read_text())
    self.assertEqual(result['attempts'][0]['reason'],'current_candidates')
    self.assertEqual(result['article']['date'],now.date().isoformat())
   finally:os.chdir(previous)
 async def test_original_verification_does_not_wait_for_content(self):
  from discover import inspect
  page=types.SimpleNamespace(goto=AsyncMock(),evaluate=AsyncMock(return_value=True),locator=unittest.mock.Mock())
  with self.assertRaisesRegex(ValueError,'verification_required'):await inspect(page,'国酒酱香','https://weixin.sogou.com/link?url=public')
  page.locator.assert_not_called()
 async def test_original_verification_stops_before_second_query(self):
  from public_contract import CN
  from datetime import datetime
  now=datetime.now(CN)
  rows=[{'title':f'{now.month}月{now.day}日行情','url':'https://weixin.sogou.com/link?url=public','listing_index':0}]
  import search_collect
  with patch.object(search_collect,'inspect_search_link',AsyncMock(side_effect=ValueError('verification_required'))) as reader:
   result,page,_=await self.exercise(rows,{'verification':False,'has_listing':True})
  self.assertEqual(page.goto.await_count,1)
  reader.assert_awaited_once()
  self.assertTrue(any(a.get('reason')=='verification_required' for a in result['attempts']))
 async def test_same_tab_failure_does_not_reuse_listing_rows(self):
  from public_contract import CN
  from datetime import datetime
  import search_collect
  now=datetime.now(CN)
  rows=[{'title':f'{now.month}月{now.day}日行情','url':f'https://weixin.sogou.com/link?url={i}','listing_index':i} for i in range(2)]
  async def leave_listing(page,source,row):
   page.url='https://mp.weixin.qq.com/s'
   raise ValueError('publisher mismatch')
  with patch.object(search_collect,'inspect_search_link',AsyncMock(side_effect=leave_listing)) as reader:
   result,page,_=await self.exercise(rows,{'verification':False,'has_listing':True})
  # First query reads row 0 and consumes its listing. The second query skips the
  # seen URL and reads row 1; it must not read row 1 on the vanished first listing.
  self.assertEqual(reader.await_count,2)
  self.assertEqual([a['stage'] for a in result['attempts']],['search_listing','current_original','search_listing','current_original'])
