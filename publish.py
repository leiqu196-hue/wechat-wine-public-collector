"""Commit only the bounded public collector result. No external service credentials."""
import base64,json,os,urllib.request,urllib.error
from pathlib import Path
raw=Path('result.json').read_bytes()
if len(raw)>250000:raise ValueError('public result size limit')
data=json.loads(raw)
if data.get('status')!='publisher_today_verified_completeness_unverified':raise ValueError('no verified current publisher article')
repo=os.environ['GITHUB_REPOSITORY']
if repo!='leiqu196-hue/wechat-wine-public-collector':raise ValueError('repository mismatch')
url='https://api.github.com/repos/'+repo+'/contents/data/latest.json'
headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
sha=None
try:
 with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=15) as response:sha=json.load(response)['sha']
except urllib.error.HTTPError as exc:
 if exc.code!=404:raise
payload={'message':'chore: refresh public publisher report '+data['article']['date'],'content':base64.b64encode(raw).decode(),'branch':'main'}
if sha:payload['sha']=sha
# Unknown PUT outcomes are never automatically repeated within a run.
with urllib.request.urlopen(urllib.request.Request(url,data=json.dumps(payload).encode(),headers=headers,method='PUT'),timeout=20) as response:
 result=json.load(response)
 print(json.dumps({'status':'public_data_saved','date':data['article']['date'],'commit':result['commit']['sha']}))
