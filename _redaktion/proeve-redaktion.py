#!/usr/bin/env python3
"""Regressioner for redaktionel udvælgelse. Ingen netværk, nøgler eller filændringer."""
import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import redaktion as r
import crawler as c

NU = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)


def artikel(navn="Ny model", prio=7, timer=2, kilde="a.example", kategori="Lanceringer", **extra):
    return {"titel": navn, "rubrik": navn, "resume": "Et konkret kilderesumé til testen.",
            "resume_da": "Et konkret dansk resumé.", "link": f"https://{kilde}/{navn.replace(' ', '-')}",
            "kilde": kilde, "kategori": kategori, "prio": prio,
            "dato": (NU-timedelta(hours=timer)).isoformat(), "foerst_set": NU.isoformat(), **extra}


def vurdering(**extra):
    return {"version":r.VERSION,"model_lancering":False,"metode":"ai","nyhed":4,"betydning":4,"brugbarhed":4,
            "dokumentation":4,"dansk":2,"type":"lancering","ai_relevant":True,
            "begrundelse":"En konkret nyhed med praktisk betydning.","forbehold":"","emne":"",**extra}


class RedaktionTests(unittest.TestCase):
    def test_geografi_giver_ingen_bonus_heller_ikke_i_gamle_vurderinger(self):
        for version in (2, r.VERSION):
            international = artikel(redaktion=vurdering(version=version, dansk=0))
            lokal = artikel(redaktion=vurdering(version=version, dansk=5))
            self.assertEqual(r.grundscore(international), r.grundscore(lokal))
            self.assertEqual(r.score(international, NU), r.score(lokal, NU))

    def test_stor_historie_slaar_lille_ny_opdatering(self):
        stor=artikel("Vigtig lancering",9,36);lille=artikel("Mindre rettelse",3,0)
        self.assertEqual(r.udvaelg([lille,stor],nu=NU)[0],stor)

    def test_opdagelsestid_forynger_ikke(self):
        gammel=artikel("Gammel model",10,240);ny=artikel("Ny model",6,2)
        self.assertNotIn(gammel,r.udvaelg([gammel,ny],nu=NU))
        self.assertLess(r.score(gammel,NU),r.score(ny,NU))

    def test_fremtid_og_ukendt_dato_faar_ingen_hovedplads(self):
        future=artikel(timer=-48);unknown=artikel(dato=None,foerst_set=None)
        self.assertEqual(r.udvaelg([future,unknown],nu=NU),[])

    def test_tidszoner_sammenlignes_som_tidspunkter(self):
        a=artikel(dato="2026-09-05T13:00:00+02:00")
        b=artikel(dato="2026-09-05T11:00:00+00:00")
        self.assertEqual(r.score(a,NU),r.score(b,NU))
        self.assertEqual(r.score(artikel(dato="2026-09-05T11:00:00"),NU),r.score(b,NU))

    def test_reklame_og_perifer_ai_faar_ingen_plads(self):
        for a in [artikel("Last chance for side events",10),artikel(redaktion=vurdering(type="reklame")),artikel(redaktion=vurdering(ai_relevant=False))]:
            self.assertEqual(r.score(a,NU),0)
            self.assertEqual(r.udvaelg([a],nu=NU),[])

    def test_rygte_og_tyndt_grundlag_beholdes_i_listen(self):
        for v in [vurdering(type="rygte"),vurdering(dokumentation=1)]:
            a=artikel(redaktion=v)
            self.assertGreater(r.score(a,NU),0)
            self.assertEqual(r.udvaelg([a],nu=NU),[])
            self.assertIn(a,r.prioriter([a],NU))

    def test_forskning_kan_vaere_hovedhistorie(self):
        research=artikel("Vigtigt forskningsresultat",kategori="Forskning",redaktion=vurdering())
        self.assertEqual(r.udvaelg([research,artikel(prio=3)],nu=NU)[0],research)

    def test_forskellige_kilder_og_emner_fremhaeves(self):
        same=[artikel(f"OpenAI model {n}",9,2) for n in range(5)]
        other=artikel("Nyt om sikkerhed",8,3,kilde="b.example",kategori="Samfund & etik")
        self.assertEqual(r.udvaelg(same+[other],nu=NU)[1],other)

    def test_mange_omtaler_er_ikke_kvalitetsbonus(self):
        a=artikel();b={**a,"andre":[{"kilde":str(n),"link":f"https://{n}.example"} for n in range(30)]}
        self.assertEqual(r.score(a,NU),r.score(b,NU))

    def test_stabil_uden_dubletter_eller_mutation(self):
        a=artikel();b=artikel("Anden artikel",kilde="b.example");items=[a,a,b];before=copy.deepcopy(items)
        self.assertEqual(len(r.udvaelg(items,nu=NU)),2)
        self.assertEqual(r.udvaelg(items,nu=NU),r.udvaelg(list(reversed(items)),nu=NU))
        self.assertEqual(items,before)

    def test_ingen_fyld_paa_stille_dage(self):
        self.assertEqual(r.udvaelg([artikel(prio=1)],nu=NU),[])
        self.assertEqual(len(r.udvaelg([artikel()],nu=NU)),1)

    def test_ugyldige_ai_tal_afvises(self):
        valid={**vurdering(),"kategori":"Lanceringer"}
        self.assertIsNotNone(r.valider(valid,c.KATEGORIER))
        for value in [-1,6,True,"4",float("nan"),None]:
            self.assertIsNone(r.valider({**valid,"nyhed":value},c.KATEGORIER))
        self.assertIsNone(r.valider({**valid,"kategori":"Opfundet"},c.KATEGORIER))
        self.assertIsNone(r.valider({**valid,"ai_relevant":"true"},c.KATEGORIER))

    def test_cache_v2_og_fallback(self):
        a=artikel(redaktion=vurdering());self.assertIsNotNone(r.vurdering(a))
        a["redaktion"]["version"]=1;self.assertIsNone(r.vurdering(a))
        for p in [None,"vrøvl",float("nan")]:
            self.assertEqual(r.grundscore(artikel(prio=p)),40)

    def test_ai_svar_matches_med_id_ikke_position(self):
        a=artikel("A");b=artikel("B");items=[a,b]
        responses=[{**vurdering(),"id":c._artikel_slug(b['link']),"kategori":"Forskning"},
                   {**vurdering(),"id":c._artikel_slug(a['link']),"kategori":"Hverdags-AI"}]
        with patch.object(c,"API_KEY","test"),patch.object(c,"hjerne_kald",return_value=json.dumps(responses)):
            c.klassificer(items)
        self.assertEqual(a["kategori"],"Hverdags-AI");self.assertEqual(b["kategori"],"Forskning")

    def test_dublerede_og_ukendte_ids_afvises(self):
        a=artikel();response={**vurdering(),"id":c._artikel_slug(a['link']),"kategori":"Forskning"}
        for responses in [[response,response],[{**response,"id":"ukendt"}],["fejl"],[{**response,"id":[]}]]:
            with patch.object(c,"API_KEY","test"),patch.object(c,"hjerne_kald",return_value=json.dumps(responses)):
                c.klassificer([a])
            self.assertNotIn("redaktion",a)

    def test_cache_overlever_omskrivning(self):
        a=artikel();cached={**a,"redaktion":vurdering()}
        with patch.object(c,"API_KEY",""):
            c.omskriv_nye([a],{a["link"]:cached})
        self.assertEqual(a["redaktion"],cached["redaktion"])

    def test_offline_genberegning_aendrer_ikke_indhold_eller_tid(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"articles.json";original={"opdateret":"2026-09-05T10:00:00Z","artikler":[artikel()],"antal":1}
            f.write_text(json.dumps(original))
            with patch.object(c,"OUTPUT_FIL",f):c.opdater_forside_lokalt()
            updated=json.loads(f.read_text());updated.pop("forside")
            self.assertEqual(updated,original)

    def test_kort_feed_mister_ikke_en_aktuel_historie(self):
        a=artikel(timer=24);now=artikel("Ny historie")
        result=r.behold_aktuelle([now],[a],[{"navn":"a.example"}],NU)
        self.assertEqual(len(result),2)
        self.assertEqual(result[1]["link"],a["link"])
        self.assertEqual(result[1]["dato"],r.dato(a))
        self.assertIsInstance(a["dato"],str)  # inddata er urørte

    def test_arkiv_respekterer_alder_kontakter_og_rettigheder(self):
        a=artikel();feeds=[{"navn":"a.example"}]
        self.assertEqual(r.behold_aktuelle([], [a], [], NU), [])
        self.assertEqual(r.behold_aktuelle([], [a], [{"navn":"a.example","kun_aktuel":True}], NU), [])
        self.assertEqual(r.behold_aktuelle([], [artikel(kun_aktuel=True)], feeds, NU), [])
        self.assertEqual(len(r.behold_aktuelle([], [artikel(timer=169)], feeds, NU)), 1)
        self.assertEqual(r.behold_aktuelle([], [artikel(timer=193)], feeds, NU), [])
        self.assertEqual(len(r.behold_aktuelle([a], [a,a], feeds, NU)),1)

    def test_astra_med_live_v2_vurdering_slaar_branchenyhed(self):
        # Vurderingen fra den udgave, hvor Astra blev skubbet ned:
        # nyhed=5, betydning=4, brugbarhed=1, dokumentation=2, dansk=0.
        astra=artikel("OpenAI lancerer GPT-6 Astra",timer=48,redaktion=vurdering(
            version=2,nyhed=5,betydning=4,brugbarhed=1,dokumentation=2,dansk=0))
        finance=artikel("Firma henter penge",timer=1,kategori="Penge & marked",
                        redaktion=vurdering(type="forretning"))
        self.assertTrue(r.model_lancering(astra))
        self.assertEqual(r.udvaelg([finance,astra],nu=NU)[0],astra)
        self.assertEqual(r.prioriter([finance,astra],NU)[0],astra)

    def test_modelprioritet_er_generel_og_begraenset_til_en_uge(self):
        new=artikel("Introducing Acme One",resume_da="Acme udgiver en ny sprogmodel.",prio=6)
        self.assertTrue(r.model_lancering(new))
        old={**new,"dato":(NU-timedelta(hours=169)).isoformat()}
        self.assertNotIn(old,r.udvaelg([old],nu=NU))
        self.assertGreater(r.score(new,NU),r.score(old,NU))

    def test_navn_eller_produktkategori_er_ikke_en_modellancering(self):
        for title in ["Microsoft lancerer Windows med GPT-6", "OpenAI lancerer plugin til GPT-6",
                      "Google Gemini sender vandrere på vildspor", "Four AI models suffer downtime",
                      "Rumors: OpenAI launches GPT-7", "OpenAI might launch GPT-7"]:
            self.assertFalse(r.model_lancering(artikel(title)),title)
        self.assertFalse(r.model_lancering(artikel("OpenAI lancerer GPT-6",redaktion=vurdering(model_lancering=False))))

    def test_model_flag_skal_vaere_gyldigt_og_rygter_beskyttes(self):
        valid={**vurdering(model_lancering=True),"kategori":"Lanceringer"}
        self.assertIsNotNone(r.valider(valid,c.KATEGORIER))
        for value in ["true",None,1]:
            self.assertIsNone(r.valider({**valid,"model_lancering":value},c.KATEGORIER))
        self.assertIsNone(r.valider({**valid,"type":"rygte"},c.KATEGORIER))
        a=artikel("OpenAI lancerer GPT-6",redaktion=vurdering(version=2,type="rygte"))
        self.assertFalse(r.model_lancering(a))
        self.assertEqual(r.udvaelg([a],nu=NU),[])

    def test_v2_bevares_indtil_ny_ai_vurdering_er_klar(self):
        a=artikel(redaktion=vurdering(version=2,type="rygte"))
        with patch.object(c,"API_KEY","test"),patch.object(c,"hjerne_kald",return_value="[]") as call:
            c.klassificer([a])
        call.assert_called_once()
        self.assertEqual(a["redaktion"]["version"],2)
        self.assertEqual(r.udvaelg([a],nu=NU),[])

    def test_template_bevarer_kilder_og_sikker_jsonld(self):
        a=artikel('<script>alert("x")</script>',sektioner=[{"overskrift":"Fakta","tekst":"Et dokumenteret forhold."}])
        rendered=c._artikel_side_html(a)
        self.assertIn('/assets/artikel.css',rendered)
        self.assertIn('id="artikeltekst"',rendered)
        self.assertIn('&lt;script&gt;',rendered)
        self.assertNotIn('<script>alert(',rendered)

    def test_lancering_giver_plads_til_nye_historier_efter_to_doegn(self):
        lancering=artikel('Acme v3 bliver frigivet',timer=48,redaktion=vurdering(model_lancering=True))
        gammel={**lancering,'dato':(NU-timedelta(hours=120)).isoformat()}
        ny=artikel('Vigtig ny historie',timer=3,redaktion=vurdering(type='analyse'))
        self.assertGreater(r.score(lancering,NU),r.score(ny,NU))
        self.assertLess(r.score(gammel,NU),r.score(ny,NU))

    def test_samme_url_med_sporing_samles_uden_at_miste_kilder(self):
        a=artikel('En konkret historie om musik',link='https://example.com/story?utm_source=feed')
        b=artikel('Ny overskrift hos samme kilde',link='https://www.example.com/story/#top')
        c=artikel('En anden konkret nyhed om musik',link='https://other.example/story',andre=[{'link':b['link'],'kilde':'Original'}])
        before=copy.deepcopy([a,b,c])
        result=r.unikke_historier([a,b,c])
        self.assertEqual(len(result),1)
        self.assertEqual({x['link'] for x in result[0]['andre']},{b['link'],c['link']})
        self.assertEqual([a,b,c],before)

    def test_betydende_query_og_forskellige_nyheder_bevares(self):
        a=artikel('En nyhed',link='https://example.com/?id=1')
        b=artikel('Anden nyhed',link='https://example.com/?id=2')
        self.assertEqual(len(r.unikke_historier([a,b])),2)
        self.assertEqual(len(r.unikke_historier([artikel('OpenAI viser ny model'),artikel('OpenAI ændrer sine priser')])),2)

    def test_samme_overskrift_paa_to_kilder_samles(self):
        a=artikel('Google lancerer en ny sprogmodel',kilde='a.example')
        b=artikel('GOOGLE lancerer en ny sprogmodel!',kilde='b.example')
        self.assertEqual(len(r.udvaelg([a,b],nu=NU)),1)

    def test_samme_modelversion_samles_men_varianter_og_api_bevares(self):
        v=vurdering(model_lancering=True)
        a=artikel('Suno lancerer ny musikmodel',resume_da='Suno v6 er trænet på licenseret musik.',redaktion=v)
        b=artikel('Suno v6 skaber nye sange',redaktion=v,kilde='b.example')
        c=artikel('Suno v6 Pro åbner for musikere',redaktion=v,kilde='c.example')
        d=artikel('Suno v6 kommer i et API',redaktion=v,kilde='d.example')
        self.assertEqual(len(r.unikke_historier([a,b,c,d])),3)
        self.assertEqual(len(r.udvaelg([a,b,c,d],nu=NU)),3)
        e=artikel('Suno v6 Zenith er lanceret',redaktion=v,kilde='e.example')
        self.assertEqual(len(r.unikke_historier([a,e])),2)
        senere={**b,'dato':(NU+timedelta(days=30)).isoformat()}
        self.assertEqual(len(r.unikke_historier([a,senere])),2)
        flash=artikel('Google lancerer Gemini 3.8 Flash',redaktion=v)
        cyber=artikel('Google giver adgang til sikkerhedsmodel',resume_da='Gemini 3.8 Flash Cyber finder sikkerhedshuller.',redaktion=v)
        self.assertEqual(len(r.unikke_historier([flash,cyber])),2)

    def test_fejlagtigt_model_flag_goer_ikke_et_produkt_til_en_model(self):
        for titel in ['Introducing ChatGPT for Financial Services','OpenAI lancerer et plugin til GPT-6']:
            self.assertFalse(r.model_lancering(artikel(titel,redaktion=vurdering(model_lancering=True))))

    def test_suno_med_forskellige_formuleringer_fra_den_rigtige_forside(self):
        rows=json.loads((Path(__file__).parent/'fixtures/suno-v6.json').read_text())
        before=copy.deepcopy(rows)
        samlet=r.unikke_historier(rows)
        self.assertEqual(len(samlet),1)
        self.assertEqual(samlet[0]['andre'][0]['link'],rows[1]['link'])
        self.assertEqual(rows,before)
        self.assertTrue(c._samme_sag(*rows),'Navnelisten må ikke blokere en korrekt AI-sammenlægning')
        for tekst in ['Suno har frigivet v6 på licenseret data','Suno releases its v6 music model']:
            anden={**rows[0],'titel':tekst,'rubrik':tekst}
            self.assertEqual(len(r.unikke_historier([anden,rows[1]])),1)
        anden={**rows[1],'rubrik':'Suno v6 Pro er lanceret','titel':'Suno v6 Pro launches','resume_da':'Suno v6 Pro er en separat modelvariant.'}
        self.assertEqual(len(r.unikke_historier([rows[0],anden])),2)


if __name__=="__main__":
    unittest.main(verbosity=2)
