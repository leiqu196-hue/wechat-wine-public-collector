"""Bounded manual inspection of public publisher pages. Never logs in or publishes prices."""
import asyncio,json,os,re,base64,hashlib
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,urlencode
from playwright.async_api import async_playwright
SOURCES={'酒业网','国酒酱香','易茅时价','茅粉鲁智深'}
def article_input(url):
 p=urlsplit(url);q=parse_qs(p.query)
 if p.scheme!='https' or p.hostname!='mp.weixin.qq.com' or p.path!='/s' or p.username or p.password or p.port not in (None,443):raise ValueError('public article origin')
 if set(q)-{'__biz','mid','idx','sn','chksm','src','timestamp','ver','signature','new'}:raise ValueError('unexpected article query')
 if len(url)>4000:raise ValueError('article URL size')
 return url
async def inspect(page,expected,url):
 await page.goto(url,wait_until='domcontentloaded',timeout=25000)
 await page.locator('#js_content').wait_for(state='visible',timeout=12000)
 d=await page.evaluate("""()=>({title:document.querySelector('#activity-name')?.innerText.trim(),author:document.querySelector('#js_name')?.innerText.trim(),biz:window.biz||null,mid:String(window.mid||window.appmsgid||''),idx:String(window.idx||window.itemidx||''),sn:window.sn||null,published_at:document.querySelector('#publish_time')?.innerText.trim(),published_timestamp:window.ct||null,canonical:window.msg_link||document.querySelector('meta[property="og:url"]')?.content||null,body:document.querySelector('#js_content').innerText,tables:[...document.querySelectorAll('#js_content table')].map(t=>[...t.rows].map(r=>[...r.cells].map(c=>c.innerText.trim()))),images:[...document.querySelectorAll('#js_content img')].map(e=>e.getAttribute('data-src')||e.src).filter(u=>u&&u.startsWith('https://mmbiz.qpic.cn/')).slice(0,100),album_ids:[...new Set([...document.documentElement.innerHTML.matchAll(/album_id[^0-9]{1,25}([0-9]{12,25})/g)].map(m=>m[1]))].slice(0,12)})""")
 if d['author']!=expected:raise ValueError('publisher mismatch')
 if not isinstance(d['biz'],str) or not re.fullmatch(r'[A-Za-z0-9+/=]{8,80}',d['biz']):raise ValueError('publisher identity absent')
 if len(d['body'])>80000 or len(d['tables'])>180:raise ValueError('public content size')
 if d['canonical']:
  try:
   cp=urlsplit(d['canonical']);q=parse_qs(cp.query)
   if cp.hostname=='mp.weixin.qq.com' and cp.path=='/s' and q.get('__biz')==[d['biz']]:
    for k in ['mid','idx','sn']:
     if not d.get(k) and len(q.get(k,[]))==1:d[k]=q[k][0]
  except ValueError:pass
 d.pop('canonical',None)
 if d['mid'].isdigit() and d['idx'].isdigit() and isinstance(d['sn'],str) and re.fullmatch('[a-fA-F0-9]{32}',d['sn']):d['source_url']='https://mp.weixin.qq.com/s?'+urlencode({'__biz':d['biz'],'mid':d['mid'],'idx':d['idx'],'sn':d['sn']})
 return d
async def main():
 target=json.loads(os.environ['DISCOVERY_TARGET']);expected=target['source']
 if expected not in SOURCES:raise ValueError('unsupported publisher')
 out={'source':expected,'status':'unavailable','articles':[],'attempts':[]}
 async with async_playwright() as pw:
  browser=await pw.firefox.launch(headless=False,timeout=20000)
  try:
   page=await browser.new_page();page.set_default_timeout(12000)
   if target.get('url'):urls=[article_input(target['url'])]
   else:
    query=target.get('query',expected)
    if not isinstance(query,str) or len(query)>80:raise ValueError('public query size')
    await page.goto('https://weixin.sogou.com/weixin?'+urlencode({'type':2,'query':query,'ie':'utf8'}),wait_until='domcontentloaded',timeout=25000)
    links=await page.evaluate("""()=>[...document.querySelectorAll('.news-list li')].slice(0,10).map(li=>({title:li.querySelector('h3')?.innerText,url:li.querySelector('h3 a')?.href,author:li.querySelector('.account')?.innerText||li.querySelector('.s-p a')?.innerText}))""")
    out['search_titles']=[{'title':r['title'],'author':r['author']} for r in links]
    links.sort(key=lambda r:r.get('author')!=expected)
    urls=[r['url'].replace('http://weixin.sogou.com/','https://weixin.sogou.com/',1) for r in links if r.get('url') and any(k in (r.get('title') or '') for k in ['价','行情']) and urlsplit(r['url']).scheme in ('http','https') and urlsplit(r['url']).hostname=='weixin.sogou.com'][:2]
   for url in urls:
    try:out['articles'].append(await inspect(page,expected,url))
    except Exception as e:out['attempts'].append({'error':type(e).__name__,'reason':str(e)[:80] if isinstance(e,ValueError) else 'public page unavailable'})
   out['status']='public_articles_inspected' if out['articles'] else 'no_public_articles'
  finally:await browser.close()
 Path('discovery.json').write_text(json.dumps(out,ensure_ascii=False))
 print(json.dumps({'source':expected,'status':out['status'],'articles':[{'title':a['title'],'published_at':a['published_at'],'biz':a['biz'],'table_count':len(a['tables']),'image_count':len(a['images']),'album_ids':a['album_ids']} for a in out['articles']],'attempts':out['attempts']},ensure_ascii=False))
if __name__=='__main__':asyncio.run(asyncio.wait_for(main(),140))
