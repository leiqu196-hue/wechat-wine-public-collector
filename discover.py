"""Bounded manual inspection of public publisher pages. Never logs in or publishes prices."""
import asyncio,json,os,re,base64,hashlib,subprocess,sys,tempfile,signal
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,urlencode
from playwright.async_api import async_playwright
SOURCES={'酒业网','国酒酱香','国酒醇香','易茅时价','茅粉鲁智深'}
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
def public_jump(value):
 p=urlsplit(value)
 if p.scheme not in ('http','https') or p.username or p.password or p.port not in (None,80,443):raise ValueError('public jump origin')
 if not ((p.hostname=='weixin.sogou.com' and p.path=='/link') or (p.hostname=='mp.weixin.qq.com' and p.path in ('/profile','/mp/profile_ext','/s'))):raise ValueError('public jump path')
 return 'https://'+p.netloc+p.path+('?' + p.query if p.query else '')
async def account_candidates(page,expected,out):
 await page.goto('https://weixin.sogou.com/weixin?'+urlencode({'type':1,'query':expected,'ie':'utf8'}),wait_until='domcontentloaded',timeout=25000)
 rows=await page.evaluate("""()=>[...document.querySelectorAll('.news-list2 li,.news-list li')].slice(0,10).map(li=>({name:li.querySelector('.tit a')?.innerText.trim(),wechat_id:li.querySelector('[name="em_weixinhao"]')?.innerText.trim(),url:li.querySelector('.tit a')?.href,recent:[...li.querySelectorAll('.recent a')].map(a=>({title:a.innerText,url:a.href}))}))""")
 out['account_page']=await page.evaluate("""()=>({title:document.title,visible_text:document.body.innerText.slice(0,900),matching_links:[...document.querySelectorAll('a')].filter(a=>a.innerText.trim()).map(a=>({title:a.innerText.trim().slice(0,100),url:a.href})).filter(a=>a.title.includes("""+json.dumps(expected)+""")).slice(0,10)})""")
 out['account_results']=[{k:r.get(k) for k in ['name','wechat_id','recent']} for r in rows]
 matches=[r for r in rows if r.get('name')==expected];urls=[]
 for r in matches[:1]:
  for entry in r['recent']:
   if any(w in entry['title'] for w in ['价','行情']):
    try:urls.append(public_jump(entry['url']))
    except ValueError:pass
  if not r.get('url'):continue
  try:
   await page.goto(public_jump(r['url']),wait_until='domcontentloaded',timeout=25000)
   profile=await page.evaluate("""()=>({title:document.title,body_tip:document.body.innerText.slice(0,400),biz:window.biz||null,rows:[...document.querySelectorAll('[hrefs],a[href]')].map(e=>({title:e.innerText.trim().slice(0,160),url:e.getAttribute('hrefs')||e.href})).filter(r=>r.title&&r.url&&r.url.includes('mp.weixin.qq.com/s?')).slice(0,20)})""")
   out['profile']=profile
   for entry in profile['rows']:
    if any(w in entry['title'] for w in ['价','行情']):
     try:urls.append(public_jump(entry['url']))
     except ValueError:pass
  except Exception as e:out['attempts'].append({'stage':'public_profile','error':type(e).__name__})
 return list(dict.fromkeys(urls))[:2]
async def main():
 target=json.loads(os.environ['DISCOVERY_TARGET']);expected=target['source']
 if expected not in SOURCES:raise ValueError('unsupported publisher')
 out={'source':expected,'status':'unavailable','articles':[],'attempts':[]}
 async with async_playwright() as pw:
  browser=await pw.firefox.launch(headless=False,timeout=20000)
  try:
   page=await browser.new_page();page.set_default_timeout(12000)
   if target.get('kind')=='account':urls=await account_candidates(page,expected,out)
   elif target.get('url'):urls=[article_input(target['url'])]
   else:
    query=target.get('query',expected)
    if not isinstance(query,str) or len(query)>80:raise ValueError('public query size')
    await page.goto('https://weixin.sogou.com/weixin?'+urlencode({'type':2,'query':query,'ie':'utf8'}),wait_until='domcontentloaded',timeout=25000)
    links=await page.evaluate("""()=>[...document.querySelectorAll('.news-list li')].slice(0,10).map(li=>({title:li.querySelector('h3')?.innerText,url:li.querySelector('h3 a')?.href,author:li.querySelector('[id*="_account_"]')?.innerText||li.querySelector('.account')?.innerText||li.querySelector('.s-p a')?.innerText}))""")
    out['search_titles']=[{'title':r['title'],'author':r['author']} for r in links]
    links.sort(key=lambda r:r.get('author')!=expected)
    urls=[r['url'].replace('http://weixin.sogou.com/','https://weixin.sogou.com/',1) for r in links if r.get('url') and any(k in (r.get('title') or '') for k in ['价','行情']) and urlsplit(r['url']).scheme in ('http','https') and urlsplit(r['url']).hostname=='weixin.sogou.com'][:2]
   for url in urls:
    try:out['articles'].append(await inspect(page,expected,url))
    except Exception as e:out['attempts'].append({'error':type(e).__name__,'reason':str(e)[:80] if isinstance(e,ValueError) else 'public page unavailable'})
   out['status']='public_articles_inspected' if out['articles'] else 'no_public_articles'
  finally:await browser.close()
 if target.get('ocr_indices') and out['articles']:
  try:
   with tempfile.TemporaryDirectory(prefix='public-wine-ocr-') as folder:
    process=subprocess.Popen([sys.executable,'image_inspect.py'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    try:
     stdout,stderr=process.communicate(json.dumps({'article':out['articles'][0],'indices':target['ocr_indices'],'directory':folder},ensure_ascii=False),timeout=75)
     if process.returncode:raise subprocess.CalledProcessError(process.returncode,'image_inspect.py')
     out['image_ocr']=json.loads(stdout)
    finally:
     try:os.killpg(process.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     process.communicate(timeout=5)
  except Exception as exc:out['image_ocr']={'status':'unavailable','error':type(exc).__name__}
 Path('discovery.json').write_text(json.dumps(out,ensure_ascii=False))
 print(json.dumps({'source':expected,'status':out['status'],'articles':[{'title':a['title'],'published_at':a['published_at'],'biz':a['biz'],'table_count':len(a['tables']),'image_count':len(a['images']),'album_ids':a['album_ids']} for a in out['articles']],'attempts':out['attempts']},ensure_ascii=False))
if __name__=='__main__':asyncio.run(asyncio.wait_for(main(),140))
