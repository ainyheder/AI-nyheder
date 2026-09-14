"""Kladder, genomtaler og modeloversigt. Ingen netværk eller rigtige API-kald."""
import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import crawler as c
import udgivelse as u
import redaktion as r
import modellanceringer as m

NU = datetime.now(timezone.utc)
DRAFT = json.loads((ROOT / '_redaktion/fixtures/faerdig-artikel.json').read_text())


def artikel(slug='nova', age=1):
    return {**copy.deepcopy(DRAFT), 'titel': DRAFT['rubrik'], 'resume_da': DRAFT['resume'],
            'link': 'https://example.com/' + slug, 'kilde': 'Eksempelkilden',
            'side': 'artikel/' + slug + '.html', 'dato': (NU-timedelta(days=age)).isoformat(),
            'publicering': {'status': 'godkendt'}, 'kategori': 'Lanceringer',
            'redaktion': {'version': 3, 'type':'lancering', 'model_lancering':True,
                         'nyhed':5, 'betydning':4, 'brugbarhed':4, 'dokumentation':4, 'dansk':0,
                         'ai_relevant': True, 'emne':'Nova'}}


class UdgivelseTests(unittest.TestCase):
    def test_ufuldstaendigt_eller_ukontrolleret_indhold_holdes_tilbage(self):
        self.assertTrue(u.klar(artikel()))
        for change in ({'sektioner': []}, {'resume_da':''}, {'rubrik':''},
                       {'sektioner':[{'overskrift':'Kort', 'tekst':'Tre linjer er ikke en artikel.'}]},
                       {'publicering': None}, {'publicering':'godkendt'},
                       {'kun_aktuel':True}, {'brief':'Resuméet mangler'}):
            with self.subTest(change=change): self.assertFalse(u.klar({**artikel(), **change}))
        a=artikel(); a['sektioner'].append({'overskrift':'Senere', 'tekst':''})
        self.assertFalse(u.klar(a))
        a=artikel(); a['sektioner'][1]['tekst']=a['sektioner'][0]['tekst']
        self.assertFalse(u.klar(a))

    def test_tidligere_kildegodkendelse_kan_bevares(self):
        a=artikel(); a.pop('publicering'); a['brief_instruks']='tidligere-kildekontrol'
        self.assertTrue(u.klar(a))
        a['sektioner']=[]
        self.assertFalse(u.klar(a))
        a=artikel(); a['brief_instruks']='gammel'; a['publicering']={'status':'afvist'}
        self.assertFalse(u.klar(a))

    def test_kladden_overlever_til_naeste_koersel_og_forlader_koeen_efter_godkendelse(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'udgivelsesdata.json'
            draft=artikel(); draft.pop('publicering'); draft.pop('sektioner')
            self.assertEqual(u.gem(path,[draft],[],NU), [])
            saved=u.laes(path); self.assertEqual(saved['kladder'][0]['link'],draft['link'])
            a=saved['kladder'][0]
            with patch.object(c,'API_KEY','test'), patch.object(c,'GENKOER_ALT',False), patch.object(c,'GENKOER_FILTER',''), patch.object(c,'kald_ai_brief',return_value=DRAFT), patch.object(c,'redaktoer_tjek',return_value={'godkendt':True,'problemer':[]}):
                c.dybe_briefs([a], kildetekster={a['link']:'Det fulde kildemateriale. '*100})
            self.assertTrue(u.klar(a))
            self.assertEqual(len(u.gem(path,[a],saved['historik'],NU)),1)
            self.assertEqual(u.laes(path)['kladder'],[])

    def test_kort_feedtekst_erstatter_ikke_den_fulde_kilde(self):
        a=artikel(); a.pop('publicering'); a.pop('sektioner')
        with patch.object(c,'API_KEY','test'), patch.object(c,'GENKOER_ALT',False), patch.object(c,'GENKOER_FILTER',''), patch.object(c,'hent_artikeltekst',return_value=(a,'Kort feedtekst',[])), patch.object(c,'kald_ai_brief') as writer:
            c.dybe_briefs([a])
        writer.assert_not_called()
        self.assertFalse(u.klar(a))

    def test_senere_omtale_beholder_den_oprindelige_historie_og_dato(self):
        old,new=artikel('gammel',20),artikel('ny-omtale',1)
        old['rubrik']='Anthropic-forsker forlader selskabet med en advarsel'
        new['rubrik']='Podcasten diskuterer Anthropic-forskerens opsigelse'
        for a in (old,new):
            a['titel']=a['rubrik']; a['resume_da']='Jacob Coxon har forladt Anthropic efter en advarsel om selvforbedrende kunstig intelligens og risiko for menneskeheden.'
        archive=[old]
        with patch.object(c,'API_KEY','test'), patch.object(c,'hjerne_kald',return_value='[[1,2]]') as ai:
            result=c.saml_dublet_historier([new],archive)
        self.assertEqual(result,[])
        self.assertIn(DRAFT['sektioner'][0]['tekst'].split('\n')[0],ai.call_args.args[2])
        self.assertEqual(r.dato(old),r.dato({'dato':old['dato']}))
        self.assertIn(new['link'],[a['link'] for a in old['andre']])
        with patch.object(c,'API_KEY',''):
            self.assertEqual(c.saml_dublet_historier([new],archive),[])

    def test_beslaegtet_men_anden_haendelse_forbliver_selvstaendig(self):
        old,new=artikel('opsigelse',20),artikel('cyberrapport',1)
        old.update(titel='Jacob Coxon quits Anthropic',rubrik='Jacob Coxon forlader Anthropic',resume_da='Forskerens opsigelse advarer om selvforbedrende superintelligens og risiko for menneskeheden.')
        new.update(titel='Anthropic cybersecurity report',rubrik='Anthropic opdager cyberangreb',resume_da='Cybersikkerhedsrapporten dokumenterer stjålne tokens, kompromitterede servere og fire datalæk hos virksomheder.')
        with patch.object(c,'API_KEY','test'), patch.object(c,'hjerne_kald',return_value='[[1,2]]'):
            result=c.saml_dublet_historier([new],[old])
        self.assertEqual(result,[new])
        self.assertNotIn('historie_dato',new)

    def test_arkivbevarelse_aendrer_ikke_omtales_originale_dato(self):
        a=artikel(); source_date=a['dato']; a['historie_dato']=(NU-timedelta(days=5)).isoformat()
        kept=r.behold_aktuelle([],[a],[{'navn':a['kilde']}],NU)
        self.assertEqual(kept[0]['dato'].isoformat(),source_date)
        self.assertEqual(r.dato(kept[0]).isoformat(),a['historie_dato'])

    def test_modeloversigten_viser_faerdige_lanceringer_nyeste_foerst(self):
        newest,older=artikel('ny-model',1),artikel('aeldre-model',20)
        newest.update(titel='Acme udgiver Orion 8',rubrik='Orion 8 kan forstå video')
        draft=artikel('kladde'); draft['sektioner']=[]
        product=artikel('app'); product['redaktion']['model_lancering']=False
        missing=artikel('uden-side'); missing.pop('side')
        out=m.oversigt([older,draft,artikel('for-gammel',91),product,missing,newest],NU)
        self.assertEqual([a['side'] for a in out['lanceringer']],[newest['side'],older['side']])

    def test_rss_og_artikelsider_udgiver_ikke_kladder(self):
        ready,draft=artikel(),artikel('kladde'); draft['sektioner']=[]
        with tempfile.TemporaryDirectory() as tmp, patch.object(c,'ROOT',Path(tmp)), patch.object(c,'ARTIKEL_MAPPE',Path(tmp)/'artikel'):
            c.lav_rss([draft,ready]); c.lav_artikelsider([draft,ready])
            self.assertNotIn(draft['link'],(Path(tmp)/'feed.xml').read_text())
            self.assertFalse((Path(tmp)/'artikel'/f'{c._artikel_slug(draft["link"])}.html').exists())
            self.assertTrue((Path(tmp)/ready['side']).is_file())

    def test_artiklen_har_korte_afsnit_faktaboks_og_sikker_html(self):
        a=artikel(); a['noegletal']=[{'tal':'<script>','label':'Pris & ydelse'}]
        out=c._artikel_side_html(a)
        self.assertIn('class="article-metrics"',out)
        self.assertIn('&lt;script&gt;',out)
        self.assertIn('</p><p>',out)
        self.assertIn('href="/modeller.html"',out)


if __name__=='__main__': unittest.main(verbosity=2)
