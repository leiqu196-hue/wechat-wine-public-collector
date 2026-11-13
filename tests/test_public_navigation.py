import asyncio,types,unittest
from unittest.mock import AsyncMock,MagicMock,patch
from discover import inspect
from public_navigation import PublicPageError,VERIFICATION_JS,page_error
from search_collect import inspect_search_link


class PublicNavigationTests(unittest.IsolatedAsyncioTestCase):
 async def test_navigation_timeout_preserves_stage_without_query(self):
  page=types.SimpleNamespace(url='https://weixin.sogou.com/link?token=DO_NOT_LOG',goto=AsyncMock(side_effect=TimeoutError('secret URL')),evaluate=AsyncMock(return_value=False))
  with self.assertRaises(PublicPageError) as raised:await inspect(page,'易茅时价','https://weixin.sogou.com/link?token=DO_NOT_LOG')
  self.assertEqual(raised.exception.diagnostic,{'stage':'original_navigation','error':'TimeoutError','page_host':'weixin.sogou.com','page_path_kind':'/link'})
  self.assertNotIn('DO_NOT_LOG',str(raised.exception)+str(raised.exception.diagnostic))

 async def test_content_timeout_is_distinct(self):
  page=types.SimpleNamespace(url='https://mp.weixin.qq.com/s?signature=DO_NOT_LOG',goto=AsyncMock(),evaluate=AsyncMock(return_value=False),locator=MagicMock(return_value=types.SimpleNamespace(wait_for=AsyncMock(side_effect=TimeoutError()))))
  with self.assertRaises(PublicPageError) as raised:await inspect(page,'易茅时价',None)
  self.assertEqual(raised.exception.diagnostic['stage'],'original_content')
  self.assertEqual(raised.exception.diagnostic['page_host'],'mp.weixin.qq.com')
  page.goto.assert_not_awaited()

 async def test_asynchronous_verification_stops_after_content_wait(self):
  page=types.SimpleNamespace(url='https://mp.weixin.qq.com/s',evaluate=AsyncMock(side_effect=[False,True]),locator=MagicMock(return_value=types.SimpleNamespace(wait_for=AsyncMock(side_effect=TimeoutError()))))
  with self.assertRaisesRegex(ValueError,'verification_required'):await inspect(page,'易茅时价',None)

 async def test_navigation_error_detects_verification(self):
  page=types.SimpleNamespace(evaluate=AsyncMock(return_value=True))
  with self.assertRaisesRegex(ValueError,'verification_required'):await page_error(page,'original_navigation',TimeoutError())
  for text in ['环境异常','完成验证','验证码','访问过于频繁','/antispider/']:
   self.assertIn(text,VERIFICATION_JS)

 def search_fixture(self,target='_blank'):
  original=types.SimpleNamespace(wait_for_load_state=AsyncMock(),close=AsyncMock())
  link=types.SimpleNamespace(evaluate=AsyncMock(return_value='https://weixin.sogou.com/link?url=public'),get_attribute=AsyncMock(return_value=target),click=AsyncMock())
  item=types.SimpleNamespace(locator=MagicMock(return_value=link))
  listing=types.SimpleNamespace(nth=MagicMock(return_value=item))
  future=asyncio.get_running_loop().create_future();future.set_result(original)
  opened=types.SimpleNamespace(value=future)
  manager=MagicMock();manager.__aenter__=AsyncMock(return_value=opened);manager.__aexit__=AsyncMock(return_value=False)
  page=types.SimpleNamespace(locator=MagicMock(return_value=listing),expect_popup=MagicMock(return_value=manager),wait_for_load_state=AsyncMock())
  row={'url':'https://weixin.sogou.com/link?url=public','listing_index':0}
  return page,original,link,row

 async def test_normal_click_reads_and_closes_popup_without_raw_goto(self):
  page,original,link,row=self.search_fixture()
  with patch('search_collect.inspect',AsyncMock(return_value={'author':'易茅时价'})) as reader:
   self.assertEqual(await inspect_search_link(page,'易茅时价',row),{'author':'易茅时价'})
   reader.assert_awaited_once_with(original,'易茅时价',None)
  link.click.assert_awaited_once();original.close.assert_awaited_once()

 async def test_popup_verification_propagates_and_closes(self):
  page,original,link,row=self.search_fixture()
  with patch('search_collect.inspect',AsyncMock(side_effect=ValueError('verification_required'))):
   with self.assertRaisesRegex(ValueError,'verification_required'):await inspect_search_link(page,'易茅时价',row)
  original.close.assert_awaited_once();link.click.assert_awaited_once()

 async def test_changed_link_is_never_clicked(self):
  page,original,link,row=self.search_fixture()
  link.evaluate.return_value='https://unrelated.example/s'
  with self.assertRaisesRegex(ValueError,'search link changed'):await inspect_search_link(page,'易茅时价',row)
  link.click.assert_not_awaited()

 async def test_same_tab_link_uses_normal_click_without_popup(self):
  page,original,link,row=self.search_fixture(target=None)
  with patch('search_collect.inspect',AsyncMock(return_value={'author':'易茅时价'})) as reader:
   await inspect_search_link(page,'易茅时价',row)
   reader.assert_awaited_once_with(page,'易茅时价',None)
  link.click.assert_awaited_once();page.expect_popup.assert_not_called()
  original.close.assert_not_awaited()

 async def test_close_failure_does_not_mask_verification_stop(self):
  page,original,link,row=self.search_fixture()
  original.close.side_effect=RuntimeError('browser closing')
  with patch('search_collect.inspect',AsyncMock(side_effect=ValueError('verification_required'))):
   with self.assertRaisesRegex(ValueError,'verification_required'):await inspect_search_link(page,'易茅时价',row)
  link.click.assert_awaited_once();original.close.assert_awaited_once()

 async def test_same_tab_failure_propagates_without_second_click(self):
  page,original,link,row=self.search_fixture(target='_self')
  with patch('search_collect.inspect',AsyncMock(side_effect=ValueError('publisher mismatch'))):
   with self.assertRaisesRegex(ValueError,'publisher mismatch'):await inspect_search_link(page,'易茅时价',row)
  link.click.assert_awaited_once();page.expect_popup.assert_not_called()
  original.close.assert_not_awaited()


if __name__=='__main__':unittest.main()
