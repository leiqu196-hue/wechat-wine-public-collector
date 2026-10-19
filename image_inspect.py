"""Unverified public image OCR diagnostic. Never produces or publishes price records."""
import csv,hashlib,io,json,re,subprocess,sys,tempfile,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image,ImageOps
from rapidocr_onnxruntime import RapidOCR
Image.MAX_IMAGE_PIXELS=25000000
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ValueError('image redirect rejected')
def main():
 d=json.load(sys.stdin);article=d['article'];indices=d['indices']
 if article['author']!='酒业网' or article['biz']!='MzIyOTIzNTk0OQ==':raise ValueError('image publisher identity')
 if not isinstance(indices,list) or not 1<=len(indices)<=2 or any(type(i) is not int or not 0<=i<min(100,len(article['images'])) for i in indices):raise ValueError('image diagnostic bounds')
 engine=RapidOCR(det_limit_side_len=2048,intra_op_num_threads=2,inter_op_num_threads=1)
 output={'status':'ocr_unverified','publisher':article['author'],'published_timestamp':article['published_timestamp'],'samples':[]}
 folder=Path(d['directory']).resolve()
 if folder.parent!=Path(tempfile.gettempdir()).resolve() or not folder.name.startswith('public-wine-ocr-') or not folder.is_dir():raise ValueError('parent-owned temporary directory')
 for index in indices:
  url=article['images'][index];p=urlsplit(url)
  if p.scheme!='https' or p.hostname!='mmbiz.qpic.cn' or p.port not in (None,443) or p.username or p.password:raise ValueError('image origin')
  with urllib.request.build_opener(NoRedirect()).open(url,timeout=8) as r:raw=r.read(6000001)
  if len(raw)>6000000:raise ValueError('image byte limit')
  image=Image.open(io.BytesIO(raw))
  if image.width*image.height>25000000:raise ValueError('image pixel limit')
  image.load()
  path=Path(folder)/('image-'+str(index)+'.png');image.convert('RGB').save(path)
  result,_=engine(str(path));rapid=[{'box':[[round(float(x),2),round(float(y),2)] for x,y in box],'text':str(text)[:500],'confidence':float(conf)} for box,text,conf in (result or [])][:1500]
  process=subprocess.run(['tesseract',str(path),'stdout','-l','chi_sim+eng','--psm','6','tsv'],capture_output=True,text=True,timeout=20,check=True)
  tesseract=[{'text':r['text'],'confidence':float(r['conf']),'box':[int(r[k]) for k in ['left','top','width','height']]} for r in csv.DictReader(io.StringIO(process.stdout),delimiter='\t') if r.get('text','').strip()][:1500]
  cells=[];crops=[]
  for token in rapid:
   box=token['box'];x=sum(v[0] for v in box)/4;y=sum(v[1] for v in box)/4
   if y<120 or not image.width*.46<x<image.width*.83 or not re.fullmatch(r'\d{1,6}',token['text']):continue
   if len(cells)>=160:raise ValueError('numeric sample limit')
   bounds=(max(0,int(min(v[0] for v in box))-3),max(0,int(min(v[1] for v in box))-3),min(image.width,int(max(v[0] for v in box))+4),min(image.height,int(max(v[1] for v in box))+4))
   if not 0<bounds[2]-bounds[0]<=200 or not 0<bounds[3]-bounds[1]<=100:raise ValueError('numeric crop bounds')
   crop=image.crop(bounds).convert('L');crop=crop.resize((crop.width*4,crop.height*4));crops.append(ImageOps.expand(crop,border=20,fill=255))
   cells.append({'rapidocr':token['text'],'box':box,'tesseract':None,'exact':False})
  if crops:
   cell_path=Path(folder)/('cells-'+str(index)+'.tiff');crops[0].save(cell_path,save_all=True,append_images=crops[1:],compression='tiff_deflate')
   checked=subprocess.run(['tesseract',str(cell_path),'stdout','-l','eng','--psm','7','-c','tessedit_char_whitelist=0123456789','tsv'],capture_output=True,text=True,timeout=25,check=True)
   pages={}
   for row in csv.DictReader(io.StringIO(checked.stdout),delimiter='\t'):
    if row.get('text','').strip():pages.setdefault(int(row['page_num']),[]).append(row['text'].strip())
   for n,cell in enumerate(cells,1):
    value=''.join(pages.get(n,[]));cell['tesseract']=value;cell['exact']=value==cell['rapidocr']
  output['samples'].append({'numeric_cell_diagnostic':cells,'index':index,'image_sha256':hashlib.sha256(raw).hexdigest(),'width':image.width,'height':image.height,'rapidocr':rapid,'tesseract':tesseract})
 print(json.dumps(output,ensure_ascii=False))
if __name__=='__main__':main()
