#!/usr/bin/env python3
"""Kildeformater og fejl håndteres uden netværk, AI eller skrivning af artikeldata."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crawler as c
from nyhedskilder import parse_nyhedsoversigt

BASE = "https://lab.example/news"
OVERSIGT = b'''<html><body>
<a href="/featured"><h2>Introducing Model Z &amp; W</h2><div>
 <a href="/featured"><time>Sep 1, 2026</time><p>A new model for coding.</p></a>
</div></a>
<a href="/recent"><span class="List__title body">A newer release</span><time>September 10, 2026</time></a>
<a href="/featured"><span class="List__title">Introducing Model Z &amp; W</span><time>Sep 1, 2026</time></a>
<a href="/grok"><div>Sep 3, 2026</div><h3>New model</h3><p>Release details.</p></a>
<a href="/no-date"><h2>An evergreen product</h2></a>
<a href="/no-title"><time>Sep 11, 2026</time><p>Just a description.</p></a>
<a href="https://other.example/story"><h2>Other site</h2><time>Sep 11, 2026</time></a>
<a href="javascript:alert(1)"><h2>Bad URL</h2><time>Sep 11, 2026</time></a>
<script><a href="/fake"><h2>Not visible</h2><time>Sep 11, 2026</time></a></script>
</body></html>'''


class KildeTests(unittest.TestCase):
    def test_featured_med_indlejret_link_bevarer_titel_dato_og_resume(self):
        articles = parse_nyhedsoversigt(OVERSIGT, BASE)
        self.assertEqual(len(articles), 3)
        article = next(a for a in articles if a['link'].endswith('/featured'))
        self.assertEqual(article['titel'], 'Introducing Model Z & W')
        self.assertEqual(article['resume'], 'A new model for coding.')
        self.assertEqual(article['dato'], datetime(2026, 9, 1, tzinfo=timezone.utc))

    def test_oversigt_sorteres_efter_udgivelse_foer_kildens_loft(self):
        with patch.object(c, 'hent_url', return_value=OVERSIGT):
            _, articles, error = c.crawl_feed({'navn':'Lab','url':BASE,'format':'nyhedsoversigt','max':2,'kun_aktuel':True})
        self.assertIsNone(error)
        self.assertEqual([a['link'] for a in articles], ['https://lab.example/recent', 'https://lab.example/grok'])
        self.assertTrue(all(a['kilde']=='Lab' and a['kun_aktuel'] for a in articles))

    def test_datetime_respekterer_tidszone_og_ugyldige_datoer_springes_over(self):
        markup = b'''<a href="/a"><h2>A</h2><time datetime="2026-09-10T13:00:00+02:00">Today</time></a>
        <a href="/b"><h2>B</h2><time>Feb 31, 2026</time></a>'''
        articles = parse_nyhedsoversigt(markup, BASE)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]['dato'], datetime(2026,9,10,11,tzinfo=timezone.utc))

    def test_aendret_html_og_tomme_feeds_giver_synlig_kildefejl(self):
        for format, data in [('feed',b'<html><body>Access denied</body></html>'),
                             ('feed',b'<rss><channel/></rss>'),
                             ('nyhedsoversigt',b'<html><h1>New layout</h1></html>'),
                             ('ukendt',OVERSIGT)]:
            with self.subTest(format=format,data=data), patch.object(c,'hent_url',return_value=data):
                _, articles, error = c.crawl_feed({'navn':'Lab','url':BASE,'format':format})
            self.assertEqual(articles, [])
            self.assertTrue(error)

    def test_rss_og_atom_bevarer_artiklens_dato_og_link(self):
        feeds = [b'<rss><channel><item><title>RSS model</title><link>https://lab.example/rss</link><pubDate>Thu, 10 Sep 2026 12:00:00 GMT</pubDate></item></channel></rss>',
                 b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom model</title><link rel="self" href="https://lab.example/self"/><link rel="alternate" href="https://lab.example/atom"/><published>2026-09-10T12:00:00Z</published><updated>2026-09-11T12:00:00Z</updated></entry></feed>']
        for name,data in zip(('rss','atom'),feeds):
            with patch.object(c,'hent_url',return_value=data):
                _, articles, error = c.crawl_feed({'navn':'Lab','url':BASE})
            self.assertIsNone(error)
            self.assertEqual(articles[0]['link'], f'https://lab.example/{name}')
            self.assertEqual(articles[0]['dato'], datetime(2026,9,10,12,tzinfo=timezone.utc))

    def test_manglende_titel_og_link_registreres_som_fejl(self):
        with patch.object(c,'hent_url',return_value=b'<rss><channel><item><title>Missing link</title></item></channel></rss>'):
            _, articles, error = c.crawl_feed({'navn':'Lab','url':BASE})
        self.assertEqual(articles, [])
        self.assertTrue(error)

    def test_netvaerksfejl_stopper_ikke_andre_kilder(self):
        with patch.object(c,'hent_url',side_effect=TimeoutError('timeout')):
            feed, articles, error = c.crawl_feed({'navn':'Lab','url':BASE})
        self.assertEqual(feed['navn'], 'Lab')
        self.assertEqual(articles, [])
        self.assertIn('TimeoutError', error)


if __name__ == '__main__':
    unittest.main(verbosity=2)
