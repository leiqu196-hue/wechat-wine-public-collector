"""Anonymous public publisher diagnostic. No login, cookies, CAPTCHA solving or private data."""
import asyncio,json,re,os
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.parse import urlsplit,parse_qs,urlencode
from playwright.async_api import async_playwright
CN=timezone(timedelta(hours=8));BIZ='Mzk0NzI1MjY4Ng==';AUTHOR='今日酒价'
ALBUM='https://mp.weixin.qq.com/mp/appmsgalbum?'+urlencode({'__biz':BIZ,'action':'getalbum','album_id':'4328328528879271941','is_reverse':'1'})
def article_url(value):
 p=urlsplit(value);q=parse_qs(p.query)
 if p.hostname!='mp.weixin.qq.com' or p.path!='/s' or p.username or p.password or p.port not in (None,80,443):raise ValueError('untrusted article origin')
 if q.get('__biz')!=[BIZ] or any(len(q.get(k,[]))!=1 for k in ['mid','idx','sn']):raise ValueError('untrusted article identity')
 if not re.fullmatch(r'\d{1,20}',q['mid'][0]) or not re.fullmatch(r'[1-9]\d?',q['idx'][0]) or not re.fullmatch(r'[a-f0-9]{32}',q['sn'][0]):raise ValueError('invalid article identity')
 clean={k:q[k][0] for k in ['__biz','mid','idx','sn']}
 if 'chksm' in q:
  if len(q['chksm'])!=1 or not re.fullmatch(r'[a-f0-9]{64,128}',q['chksm'][0]):raise ValueError('invalid checksum')
  clean['chksm']=q['chksm'][0]
 return 'https://mp.weixin.qq.com/s?'+urlencode(clean)
def verify(d,today):
 if d['author']!=AUTHOR or d['biz']!=BIZ:raise ValueError('publisher mismatch')
 match=re.search(r'(20\d\d)年(\d\d?)月(\d\d?)日',d['published_at'])
 if not match or datetime(*map(int,match.groups()),tzinfo=CN).date().isoformat()!=today:raise ValueError('not today')
 expected=[];headers=0
 for table in d['tables']:
  for i,row in enumerate(table):
   if row not in (['品名','规格','昨日行情','今日行情'],['品名','产品参数','单瓶价']):continue
   headers+=1
   for cells in table[i+1:]:
    if len(cells)!=len(row):continue
    if re.fullmatch(r'\d{1,6}(?:\s*[⬆⬇↑↓])?',cells[-1]):expected.append(cells)
 if headers<10 or not 100<=len(expected)<=500:raise ValueError('incomplete full quotation')
 d['coverage']={'price_rows':len(expected),'price_tables':headers};d['date']=today
 return d
async def run():
 today=datetime.now(CN).date().isoformat();attempts=[]
 async with async_playwright() as pw:
  for engine in ['chromium','firefox']:
   browser=None;page=None;stage='launch'
   try:
    opts={'headless':False,'timeout':20000}
    if engine=='chromium':opts['chromium_sandbox']=True
    browser=await getattr(pw,engine).launch(**opts);page=await browser.new_page();page.set_default_timeout(12000)
    stage='album_navigation';await page.goto(ALBUM,wait_until='domcontentloaded',timeout=25000)
    stage='album_identity';listing=await page.evaluate("""()=>({biz:window.biz,author:document.querySelector('.album__author-name')?.textContent.trim(),rows:[...document.querySelectorAll('li[data-link]')].slice(0,3).map(e=>({title:e.dataset.title,url:e.dataset.link}))})""")
    if listing['biz']!=BIZ or listing['author']!=AUTHOR:raise ValueError('album publisher mismatch')
    prefix=f'{int(today[5:7])}月{int(today[8:])}日'
    candidates=[r for r in listing['rows'] if prefix in r['title']]
    if not candidates:raise ValueError('no current daily article')
    stage='article_navigation';url=article_url(candidates[0]['url']);await page.goto(url,wait_until='domcontentloaded',timeout=25000)
    stage='article_content';await page.locator('#js_content').wait_for(state='visible',timeout=12000)
    data=await page.evaluate("""()=>({title:document.querySelector('#activity-name')?.innerText.trim(),author:document.querySelector('#js_name')?.innerText.trim(),biz:window.biz,published_at:document.querySelector('#publish_time')?.innerText.trim(),body:document.querySelector('#js_content').innerText,tables:[...document.querySelectorAll('#js_content table')].map(t=>[...t.rows].map(r=>[...r.cells].map(c=>c.innerText.trim())))})""")
    if len(data['body'])>80000:raise ValueError('body size limit')
    stage='article_validation';data.update(source_url=url,engine=engine,source=AUTHOR);data=verify(data,today)
    out={'status':'publisher_today_verified_completeness_unverified','checked_at':datetime.now(CN).isoformat(),'article':data,'attempts':attempts}
    Path('result.json').write_text(json.dumps(out,ensure_ascii=False));print(json.dumps({'status':'publisher_today_verified_completeness_unverified','date':today,'engine':engine,'coverage':data['coverage'],'title':data['title']},ensure_ascii=False));return
   except Exception as e:
    diagnostic={'engine':engine,'stage':stage,'status':'unavailable','error':type(e).__name__}
    if isinstance(e,ValueError):diagnostic['reason']=str(e)[:120]
    if page:
     try:
      diagnostic['page']=await asyncio.wait_for(page.evaluate("""()=>({title:document.title.slice(0,160),has_content:!!document.querySelector('#js_content'),has_album:!!document.querySelector('li[data-link]'),verification:document.body.innerText.includes('环境异常')||document.body.innerText.includes('完成验证'),biz:window.biz||null,author:document.querySelector('.album__author-name')?.textContent.trim()||null})"""),3)
     except Exception:pass
    attempts.append(diagnostic)
   finally:
    if browser:await browser.close()
 out={'status':'no_today_verified_quotes','checked_at':datetime.now(CN).isoformat(),'attempts':attempts};Path('result.json').write_text(json.dumps(out));print(json.dumps(out));raise SystemExit(1)
if __name__=='__main__':asyncio.run(asyncio.wait_for(run(),150))
