"""Small, bounded discovery decisions, independent of browser/network state."""
import re

ALBUM_LIMIT=20

def current_titles(rows,day):
 def matches(row):
  title=row.get('title') or ''
  dates=re.findall(r'(?<!\d)(?:(20\d{2})年)?(\d{1,2})月(\d{1,2})日',title)
  return any((not year or int(year)==day.year) and (int(month),int(date))==(day.month,day.day) for year,month,date in dates)
 return [row for row in rows if matches(row)]

def listing_diagnostic(rows,day,stage,verification=False,has_listing=True):
 candidates=current_titles(rows,day)
 reason=('verification_required' if verification else 'current_candidates' if candidates else 'no_current_title_in_bounded_listing' if rows else 'empty_listing' if has_listing else 'listing_markup_missing')
 return {'stage':stage,'reason':reason,'observed_rows':len(rows),'current_candidates':len(candidates),'titles':[(row.get('title') or '')[:160] for row in rows][:ALBUM_LIMIT]}
