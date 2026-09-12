"""Regressioner for redaktionsforløbet. Kun testdata, ingen netværk eller udgivelse."""
import copy
import json
import runpy
import sys
import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import crawler as c
import redaktoer_agent as agent
import redaktion as r

fixtures = runpy.run_path(str(ROOT / "_redaktion/proeve-redaktoer-agent.py"))
artikel, plan, tool, NU, KILDE = (fixtures[k] for k in ("artikel", "plan", "tool", "NU", "KILDE"))
kontroller = runpy.run_path(str(ROOT / "_redaktion/kontroller-udgave.py"))["kontroller"]
DRAFT = {"rubrik": "Nova kan læse billeder", "resume": "Ny model med billedforståelse.",
         "sektioner": [{"overskrift": "Muligheder", "tekst": "Nova kan behandle tekst og billeder."}]}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.a, self.b = artikel("Nova", 4), artikel("Finansiering", 10)
        self.editor = agent.Redaktion([self.a, self.b], {}, "Modeller først", NU, lambda *_: {},
                                      lambda _: {"tekst": KILDE, "henvisninger": []})
        self.editor.laes(agent.ident(self.a["link"]))
        self.edition = self.editor.forside(plan(self.a), [self.a, self.b])

    def test_research_slutter_i_tide_til_at_reparere_aflevering(self):
        calls = []
        def svar(messages, tools):
            calls.append(copy.deepcopy(tools))
            if len(calls) <= agent.MAX_RESEARCH_RUNDER:
                return tool("laes_kilde", {"id": agent.ident(self.a["link"])})
            p = plan(self.a)
            if len(calls) == agent.MAX_RESEARCH_RUNDER + 1:
                p["udvalgte"][0]["nyt_siden_sidst"] = "Ny"
            return tool("aflever_udgave", p)
        self.editor.kald = svar
        self.assertEqual(self.editor.koer(), plan(self.a))
        self.assertLessEqual(len(calls), agent.MAX_KALD)
        self.assertTrue(self.editor.log[-2]["fejl"])
        self.assertTrue(all(t == [agent.TOOLS[-1]] for t in calls[agent.MAX_RESEARCH_RUNDER:]))

    def test_afleveringsfasen_kan_ikke_fortsaette_research(self):
        self.editor.kald = lambda *_: tool("find_kilder", {"soegning": "Nova"})
        with self.assertRaisesRegex(agent.UdgaveFejl, "Research er afsluttet"):
            self.editor.koer()
        self.assertEqual(self.editor.antal_kald, agent.MAX_KALD)

    def test_reservestatus_forklarer_den_konkrete_afleveringsfejl(self):
        p = plan(self.a); p["udvalgte"][0]["skriveopgave"] = ""
        with patch.object(c, "DEEPSEEK_KEY", "test"), patch.object(agent, "deepseek_kald", return_value=tool("aflever_udgave", p)):
            context = c.forbered_redaktoer([self.a, self.b], None, NU)
        self.assertIn("skriveopgave har 0 tegn", context["status"]["forklaring"])
        self.assertEqual(context["status"]["status"], "reserve")

    def test_alle_afviste_og_ukontrollerede_briefs_rulles_tilbage(self):
        for dom in (None, {"godkendt": False, "problemer": ["Intet belæg"]},
                    {"godkendt": True, "problemer": ["Tal mangler belæg"]}):
            for gammel in (False, True):
                with self.subTest(dom=dom, gammel=gammel):
                    a = copy.deepcopy(self.a)
                    if gammel: a["sektioner"] = [{"tekst": "Eksisterende artikel"}]
                    before = copy.deepcopy(a)
                    with patch.object(c, "API_KEY", "test"), patch.object(c, "GENKOER_ALT", False), patch.object(c, "GENKOER_FILTER", ""), patch.object(c, "kald_ai_brief", return_value=DRAFT), patch.object(c, "redaktoer_tjek", return_value=dom):
                        c.dybe_briefs([a], kildetekster={a["link"]: KILDE})
                    self.assertEqual(a, before)

    def test_malformed_kontrolsvar_er_ingen_godkendelse(self):
        for dom in ({"godkendt": True}, {"godkendt": "ja", "problemer": []},
                    {"godkendt": False, "problemer": 5}, {"godkendt": True, "problemer": [{}]}):
            with patch.object(c, "hjerne_kald", return_value=json.dumps(dom)):
                self.assertIsNone(c.redaktoer_tjek(self.a, KILDE))

    def test_ugyldige_anbefalinger_afvises_som_plan(self):
        for extra in ([self.a["link"]], ["https://ukendt.example"], None):
            f = {**self.edition, "anbefalede": extra}
            self.assertFalse(agent.gyldig_forside(f, [self.a, self.b], NU))

    def test_ny_prompt_genbehandler_men_godkendt_cache_genbruges(self):
        a = copy.deepcopy(self.a)
        with patch.object(c, "_hjerner_cache", {"brief": {"prompt": "Første instruktion"}}) as config, patch.object(c, "API_KEY", "test"), patch.object(c, "GENKOER_ALT", False), patch.object(c, "GENKOER_FILTER", ""), patch.object(c, "kald_ai_brief", return_value=DRAFT) as writer, patch.object(c, "redaktoer_tjek", return_value={"godkendt": True, "problemer": []}):
            c.dybe_briefs([a], kildetekster={a["link"]: KILDE})
            self.assertIn("brief_instruks", a)
            c.dybe_briefs([a], kildetekster={a["link"]: KILDE})
            self.assertEqual(writer.call_count, 1)
            config["brief"]["prompt"] = "Prioritér konkret adgang og begrænsninger"
            c.dybe_briefs([a], kildetekster={a["link"]: KILDE})
            self.assertEqual(writer.call_count, 2)

    def test_vurdering_opdateres_ved_ny_instruks_og_bevares_ved_fejl(self):
        a = copy.deepcopy(self.a)
        assessment = {"id": c._artikel_slug(a["link"]), "kategori": "Lanceringer", "nyhed": 4,
                      "betydning": 4, "brugbarhed": 4, "dokumentation": 4, "dansk": 0,
                      "type": "lancering", "model_lancering": True, "ai_relevant": True,
                      "begrundelse": "Ny model med dokumenteret adgang", "forbehold": "", "emne": "Nova"}
        with patch.object(c, "_hjerner_cache", {"kategori": {"prompt": "Vurdér nyhedsværdi"}}) as config, patch.object(c, "API_KEY", "test"), patch.object(c, "hjerne_kald", return_value=json.dumps([assessment])) as ai:
            c.klassificer([a]); self.assertIn("redaktion_instruks", a)
            c.klassificer([a]); self.assertEqual(ai.call_count, 1)
            before = copy.deepcopy(a)
            config["kategori"]["prompt"] = "Nye modeller først"
            ai.return_value = "[]"
            c.klassificer([a]); self.assertEqual(a, before)
            ai.return_value = json.dumps([assessment])
            c.klassificer([a]); self.assertNotEqual(a["redaktion_instruks"], before["redaktion_instruks"])

    def test_cache_gemmer_instrukssignaturer(self):
        cached = {**self.a, "brief": "Tekst", "brief_instruks": "skriver", "redaktion_instruks": "vurderer"}
        fresh = {k: self.a[k] for k in ("titel", "link", "dato", "resume", "kilde")}
        with patch.object(c, "API_KEY", ""):
            c.omskriv_nye([fresh], {fresh["link"]: cached})
        self.assertEqual(fresh["brief_instruks"], "skriver")
        self.assertEqual(fresh["redaktion_instruks"], "vurderer")

    def test_billeder_foelger_agenten_selvom_pointlisten_er_uenig(self):
        self.assertEqual(r.udvaelg([self.a, self.b], nu=NU)[0], self.b)
        self.assertEqual(c._kort_artikler([self.b, self.a], self.edition, NU), {self.a["link"]})
        with patch.object(c, "API_KEY", "test"), patch.object(c, "BILLED_ANTAL", 1), patch.object(c, "hjerne_kald", return_value='[{"motiv":"A glass prism"}]') as ai:
            c.udfyld_billedmotiver([self.b, self.a], self.edition, NU)
        self.assertIn(self.a["rubrik"], ai.call_args.args[2])
        self.assertNotIn("billedmotiv", self.b)

    def test_tom_godkendt_plan_fyldes_ikke_op_fra_pointlisten(self):
        empty = self.editor.forside({"udvalgte": [], "anbefalede": [], "redaktionsnote": "Stille dag"}, [self.a, self.b])
        self.assertEqual(c._kort_artikler([self.a, self.b], empty, NU), set())
        self.assertEqual(c.udgavens_artikler([self.a, self.b], empty, nu=NU), [])

    def test_samlet_dublet_kommer_ikke_tilbage_i_overblik_eller_billeder(self):
        self.editor.laes(agent.ident(self.b["link"]))
        f = self.editor.forside(plan(self.a, [agent.ident(self.b["link"])]), [self.a, self.b])
        self.assertEqual(c.udgavens_artikler([self.b, self.a], f, nu=NU), [self.a])
        f["beregnet"] = (NU-timedelta(days=2)).isoformat()
        self.assertEqual(c.udgavens_artikler([self.a, self.b], f, nu=NU), r.udvaelg([self.a, self.b], nu=NU))

    def test_udgivelseskontrol_afviser_oedelagte_data_og_filer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / "data").mkdir(); (root / "artikel").mkdir()
            for name in ("feed.xml", "sitemap-artikler.xml"): (root/name).write_text("<root/>")
            a = {**self.a, "side": "artikel/nova.html", "sektioner": [{"tekst": "Kildetekst"}]}
            side = root / a["side"]; side.write_text("<!doctype html><p>Ny model</p>")
            data = {"artikler": [a], "antal": 1, "opdateret": NU.isoformat(), "forside": r.forside([a], NU)}
            def save(d): (root/"data/articles.json").write_text(json.dumps(d))
            save(data); self.assertEqual(kontroller(root), 1)
            # Forskellige links og rubrikker må ikke omgå udgivelseskontrollen.
            suno=json.loads((ROOT/'_redaktion/fixtures/suno-v6.json').read_text())
            duplicated={'artikler':suno,'antal':2,'opdateret':NU.isoformat(),
                        'forside':{'udvalgte':[s['link'] for s in suno],'raekkefoelge':[s['link'] for s in suno]}}
            save(duplicated)
            with self.assertRaisesRegex(ValueError,'samme begivenhed'): kontroller(root)
            for mutate in (
                lambda d: d.update(antal=2),
                lambda d: d.update(artikler=[], antal=0),
                lambda d: d["forside"].update(udvalgte=["https://unknown.example"]),
                lambda d: d["artikler"][0].update(billede="data/img/mangler.jpg"),
                lambda d: d["artikler"][0].update(side="../secrets"),
            ):
                broken = copy.deepcopy(data); mutate(broken); save(broken)
                with self.assertRaises(ValueError): kontroller(root)
            save(data); side.write_text("<<<<<<< HEAD\nkonflikt\n=======\nanden tekst\n>>>>>>> main")
            with self.assertRaisesRegex(ValueError, "mergekonflikt"): kontroller(root)

    def test_dagens_overblik_reagerer_paa_aendret_plan_i_samme_tidsblok(self):
        now = datetime.now(timezone.utc)
        artikler = [artikel(f"Nyhed-{i}", dato=now.isoformat()) for i in range(4)]
        e = agent.Redaktion(artikler, {}, "", now, lambda *_: {})
        def edition(items):
            return e.forside({"udvalgte": [], "anbefalede": [agent.ident(a["link"]) for a in items],
                             "redaktionsnote": "Tre forskellige historier"}, artikler)
        svar = json.dumps([{"nr": n, "tekst": "En konkret nyhed med adgang til en ny model."} for n in (1, 2, 3)])
        with tempfile.TemporaryDirectory() as tmp, patch.object(c, "BRIEF_FIL", Path(tmp)/"brief.json") as fil, patch.object(c, "API_KEY", "test"), patch.object(c, "hjerne_kald", return_value=svar) as ai:
            f = edition(artikler[:3])
            c.lav_dagens_brief(artikler, f)
            c.lav_dagens_brief(artikler, f)
            self.assertEqual(ai.call_count, 1)
            c.lav_dagens_brief(artikler, edition(artikler[1:]))
            self.assertEqual(ai.call_count, 2)
            self.assertEqual([p["link"] for p in json.loads(fil.read_text())["punkter"]], [a["link"] for a in artikler[1:]])
            c.lav_dagens_brief(artikler, edition([]))
            self.assertEqual(json.loads(fil.read_text())["punkter"], [])
            self.assertEqual(ai.call_count, 2)

    def test_main_godkender_foer_billeder_og_bruger_samme_plan_til_overblik(self):
        a = {**self.a, "dato": datetime.now(timezone.utc)}
        feed = {"navn": "Test", "url": "https://example.com/feed"}
        events, planer = [], []
        def skriv(artikler, *_):
            events.append("udkast"); artikler[0]["rubrik"] = "Udkast"
        def godkend(_, artikler, nu):
            events.append("godkendt"); artikler[0]["rubrik"] = "Godkendt artikel"
            f = r.forside(artikler, nu); planer.append(f); return f
        def modtag(navn):
            def trin(artikler, forside=None, *args):
                self.assertEqual(artikler[0]["rubrik"], "Godkendt artikel")
                if forside is not None: self.assertIs(forside, planer[0])
                events.append(navn)
            return trin
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root = Path(tmp); (root / "data").mkdir()
            feeds = root/"feeds.json"; feeds.write_text(json.dumps({"feeds": [feed]}))
            changes = {"ROOT": root, "OUTPUT_FIL": root/"data/articles.json", "FEEDS_FIL": feeds,
                       "API_KEY": "", "GEMINI_KEY": "", "DEEPSEEK_KEY": "", "_hjerner_cache": {}}
            for key, value in changes.items(): stack.enter_context(patch.object(c, key, value))
            for name in ("skriv_hjerne_status", "omskriv_nye", "klassificer", "_skriv_foerst_set_butik",
                         "gem_redaktoer_status", "skriv_kilde_status", "lav_rss", "lav_ugens_overblik",
                         "hent_laesertal",
                         "tjek_statisk_sitemap", "skriv_kommando_data"):
                stack.enter_context(patch.object(c, name))
            for name in ("lav_dagens_prompt", "lav_ugens_quiz", "lav_youtube"):
                stack.enter_context(patch.object(c, name, side_effect=AssertionError("Nedlagte sektioner må ikke produceres")))
            stack.enter_context(patch.object(c, "_aktive_feeds", return_value=([feed], [])))
            stack.enter_context(patch.object(c, "crawl_feed", return_value=(feed, [a], None)))
            stack.enter_context(patch.object(c, "_laes_foerst_set_butik", return_value={}))
            stack.enter_context(patch.object(c, "saml_dublet_historier", side_effect=lambda rows: rows))
            stack.enter_context(patch.object(c, "forbered_redaktoer", return_value={"opgaver": {}, "tekster": {}}))
            stack.enter_context(patch.object(c, "dybe_briefs", side_effect=skriv))
            stack.enter_context(patch.object(c, "afslut_redaktoer", side_effect=godkend))
            for navn in ("udfyld_billedmotiver", "lav_billeder", "lav_artikelsider", "lav_dagens_brief", "del_paa_platforme"):
                stack.enter_context(patch.object(c, navn, side_effect=modtag(navn)))
            for name in ("navngiv_rubrikker", "stram_betydninger"):
                stack.enter_context(patch.object(c, name, side_effect=AssertionError("AI-tekst må ikke ændres efter artikelkontrollen")))
            stack.enter_context(patch.object(c.urllib.request, "urlopen", side_effect=AssertionError("Intet netværk i testen")))
            c.main()
            self.assertEqual(events, ["udkast", "godkendt", "udfyld_billedmotiver", "lav_billeder",
                                      "lav_artikelsider", "lav_dagens_brief", "del_paa_platforme"])
            self.assertEqual(json.loads(c.OUTPUT_FIL.read_text())["artikler"][0]["rubrik"], "Godkendt artikel")


if __name__ == "__main__":
    unittest.main(verbosity=2)
