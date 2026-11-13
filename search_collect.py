"""Anonymous daily original discovery for fixed public publishers; server verifies full coverage."""
import asyncio,json,os,re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlencode,urlsplit
from discovery_contract import current_titles,listing_diagnostic
from discover import inspect
from public_contract import CN,CONFIG,current_article
from public_navigation import page_error


async def inspect_search_link(page,source,row):
 # Follow the publisher-search site's normal link interaction. A raw goto(href)
 # skips the site's click handler and may leave the browser on an intermediary.
 link=page.locator('.news-list li').nth(row['listing_index']).locator('h3 a')
 if await link.evaluate('(a)=>a.href')!=row['url']:raise ValueError('search link changed')
 article_page=page
 try:
  try:
   if await link.get_attribute('target')=='_blank':
    async with page.expect_popup(timeout=25000) as opened:
     await link.click(timeout=12000)
    article_page=await opened.value
   else:await link.click(timeout=12000)
   await article_page.wait_for_load_state('domcontentloaded',timeout=25000)
  except Exception as exc:raise await page_error(article_page,'original_link_navigation',exc) from exc
  return await inspect(article_page,source,None)
 finally:
  if article_page is not page:
   # Cleanup must never mask verification_required and allow another attempt.
   try:await article_page.close()
   except Exception:pass


async def run():
 from playwright.async_api import async_playwright
 source=os.environ['WINE_SOURCE'];biz,term=CONFIG[source];now=datetime.now(CN);attempts=[];reads=0;seen=set()
 queries=['"'+term+'" "'+str(now.month)+'月"',('"茅台酒'+str(now.month)+'月'+str(now.day)+'日" "行情价"') if source=='国酒酱香' else '"易茅时价" "'+str(now.month)+'月'+str(now.day)+'日"']
 async with async_playwright() as pw:
  browser=await pw.firefox.launch(headless=False,timeout=20000)
  try:
   page=await browser.new_page();page.set_default_timeout(12000)
   for query in queries:
    await page.goto('https://weixin.sogou.com/weixin?'+urlencode({'type':2,'query':query,'ie':'utf8'}),wait_until='domcontentloaded',timeout=25000)
    listing_url=page.url
    candidates=await page.evaluate("""()=>[...document.querySelectorAll('.news-list li')].slice(0,10).map((li,listing_index)=>({title:li.querySelector('h3')?.innerText,url:li.querySelector('h3 a')?.href,listing_index}))""")
    state=await page.evaluate("""()=>({verification:document.body.innerText.includes('验证码')||document.body.innerText.includes('访问过于频繁')||document.body.innerText.includes('完成验证'),has_listing:!!document.querySelector('.news-list')})""")
    attempts.append(dict(listing_diagnostic(candidates,now.date(),'search_listing',state['verification'],state['has_listing']),query_index=queries.index(query)))
    if state['verification']:break
    candidates=current_titles(candidates,now.date())
    for row in candidates:
     if reads>=3:break
     url=row.get('url') or ''
     parsed=urlsplit(url)
     if parsed.hostname!='weixin.sogou.com' or parsed.path!='/link' or parsed.scheme not in ('http','https') or parsed.username or parsed.password or parsed.port not in (None,80,443) or len(url)>6000 or url in seen:continue
     seen.add(url);reads+=1
     try:
      article=current_article(await inspect_search_link(page,source,row),source,now)
      report={'status':'publisher_today_verified_completeness_unverified','checked_at':datetime.now(CN).isoformat(),'article':article,'attempts':attempts}
      Path('result.json').write_text(json.dumps(report,ensure_ascii=False));print(json.dumps({'status':report['status'],'source':source,'date':article['date'],'rows':article['coverage']['price_rows']}));return True
     except Exception as exc:
      attempts.append({'stage':'current_original','error':type(exc).__name__,'reason':str(exc)[:100] if isinstance(exc,ValueError) else 'public original unavailable',**getattr(exc,'diagnostic',{})})
      if str(exc)=='verification_required':raise
      # A same-tab link consumed this listing. Never reuse stale row indices or
      # reload/retry the original; the next bounded query will load a new listing.
      if page.url!=listing_url:break
  except Exception as exc:
   attempts.append({'stage':'search_runtime','error':type(exc).__name__})
  finally:await browser.close()
 Path('result.json').write_text(json.dumps({'status':'no_today_verified_quotes','checked_at':datetime.now(CN).isoformat(),'source':source,'attempts':attempts}));return False
async def main():
 try:return await asyncio.wait_for(run(),180)
 except Exception as exc:
  Path('result.json').write_text(json.dumps({'status':'no_today_verified_quotes','source':os.environ.get('WINE_SOURCE'),'checked_at':datetime.now(CN).isoformat(),'attempts':[{'stage':'collector_runtime','error':type(exc).__name__}]}))
  raise
if __name__=='__main__':raise SystemExit(0 if asyncio.run(main()) else 1)
