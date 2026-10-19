"""Bounded manual full-image OCR evidence only. Never publishes quotation records."""
import asyncio,json,os,signal,subprocess,sys,tempfile,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
from playwright.async_api import async_playwright
from discover import article_input,inspect

def stop(process):
 try:os.killpg(process.pid,signal.SIGKILL)
 except ProcessLookupError:pass
 process.communicate(timeout=5)

def grid_lines(path):
 import cv2,numpy as np
 from PIL import Image
 with Image.open(path) as image:array=np.asarray(image.convert('RGB'))
 gray=cv2.cvtColor(array,cv2.COLOR_RGB2GRAY);binary=cv2.threshold(gray,180,255,cv2.THRESH_BINARY_INV)[1]
 opened=cv2.morphologyEx(binary,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(max(20,int(array.shape[1]*.72)),1)))
 ys=np.where(np.count_nonzero(opened,axis=1)>array.shape[1]*.70)[0].tolist();groups=[]
 for y in ys:
  if not groups or y>groups[-1][-1]+1:groups.append([y])
  else:groups[-1].append(y)
 return [round(sum(g)/len(g),2) for g in groups]

async def read_original():
 url=article_input(os.environ['ARTICLE_URL'])
 async with async_playwright() as pw:
  browser=await pw.firefox.launch(headless=False,timeout=20000)
  try:
   page=await browser.new_page();page.set_default_timeout(12000);article=await inspect(page,'酒业网',url)
   if article.get('biz')!='MzIyOTIzNTk0OQ==':raise ValueError('publisher identity mismatch')
   return article
  finally:await browser.close()

def main():
 deadline=time.monotonic()+480;article=asyncio.run(read_original())
 if not 10<=len(article['images'])<=40:raise ValueError('unexpected complete image list size')
 samples=[]
 for start in range(0,len(article['images']),2):
  remaining=deadline-time.monotonic()
  if remaining<10:raise TimeoutError('full-image overall deadline')
  indices=list(range(start,min(start+2,len(article['images']))))
  with tempfile.TemporaryDirectory(prefix='public-wine-ocr-') as folder:
   process=subprocess.Popen([sys.executable,'image_inspect.py'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
   try:
    stdout,stderr=process.communicate(json.dumps({'article':article,'indices':indices,'directory':folder},ensure_ascii=False),timeout=min(75,remaining))
    if process.returncode:raise RuntimeError('bounded image batch failed: '+str(process.returncode))
    data=json.loads(stdout)
    if data.get('status')!='ocr_unverified' or [s['index'] for s in data.get('samples',[])]!=indices:raise ValueError('image evidence mismatch')
    for sample in data['samples']:
     samples.append({'index':sample['index'],'sha256':sample['image_sha256'],'width':sample['width'],'height':sample['height'],'grid_y':grid_lines(Path(folder)/('image-'+str(sample['index'])+'.png')),'rapid':[[t['text'],t['box'],round(t['confidence'],5)] for t in sample['rapidocr']],'tesseract':[[t['text'],t['box'],round(t['confidence'],2)] for t in sample['tesseract']],'numeric_cells':[[t['rapidocr'],t['tesseract'],t['exact'],t['box']] for t in sample.get('numeric_cell_diagnostic',[])]})
   finally:stop(process)
  print(json.dumps({'batch_complete':indices,'images_completed':len(samples)}),flush=True)
 if [s['index'] for s in samples]!=list(range(len(article['images']))):raise ValueError('incomplete image evidence')
 result={'status':'ocr_unverified_public','checked_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'article':article,'samples':samples,'coverage':{'images':len(samples),'numeric_cells':sum(len(s['numeric_cells']) for s in samples),'numeric_agreements':sum(c[2] for s in samples for c in s['numeric_cells']),'quote_records_published':0}}
 raw=json.dumps(result,ensure_ascii=False).encode()
 if len(raw)>900000:raise ValueError('full evidence size limit')
 Path('full-image.json').write_bytes(raw);print(json.dumps(result['coverage']))
if __name__=='__main__':main()
