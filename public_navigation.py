"""Bounded public-page diagnostics. Never expose redirect query strings or challenges."""
from urllib.parse import urlsplit

VERIFICATION_JS = """()=>['环境异常','完成验证','验证码','访问过于频繁'].some(t=>(document.body?.innerText||'').includes(t))||location.pathname.startsWith('/antispider/')"""


def page_location(page):
 # Only classify an already observed URL. Never retain paths, query strings,
 # arbitrary hostnames, credentials or page contents, and never make a request.
 try:
  host=urlsplit(page.url).hostname
  return {'page_host':host if host in ('weixin.sogou.com','mp.weixin.qq.com') else 'other'}
 except (AttributeError,TypeError,ValueError):return {'page_host':'unknown'}


class PublicVerificationRequired(ValueError):
 def __init__(self, stage, state):
  super().__init__('verification_required')
  self.diagnostic=dict(stage='verification_required',verification_stage=stage,**state)


class PublicPageError(RuntimeError):
 def __init__(self, stage, error, state):
  super().__init__('public page unavailable')
  self.diagnostic = dict(stage=stage, error=type(error).__name__, **state)


async def require_public_page(page, stage='original_content'):
 if await page.evaluate(VERIFICATION_JS):
  raise PublicVerificationRequired(stage,page_location(page))


async def page_error(page, stage, error):
 # Recheck after asynchronous redirects/content waits, not just initial navigation.
 try:await require_public_page(page,stage)
 except ValueError:raise
 except Exception:pass
 return PublicPageError(stage,error,page_location(page))
