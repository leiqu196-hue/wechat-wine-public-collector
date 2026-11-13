"""Bounded public-page diagnostics. Never expose redirect query strings or challenges."""
from urllib.parse import urlsplit

VERIFICATION_JS = """()=>['环境异常','完成验证','验证码','访问过于频繁'].some(t=>(document.body?.innerText||'').includes(t))||location.pathname.startsWith('/antispider/')"""


class PublicPageError(RuntimeError):
 def __init__(self, stage, error, state):
  super().__init__('public page unavailable')
  self.diagnostic = dict(stage=stage, error=type(error).__name__, **state)


async def require_public_page(page):
 if await page.evaluate(VERIFICATION_JS):
  raise ValueError('verification_required')


async def page_error(page, stage, error):
 # Recheck after asynchronous redirects/content waits, not just initial navigation.
 try:await require_public_page(page)
 except ValueError:raise
 except Exception:pass
 try:
  parsed=urlsplit(page.url)
  host=parsed.hostname if parsed.hostname in ('weixin.sogou.com','mp.weixin.qq.com') else 'other'
  path=parsed.path if parsed.path in ('/link','/s','/weixin') else 'other'
  state={'page_host':host,'page_path_kind':path}
 except (TypeError,ValueError):state={'page_host':'unknown','page_path_kind':'unknown'}
 return PublicPageError(stage,error,state)
