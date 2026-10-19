"""Save bounded public full-image diagnostics to one fixed non-production file."""
import base64,json,os,urllib.request,urllib.error
from pathlib import Path
raw=Path('full-image.json').read_bytes()
if not 0<len(raw)<=900000:raise ValueError('public diagnostic size')
d=json.loads(raw)
if d.get('status')!='ocr_unverified_public' or d['article'].get('author')!='酒业网' or d['article'].get('biz')!='MzIyOTIzNTk0OQ==':raise ValueError('public diagnostic identity')
if os.environ['GITHUB_REPOSITORY']!='leiqu196-hue/wechat-wine-public-collector':raise ValueError('repository mismatch')
url='https://api.github.com/repos/leiqu196-hue/wechat-wine-public-collector/contents/data/diagnostics/wine-industry-full.json'
headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
sha=None
try:
 with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=15) as response:sha=json.load(response)['sha']
except urllib.error.HTTPError as exc:
 if exc.code!=404:raise
payload={'message':'chore: save public full-image OCR evidence','content':base64.b64encode(raw).decode(),'branch':'main'}
if sha:payload['sha']=sha
# Unknown write outcomes are not repeated.
with urllib.request.urlopen(urllib.request.Request(url,data=json.dumps(payload).encode(),headers=headers,method='PUT'),timeout=25) as response:
 print(json.dumps({'status':'public_evidence_saved','commit':json.load(response)['commit']['sha']}))
