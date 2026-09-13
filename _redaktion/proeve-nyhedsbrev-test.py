"""Test Gmail-isolation og AI-kontrol uden rigtige kald."""
import json
import io
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
t = runpy.run_path(str(ROOT / '_redaktion/send-nyhedsbrev-test.py'))
f = runpy.run_path(str(ROOT / '_redaktion/proeve-nyhedsbrev.py'))

class TestMail(unittest.TestCase):
    def test_empty_send_receipt_completes_gmail_test_once(self):
        draft = f['draft']()
        for status_code in (200, 204):
            with self.subTest(status=status_code), tempfile.TemporaryDirectory() as tmp:
                responses = [
                    json.dumps({'id': 'em_test', 'status': 'draft'}).encode(),
                    json.dumps({'status': 'draft', 'subject': draft['emne'],
                                'body': t['n'].render(draft)}).encode(),
                    b'',
                ]
                def response(request, **kwargs):
                    body = io.BytesIO(responses.pop(0))
                    body.status = status_code if not responses else 200
                    return body
                with patch.object(t['n'], 'urlopen', side_effect=response) as call:
                    t['send_test'](t['n'].Buttondown('test-token'), draft,
                                   f['SOURCE'], '123', Path(tmp))
                saved = json.loads((Path(tmp) / 'status.json').read_text())
                self.assertEqual(saved['status'], 'test_accepteret')
                self.assertEqual(call.call_count, 3)
                request = call.call_args.args[0]
                self.assertEqual(request.method, 'POST')
                self.assertTrue(request.full_url.endswith('/em_test/send-draft'))
                self.assertEqual(json.loads(request.data), {'recipients': ['soemandtorben@gmail.com']})

    def test_empty_receipt_exception_does_not_hide_other_bad_responses(self):
        for method, path, body, status in [
            ('GET', '/em_test', b'', 200),
            ('POST', '', b'', 201),
            ('PATCH', '/em_test', b'', 200),
            ('POST', '/em_test/send-draft', b'<html>unexpected</html>', 200),
            ('POST', '/em_test/send-draft', b'', 500),
        ]:
            with self.subTest(method=method, path=path, status=status):
                response = io.BytesIO(body)
                response.status = status
                with patch.object(t['n'], 'urlopen', return_value=response):
                    with self.assertRaises(json.JSONDecodeError):
                        t['n'].Buttondown('test-token').call(method, path)

    def test_send_http_error_is_not_retried_or_accepted(self):
        error = HTTPError('https://api.buttondown.com', 403, 'Forbidden', {}, None)
        with patch.object(t['n'], 'urlopen', side_effect=error) as call:
            with self.assertRaises(HTTPError):
                t['n'].Buttondown('test-token').call('POST', '/em_test/send-draft')
        call.assert_called_once()

    def test_test_mail_requires_live_feed_and_chooses_latest(self):
        from unittest.mock import patch
        config = {'feed': 'https://metatrends.substack.com/feed'}
        older = {**f['SOURCE'], 'dato': '2026-09-10T00:00:00+00:00'}
        with patch.object(t['n'], 'fetch_feed', return_value=[f['SOURCE'], older]) as fetch:
            self.assertEqual(t['source_for_test'](config), f['SOURCE'])
        fetch.assert_called_once_with(config['feed'])
        with patch.object(t['n'], 'fetch_feed', side_effect=ValueError('HTTP 403')):
            with self.assertRaisesRegex(ValueError, 'HTTP 403'):
                t['source_for_test'](config)

    def test_only_explicit_recipient_and_draft_endpoint(self):
        draft = f['draft']()
        body = t['n'].render(draft)
        api = Mock()
        api.call.side_effect = [{'id': 'em_test', 'status': 'draft'}, {}]
        api.get.return_value = {'status': 'draft', 'subject': draft['emne'], 'body': body}
        with tempfile.TemporaryDirectory() as tmp:
            t['send_test'](api, draft, f['SOURCE'], '123', Path(tmp))
            status = json.loads((Path(tmp) / 'status.json').read_text())
        self.assertEqual(status['status'], 'test_accepteret')
        self.assertEqual(api.call.call_args_list[0].args[2]['status'], 'draft')
        self.assertEqual(api.call.call_args_list[1].args[:3], ('POST', '/em_test/send-draft', {'recipients': ['soemandtorben@gmail.com']}))
        self.assertEqual(api.call.call_count, 2)

    def test_changed_draft_is_not_sent(self):
        api = Mock()
        api.call.return_value = {'id': 'em_test', 'status': 'draft'}
        api.get.return_value = {'status': 'draft', 'body': 'Changed'}
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            t['send_test'](api, f['draft'](), f['SOURCE'], '123', Path(tmp))
        self.assertEqual(api.call.call_count, 1)

    def test_reviewer_feedback_reaches_new_attempt(self):
        bad = {**f['REVIEW'], 'godkendt': False, 'problemer': ['Eksemplerne gentager sig']}
        ai = Mock(side_effect=[f['draft'](), bad, f['draft'](), f['REVIEW']])
        with tempfile.TemporaryDirectory() as tmp:
            t['generate'](f['SOURCE'], f['CONFIG'], Path(tmp), ai)
        self.assertIn('gentager', ai.call_args_list[2].args[2]['tidligere_fejl'])
        self.assertEqual(ai.call_args_list[2].args[2]['tidligere_udkast'], f['draft']())
        self.assertEqual(ai.call_count, 4)

    def test_rejected_output_never_returns_a_letter(self):
        ai = Mock(return_value={'status': 'kraever_mere_materiale'})
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            t['generate'](f['SOURCE'], f['CONFIG'], Path(tmp), ai)
        self.assertEqual(ai.call_count, 6)

    def test_review_retry_preserves_artifact_without_rewriting_letter(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            calls = []
            def ai(step, prompt, payload):
                calls.append(step)
                if step == 'nyhedsbrev':
                    return f['draft']()
                attempt = len(calls) - 1
                saved = json.loads((folder / f'forsog-{attempt}.json').read_text())
                self.assertEqual(saved['udkast'], payload['udkast'])
                self.assertEqual(saved['naeste_trin'], 'kontrol')
                self.assertTrue(saved['fejl'])  # Ikke godkendt før kontrollens svar.
                if attempt == 1:
                    raise RuntimeError('Afslutning: length; intet kontrolsvar')
                return f['REVIEW']
            result = t['generate'](f['SOURCE'], f['CONFIG'], folder, ai)
            self.assertEqual(result, f['draft']())
            self.assertEqual(calls, ['nyhedsbrev', 'nyhedsbrev_kontrol', 'nyhedsbrev_kontrol'])
            self.assertNotIn('fejl', json.loads((folder / 'forsog-2.json').read_text()))

    def test_technical_control_failures_exhaust_test_budget_without_returning_letter(self):
        ai = Mock(side_effect=[f['draft']()] + [RuntimeError('Tomt kontrolsvar')] * 3)
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            t['generate'](f['SOURCE'], f['CONFIG'], Path(tmp), ai)
        self.assertEqual([c.args[0] for c in ai.call_args_list],
                         ['nyhedsbrev', 'nyhedsbrev_kontrol', 'nyhedsbrev_kontrol', 'nyhedsbrev_kontrol'])

    def test_ascii_apostrophe_is_valid_but_repeated_author_is_not(self):
        draft = f['draft']()
        draft['brev_markdown'] = draft['brev_markdown'].replace('Diamandis’', "Diamandis'")
        t['n'].validate_draft(draft, f['SOURCE'])
        draft['brev_markdown'] += '\n\nDiamandis siger mere.'
        with self.assertRaisesRegex(ValueError, '2 gange'):
            t['n'].validate_draft(draft, f['SOURCE'])

if __name__ == '__main__':
    unittest.main()
