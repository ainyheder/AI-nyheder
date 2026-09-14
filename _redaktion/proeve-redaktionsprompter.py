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

class ImageEditorialFlow(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.images = Path(temp.name)
        for setting, value in [('API_KEY', 'test'), ('BILLED_MAPPE', self.images),
                               ('MAX_BILLEDER_PR_KOERSEL', 10), ('_hjerner_cache', {})]:
            override = patch.object(c, setting, value)
            override.start()
            self.addCleanup(override.stop)

    def article(self, name):
        return {'link': 'https://example.org/' + name, 'rubrik': name,
                'resume_da': 'Den korte introduktion.',
                'sektioner': [{'overskrift': 'Hvad ændrer sig?',
                              'tekst': 'Den konkrete funktion står i den færdige artikel.'}],
                'kilde': 'Et medie, som ikke er nyhedens hovedaktør'}

    def write(self, articles, response):
        with patch.object(c, '_billedartikler', return_value=articles), \
             patch.object(c, 'hjerne_kald', return_value=json.dumps(response)) as call:
            c.udfyld_billedmotiver(articles)
        return call

    def test_art_director_reads_story_not_only_headline_or_publisher(self):
        article = self.article('DeepSeek')
        article['sektioner'].append({'overskrift': 'Lokal brug', 'tekst': 'Modellen kører på brugerens egen computer.'})
        call = self.write([article], [{'nr': 1, 'motiv': 'A blue DeepSeek whale on an open laptop.'}])
        supplied = json.loads(call.call_args.args[2])[0]
        self.assertIn(article['sektioner'][0]['tekst'], supplied['artikel'])
        self.assertIn(article['sektioner'][1]['tekst'], supplied['artikel'])
        self.assertNotIn(article['kilde'], call.call_args.args[2])
        self.assertEqual(supplied['nr'], 1)
        self.assertEqual(supplied['resume'], article['resume_da'])

    def test_out_of_order_motifs_are_assigned_to_correct_article(self):
        articles = [self.article('OpenAI'), self.article('Gemini')]
        self.write(articles, [{'nr': 2, 'motiv': 'Gemini spark and a picture frame.'},
                              {'nr': 1, 'motiv': 'OpenAI Blossom and a microphone.'}])
        self.assertEqual(articles[0]['billedmotiv'], 'OpenAI Blossom and a microphone.')
        self.assertEqual(articles[1]['billedmotiv'], 'Gemini spark and a picture frame.')

    def test_ambiguous_and_malformed_replies_cannot_swap_images(self):
        articles = [self.article(str(i)) for i in range(4)]
        self.write(articles, [{'nr': 1, 'motiv': 'First'}, {'nr': 1, 'motiv': 'Contradiction'},
                              {'nr': 2, 'motiv': 'The valid scene'}, {'nr': True, 'motiv': 'Boolean'},
                              {'nr': 3, 'motiv': ['not text']}, {'nr': 4, 'motiv': 'x' * 701},
                              {'nr': 99, 'motiv': 'Unknown'}, {'motiv': 'No number'}, None])
        self.assertEqual(articles[1]['billedmotiv'], 'The valid scene')
        for article in [articles[0], *articles[2:]]:
            self.assertNotIn('billedmotiv', article)

    def test_only_unpictured_stale_motifs_are_replanned(self):
        paid, waiting = self.article('paid'), self.article('waiting')
        paid['billede'] = 'data/img/paid.jpg'
        (self.images / 'paid.jpg').write_bytes(b'already paid')
        for article in (paid, waiting):
            article.update(billedmotiv='Old scene', billedmotiv_instruks='old prompt')
        call = self.write([paid, waiting], [{'nr': 1, 'motiv': 'New relevant scene'}])
        self.assertEqual(len(json.loads(call.call_args.args[2])), 1)
        self.assertEqual(paid['billedmotiv'], 'Old scene')
        self.assertEqual(waiting['billedmotiv'], 'New relevant scene')
        self.write([paid, waiting], []).assert_not_called()
        waiting['sektioner'][0]['tekst'] += ' En vigtig rettelse.'
        self.write([paid, waiting], [{'nr': 1, 'motiv': 'Corrected scene'}]).assert_called_once()
        self.assertEqual(waiting['billedmotiv'], 'Corrected scene')
        with patch.object(c, '_hjerner_cache', {'motiv': {'prompt': 'Ændret billedinstruks fra centralen'}}):
            self.write([paid, waiting], [{'nr': 1, 'motiv': 'New art direction'}]).assert_called_once()
            self.assertEqual(waiting['billedmotiv'], 'New art direction')
            self.assertEqual(paid['billedmotiv'], 'Old scene')
        self.assertEqual((self.images / 'paid.jpg').read_bytes(), b'already paid')

    def test_failed_refresh_does_not_keep_a_wrong_unpictured_motif(self):
        article = self.article('waiting')
        article['billedmotiv'] = 'Wrong idea from an old prompt'
        with patch.object(c, '_billedartikler', return_value=[article]), \
             patch.object(c, 'hjerne_kald', side_effect=TimeoutError):
            c.udfyld_billedmotiver([article])
        self.assertNotIn('billedmotiv', article)
        self.write([article], [{'nr': 1, 'motiv': 'Recovered scene'}]).assert_called_once()

    def test_newsletter_passes_motif_and_identity_before_its_style(self):
        from _redaktion import nyhedsbrev_billeder as images
        motif = 'A blue DeepSeek whale on a laptop processing a local document.'
        with patch.object(c, 'lav_flux_billede', return_value=b'raw') as api, \
             patch.object(images, 'cutout_png', return_value=b'transparent PNG') as cutout:
            self.assertEqual(images.generate_png(motif), b'transparent PNG')
        prompt = api.call_args.args[0]
        self.assertLess(prompt.index(motif), prompt.index('ART DIRECTION:'))
        self.assertEqual(prompt.count(motif), 1)
        cutout.assert_called_once_with(b'raw')


if __name__=='__main__': unittest.main(verbosity=2)
