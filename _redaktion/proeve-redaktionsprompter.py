"""Kontrollér at centralens aktive instrukser når API-kald uden at tabe kontekst.
Ingen eksterne kald eller artikeludgivelse. Kør fra projektets rod.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crawler as c

ROOT = Path(__file__).resolve().parent.parent

class PromptFlow(unittest.TestCase):
    def setUp(self):
        # Faste testprompts: brugerens legitime valg/reset må ikke få CI til at fejle.
        self.config = {'hjerner': {n: {'prompt': 'Egen instruktion til ' + n}
                                  for n in c._standard_prompts()}}
        self.config['hjerner']['billedgenerator'] = {'model': c.FLUX_MODEL, 'prompt': 'Custom image style'}
        self.cache = patch.object(c, '_hjerner_cache', self.config['hjerner'])
        self.cache.start()
        self.addCleanup(self.cache.stop)

    def test_all_configured_instructions_reach_transport(self):
        seen=[]
        with patch.object(c, 'hjerne_model', return_value=None), patch.object(c, 'kald_ai', side_effect=lambda system,*args:seen.append(system) or '{}'):
            for name, default in c._standard_prompts().items():
                c.hjerne_kald(name, default, 'fixture', 100)
                self.assertEqual(seen[-1], self.config['hjerner'][name]['prompt'])

    def test_missing_transcript_survives_custom_prompt(self):
        with patch.object(c, 'kald_ai', return_value='{"rubrik":"Test","hoejdepunkter":[]}') as api:
            c.yt_kald_ai({'kanal':'Test','titel':'Test'}, '', [], 'Kort beskrivelse')
        system=api.call_args.args[0]
        self.assertIn(self.config['hjerner']['youtube']['prompt'], system)
        self.assertIn(c.SYSTEM_YT_UDEN_TRANSKRIPT.strip(), system)
        self.assertEqual(system.count(c.SYSTEM_YT_UDEN_TRANSKRIPT.strip()),1)

    def test_source_control_survives_custom_prompt(self):
        with patch.object(c, 'kald_ai', return_value='{"godkendt":true,"problemer":[]}') as api:
            c.redaktoer_tjek({'rubrik':'Test'}, 'Kildens dokumenterede oplysninger')
        self.assertIn('Kontrollér også påstande og tal mod kildematerialet', api.call_args.args[0])
        self.assertIn('Kildens dokumenterede oplysninger', api.call_args.args[1])

    def test_research_context_survives_custom_prompt(self):
        with patch.object(c, 'kald_ai', return_value='{"rubrik":"Test","sektioner":[{"overskrift":"Test","tekst":"Test"}]}') as api:
            c.kald_ai_brief({'kilde':'arXiv','titel':'Test'}, 'Forskningsmateriale', [])
        self.assertIn(c.SYSTEM_BRIEF_FORSKNING.strip(), api.call_args.args[0])
        self.assertIn(self.config['hjerner']['brief']['prompt'], api.call_args.args[0])

    def test_missing_override_preserves_entire_default(self):
        with patch.object(c,'_hjerner_cache',{}):
            value=c.SYSTEM_YT+c.SYSTEM_YT_UDEN_TRANSKRIPT
            self.assertEqual(c.hjerne_prompt('youtube',value),value)

    def test_article_prompts_do_not_require_newsletter_files(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(c, 'ROOT', Path(tmp)):
            signature = c.instruks_signatur('brief', 'redaktoer')
            self.config['hjerner']['brief']['prompt'] = 'Ny skriveinstruks'
            self.assertNotEqual(c.instruks_signatur('brief', 'redaktoer'), signature)
            self.assertEqual(c.hjerne_prompt('brief', c.SYSTEM_BRIEF_ARTIKEL), 'Ny skriveinstruks')
            # Nyhedsbrevet skal stadig melde fejl, hvis dets egen prompt mangler.
            with self.assertRaises(FileNotFoundError):
                c._standard_prompts('nyhedsbrev')

    def test_meaning_does_not_force_invented_personal_benefit(self):
        self.assertEqual(c._betydning_problemer(''),[])
        self.assertEqual(c._betydning_problemer('Udviklere kan nu hente modelvægtene.'),[])
        self.assertTrue(c._betydning_problemer('ord '*36))

    def test_image_instruction_uses_its_own_prompt(self):
        self.assertEqual(c.hjerne_prompt('billedgenerator', c.SYSTEM_BILLEDSTIL), self.config['hjerner']['billedgenerator']['prompt'])
        self.assertEqual(c.hjerne_model('billedgenerator'),c.FLUX_MODEL)

if __name__=='__main__': unittest.main(verbosity=2)
