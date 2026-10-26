import unittest,xml.etree.ElementTree as ET
from pathlib import Path
from html.parser import HTMLParser
from static_assets import STATIC_FILES
ROOT=Path(__file__).parent
BASE='https://crypto-portfolio-tracker-rouge.vercel.app'
class Page(HTMLParser):
 def __init__(self,source):super().__init__();self.tags=[];self.feed(source)
 def handle_starttag(self,tag,attrs):self.tags.append((tag,dict(attrs)))
class SEOTests(unittest.TestCase):
 def test_sitemap_pages_have_unique_titles_descriptions_and_canonicals(self):
  sitemap=ET.fromstring((ROOT/'sitemap.xml').read_text());urls=[node.text for node in sitemap.findall('{*}url/{*}loc')]
  self.assertEqual(len(urls),4);titles=set();descriptions=set()
  for url in urls:
   self.assertTrue(url.startswith(BASE+'/'));path=url[len(BASE):];filename,kind=STATIC_FILES[path]
   source=(ROOT/filename).read_text(encoding='utf-8');page=Page(source)
   import re
   title=re.search(r'<title>(.*?)</title>',source).group(1)
   self.assertNotIn(title,titles);titles.add(title)
   meta={attrs.get('name'):attrs.get('content') for tag,attrs in page.tags if tag=='meta'}
   self.assertNotIn(meta['description'],descriptions);descriptions.add(meta['description'])
   self.assertEqual(meta['robots'],'index,follow')
   self.assertEqual(sum(tag=='h1' for tag,attrs in page.tags),1)
   self.assertIn(('link',{'rel':'canonical','href':url}),page.tags)
   self.assertNotIn('<script',source)
   for tag,attrs in page.tags:
    if tag=='a' and attrs.get('href','').startswith('/'):
     self.assertIn(attrs['href'],STATIC_FILES)
 def test_private_workspace_is_noindex_but_guides_crawlable(self):
  source=(ROOT/'app.html').read_text(encoding='utf-8')
  self.assertIn('content="noindex,follow"',source)
  self.assertIn('href="/">About the crypto portfolio tracker',source)
  robots=(ROOT/'robots.txt').read_text()
  self.assertIn('Sitemap: '+BASE+'/sitemap.xml',robots)
  self.assertNotIn('Disallow: /',robots)
 def test_worked_example(self):
  average=(2000+10+3000+10)/2
  self.assertEqual(1600-5-average*.5,340)
  self.assertEqual(1.5*3000-average*1.5,735)
 def test_homepage_and_breadcrumb_schema(self):
  page=(ROOT/'index.html').read_text(encoding='utf-8')
  self.assertIn('https://schema.org/WebSite',page)
  self.assertIn('itemprop="name" content="Orbit"',page)
  self.assertIn('href="/app.html"',page)
  self.assertNotIn('id="authForm"',page)
  for name in ('crypto-profit-loss','wallet-tracking'):
   guide=(ROOT/('guides/'+name+'.html')).read_text(encoding='utf-8')
   self.assertIn('https://schema.org/BreadcrumbList',guide)
   self.assertIn('aria-current="page"',guide)
 def test_redirects_target_canonical_home(self):
  import json
  config=json.loads((ROOT/'vercel.json').read_text())
  for path in ('/index.html','/crypto-portfolio-tracker.html'):
   self.assertIn({'source':path,'destination':'/','permanent':True},config['redirects'])
 def test_public_pages_need_no_application_bundle(self):
  for name in ('index.html','guides/wallet-tracking.html','guides/crypto-profit-loss.html','about-orbit.html'):
   source=(ROOT/name).read_text(encoding='utf-8')
   self.assertNotIn('<script',source)
   self.assertNotIn('app.js',source)
   self.assertIn('public_site.css',source)
  self.assertLess((ROOT/'public_site.css').stat().st_size,6000)
 def test_icons_present_on_public_and_private_pages(self):
  for name in ('index.html','app.html','about-orbit.html','guides/wallet-tracking.html','guides/crypto-profit-loss.html'):
   source=(ROOT/name).read_text(encoding='utf-8')
   for icon in ('/favicon.ico','/favicon.svg','/favicon-96.png','/apple-touch-icon.png'):
    self.assertIn('href="'+icon+'"',source)
    self.assertIn(icon,STATIC_FILES)
  self.assertEqual((ROOT/'favicon.ico').read_bytes()[:4],b'\x00\x00\x01\x00')
 def test_public_build_removes_blocking_css_request(self):
  import tempfile
  from build_static import build
  with tempfile.TemporaryDirectory() as directory:
   build(directory)
   for name in ('index.html','guides/wallet-tracking.html','guides/crypto-profit-loss.html','about-orbit.html'):
    source=Path(directory,name).read_text(encoding='utf-8')
    self.assertIn('<style>',source)
    self.assertNotIn('rel="stylesheet"',source)
    self.assertNotIn('<script',source)
   self.assertIn('rel="stylesheet"',Path(directory,'app.html').read_text(encoding='utf-8'))
if __name__=='__main__':unittest.main()
