"""Save only bounded anonymous public-source diagnostics to fixed public files."""
import base64,json,os,urllib.request,urllib.error
from pathlib import Path
raw=Path('discovery.json').read_bytes()
if len(raw)>250000:raise ValueError('diagnostic size limit')
data=json.loads(raw)
names={'酒业网':'wine-industry','国酒酱香':'guojiu','易茅时价':'yimao','茅粉鲁智深':'maofen'}
name=names[data['source']]
if data['status'] not in ('public_articles_inspected','no_public_articles'):raise ValueError('unsupported diagnostic status')
repo=os.environ['GITHUB_REPOSITORY']
if repo!='leiqu196-hue/wechat-wine-public-collector':raise ValueError('repository mismatch')
url='https://api.github.com/repos/'+repo+'/contents/data/diagnostics/'+name+'.json'
headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
sha=None
try:
 with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=15) as response:sha=json.load(response)['sha']
except urllib.error.HTTPError as exc:
 if exc.code!=404:raise
payload={'message':'chore: save public source inspection '+name,'content':base64.b64encode(raw).decode(),'branch':'main'}
if sha:payload['sha']=sha
# A timed-out PUT is not repeated in this run; inspect the public file before retrying.
with urllib.request.urlopen(urllib.request.Request(url,data=json.dumps(payload).encode(),headers=headers,method='PUT'),timeout=20) as response:
 result=json.load(response);print(json.dumps({'status':'public_diagnostic_saved','path':'data/diagnostics/'+name+'.json','commit':result['commit']['sha']}))
