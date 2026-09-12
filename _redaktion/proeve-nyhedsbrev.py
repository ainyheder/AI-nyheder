"""Ingen netværk, rigtig AI eller mail. Test udsendelsesgrænser og genoptagelse."""
import copy
import contextlib
import io
import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

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
    def test_deepseek_diagnostics_never_expose_reasoning_or_provider_text(self):
        import crawler
        reply = {'choices': [{'finish_reason': 'stop', 'message': {
            'content': '{"ok": true}', 'reasoning_content': 'PRIVATE REASONING'}}],
            'usage': {'prompt_tokens': 12, 'completion_tokens': 20,
                      'completion_tokens_details': {'reasoning_tokens': 15}}}
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            self.assertEqual(crawler.deepseek_json_svar(json.dumps(reply).encode()), '{"ok": true}')
        self.assertIn('"reasoning_tokens": 15', log.getvalue())
        self.assertNotIn('PRIVATE', log.getvalue())
        for reason, content in [('length', '{"ok": true}'), ('stop', ''),
                                ('stop', 'PRIVATE PROVIDER TEXT'), ('stop', '[]'),
                                ('insufficient_system_resource', '')]:
            bad = copy.deepcopy(reply)
            bad['choices'][0].update(finish_reason=reason)
            bad['choices'][0]['message']['content'] = content
            with contextlib.redirect_stdout(log), self.assertRaises(crawler.DeepSeekSvarFejl) as failure:
                crawler.deepseek_json_svar(json.dumps(bad).encode())
            self.assertNotIn('PRIVATE', str(failure.exception))
            self.assertNotIn('PRIVATE', log.getvalue())
        for raw in (b'PRIVATE PROVIDER TEXT', b'{"error": "PRIVATE PROVIDER TEXT"}'):
            with self.assertRaises(crawler.DeepSeekSvarFejl) as failure:
                crawler.deepseek_json_svar(raw)
            self.assertNotIn('PRIVATE', str(failure.exception))

    def test_broken_max_reply_does_not_trigger_hidden_fallback_generation(self):
        import crawler
        with patch.object(crawler, 'hjerne_model', return_value='deepseek-flash'), \
             patch.object(crawler, '_doede_modeller', set()), \
             patch.object(crawler, '_udbyder_noegle', return_value=True), \
             patch.object(crawler, 'kald_deepseek_model', side_effect=http.client.IncompleteRead(b'private')), \
             patch.object(crawler, 'kald_ai') as fallback:
            with self.assertRaisesRegex(crawler.DeepSeekSvarFejl, 'IncompleteRead'):
                crawler.hjerne_kald('nyhedsbrev', 'JSON', 'data', 32768, reasoning_effort='max')
            fallback.assert_not_called()

    def test_writer_and_reviewer_use_flash_with_max_from_settings(self):
        import crawler
        config = json.loads((n.ROOT / "opsaetning/nyhedsbrev.json").read_text())
        self.assertEqual(config["model"], "deepseek-flash")
        self.assertEqual(config["reasoning_effort"], "max")
        with patch.object(crawler, 'hjerne_model', return_value=None), \
             patch.object(crawler, 'hjerne_kald', return_value='{"ok": true}') as call:
            for step, budget in (('nyhedsbrev', 32768), ('nyhedsbrev_kontrol', 65536)):
                self.assertEqual(n.ai_call(step, 'Prompt', {'original': SOURCE}), {'ok': True})
                self.assertEqual(call.call_args.args[0], step)
                self.assertEqual(call.call_args.args[3:5], (budget, 'deepseek-flash'))
                self.assertEqual(call.call_args.kwargs, {'reasoning_effort': 'max'})

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

    def test_rewrites_in_same_run_with_draft_and_both_kinds_of_feedback(self):
        store = Store(); api = API(store)
        rejected = draft()
        rejected["brev_markdown"] += "\n\nDiamandis gentages."
        review = {**REVIEW, "godkendt": False, "laesevaerdi": False,
                  "problemer": ["Intro og afslutning gentager samme forklaring"]}
        writer = Mock(side_effect=[rejected, review, draft(), REVIEW])
        self.run_flow(store, api, writer=writer)
        revision = writer.call_args_list[2].args[2]
        self.assertEqual(revision["tidligere_udkast"], rejected)
        self.assertIn("Kreditering:", revision["tidligere_fejl"])
        self.assertIn("gentager samme forklaring", revision["tidligere_fejl"])
        self.assertEqual(writer.call_count, 4)
        self.assertEqual((api.created, api.sent), (1, 1))
        self.assertEqual(store.durable["entries"]["new"]["forsog"], 2)
        self.assertNotIn("tidligere_udkast", store.durable["entries"]["new"])

    def test_rejected_draft_and_budget_survive_interrupted_revision(self):
        store = Store(); api = API(store)
        review = {**REVIEW, "godkendt": False, "problemer": ["Forkert tal i introen"]}
        writer = Mock(side_effect=[draft(), review, TimeoutError("AI afbrudt")])
        with self.assertRaises(TimeoutError):
            self.run_flow(store, api, writer=writer)
        self.assertEqual(store.durable["entries"]["new"]["forsog"], 2)
        self.assertEqual(store.durable["entries"]["new"]["tidligere_udkast"], draft())
        self.assertEqual(api.created, 0)
        fresh = Store(store.durable); api.store = fresh
        resumed = Mock(side_effect=[draft(), REVIEW])
        self.run_flow(fresh, api, writer=resumed)
        revision = resumed.call_args_list[0].args[2]
        self.assertEqual(revision["tidligere_udkast"], draft())
        self.assertIn("Forkert tal", revision["tidligere_fejl"])
        self.assertEqual(fresh.durable["entries"]["new"]["forsog"], 3)
        self.assertEqual(api.sent, 1)

    def test_malformed_review_is_held_and_repair_keeps_last_draft(self):
        store = Store(); api = API(store)
        writer = Mock(side_effect=[draft(), None, ValueError("Ugyldig AI-JSON"), REVIEW])
        self.run_flow(store, api, writer=writer)
        revision = writer.call_args_list[3].args[2]
        self.assertEqual(revision["udkast"], draft())
        self.assertEqual([c.args[0] for c in writer.call_args_list],
                         ["nyhedsbrev", "nyhedsbrev_kontrol", "nyhedsbrev_kontrol", "nyhedsbrev_kontrol"])
        self.assertEqual(store.durable["entries"]["new"]["forsog"], 3)
        self.assertEqual(api.sent, 1)

    def test_interrupted_review_resumes_saved_draft_in_fresh_job(self):
        store = Store(); api = API(store)
        writer = Mock(side_effect=[draft(), TimeoutError("Kontrollen afbrudt")])
        with self.assertRaises(TimeoutError):
            self.run_flow(store, api, writer=writer)
        saved = store.durable["entries"]["new"]
        self.assertEqual((saved["forsog"], saved["naeste_trin"]), (1, "kontrol"))
        self.assertEqual(saved["tidligere_udkast"], draft())
        self.assertEqual(api.created, 0)
        fresh = Store(store.durable); api.store = fresh
        reviewer = Mock(return_value=REVIEW)
        self.run_flow(fresh, api, writer=reviewer)
        self.assertEqual(reviewer.call_count, 1)
        self.assertEqual(reviewer.call_args.args[0], "nyhedsbrev_kontrol")
        self.assertEqual(reviewer.call_args.args[2]["udkast"], draft())
        self.assertEqual(api.sent, 1)

    def test_repeated_technical_review_failures_do_not_rewrite_or_reset_budget(self):
        import crawler
        store = Store(); api = API(store)
        writer = Mock(side_effect=[draft()] + [crawler.DeepSeekSvarFejl("Afslutning: length")] * 3)
        for _ in range(4):
            with self.assertRaises(ValueError):
                self.run_flow(store, api, writer=writer)
        self.assertEqual([c.args[0] for c in writer.call_args_list],
                         ["nyhedsbrev", "nyhedsbrev_kontrol", "nyhedsbrev_kontrol", "nyhedsbrev_kontrol"])
        self.assertEqual(store.durable["entries"]["new"]["forsog"], 3)
        self.assertEqual((api.created, api.sent), (0, 0))

    def test_review_retry_still_rewrites_after_substantive_rejection(self):
        store = Store(); api = API(store)
        rejected = {**REVIEW, "godkendt": False, "problemer": ["Forkert tal i introen"]}
        writer = Mock(side_effect=[draft(), RuntimeError("Tomt kontrolsvar"), rejected, draft(), REVIEW])
        self.run_flow(store, api, writer=writer)
        self.assertEqual([c.args[0] for c in writer.call_args_list],
                         ["nyhedsbrev", "nyhedsbrev_kontrol", "nyhedsbrev_kontrol", "nyhedsbrev", "nyhedsbrev_kontrol"])
        revision = writer.call_args_list[3].args[2]
        self.assertEqual(revision["tidligere_udkast"], draft())
        self.assertIn("Forkert tal", revision["tidligere_fejl"])
        self.assertEqual(api.sent, 1)

    def test_invalid_draft_cannot_skip_writing_after_review_failure(self):
        store = Store(); api = API(store)
        invalid = draft(); invalid["brev_markdown"] += "\n\nDiamandis igen."
        writer = Mock(side_effect=[invalid, RuntimeError("Tomt kontrolsvar"), draft(), REVIEW])
        self.run_flow(store, api, writer=writer)
        self.assertEqual(writer.call_args_list[2].args[0], "nyhedsbrev")
        self.assertIn("Kreditering", writer.call_args_list[2].args[2]["tidligere_fejl"])
        self.assertEqual(api.sent, 1)

    def test_review_resume_revalidates_source_metadata(self):
        changed = {**SOURCE, "titel": "Ny kildetitel"}
        writer = Mock(side_effect=[draft(changed), REVIEW])
        result = n.editorial_attempt(changed, "Writer", "Reviewer", draft(), ai=writer, review_only=True)
        self.assertEqual(writer.call_args_list[0].args[0], "nyhedsbrev")
        self.assertIn("metadata", writer.call_args_list[0].args[2]["tidligere_fejl"])
        self.assertNotIn("fejl", result)

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

    def test_buttondown_serialization_preserves_approved_content(self):
        body = '<style>\np { color:red; }\n</style><table><tr><td><p>Peter&#x27;s tekst &amp; forklaring</p></td></tr></table>'
        remote = '<!-- buttondown-editor-mode: fancy --><style>p { color:red; }</style><table><tbody><tr><td><p>Peter\'s tekst &amp; forklaring</p></td></tr></tbody></table>'
        self.assertTrue(n.unchanged_draft({'status':'draft','subject':'Prøve','body':remote}, 'Prøve', body))
        self.assertFalse(n.unchanged_draft({'status':'draft','subject':'Ændret','body':remote}, 'Prøve', body))
        self.assertFalse(n.unchanged_draft({'status':'sent','subject':'Prøve','body':remote}, 'Prøve', body))
        self.assertFalse(n.same_email_html(body, remote.replace('forklaring','anbefaling')))

    def test_html_comparison_preserves_links_images_styles_and_literal_text(self):
        body = '<p>&lt;b&gt;tekst&lt;/b&gt; <a href="https://example.org" style="color:red">Kilde</a></p><img src="https://example.org/a.png" alt="Illustration">'
        for changed in (body.replace('&lt;b&gt;tekst&lt;/b&gt;', '<b>tekst</b>'),
                        body.replace('https://example.org"', 'https://other.example"'),
                        body.replace('/a.png', '/b.png'), body.replace('Illustration', 'Fotografi'),
                        body.replace('color:red', 'color:white'), body.replace('</p>', '<script>run()</script></p>')):
            self.assertFalse(n.same_email_html(body, changed))
        self.assertFalse(n.same_email_html(body, None))

    def test_feed_uses_full_body_canonical_link_and_original_metadata(self):
        raw = b'''<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><item><title>Original</title><link>https://metatrends.substack.com/p/test?utm_source=mail</link><pubDate>Thu, 10 Sep 2026 16:54:27 GMT</pubDate><dc:creator>Peter H. Diamandis</dc:creator><description>Kort</description><content:encoded><![CDATA[<p>Hele teksten</p><script>Skjult</script>]]></content:encoded></item></channel></rss>'''
        items = n.feed_items(raw)
        self.assertEqual(items[0]["tekst"], "Hele teksten")
        self.assertEqual(items[0]["url"], "https://metatrends.substack.com/p/test")
        with self.assertRaises(ValueError): n.feed_items(raw.replace(b"metatrends.substack.com", b"localhost"))
        with self.assertRaises(ValueError): n.feed_items(b"<!DOCTYPE rss>" + raw)

    def test_visual_blocks_keep_values_qualifiers_and_links_without_copying_them(self):
        content = draft()
        content['brev_markdown'] = ('# En overskrift\n\nKort intro.\n\n'
            '| Måling | Beregning |\n| --- | --- |\n| **12** | **300** |\n'
            '| Eksperimentelt bestemt | Skal efterprøves |\n\n'
            '> **Vigtig forskel.** [Kilden](https://example.org/fakta) beskriver usikkerheden.\n\n'
            '- **Først:** Find mønstret.\n- **Dernæst:** Undersøg årsagen.')
        result = n.render(content)
        parser = n.TextOnly(); parser.feed(result)
        text = ' '.join(''.join(parser.parts).split())
        for value in ('12', '300', 'Eksperimentelt bestemt', 'Skal efterprøves', 'Vigtig forskel.', 'Find mønstret.', 'Undersøg årsagen.'):
            self.assertEqual(text.count(value), 1)
        self.assertLess(text.index('12'), text.index('Eksperimentelt bestemt'))
        self.assertLess(text.index('300'), text.index('Skal efterprøves'))
        self.assertEqual(result.count('<li '), 2)
        self.assertNotIn('<blockquote', result)
        self.assertIn('href="https://example.org/fakta"', result)

    def test_visual_cells_and_highlights_escape_untrusted_content(self):
        content = draft()
        content['brev_markdown'] = ('# Test\n\n| <script>x</script> | Sikker |\n| --- | --- |\n'
            '| **<img src=x>** | [Klik](javascript:alert) |\n\n'
            '> <img src=x onerror=alert(1)>\n\n- <script>attack</script>')
        result = n.render(content)
        self.assertNotIn('<script', result)
        self.assertNotIn('<img', result)
        self.assertNotIn('href="javascript:', result)
        self.assertIn('&lt;script&gt;', result)
        self.assertIn('&lt;img', result)

    def test_double_escaped_newlines_stop_before_a_broken_email_is_rendered(self):
        content = draft()
        content['brev_markdown'] = content['brev_markdown'].replace('\n', r'\n')
        with self.assertRaisesRegex(ValueError, 'linjeskift'):
            n.validate_draft(content, SOURCE)
        with self.assertRaisesRegex(ValueError, 'linjeskift'):
            n.render(content)

    def test_image_generation_is_checkpointed_reused_and_limited(self):
        spec = {'placering': 'intro', 'motiv': 'En planet', 'alt': 'AI-illustration: en forestillet planet.'}
        entry = {'url': SOURCE['url'], 'draft': {**draft(), 'illustrationer': [spec]}}
        api = Mock(); api.upload_image.return_value = {'id': 'im_test', 'image': 'https://example.org/planet.png'}
        saved = []
        def save(): saved.append(copy.deepcopy(entry))
        def make(motif):
            self.assertEqual(list(saved[-1]['billeder'].values())[0]['status'], 'genererer')
            return b'PNG'
        generator = Mock(side_effect=make)
        config = {'billeder': {'aktiv': True, 'maks_pr_brev': 1}}
        first = n.nyhedsbrev_billeder.prepare(entry, config, api, save, generator)
        second = n.nyhedsbrev_billeder.prepare(entry, config, api, save, generator)
        self.assertEqual(first, second)
        self.assertEqual(generator.call_count, 1)
        self.assertEqual(api.upload_image.call_count, 1)
        entry['draft']['illustrationer'][0]['motiv'] = 'Et ændret motiv'
        n.nyhedsbrev_billeder.prepare(entry, config, api, save, generator)
        self.assertEqual(generator.call_count, 1)

    def test_image_failure_or_interruption_never_inserts_a_dark_original(self):
        entry = {'url': SOURCE['url'], 'draft': {**draft(), 'illustrationer': [
            {'placering': 'intro', 'motiv': 'Et protein', 'alt': 'AI-illustration: protein.'}]}}
        config = {'billeder': {'aktiv': True}}
        generator = Mock(side_effect=ValueError('Dårlig maske')); api = Mock()
        self.assertEqual(n.nyhedsbrev_billeder.prepare(entry, config, api, lambda: None, generator), [])
        self.assertEqual(n.nyhedsbrev_billeder.prepare(entry, config, api, lambda: None, generator), [])
        self.assertEqual(generator.call_count, 1)
        api.upload_image.assert_not_called()
        record = next(iter(entry['billeder'].values()))
        record['status'] = 'genererer'
        self.assertEqual(n.nyhedsbrev_billeder.prepare(entry, config, api, lambda: None, generator), [])
        self.assertEqual(generator.call_count, 1)
        entry['billeder'] = {}
        def failed_save(): raise OSError('Status kunne ikke gemmes')
        with self.assertRaises(OSError):
            n.nyhedsbrev_billeder.prepare(entry, config, api, failed_save, generator)
        self.assertEqual(generator.call_count, 1)

    def test_images_only_reach_rendering_after_approved_review(self):
        store = Store(); api = API(store)
        def prepared(entry, config, api, save):
            self.assertEqual(entry['status'], 'illustrerer')
            self.assertEqual(store.durable['entries']['new']['kontrol'], REVIEW)
            return [{'placering': 'intro', 'url': 'https://example.org/planet.png', 'alt': 'AI-illustration: planet.'}]
        with patch.object(n.nyhedsbrev_billeder, 'prepare', side_effect=prepared) as images:
            self.run_flow(store, api)
        images.assert_called_once()
        self.assertIn('src="https://example.org/planet.png"', api.email['body'])
        rejected = lambda step, prompt, payload: draft() if step == 'nyhedsbrev' else {**REVIEW, 'godkendt': False}
        with patch.object(n.nyhedsbrev_billeder, 'prepare') as images:
            with self.assertRaises(ValueError): self.run_flow(Store(), API(Store()), writer=rejected)
        images.assert_not_called()

    def test_image_plan_and_renderer_reject_unsafe_or_ambiguous_placement(self):
        item = {'placering': 'intro', 'motiv': 'En planet', 'alt': 'AI-illustration: planet.'}
        for plan in ([item]*3, [item,item], [{**item,'placering':'Ukendt'}], [{**item,'alt':'Et fotografi'}]):
            with self.assertRaises(ValueError): n.validate_draft({**draft(),'illustrationer':plan}, SOURCE)
        with self.assertRaises(ValueError):
            n.render(draft(), [{**item, 'url':'javascript:alert(1)'}])
        with self.assertRaises(ValueError):
            n.render(draft(), [{**item, 'url':'illustrationer/planet.png'}])
        local = n.render(draft(), [{**item, 'url':'illustrationer/planet.png'}], preview=True)
        self.assertIn('src="illustrationer/planet.png"', local)
        self.assertEqual(local.count('<img '), 1)

    def test_buttondown_image_upload_uses_documented_multipart_endpoint(self):
        import io
        requests = []
        def response(request, timeout):
            requests.append(request)
            return io.BytesIO(b'{"id":"im_test","image":"https://example.org/planet.png"}')
        png = b'\x89PNG\r\n\x1a\n' + b'image fixture'
        with patch.object(n, 'urlopen', side_effect=response):
            n.Buttondown('test-token').upload_image(png, 'test-image')
        request = requests[0]
        self.assertEqual(request.full_url, 'https://api.buttondown.com/v1/images')
        self.assertEqual(request.method, 'POST')
        self.assertIn(b'name="image"', request.data)
        self.assertIn(b'Content-Type: image/png', request.data)
        self.assertIn(png, request.data)

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
