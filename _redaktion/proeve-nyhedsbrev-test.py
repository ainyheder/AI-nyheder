"""Test Gmail-isolation og AI-kontrol uden rigtige kald."""
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
t = runpy.run_path(str(ROOT / '_redaktion/send-nyhedsbrev-test.py'))
f = runpy.run_path(str(ROOT / '_redaktion/proeve-nyhedsbrev.py'))

class TestMail(unittest.TestCase):
    def test_supplied_full_source_avoids_remote_feed(self):
        from unittest.mock import patch
        with patch.object(t['n'], 'fetch_feed', side_effect=AssertionError('Må ikke genhente')):
            self.assertEqual(t['source_for_test']({}, json.dumps(f['SOURCE'])), f['SOURCE'])
        with self.assertRaises(ValueError):
            t['source_for_test']({}, json.dumps({**f['SOURCE'], 'url': 'https://example.com/fake'}))

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
        self.assertEqual(ai.call_count, 4)

    def test_rejected_output_never_returns_a_letter(self):
        ai = Mock(return_value={'status': 'kraever_mere_materiale'})
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            t['generate'](f['SOURCE'], f['CONFIG'], Path(tmp), ai)
        self.assertEqual(ai.call_count, 3)

if __name__ == '__main__':
    unittest.main()
