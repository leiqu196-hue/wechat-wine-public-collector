"""Fail closed before any network write, even for an old successful result file."""
import re
from datetime import datetime,timedelta
from public_contract import CN
DESTINATIONS={'今日酒价':('Mzk0NzI1MjY4Ng==','data/latest.json'),'茅粉鲁智深':('Mzg4MzMyMTExMQ==','data/maofen.json'),'易茅时价':('MzYyMTQ3NTQ1OQ==','data/yimao.json'),'国酒酱香':('MzI2MTY5ODk5Ng==','data/guojiu.json')}

def validate_report(data,now=None):
 now=now or datetime.now(CN)
 if data.get('status')!='publisher_today_verified_completeness_unverified':raise ValueError('no verified current publisher article')
 article=data['article'];source=article['source'];biz,path=DESTINATIONS[source]
 if article.get('biz')!=biz or article.get('author')!=source:raise ValueError('publisher identity mismatch')
 today=now.astimezone(CN).date()
 checked=datetime.fromisoformat(data['checked_at'])
 if checked.tzinfo is None or checked.astimezone(CN).date()!=today or checked>now+timedelta(minutes=10):raise ValueError('collection date mismatch')
 stamp=article.get('published_timestamp')
 if isinstance(stamp,bool) or not re.fullmatch(r'\d{10}',str(stamp)):raise ValueError('original timestamp missing')
 published=datetime.fromtimestamp(int(stamp),CN)
 if article.get('date')!=today.isoformat() or published.date()!=today or published>now+timedelta(minutes=10):raise ValueError('original publication date mismatch')
 return path
