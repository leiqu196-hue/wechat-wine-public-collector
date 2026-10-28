"""Anonymous public publisher diagnostic. No login, cookies, CAPTCHA solving or private data."""
import asyncio,json,re,os
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.parse import urlsplit,parse_qs,urlencode
from discovery_contract import current_titles,listing_diagnostic
CN=timezone(timedelta(hours=8))
CONFIG={'今日酒价':('Mzk0NzI1MjY4Ng==','4328328528879271941'),'茅粉鲁智深':('Mzg4MzMyMTExMQ==','4475132542408294400')}
AUTHOR=os.environ.get('WINE_SOURCE','今日酒价')
BIZ,ALBUM_ID=CONFIG[AUTHOR]
ALBUM='https://mp.weixin.qq.com/mp/appmsgalbum?'+urlencode({'__biz':BIZ,'action':'getalbum','album_id':ALBUM_ID,'is_reverse':'1'})
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
 stamp=d.get('published_timestamp')
 if str(stamp).isdigit() and 1000000000<int(stamp)<9999999999:
  published_date=datetime.fromtimestamp(int(stamp),CN).date().isoformat()
  d['publication_date_method']='original_page_timestamp'
 elif match:
  published_date=datetime(*map(int,match.groups()),tzinfo=CN).date().isoformat()
  d['publication_date_method']='original_page_chinese_date'
 else:raise ValueError('unrecognized original publication date')
 if published_date!=today:raise ValueError('not today')
 if match and datetime(*map(int,match.groups()),tzinfo=CN).date().isoformat()!=published_date:raise ValueError('publication metadata conflict')
 if AUTHOR=='茅粉鲁智深':
  d['coverage']=verify_maofen_tables(d['tables'],today);d['date']=today;return d
 expected=[];headers=0
 for table in d['tables']:
  potential=[r for r in table if len(r) in (3,4) and r[0] and re.search(r'\d',r[1]) and re.search(r'\d',r[-1])]
  if potential and not any(r in (['品名','规格','昨日行情','今日行情'],['品名','产品参数','单瓶价']) for r in table):raise ValueError('unknown quotation header')
  for i,row in enumerate(table):
   if row not in (['品名','规格','昨日行情','今日行情'],['品名','产品参数','单瓶价']):continue
   headers+=1
   for cells in table[i+1:]:
    if len(cells)!=len(row):
     if cells in potential:raise ValueError('unexplained quotation row')
     continue
    if re.fullmatch(r'\d{1,6}(?:\s*[⬆⬇↑↓])?',cells[-1]):expected.append(cells)
    elif cells in potential:raise ValueError('unsupported quotation price')
 if headers<10 or not 100<=len(expected)<=500:raise ValueError('incomplete full quotation')
 d['coverage']={'price_rows':len(expected),'price_tables':headers};d['date']=today
 return d
def verify_maofen_tables(tables,today):
 day=datetime.fromisoformat(today).date();previous=(day-timedelta(days=1)).day
 count=0;prices=0;daily=0;reference=0
 for table in tables:
  if not table:continue
  headers=[i for i,r in enumerate(table) if r and r[0]=='品名']
  if not headers:
   if any(len(r)>=3 and any(re.search(r'\d',v) for v in r[1:3]) for r in table):raise ValueError('unknown quotation table')
   continue
  if len(headers)!=1:raise ValueError('ambiguous quotation table')
  i=headers[0];header=table[i]
  if header==['品名','行情价','零售价','涨跌']:
   mode='reference'
   if len(table[0])!=2 or table[0][1]!=f'{day.month}月{day.day}日':raise ValueError('stale section date')
  elif header==['品名',f'{previous}日',f'{day.day}日','涨跌']:
   mode='daily'
   if len(table[0])!=1 or not table[0][0].startswith(f'{day.month}月{day.day}日茅台行情价'):raise ValueError('stale daily table date')
  else:raise ValueError('unknown quotation header')
  count+=1
  for r in table[i+1:]:
   if len(r)==1 and (r[0].startswith('数据来源于茅粉鲁智深') or r[0].startswith('※ 茅台酒价格')):continue
   if len(r)!=4 or not r[0] or not re.fullmatch(r'\d{1,6}',r[1]) or not re.fullmatch(r'\d{1,6}',r[2]) or not re.fullmatch(r'[+-]?\d{1,6}',r[3]):raise ValueError('unparsed quotation row')
   prices+=1
   if mode=='daily':daily+=1
   else:reference+=1
 if not 5<=count<=30 or not 50<=prices<=500 or not daily or not reference:raise ValueError('incomplete quotation')
 return {'price_rows':prices,'price_tables':count,'daily_price_rows':daily,'reference_price_rows':reference}
async def run():
 from playwright.async_api import async_playwright
 today=datetime.now(CN).date().isoformat();attempts=[]
 async with async_playwright() as pw:
  for engine in ['firefox','chromium']:
   browser=None;page=None;data=None;stage='launch'
   try:
    opts={'headless':False,'timeout':20000}
    if engine=='chromium':opts['chromium_sandbox']=True
    browser=await getattr(pw,engine).launch(**opts);page=await browser.new_page();page.set_default_timeout(12000)
    stage='album_navigation';await page.goto(ALBUM,wait_until='domcontentloaded',timeout=25000)
    stage='album_identity';listing=await page.evaluate("""()=>({biz:window.biz,author:document.querySelector('.album__author-name')?.textContent.trim(),verification:document.body.innerText.includes('环境异常')||document.body.innerText.includes('完成验证'),rows:[...document.querySelectorAll('li[data-link]')].slice(0,20).map(e=>({title:e.dataset.title,url:e.dataset.link}))})""")
    if listing['biz']!=BIZ or listing['author']!=AUTHOR:raise ValueError('album publisher mismatch')
    stage='album_candidates'
    attempts.append(dict(listing_diagnostic(listing['rows'],datetime.fromisoformat(today).date(),stage,listing.get('verification',False)),engine=engine))
    if listing.get('verification'):break
    candidates=current_titles(listing['rows'],datetime.fromisoformat(today).date())
    if not candidates:raise ValueError('no current daily article')
    stage='article_navigation';url=article_url(candidates[0]['url']);await page.goto(url,wait_until='domcontentloaded',timeout=25000)
    stage='article_content';await page.locator('#js_content').wait_for(state='visible',timeout=12000)
    data=await page.evaluate("""()=>({title:document.querySelector('#activity-name')?.innerText.trim(),author:document.querySelector('#js_name')?.innerText.trim(),biz:window.biz,published_at:document.querySelector('#publish_time')?.innerText.trim(),published_timestamp:window.ct||null,body:document.querySelector('#js_content').innerText,tables:[...document.querySelectorAll('#js_content table')].map(t=>[...t.rows].map(r=>[...r.cells].map(c=>c.innerText.trim())))})""")
    if len(data['body'])>80000:raise ValueError('body size limit')
    stage='article_validation';data.update(source_url=url,engine=engine,source=AUTHOR);data=verify(data,today)
    out={'status':'publisher_today_verified_completeness_unverified','checked_at':datetime.now(CN).isoformat(),'article':data,'attempts':attempts}
    Path('result.json').write_text(json.dumps(out,ensure_ascii=False));print(json.dumps({'status':'publisher_today_verified_completeness_unverified','date':today,'engine':engine,'coverage':data['coverage'],'title':data['title']},ensure_ascii=False));return
   except Exception as e:
    diagnostic={'engine':engine,'stage':stage,'status':'unavailable','error':type(e).__name__}
    if isinstance(e,ValueError):diagnostic['reason']=str(e)[:120]
    if data and data.get('author')==AUTHOR and data.get('biz')==BIZ:
     diagnostic['original_metadata']={k:data.get(k) for k in ['title','published_at','published_timestamp']}
    if page:
     try:
      diagnostic['page']=await asyncio.wait_for(page.evaluate("""()=>({title:document.title.slice(0,160),has_content:!!document.querySelector('#js_content'),has_album:!!document.querySelector('li[data-link]'),verification:document.body.innerText.includes('环境异常')||document.body.innerText.includes('完成验证'),biz:window.biz||null,author:document.querySelector('.album__author-name')?.textContent.trim()||null})"""),3)
     except Exception:pass
    attempts.append(diagnostic)
    if diagnostic.get('page',{}).get('verification'):break
   finally:
    if browser:await browser.close()
 out={'status':'no_today_verified_quotes','checked_at':datetime.now(CN).isoformat(),'attempts':attempts};Path('result.json').write_text(json.dumps(out));print(json.dumps(out));raise SystemExit(1)
if __name__=='__main__':asyncio.run(asyncio.wait_for(run(),150))
