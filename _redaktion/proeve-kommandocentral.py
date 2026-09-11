#!/usr/bin/env python3
"""Statuspakkens faktiske data, tomme mapper og usikker inputtekst.

Kør: python3 _redaktion/proeve-kommandocentral.py
Prøverne skriver kun i midlertidige mapper og foretager ingen netværkskald.
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kommandocentral import skriv_kommando_data


class KommandoDataProeve(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def skriv(self, fil, data):
        sti = self.root / fil
        sti.parent.mkdir(parents=True, exist_ok=True)
        sti.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")

    def pakke(self):
        sti = skriv_kommando_data(self.root)
        tekst = sti.read_text(encoding="utf-8")
        return json.loads(tekst.removeprefix("window.KOMMANDO_DATA = ").removesuffix(";\n")), tekst

    def test_tom_mappe_viser_manglende_data_uden_falsk_succes(self):
        data, _ = self.pakke()
        self.assertEqual(len(data["fejl"]), 9)
        self.assertFalse(any(data["tilgaengelige"].values()))
        self.assertEqual(data["feeds_fil"], {"feeds": []})
        self.assertEqual(data["hjerner_fil"], {"hjerner": {}})
        self.assertEqual(data["artikler"]["udvalgte"], [])
        self.assertIsNone(data["artikler"]["opdateret"])
        self.assertNotIn("status", data["redaktoer_status"])
        self.assertEqual(data["version"], 1)

    def test_oe_delagt_json_og_forkert_datatype(self):
        self.skriv("data/articles.json", '{"artikler": null}')
        self.skriv("opsaetning/feeds.json", '{"feeds": [')
        self.skriv("_redaktion/hjerner.json", [])
        data, _ = self.pakke()
        for navn in ("artikler", "feeds", "hjerner"):
            self.assertFalse(data["tilgaengelige"][navn])
        self.assertEqual(data["artikler"]["antal"], 0)
        self.assertTrue(all("grund" in f for f in data["fejl"]))

    def test_script_udbrud_og_unicode_er_ufarligt_og_tabsfrit(self):
        ond = '</script><script>alert("x")</script><!-- & \u2028\u2029 æøå'
        self.skriv("opsaetning/redaktoer.md", ond)
        self.skriv("_redaktion/hjerner.json", {"hjerner": {"omskriv": {"prompt": ond}}})
        data, tekst = self.pakke()
        self.assertNotIn("<", tekst)
        self.assertNotIn(">", tekst)
        self.assertNotIn("&", tekst)
        self.assertNotIn("\u2028", tekst)
        self.assertNotIn("\u2029", tekst)
        self.assertEqual(data["redaktoer_instruks"], ond)
        self.assertEqual(data["hjerner_fil"]["hjerner"]["omskriv"]["prompt"], ond)

    def test_lokal_konfiguration_vinder_over_gammel_status(self):
        self.skriv("opsaetning/feeds.json", {"feeds": [
            {"navn": "Nyt navn", "url": "https://example.com/feed", "aktiv": False,
             "format": "nyhedsoversigt", "fremtidigt_felt": {"bevar": True},
             "api_key": "secret-value"}
        ]})
        self.skriv("data/kilder.json", {"feeds_fil": {"feeds": [{"navn": "Gammelt navn"}]},
                                        "kilder": [], "api_token": "secret-value"})
        data, tekst = self.pakke()
        kilde = data["feeds_fil"]["feeds"][0]
        self.assertEqual(kilde["navn"], "Nyt navn")
        self.assertIs(kilde["aktiv"], False)
        self.assertEqual(kilde["fremtidigt_felt"], {"bevar": True})
        self.assertNotIn("secret-value", tekst)
        self.assertNotIn("feeds_fil", data["kilder"])

    def test_artikeludvalg_foelger_udgivet_plan_og_taeller_kun_rigtige_billeder(self):
        self.skriv("data/img/virker.jpg", "billedindhold")
        self.skriv("data/articles.json", {
            "opdateret": "2026-01-02T03:04:05+00:00", "antal": 999,
            "artikler": [
                {"titel": "B", "link": "https://example.com/b", "dato": "2026-01-02",
                 "kategori": "Lanceringer", "kilde": "Primær", "billede": "data/img/mangler.jpg",
                 "brief": "HELE ARTIKLEN SKAL IKKE UD"},
                {"rubrik": "A", "link": "https://example.com/a", "dato": "2026-01-01",
                 "kategori": "Lanceringer", "kilde": "Primær", "billede": "data/img/virker.jpg"},
            ],
            "forside": {"udvalgte": ["https://example.com/a", "https://example.com/b",
                                      "https://example.com/a", "https://example.com/slettet"]},
        })
        data, tekst = self.pakke()
        a = data["artikler"]
        self.assertEqual(a["antal"], 2)
        self.assertEqual(a["med_billede"], 1)
        self.assertEqual(a["paa_dansk"], 1)
        self.assertEqual(a["kategorier"], {"Lanceringer": 2})
        self.assertEqual([r["link"] for r in a["udvalgte"]],
                         ["https://example.com/a", "https://example.com/b"])
        self.assertEqual(a["seneste"][0]["titel"], "B")
        self.assertEqual(a["opdateret"], "2026-01-02T03:04:05+00:00")
        self.assertNotEqual(data["genereret"], a["opdateret"])
        self.assertNotIn("HELE ARTIKLEN", tekst)

    def test_modelprompter_kommer_med_men_historik_og_fremtidige_private_felter_goer_ikke(self):
        self.skriv("data/hjerner-status.json", {
            "daglig_model": "deepseek-flash", "arbejdsloop": [{"indhold": "PRIVAT LOG"}],
            "hjerner": {"redaktoer": {"model": "deepseek-flash", "standard_prompt": "Standard",
                                      "aktiv_prompt": "Aktiv", "privat_felt": "PRIVAT LOG"}},
        })
        self.skriv("data/redaktoer-status.json", {"status": "reserve", "forklaring": "Kald fejlede",
                                                  "privat_felt": "PRIVAT LOG"})
        data, tekst = self.pakke()
        self.assertEqual(data["redaktoer_status"]["status"], "reserve")
        self.assertEqual(data["hjerner_status"]["daglig_model"], "deepseek-flash")
        self.assertEqual(data["hjerner_status"]["hjerner"]["redaktoer"]["standard_prompt"], "Standard")
        self.assertNotIn("PRIVAT LOG", tekst)
        self.assertNotIn("arbejdsloop", data["hjerner_status"])

    def test_lofter_holder_pakken_lille(self):
        self.skriv("data/laesertal.json", {"serie": [{"dato": str(i), "besoeg": i} for i in range(90)],
                                          "sider": [{"sti": str(i)} for i in range(90)]})
        self.skriv("data/kilder.json", {"kilder": [{"navn": "A", "seneste":
                                                   [{"rubrik": str(i)} for i in range(90)]}]})
        data, _ = self.pakke()
        self.assertEqual(len(data["laesertal"]["serie"]), 30)
        self.assertEqual(data["laesertal"]["serie"][-1]["dato"], "89")
        self.assertEqual(len(data["laesertal"]["sider"]), 10)
        self.assertEqual(len(data["kilder"]["kilder"][0]["seneste"]), 12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
