"""Test RSS-transport og afvisning af fejlindhold uden netværk eller mail."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nyhedsbrev as n
from _redaktion import nyhedsbrev_feed as feed

XML = b'''<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><item>
 <title>A whole letter</title><link>https://metatrends.substack.com/p/letter</link>
 <pubDate>Thu, 10 Sep 2026 16:54:27 GMT</pubDate><dc:creator>Peter H. Diamandis</dc:creator>
 <description>A teaser only</description><content:encoded><![CDATA[<p>Full original.</p>]]></content:encoded>
 </item></channel></rss>'''


def reply(body=XML, status=200, content_type='application/xml; charset=utf-8', code=0,
          url=feed.FEED_URL, headers=''):
    def run(command, **kwargs):
        Path(command[command.index('--output') + 1]).write_bytes(body)
        Path(command[command.index('--dump-header') + 1]).write_text(headers)
        return subprocess.CompletedProcess(command, code, json.dumps({
            'http_code': status, 'http_version': '2', 'content_type': content_type,
            'url_effective': url,
        }), '')
    return run


class FeedTests(unittest.TestCase):
    def test_live_transport_uses_full_rss_content(self):
        with patch.object(feed.subprocess, 'run', side_effect=reply()) as run:
            result = n.fetch_feed(feed.FEED_URL)
        self.assertEqual(result[0]['tekst'], 'Full original.')
        args = run.call_args.args[0]
        self.assertEqual(args[:2], ['curl', '--disable'])
        self.assertIn('--compressed', args)
        self.assertEqual(args[args.index('--retry') + 1], '2')
        self.assertNotIn('--retry-all-errors', args)
        self.assertNotIn('--insecure', args)
        self.assertNotIn('--location', args)
        self.assertEqual(args[-1], feed.FEED_URL)

    def test_unknown_feed_rejected_before_any_request(self):
        with patch.object(feed.subprocess, 'run') as run:
            with self.assertRaises(ValueError): feed.fetch_xml('https://example.com/feed')
        run.assert_not_called()

    def test_access_denial_is_clear_and_never_treated_as_content(self):
        for status in (401, 403):
            with self.subTest(status=status), patch.object(feed.subprocess, 'run', side_effect=reply(
                b'<html>Access denied</html>', status=status, content_type='text/html', code=22,
                headers='CF-Mitigated: challenge\r\nSet-Cookie: never-log-this\r\n')):
                with self.assertRaisesRegex(ValueError, f'HTTP {status}.*Cloudflare') as error:
                    n.fetch_feed(feed.FEED_URL)
                self.assertNotIn('never-log-this', str(error.exception))

    def test_html_error_with_http_200_cannot_pass(self):
        with patch.object(feed.subprocess, 'run', side_effect=reply(b'<html>Login</html>', content_type='text/html')):
            with self.assertRaisesRegex(ValueError, 'ikke XML'): n.fetch_feed(feed.FEED_URL)

    def test_redirects_and_changed_destination_rejected(self):
        for changes in ({'status': 302}, {'url': 'https://example.com/feed'}):
            with self.subTest(changes=changes), patch.object(feed.subprocess, 'run', side_effect=reply(**changes)):
                with self.assertRaises(ValueError): n.fetch_feed(feed.FEED_URL)

    def test_partial_download_and_exhausted_retries_cannot_pass(self):
        for changes in ({'code': 18}, {'status': 503, 'code': 22}):
            with self.subTest(changes=changes), patch.object(feed.subprocess, 'run', side_effect=reply(**changes)):
                with self.assertRaises(ValueError): n.fetch_feed(feed.FEED_URL)

    def test_size_limit_is_checked_after_decompression(self):
        with patch.object(feed, 'MAX_BYTES', 10), patch.object(feed.subprocess, 'run', side_effect=reply()):
            with self.assertRaisesRegex(ValueError, 'for stort'): n.fetch_feed(feed.FEED_URL)

    def test_malformed_and_empty_xml_never_succeed(self):
        for body in (b'<rss><channel/></rss>', b'<!DOCTYPE rss><rss/>'):
            with self.subTest(body=body), patch.object(feed.subprocess, 'run', side_effect=reply(body)):
                with self.assertRaises(ValueError): n.fetch_feed(feed.FEED_URL)

    def test_missing_curl_and_timeout_give_actionable_errors(self):
        for error, message in ((FileNotFoundError(), 'kræver curl'),
                               (subprocess.TimeoutExpired('curl', 100), '100 sekunder')):
            with self.subTest(error=error), patch.object(feed.subprocess, 'run', side_effect=error):
                with self.assertRaisesRegex(ValueError, message): n.fetch_feed(feed.FEED_URL)


if __name__ == '__main__':
    unittest.main()
