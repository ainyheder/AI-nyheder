#!/usr/bin/env python3
"""Agentens kontrakt, værktøjer og crawler-integration. Ingen netværkskald."""
import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crawler as c
import redaktion as r
import redaktoer_agent as agent

NU = datetime(2026, 9, 11, 12, tzinfo=timezone.utc)
KILDE = ("Acme har udgivet modellen Nova v2. Den kan behandle tekst og billeder. "
         "Adgangen åbner i dag. Priser og en uafhængig sammenligning er ikke oplyst. ") * 5


def artikel(navn, prio=5, **kw):
    return {"link": "https://example.com/" + navn, "titel": navn, "rubrik": navn,
            "resume": KILDE[:300], "resume_da": KILDE[:150], "kategori": "Lanceringer",
            "kilde": "Eksempelkilden", "prio": prio, "dato": (NU-timedelta(hours=2)).isoformat(), **kw}


def tool(name, args, id_="t1"):
    return {"role": "assistant", "content": None, "tool_calls": [{"id": id_, "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}]}


def valg(a, duplicates=None):
    id_ = agent.ident(a["link"])
    return {"id": id_, "begrundelse": "En ny model giver læseren en konkret mulighed.",
            "nyt_siden_sidst": "Udgivelsen har ikke tidligere været fremhævet.",
            "skriveopgave": "Forklar modellens billedforståelse og vær tydelig om de manglende priser.",
            "kilder": [id_], "samme_historie": duplicates or []}


def plan(a, duplicates=None):
    return {"udvalgte": [valg(a, duplicates)], "anbefalede": [], "redaktionsnote": "Ny model i fokus."}


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.a, self.b = artikel("Ny-model", 4), artikel("Firma-henter-penge", 10)
        self.reads = []

    def lav(self, svar=None, memory=None):
        def hent(url):
            self.reads.append(url)
            return {"tekst": KILDE, "henvisninger": []}
        return agent.Redaktion([self.a, self.b], memory or {}, "Modeller først", NU,
                               svar or (lambda *_: tool("aflever_udgave", plan(self.a))), hent)

    def test_agenten_kan_vaelge_anderledes_end_pointlisten(self):
        calls = []
        def svar(messages, tools):
            calls.append(copy.deepcopy(messages))
            return tool("laes_kilde", {"id": agent.ident(self.a["link"])}) if len(calls) == 1 else tool("aflever_udgave", plan(self.a))
        editor = self.lav(svar)
        result = editor.koer()
        self.assertEqual(r.udvaelg([self.a, self.b], nu=NU)[0]["link"], self.b["link"])
        self.assertEqual(result["udvalgte"][0]["id"], agent.ident(self.a["link"]))
        self.assertEqual(calls[1][-1]["role"], "tool")
        self.assertIn(KILDE[:80], calls[1][-1]["content"])
        self.assertEqual(editor.antal_kald, 2)

    def test_hukommelse_og_retning_sendes_med(self):
        seen = []
        memory = {"udgaver": [{"tid": (NU-timedelta(days=3)).isoformat(), "historier": [{"link": self.a["link"], "rubrik": "Tidligere modelhistorie"}]}]}
        def svar(messages, tools):
            seen.extend(messages)
            return tool("aflever_udgave", {"udvalgte": [], "anbefalede": [], "redaktionsnote": "Stille dag"})
        self.lav(svar, memory).koer()
        context = json.loads(seen[1]["content"])
        self.assertEqual(context["retning"], "Modeller først")
        self.assertEqual(context["omtaler_seneste_uge"][self.a["link"]]["antal"], 1)

    def test_ukendte_id_og_ulaeste_kilder_afvises(self):
        editor = self.lav()
        with self.assertRaises(ValueError): editor.valider(plan(self.a))
        editor.laes(agent.ident(self.a["link"]))
        invalid = plan(self.a); invalid["udvalgte"][0]["id"] = "opfundet"
        with self.assertRaises(ValueError): editor.valider(invalid)
        invalid = plan(self.a); invalid["udvalgte"][0]["kilder"] = [agent.ident(self.b["link"])]
        with self.assertRaises(ValueError): editor.valider(invalid)

    def test_agenten_faar_praecis_fejl_og_kan_rette_afleveringen(self):
        calls=[]
        def svar(messages, tools):
            calls.append(copy.deepcopy(messages))
            p=plan(self.a)
            if len(calls)==1: p['udvalgte'][0]['nyt_siden_sidst']='Ny'
            return tool('aflever_udgave',p)
        editor=self.lav(svar);editor.laes(agent.ident(self.a['link']))
        self.assertEqual(editor.koer(),plan(self.a))
        fejl=json.loads(next(m['content'] for m in reversed(calls[1]) if m['role']=='tool'))['fejl']
        self.assertIn('nyt_siden_sidst',fejl)
        self.assertIn('2 tegn',fejl)
        self.assertIn(agent.ident(self.a['link']),fejl)
        self.assertEqual(editor.antal_kald,2)

    def test_samme_lancering_maa_ikke_vaelges_to_gange_med_forskellige_links(self):
        rows=json.loads((Path(__file__).parent/'fixtures/suno-v6.json').read_text())
        editor=agent.Redaktion(rows,{},'',NU,lambda *_: {},lambda _: {'tekst':KILDE,'henvisninger':[]})
        for a in rows: editor.laes(agent.ident(a['link']))
        p=plan(rows[0]);p['udvalgte'].append(valg(rows[1]))
        with self.assertRaisesRegex(ValueError,'Samme begivenhed'): editor.valider(p)
        f=editor.forside(p,rows)
        self.assertFalse(agent.gyldig_forside(f,rows,NU))
        p=plan(rows[0],[agent.ident(rows[1]['link'])])
        self.assertEqual(len(editor.valider(p)['udvalgte']),1)

    def test_semantisk_kontrol_ser_anbefalinger_og_gemmer_sin_konklusion(self):
        messages=[]
        editor=self.lav(lambda m,t: messages.extend(m) or tool('godkend_udgave',{'godkendt':False,'problemer':['To vinkler på samme lancering']}))
        editor.laes(agent.ident(self.a['link']));editor.laes(agent.ident(self.b['link']))
        p=plan(self.a);p['anbefalede']=[agent.ident(self.b['link'])]
        self.assertFalse(editor.kontroller(p,[self.a,self.b]))
        payload=json.loads(messages[1]['content'])
        self.assertEqual(payload['anbefalede'][0]['kilder'][0]['tekst'],KILDE.strip())
        self.assertEqual(len(payload['kandidatoversigt']),2)
        self.assertEqual(editor.kontrolproblemer,['To vinkler på samme lancering'])

    def test_ukendt_vaerktoej_og_url_udfoeres_ikke(self):
        calls = []
        def svar(messages, tools):
            calls.append(1)
            if len(calls) == 1: return tool("skriv_fil", {"sti": "/tmp/agent-write"})
            if len(calls) == 2: return tool("laes_kilde", {"id": "http://127.0.0.1/"})
            return tool("aflever_udgave", {"udvalgte": [], "anbefalede": [], "redaktionsnote": "Ingen"})
        editor = self.lav(svar); editor.koer()
        self.assertEqual(self.reads, [])
        self.assertTrue(editor.log[0]["fejl"])

    def test_værktoej_budget_og_reparation_af_ugyldigt_svar(self):
        editor = self.lav()
        with self.assertRaises(ValueError): editor.koer()
        self.assertEqual(editor.antal_kald, agent.MAX_KALD)
        for i in range(20):
            a = artikel(str(i)); editor.kilder[str(i)] = {"link": a["link"], "artikel": str(i)}
            editor.laes(str(i))
        self.assertEqual(len(self.reads), agent.MAX_KILDER)

    def test_kilde_cache_og_officielle_henvisninger(self):
        editor = self.lav()
        editor.hent = lambda _: {"tekst": KILDE, "henvisninger": [{"link": "https://openai.com/index/nova-new-model", "titel": "Nova"}, {"link": "http://127.0.0.1/private"}]}
        result = editor.laes(agent.ident(self.a["link"]))
        self.assertEqual(len(result["henvisninger"]), 1)
        self.assertIn(result["henvisninger"][0]["id"], editor.kilder)
        editor.hent = lambda _: self.fail("Må ikke genhente samme kilde")
        self.assertEqual(editor.laes(agent.ident(self.a["link"])), result)

    def test_netvaerksfejl_faar_aerligt_resumegrundlag(self):
        editor = self.lav()
        def fejl(_): raise OSError("Ingen adgang")
        editor.hent = fejl
        result = editor.laes(agent.ident(self.a["link"]))
        self.assertEqual(result["grundlag"], "rss_resume")
        self.assertEqual(result["tekst"], self.a["resume"])

    def test_lokalnet_og_redirects_afvises(self):
        with patch.object(agent.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 80))]):
            with self.assertRaises(ValueError): agent.offentlig_url("https://evil.example/news")
            with self.assertRaises(ValueError): agent.OffentligRedirect().redirect_request(None, None, 302, "", {}, "http://evil.example/news")
        for url in ["file:///etc/passwd", "http://user:pass@example.com", "https://example.com:8080"]:
            with self.assertRaises(ValueError): agent.offentlig_url(url)

    def test_dubletter_skal_vaere_laeste_og_maa_ikke_ogsaa_vaelges(self):
        editor = self.lav(); editor.laes(agent.ident(self.a["link"]))
        p = plan(self.a, [agent.ident(self.b["link"])])
        with self.assertRaises(ValueError): editor.valider(p)
        editor.laes(agent.ident(self.b["link"])); editor.valider(p)
        p["udvalgte"].append(valg(self.b))
        with self.assertRaises(ValueError): editor.valider(p)

    def test_reklame_rygter_og_for_gammelt_er_ikke_kandidater(self):
        old = artikel("Old", dato=(NU-timedelta(days=8)).isoformat())
        ad = artikel("Last chance for side events")
        e = agent.Redaktion([old, ad], {}, "", NU, lambda *_: self.fail("Ingen kandidater kræver intet kald"))
        self.assertEqual(e.koer()["udvalgte"], [])

    def test_gyldig_forside_og_forældet_reserve(self):
        editor = self.lav(); editor.laes(agent.ident(self.a["link"]))
        f = editor.forside(plan(self.a), [self.a, self.b])
        self.assertTrue(agent.gyldig_forside(f, [self.a, self.b], NU))
        self.assertIsNone(agent.genbrug_forside(f, [self.a, self.b], NU+timedelta(hours=25)))
        self.assertFalse(agent.gyldig_forside(f, [self.b], NU))
        bad = {**f, "samlede": {self.a["link"]: [self.b["link"]]}}
        self.assertFalse(agent.gyldig_forside(bad, [self.a, self.b], NU))

    def test_udgavekontrol_ser_baade_tekst_og_kilder(self):
        messages = []
        editor = self.lav(lambda m, t: messages.extend(m) or tool("godkend_udgave", {"godkendt": True, "problemer": []}))
        editor.laes(agent.ident(self.a["link"]))
        self.assertTrue(editor.kontroller(plan(self.a), [self.a]))
        self.assertIn("kilder", messages[1]["content"])
        self.assertIn(KILDE[:100], messages[1]["content"])

    def test_afvist_udgave_overtager_ikke_forsiden(self):
        editor = self.lav(lambda *_: tool("godkend_udgave", {"godkendt": False, "problemer": ["En påstand mangler belæg"]}))
        editor.laes(agent.ident(self.a["link"]))
        fallback = r.forside([self.a, self.b], NU)
        context = {"agent": editor, "plan": plan(self.a), "forside": fallback, "status": {}}
        self.assertEqual(c.afslut_redaktoer(context, [self.a, self.b], NU), fallback)
        self.assertEqual(context["status"]["status"], "reserve")
        self.assertNotIn("hukommelse", context)

    def test_ingen_noegle_giver_reserve_uden_kald(self):
        with patch.object(c, "DEEPSEEK_KEY", ""), patch.object(agent, "deepseek_kald") as call:
            context = c.forbered_redaktoer([self.a, self.b], None, NU)
        call.assert_not_called()
        self.assertEqual(context["status"]["status"], "reserve")

    def test_afvist_slutkontrol_gendanner_teksten_ogsaa_i_nyhedslisten(self):
        for timeout in (False, True):
            with self.subTest(timeout=timeout):
                a = copy.deepcopy(self.a)
                original = copy.deepcopy(a)
                def kald(*_):
                    if timeout:
                        raise TimeoutError()
                    return tool("godkend_udgave", {"godkendt": False, "problemer": ["Opfundne tal"]})
                editor = self.lav(kald)
                editor.laes(agent.ident(a["link"]))
                context = {"agent": editor, "plan": plan(a), "forside": r.forside([a, self.b], NU),
                           "status": {}, "originaler": {a["link"]: original}}
                a.update(rubrik="Uunderbygget rubrik", sektioner=[{"tekst": "Opfundne tal"}],
                         redaktoer_opgave_id="ny", billede="data/img/nyt.jpg")
                c.afslut_redaktoer(context, [a, self.b], NU)
                self.assertEqual(a["rubrik"], original["rubrik"])
                self.assertNotIn("sektioner", a)
                self.assertNotIn("redaktoer_opgave_id", a)
                self.assertEqual(a["billede"], "data/img/nyt.jpg")
                self.assertEqual(context["status"]["status"], "reserve")

    def test_hele_forloebet_med_native_tool_kald(self):
        seen = []
        def kald(key, model, messages, tools):
            self.assertEqual(model, "deepseek-flash")
            seen.append(copy.deepcopy(messages))
            if len(seen) == 1: return tool("laes_kilde", {"id": agent.ident(self.a["link"])})
            if len(seen) == 2: return tool("aflever_udgave", plan(self.a))
            return tool("godkend_udgave", {"godkendt": True, "problemer": []})
        with patch.object(c, "DEEPSEEK_KEY", "test"), patch.object(agent, "deepseek_kald", side_effect=kald), patch.object(agent, "hent_kilde", return_value={"tekst": KILDE, "henvisninger": []}):
            context = c.forbered_redaktoer([self.a, self.b], None, NU)
            self.assertIn(self.a["link"], context["opgaver"])
            f = c.afslut_redaktoer(context, [self.a, self.b], NU)
        self.assertEqual(f["udvalgte"], [self.a["link"]])
        self.assertEqual(len(seen), 3)
        self.assertEqual(context["status"]["status"], "godkendt")

    def test_uændret_udgave_genbruges_og_aendret_retning_udloeser_moede(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); settings = root/"opsaetning"; settings.mkdir()
            (settings/"redaktoer.md").write_text("Modeller først")
            with patch.object(c, "ROOT", root), patch.object(c, "OPSAETNING", settings), patch.object(c, "DEEPSEEK_KEY", ""):
                initial = c.forbered_redaktoer([self.a, self.b], None, NU)
                agent.gem_json(root/"data/redaktoer-status.json", initial["status"])
                e = self.lav(); e.laes(agent.ident(self.a["link"]))
                previous = e.forside(plan(self.a), [self.a, self.b])
                cached = c.forbered_redaktoer([self.a, self.b], previous, NU+timedelta(hours=1))
                self.assertEqual(cached["status"]["status"], "genbrugt")
                (settings/"redaktoer.md").write_text("Prioritér åbne modeller og dansk adgang")
                changed = c.forbered_redaktoer([self.a, self.b], previous, NU+timedelta(hours=1))
                self.assertNotEqual(changed["status"]["status"], "genbrugt")
                self.assertEqual(changed["forside"]["udvalgte"], previous["udvalgte"])

    def test_kildereferencer_kommer_med_paa_artikelsiden(self):
        a = {**self.a, "redaktoer_kilder": [{"link": "https://openai.com/index/nova", "kilde": "Officiel kilde"}]}
        self.assertIn('href="https://openai.com/index/nova"', c._artikel_side_html(a))

    def test_nye_historier_kommer_foran_gammel_liste_ved_genbrug(self):
        old = [artikel("Arkiv-"+str(i), dato=(NU-timedelta(days=3, minutes=i)).isoformat()) for i in range(40)]
        editor = self.lav()
        f = editor.forside(plan(self.a), [self.a]+old)
        new = artikel("Dagens-robot", dato=(NU-timedelta(minutes=5)).isoformat())
        reused = agent.genbrug_forside(f, [self.a]+old+[new], NU)
        self.assertEqual(reused["raekkefoelge"][:2], [self.a["link"], new["link"]])
        self.assertTrue(agent.gyldig_forside(reused, [self.a]+old+[new], NU))

    def test_gammel_anbefaling_kan_ikke_overhale_dagens_nyhed(self):
        old = artikel("Gammel-anbefaling", dato=(NU-timedelta(days=3)).isoformat())
        editor = agent.Redaktion([old,self.a], {}, "", NU, lambda *_: None)
        p = {"udvalgte": [], "anbefalede": [agent.ident(old["link"])], "redaktionsnote": "En anbefaling"}
        f = editor.forside(p, [old,self.a])
        self.assertEqual(f["raekkefoelge"], [self.a["link"], old["link"]])
        self.assertTrue(agent.gyldig_forside(f, [old,self.a], NU))
        editor.laes(agent.ident(old["link"]))
        with self.assertRaisesRegex(ValueError, "48 timer"):
            editor.valider(plan(old))

    def test_anbefalinger_kontrolleres_ogsaa_uden_hovedhistorier(self):
        seen = []
        editor = self.lav(lambda m,t: seen.append(m) or tool("godkend_udgave", {"godkendt":False,"problemer":["Gentagelse"]}))
        context = {"agent":editor, "plan":{"udvalgte":[],"anbefalede":[agent.ident(self.a["link"])],"redaktionsnote":""},
                   "forside":r.forside([self.a,self.b],NU),"status":{}}
        c.afslut_redaktoer(context,[self.a,self.b],NU)
        self.assertEqual(len(seen),1)
        self.assertEqual(context["status"]["status"],"reserve")

    def test_thinking_fortsat_i_vaerktoejssamtalen_men_ikke_i_log(self):
        seen = []
        def respond(messages, tools):
            seen.append(copy.deepcopy(messages))
            if len(seen)==1:
                return {**tool("laes_kilde", {"id":agent.ident(self.a["link"])}), "reasoning_content":"test-only-private-reasoning"}
            self.assertEqual(messages[2]["reasoning_content"],"test-only-private-reasoning")
            return tool("aflever_udgave", plan(self.a))
        editor = self.lav(respond)
        p = editor.koer()
        self.assertEqual(len(seen),2)
        self.assertNotIn("test-only-private-reasoning",json.dumps([p,editor.log,editor.husk(p)]))

    def test_transport_bruger_rigtigt_endpoint_model_og_vaerktoejer(self):
        class Svar:
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def read(self, _): return json.dumps({"choices": [{"finish_reason": "tool_calls", "message": tool("laes_kilde", {"id": "kendt"})}]}).encode()
        with patch.object(agent.urllib.request, "urlopen", return_value=Svar()) as urlopen:
            result = agent.deepseek_kald("hemmelig-testnoegle", "deepseek-flash", [{"role": "user", "content": "redaktionsmøde"}], agent.TOOLS)
        request = urlopen.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.deepseek.com/chat/completions")
        self.assertEqual(body["model"], "deepseek-flash")
        self.assertEqual(body["tools"], agent.TOOLS)
        self.assertEqual(body["thinking"], {"type": "enabled"})
        self.assertEqual(body["reasoning_effort"], "max")
        self.assertGreaterEqual(body["max_tokens"], 32768)
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 600)
        self.assertEqual(result["tool_calls"][0]["function"]["name"], "laes_kilde")

    def test_godkendt_udgave_gemmer_hukommelse_uden_kildetekst(self):
        editor = self.lav(lambda *_: tool("godkend_udgave", {"godkendt": True, "problemer": []}))
        editor.laes(agent.ident(self.a["link"]))
        context = {"agent": editor, "plan": plan(self.a), "forside": r.forside([self.a, self.b], NU), "status": {}}
        result = c.afslut_redaktoer(context, [self.a, self.b], NU)
        self.assertEqual(result["metode"], "agent")
        with tempfile.TemporaryDirectory() as path, patch.object(c, "ROOT", Path(path)):
            c.gem_redaktoer_status(context)
            memory = agent.laes_json(Path(path)/"data/redaktoer-hukommelse.json", {})
            self.assertEqual(memory["udgaver"][0]["historier"][0]["link"], self.a["link"])
            self.assertNotIn(KILDE, json.dumps(memory))

    def test_gammel_hukommelse_og_fremtiden_fjernes(self):
        entries = [{"tid": (NU+timedelta(days=d)).isoformat(), "historier": []} for d in [-8, -1, 1]]
        self.assertEqual(len(agent.hukommelse({"udgaver": entries}, NU)), 1)

    def test_skriveopgave_naar_skriver_og_kildekontrol(self):
        a = {**self.a, "sektioner": [{"overskrift": "Gammelt", "tekst": "Gammel tekst"}]}
        opgave = "Forklar den nye billedforståelse."
        draft = {"rubrik": "Ny model med billeder", "resume": "Kort", "sektioner": [{"overskrift": "Nyt", "tekst": "Modellen kan læse billeder."}]}
        with patch.object(c, "API_KEY", "test"), patch.object(c, "GENKOER_ALT", False), patch.object(c, "GENKOER_FILTER", ""), patch.object(c, "kald_ai_brief", return_value=draft) as writer, patch.object(c, "redaktoer_tjek", return_value={"godkendt": True, "problemer": []}) as check:
            c.dybe_briefs([a], {a["link"]: opgave}, {a["link"]: KILDE})
        self.assertEqual(writer.call_args.kwargs["redaktoer_noter"], opgave)
        self.assertEqual(check.call_args.args[1], KILDE)
        self.assertIn("redaktoer_opgave_id", a)

    def test_afvist_genskrivning_bevarer_gammel_artikel(self):
        a = {**self.a, "sektioner": [{"overskrift": "Gammelt", "tekst": "Gammel tekst"}]}
        before = copy.deepcopy(a)
        draft = {"rubrik": "Forkert rubrik", "sektioner": [{"overskrift": "Fup", "tekst": "Opfundne tal"}]}
        with patch.object(c, "API_KEY", "test"), patch.object(c, "GENKOER_ALT", False), patch.object(c, "GENKOER_FILTER", ""), patch.object(c, "kald_ai_brief", return_value=draft), patch.object(c, "redaktoer_tjek", return_value={"godkendt": False, "problemer": ["Tallene mangler i kilden"]}):
            c.dybe_briefs([a], {a["link"]: "Kontrollér tallene"}, {a["link"]: KILDE})
        self.assertTrue(a.pop("redaktoer_afvist"))
        self.assertEqual(a, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
