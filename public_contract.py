"""Bounded native identity/date contract; full price coverage is verified independently on ECS."""
import re
from datetime import datetime,timedelta,timezone
from urllib.parse import urlencode
CN=timezone(timedelta(hours=8))
CONFIG={'易茅时价': ('MzYyMTQ3NTQ1OQ==', '易茅时价'), '国酒酱香': ('MzI2MTY5ODk5Ng==', '国酒酱香')}

def current_article(article,source,now):
 biz=CONFIG[source][0]
 if article.get('author')!=source or article.get('biz')!=biz:raise ValueError('publisher identity mismatch')
 stamp=article.get('published_timestamp')
 if isinstance(stamp,bool) or not re.fullmatch(r'\d{10}',str(stamp)):raise ValueError('original timestamp missing')
 published=datetime.fromtimestamp(int(stamp),CN)
 if published.date()!=now.date() or published>now+timedelta(minutes=10):raise ValueError('not current original publication')
 if not re.fullmatch(r'\d{1,20}',article.get('mid','')) or not re.fullmatch(r'[1-9]\d?',article.get('idx','')):raise ValueError('native original identity missing')
 if not isinstance(article.get('body'),str) or not 100<len(article['body'])<=80000 or not 1<=len(article.get('tables',[]))<=10:raise ValueError('original size')
 numeric=sum(len(row)==4 and all(re.fullmatch(r'\d{1,6}',re.sub(r'\s+','',v)) for v in row[1:3]) for table in article['tables'] for row in table)
 if not (100<=numeric<=500 if source=='易茅时价' else 50<=numeric<=100):raise ValueError('no complete-sized price tables')
 keys={'__biz':biz,'mid':article['mid'],'idx':article['idx']}
 if isinstance(article.get('sn'),str) and re.fullmatch(r'[a-f0-9]{32}',article['sn']):keys['sn']=article['sn']
 # sn is optional public permalink metadata, never fabricated. Identity is captured from the native original page.
 article['source_url']='https://mp.weixin.qq.com/s?'+urlencode(keys)
 article.update(source=source,date=now.date().isoformat(),engine='firefox',coverage={'price_rows':numeric,'completeness':'independent_server_validation_required'},link_identity_method='native_biz_mid_idx')
 return article

