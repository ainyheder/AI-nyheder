"""Ingen netværk, rigtig AI eller mail. Test udsendelsesgrænser og genoptagelse."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nyhedsbrev as n

CONFIG = {"nye_fra": "2026-09-12T00:00:00+00:00", "maks_forsog": 3}
SOURCE = {"id": "new", "url": "https://metatrends.substack.com/p/new-letter", "titel": "New letter",
          "dato": "2026-09-13T00:00:00+00:00", "forfatter": "Peter H. Diamandis", "tekst": "original " * 600}
REVIEW = {k: True for k in ("godkendt", "fuld_kilde", "faktuel_troskab", "selvstaendig", "laesevaerdi")}
REVIEW["problemer"] = []


def draft(source=SOURCE):
    # Indholdet er en teknisk fixture; ingen test hævder at kontrollere AI-kvalitet.
    return {"status": "udkast", "emne": "En ny forståelse", "preheader": "Et konkret eksempel.",
            "brev_markdown": "# En ny forståelse\n\nLæs [Peter Diamandis’ læserbrev](" + source["url"] + ").\n\n" + "Forklaring med eksempel. " * 240,
            "redaktionsnote": {"original": {k: source[k] for k in ("url", "titel", "dato", "forfatter")},
                               "uafklaret": [], "hovedide": "Ny forståelse", "bevarede_pointer": ["Eksempel"],
                               "selvstaendige_greb": ["Ny disposition"]}}


class Store:
    def __init__(self, state=None):
        self.state = copy.deepcopy(state or {"version": 1, "entries": {}})
        self.durable = copy.deepcopy(self.state)
        self.fail_on = None

    def save(self):
        if any(e["status"] == self.fail_on for e in self.state["entries"].values()):
            raise OSError("Simuleret pushfejl")
        self.durable = copy.deepcopy(self.state)


class API:
    def __init__(self, store):
        self.store = store
        self.created = self.sent = 0
        self.email = None
        self.timeout_create = self.timeout_send = False
        self.edit_draft = False

    def create(self, entry):
        assert self.store.durable["entries"][entry["id"]]["status"] == "opretter"
        self.created += 1
        self.email = {"id": "em_test", "status": "draft", "body": entry["html"], "subject": entry["draft"]["emne"]}
        if self.timeout_create:
            raise TimeoutError()
        return copy.deepcopy(self.email)

    def get(self, email_id):
        assert email_id == "em_test"
        email = copy.deepcopy(self.email)
        if self.edit_draft:
            email["body"] += " Ændret"
        return email

    def send(self, email_id, url):
        assert self.store.durable["entries"]["new"]["status"] == "sender"
        self.sent += 1
        self.email["status"] = "about_to_send"
        if self.timeout_send:
            raise TimeoutError()
        return copy.deepcopy(self.email)


def ai(step, prompt, payload):
    if step == "nyhedsbrev":
        assert payload["original"]["tekst"]
        return draft(payload["original"])
    assert payload["original"]["tekst"] and payload["udkast"]
    return copy.deepcopy(REVIEW)


class NewsletterTests(unittest.TestCase):
    def run_flow(self, store, api, items=None, writer=ai):
        n.process(items if items is not None else [SOURCE], CONFIG, store, api, writer)

    def test_one_send_across_fresh_jobs_and_modified_original(self):
        store = Store(); api = API(store)
        self.run_flow(store, api)
        fresh = Store(store.durable); api.store = fresh
        self.run_flow(fresh, api, [{**SOURCE, "tekst": "rettet " * 600}])
        self.assertEqual((api.created, api.sent), (1, 1))
        self.assertEqual(fresh.state["entries"]["new"]["status"], "overdraget")

    def test_old_original_never_sent(self):
        store = Store(); api = API(store)
        self.run_flow(store, api, [{**SOURCE, "dato": "2026-09-10T00:00:00+00:00"}])
        self.assertEqual(api.created, 0)
        self.assertEqual(store.state["entries"]["new"]["status"], "baseline")

    def test_separate_review_blocks_and_limits_retries(self):
        store = Store(); api = API(store); calls = []
        def reject(step, prompt, payload):
            calls.append(step)
            return ai(step, prompt, payload) if step == "nyhedsbrev" else {**REVIEW, "faktuel_troskab": False, "problemer": ["Forkert tal"]}
        for _ in range(4):
            with self.assertRaises(ValueError): self.run_flow(store, api, writer=reject)
        self.assertEqual(api.created, 0)
        self.assertEqual(calls.count("nyhedsbrev"), 3)
        self.assertIn("Forkert tal", store.state["entries"]["new"]["fejl"])

    def test_incomplete_or_other_author_never_reaches_ai(self):
        for changes in ({"tekst": "Et uddrag"}, {"forfatter": "Ukendt"}):
            store = Store(); api = API(store)
            with self.assertRaises(ValueError):
                self.run_flow(store, api, [{**SOURCE, **changes}], writer=lambda *a: self.fail("AI kaldt"))
            self.assertEqual(api.created, 0)

    def test_checkpoint_failure_prevents_external_creation_or_send(self):
        for status, expected_creates in (("opretter", 0), ("sender", 1)):
            store = Store(); store.fail_on = status; api = API(store)
            with self.assertRaises(OSError): self.run_flow(store, api)
            self.assertEqual(api.created, expected_creates)
            self.assertEqual(api.sent, 0)

    def test_unknown_creation_stops_without_another_draft(self):
        store = Store(); api = API(store); api.timeout_create = True
        with self.assertRaises(TimeoutError): self.run_flow(store, api)
        fresh = Store(store.durable); api.store = fresh
        with self.assertRaises(ValueError): self.run_flow(fresh, api)
        self.assertEqual((api.created, api.sent), (1, 0))

    def test_send_timeout_reconciles_without_resend(self):
        store = Store(); api = API(store); api.timeout_send = True
        with self.assertRaises(TimeoutError): self.run_flow(store, api)
        fresh = Store(store.durable); api.store = fresh
        self.run_flow(fresh, api)
        self.assertEqual(api.sent, 1)
        self.assertEqual(fresh.state["entries"]["new"]["status"], "overdraget")

    def test_unknown_send_with_remote_draft_does_not_retry(self):
        store = Store(); api = API(store); api.timeout_send = True
        with self.assertRaises(TimeoutError): self.run_flow(store, api)
        api.email["status"] = "draft"
        fresh = Store(store.durable); api.store = fresh
        with self.assertRaises(ValueError): self.run_flow(fresh, api)
        self.assertEqual(api.sent, 1)

    def test_manually_edited_draft_is_held(self):
        store = Store(); api = API(store); api.edit_draft = True
        with self.assertRaises(ValueError): self.run_flow(store, api)
        self.assertEqual(api.sent, 0)

    def test_resume_approved_draft_after_source_leaves_feed(self):
        store = Store(); store.fail_on = "opretter"; api = API(store)
        with self.assertRaises(OSError): self.run_flow(store, api)
        fresh = Store(store.durable); api.store = fresh
        self.run_flow(fresh, api, [])
        self.assertEqual(api.sent, 1)

    def test_quality_schema_and_credit_fail_closed(self):
        for change in ({"status": "kraever_rettighedsafklaring"}, {"brev_markdown": "For kort"},
                       {"redaktionsnote": {"uafklaret": ["Mangler belæg"]}}):
            with self.assertRaises(ValueError): n.validate_draft({**draft(), **change}, SOURCE)
        for change in ({"godkendt": "true"}, {"fuld_kilde": False}, {"problemer": ["Manglende kilde"]}):
            with self.assertRaises(ValueError): n.validate_review({**REVIEW, **change})
        bad = draft(); bad["brev_markdown"] += "\n\nAfmeld her"
        with self.assertRaises(ValueError): n.validate_draft(bad, SOURCE)

    def test_renderer_escapes_html_and_unsafe_links_without_extra_footer(self):
        rendered = n.render(draft())
        self.assertIn("#d5ff5f", rendered)
        self.assertNotIn("{{ unsubscribe_url }}", rendered)
        self.assertEqual(rendered.count('href="' + SOURCE["url"] + '"'), 1)
        self.assertNotIn('href="javascript:', n.inline('[Klik](javascript:alert)'))
        self.assertIn('&lt;script&gt;', n.inline('<script>attack</script>'))

    def test_feed_uses_full_body_canonical_link_and_original_metadata(self):
        raw = b'''<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><item><title>Original</title><link>https://metatrends.substack.com/p/test?utm_source=mail</link><pubDate>Thu, 10 Sep 2026 16:54:27 GMT</pubDate><dc:creator>Peter H. Diamandis</dc:creator><description>Kort</description><content:encoded><![CDATA[<p>Hele teksten</p><script>Skjult</script>]]></content:encoded></item></channel></rss>'''
        items = n.feed_items(raw)
        self.assertEqual(items[0]["tekst"], "Hele teksten")
        self.assertEqual(items[0]["url"], "https://metatrends.substack.com/p/test")
        with self.assertRaises(ValueError): n.feed_items(raw.replace(b"metatrends.substack.com", b"localhost"))
        with self.assertRaises(ValueError): n.feed_items(b"<!DOCTYPE rss>" + raw)

    def test_buttondown_uses_draft_then_patch_with_distinct_stable_keys(self):
        import io
        requests = []
        def response(request, timeout):
            requests.append(request)
            return io.BytesIO(json.dumps({"id": "em_test", "status": "draft"}).encode())
        entry = {"draft": draft(), "html": n.render(draft()), "url": SOURCE["url"]}
        api = n.Buttondown("test-token")
        with patch.object(n, 'urlopen', side_effect=response):
            api.create(entry); api.create(entry); api.get('em_test'); api.send('em_test', SOURCE['url'])
        self.assertEqual([r.method for r in requests], ['POST', 'POST', 'GET', 'PATCH'])
        self.assertEqual(json.loads(requests[0].data)['status'], 'draft')
        self.assertEqual(json.loads(requests[3].data)['status'], 'about_to_send')
        self.assertEqual(requests[0].get_header('X-idempotency-key'), requests[1].get_header('X-idempotency-key'))
        self.assertNotEqual(requests[0].get_header('X-idempotency-key'), requests[3].get_header('X-idempotency-key'))
        self.assertTrue(requests[3].get_header('X-idempotency-key'))

    def test_weekly_page_no_longer_dispatches_even_if_old_flag_is_true(self):
        import crawler
        source = Path(crawler.__file__).read_text()
        function = source[source.index('def lav_ugens_overblik('):source.index('# ----- Statiske artikelsider')]
        self.assertNotIn('_udgiv_fredagsbrev(', function)
        workflow = (n.ROOT / '.github/workflows/crawl.yml').read_text()
        self.assertNotIn('BUTTONDOWN_API_KEY', workflow)

    def test_git_checkpoint_survives_new_clone_and_rejects_missing_state(self):
        def git(folder, *args):
            return subprocess.run(['git', *args], cwd=folder, check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); remote = root / 'remote.git'; work = root / 'work'
            git(root, 'init', '--bare', str(remote)); work.mkdir(); git(work, 'init')
            git(work, 'switch', '--orphan', n.STATE_BRANCH)
            git(work, 'config', 'user.name', 'Test'); git(work, 'config', 'user.email', 'test@example.invalid')
            git(work, 'remote', 'add', 'origin', str(remote))
            store = n.GitStore(work); store.state['entries']['x'] = {'status': 'sender'}; store.save()
            git(root, 'clone', '--branch', n.STATE_BRANCH, str(remote), str(root / 'fresh'))
            fresh = n.GitStore(root / 'fresh')
            self.assertEqual(fresh.state['entries']['x']['status'], 'sender')
            (root / 'fresh/state.json').unlink()
            with self.assertRaises(ValueError): n.GitStore(root / 'fresh')


if __name__ == '__main__':
    unittest.main()
