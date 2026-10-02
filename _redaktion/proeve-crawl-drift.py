"""Offline: tidsgrænser, parallel kildekontrol og genoptagelse efter afbrydelse."""
import copy
import io
import json
import runpy
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier, Lock
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import crawler as c
from _redaktion.crawl_drift import Drift, TidOpbrugt

fixture = runpy.run_path(str(ROOT / '_redaktion/proeve-redaktoer-agent.py'))
artikel, KILDE = fixture['artikel'], fixture['KILDE']
DRAFT = json.loads((ROOT / '_redaktion/fixtures/faerdig-artikel.json').read_text())


class DriftTests(unittest.TestCase):
    def test_fase_stopper_kald_og_reserverer_resten_af_koerslen(self):
        now = [0]
        with tempfile.TemporaryDirectory() as tmp:
            d = Drift(tmp, clock=lambda: now[0])
            with d.fase('Artikler', 1):
                self.assertEqual(d.tid(), 60)
                now[0] = 56
                with self.assertRaises(TidOpbrugt):
                    d.tid()
            self.assertEqual(d.tid(), 180)
            now[0] = 75 * 60
            with self.assertRaises(TidOpbrugt):
                d.tid()

    def test_cache_overlever_afbrudt_koersel_og_ignoreres_efter_ny_udgivelse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'data').mkdir()
            basis = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            (root / 'data/articles.json').write_text(json.dumps({'opdateret': basis}))
            a = artikel('Nova'); a['publicering'] = {'status': 'godkendt'}
            Drift(root).gem([a])
            d = Drift(root)
            self.assertEqual(d.laes(basis)[0]['link'], a['link'])
            self.assertEqual(d.laes(datetime.now(timezone.utc).isoformat()), [])
            old = json.loads(d.cache.read_text())
            old['opdateret'] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
            d.cache.write_text(json.dumps(old))
            self.assertEqual(d.laes(basis), [])
            d.cache.write_text('{ufærdig')
            self.assertEqual(d.laes(basis), [])

    def test_chefaendringer_gemmes_foerst_efter_udgavekontrollen(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Drift(tmp); a = artikel('Nova'); original = copy.deepcopy(a)
            d.beskyttede = {a['link']: original}
            a['rubrik'] = 'Afventer samlet kildekontrol'
            d.gem([a])
            self.assertEqual(d.laes()[0]['rubrik'], original['rubrik'])
            d.beskyttede = {}
            d.gem([a])
            self.assertEqual(d.laes()[0]['rubrik'], a['rubrik'])

    def test_nye_billeder_genbruges_efter_afbrydelse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); d = Drift(root)
            a = artikel('Nova'); a['billede'] = 'data/img/0123456789abcdef.webp'
            path = root / a['billede']; path.parent.mkdir(parents=True)
            path.write_bytes(b'fixture-image')
            d.gem([a]); path.unlink()
            self.assertEqual(Drift(root).laes()[0]['billede'], a['billede'])
            self.assertEqual(path.read_bytes(), b'fixture-image')
            self.assertIsNone(d.billednavn('data/img/../../secret'))

    def test_tidsbudget_udloeser_ikke_nyt_reservekald(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(c, '_drift', Drift(tmp)), \
             patch.object(c, '_hjerner_cache', {'brief': {'model': 'deepseek-flash'}}), \
             patch.object(c, 'DEEPSEEK_KEY', 'test'), \
             patch.object(c, 'kald_deepseek_model', side_effect=TidOpbrugt('stop')), \
             patch.object(c, 'kald_ai') as fallback:
            with self.assertRaises(TidOpbrugt):
                c.hjerne_kald('brief', 'system', 'tekst', 1000)
            fallback.assert_not_called()

    def test_transport_faar_kort_timeout_kun_under_crawl(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(c, '_drift', Drift(tmp)), \
             patch.object(c.urllib.request, 'urlopen', return_value=io.BytesIO(b'{}')) as url:
            self.assertEqual(c.hent_url('https://example.com', timeout=600), b'{}')
            self.assertEqual(url.call_args.kwargs['timeout'], 180)
        with patch.object(c, '_drift', None), \
             patch.object(c.urllib.request, 'urlopen', return_value=io.BytesIO(b'{}')) as url:
            c.hent_url('https://example.com', timeout=600)
            self.assertEqual(url.call_args.kwargs['timeout'], 600)

    def test_parallelle_artikler_isolerer_afvisning_og_genbruger_faerdigt_arbejde(self):
        rows = [artikel(f'Nova-{i}') for i in range(3)]
        barrier = Barrier(3)
        lock = Lock(); aktive = [0, 0]
        def skriv(a, *_args, **kwargs):
            with lock:
                aktive[0] += 1; aktive[1] = max(aktive[1], aktive[0])
            barrier.wait(timeout=3)
            with lock:
                aktive[0] -= 1
            return copy.deepcopy(DRAFT)
        def kontrol(a, *_args):
            return {'godkendt': a['link'] != rows[1]['link'],
                    'problemer': [] if a['link'] != rows[1]['link'] else ['Mangler belæg']}
        # Et afvist udkast kræver endnu et skriveforsøg. Barrier bruges kun første gang.
        first = set()
        def writer(a, *args, **kwargs):
            with lock:
                ny = a['link'] not in first; first.add(a['link'])
            return skriv(a, *args, **kwargs) if ny else copy.deepcopy(DRAFT)
        before = copy.deepcopy(rows[1])
        with tempfile.TemporaryDirectory() as tmp, patch.object(c, '_drift', Drift(tmp)), \
             patch.object(c, 'API_KEY', 'test'), patch.object(c, 'UDBYDER', 'xiaomi'), \
             patch.object(c, '_hjerner_cache', {}), patch.object(c, 'GENKOER_ALT', False), \
             patch.object(c, 'GENKOER_FILTER', ''), patch.object(c, 'kald_ai_brief', side_effect=writer) as ai, \
             patch.object(c, 'redaktoer_tjek', side_effect=kontrol):
            c.dybe_briefs(rows, kildetekster={a['link']: KILDE for a in rows})
            self.assertEqual(aktive[1], 3)
            self.assertEqual(rows[1], before)
            self.assertTrue(c.udgivelse.klar(rows[0]))
            self.assertTrue(c.udgivelse.klar(rows[2]))
            saved = c._drift.laes()
            self.assertEqual(sum(c.udgivelse.klar(a) for a in saved), 2)
            # En ny proces genbruger de kontrollerede artikler uden flere skrivekald.
            count = ai.call_count
            c.dybe_briefs([a for a in saved if c.udgivelse.klar(a)],
                          kildetekster={a['link']: KILDE for a in rows})
            self.assertEqual(ai.call_count, count)

    def test_udloebet_budget_bevarer_artikler_og_afviser_ufuldt_chefarbejde(self):
        rows = [artikel('Nova')]; before = copy.deepcopy(rows[0])
        with tempfile.TemporaryDirectory() as tmp:
            d = Drift(tmp, clock=lambda: 0); d.slut = 0
            with patch.object(c, '_drift', d), patch.object(c, 'API_KEY', 'test'), \
                 patch.object(c, 'GENKOER_ALT', False), patch.object(c, 'GENKOER_FILTER', ''), \
                 patch.object(c, 'kald_ai_brief') as writer:
                c.dybe_briefs(rows, {rows[0]['link']: 'Chefbestilling'}, {rows[0]['link']: KILDE})
            writer.assert_not_called()
            self.assertTrue(rows[0].pop('redaktoer_afvist'))
            self.assertEqual(rows[0], before)

    def test_faerdige_artikler_optager_ikke_nye_artiklers_skrivebudget(self):
        gammel, ny = artikel('Gammel'), artikel('Ny')
        c._anvend_brief(gammel, copy.deepcopy(DRAFT), [])
        gammel['publicering'] = {'status': 'godkendt'}
        gammel['brief_instruks'] = c.instruks_signatur('brief', 'redaktoer')
        with patch.object(c, 'API_KEY', 'test'), patch.object(c, 'DYBDE_ANTAL', 1), \
             patch.object(c, 'GENKOER_ALT', False), patch.object(c, 'GENKOER_FILTER', ''), \
             patch.object(c, 'kald_ai_brief', return_value=copy.deepcopy(DRAFT)) as writer, \
             patch.object(c, 'redaktoer_tjek', return_value={'godkendt': True, 'problemer': []}):
            c.dybe_briefs([gammel, ny], kildetekster={ny['link']: KILDE})
            self.assertEqual(writer.call_count, 1)
            self.assertEqual(writer.call_args.args[0]['link'], ny['link'])
            self.assertTrue(c.udgivelse.klar(ny))

    def test_dubletkontrol_genbruges_men_nye_instrukser_udloeser_kald(self):
        nu = datetime.now(timezone.utc)
        rows = [artikel('Ny hardware', dato=nu.isoformat()), artikel('AI lovgivning', dato=nu.isoformat())]
        for a in rows:
            c._anvend_brief(a, copy.deepcopy(DRAFT), [])
            a['rubrik'] = a['titel']
            a['publicering'] = {'status': 'godkendt'}
        with tempfile.TemporaryDirectory() as tmp, patch.object(c, 'ROOT', Path(tmp)), \
             patch.object(c, '_drift', Drift(tmp)), patch.object(c, 'API_KEY', 'test'), \
             patch.object(c, '_hjerner_cache', {}) as config, \
             patch.object(c, '_klynger', return_value=[]), \
             patch.object(c, 'hjerne_kald', return_value='[]') as ai:
            c.saml_dublet_historier(copy.deepcopy(rows))
            c.saml_dublet_historier(copy.deepcopy(rows))
            self.assertEqual(ai.call_count, 1)
            config['dublet'] = {'prompt': 'Læs den konkrete nye hændelse'}
            c.saml_dublet_historier(copy.deepcopy(rows))
            self.assertEqual(ai.call_count, 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
