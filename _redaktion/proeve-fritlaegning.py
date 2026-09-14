"""Masker, gennemsigtighed og fejlreserve; ingen modeldownload eller API-kald."""
import io
import hashlib
import importlib.util
import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from contextlib import redirect_stdout, redirect_stderr
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crawler as c
import fritlaeg_billede as f
from fritlaeg_billede import fritlaeg, kontroller_maske
from _redaktion.nyhedsbrev_billeder import cutout_png, CutoutError


class Fritlaegning(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'original.jpg'
        self.image = Image.new('RGB',(200,100),'#171a21')
        self.image.save(self.path)
        self.bytes = self.path.read_bytes()

    def mask(self, rect):
        image=Image.new('RGBA',(200,100))
        ImageDraw.Draw(image).rectangle(rect,fill=(200,240,80,255))
        return image

    def test_grove_maskefejl_afvises(self):
        for rect in [(0,0,1,1),(0,0,199,99),(70,45,100,50)]:
            with self.assertRaises(ValueError): kontroller_maske(self.mask(rect))
        kontroller_maske(self.mask((40,25,140,75)))

    def test_webp_bevarer_alpha_og_original_med_plads_omkring(self):
        fake=SimpleNamespace(remove=lambda *a,**kw:self.mask((40,25,140,75)))
        with patch.dict(sys.modules,{'rembg':fake}):
            fake.new_session=lambda *a,**kw:object()
            dest=fritlaeg(self.path,self.path.with_suffix('.webp'),session=object())
        with Image.open(dest) as img:
            self.assertEqual(img.width * 3, img.height * 4)
            bounds=img.getchannel('A').getbbox()
            self.assertGreater(max((bounds[2]-bounds[0])/img.width,(bounds[3]-bounds[1])/img.height),.8)
            self.assertEqual(img.mode,'RGBA')
            self.assertEqual(img.getchannel('A').getextrema(),(0,255))
            self.assertEqual(img.getpixel((0,0))[3],0)
        self.assertEqual(self.path.read_bytes(),self.bytes)
        self.assertFalse(dest.with_suffix('.webp.tmp').exists())

    def test_afvist_maske_skriver_ingen_webp(self):
        fake=SimpleNamespace(remove=lambda *a,**kw:self.mask((0,0,1,1)),new_session=lambda *a,**kw:object())
        with patch.dict(sys.modules,{'rembg':fake}), self.assertRaises(ValueError):
            fritlaeg(self.path,self.path.with_suffix('.webp'),session=object())
        self.assertFalse(self.path.with_suffix('.webp').exists())
        self.assertEqual(self.path.read_bytes(),self.bytes)

    def test_timeout_importfejl_og_manglende_output_bruger_jpg(self):
        for error in [subprocess.TimeoutExpired('test',180),subprocess.CalledProcessError(1,'test'),OSError('test'),None]:
            with patch('subprocess.run',side_effect=error) as run:
                result=c._gem_artikelbillede(self.bytes,self.path)
                self.assertEqual(result,self.path)
                self.assertEqual(run.call_args.kwargs['timeout'],180)
                with Image.open(result) as img: self.assertEqual(img.format,'JPEG')

    def test_succes_bruger_webp(self):
        def run(*args,**kwargs):
            self.mask((40,25,140,75)).save(self.path.with_suffix('.webp'),'WEBP')
        with patch('subprocess.run',side_effect=run):
            self.assertEqual(c._gem_artikelbillede(self.bytes,self.path),self.path.with_suffix('.webp'))
        self.assertTrue(self.path.is_file())

    def test_newsletter_reports_cutout_stage_and_exit_without_provider_data(self):
        for code, stderr, expected in [(-9, 'Private request-data', 'ProcesAfbrudt'),
                                       (1, 'Private request-data\nCUTOUT_ERROR=ValueError\n', 'ValueError')]:
            result = SimpleNamespace(returncode=code, stdout='CUTOUT_STAGE=model\nCUTOUT_STAGE=kontrol\n', stderr=stderr)
            with patch('subprocess.run', return_value=result), self.assertRaises(CutoutError) as error:
                cutout_png(self.bytes)
            self.assertEqual(error.exception.details, {'trin':'kontrol', 'returkode':code, 'fejltype':expected})
            self.assertNotIn('Private request-data', str(error.exception))

    def test_newsletter_reads_error_marker_after_progressbar(self):
        result = SimpleNamespace(returncode=1, stdout='CUTOUT_STAGE=modeldownload\n',
                                 stderr='99% downloaded Private request-data CUTOUT_ERROR=HTTPError\n')
        with patch('subprocess.run', return_value=result), self.assertRaises(CutoutError) as error:
            cutout_png(self.bytes)
        self.assertEqual(error.exception.details,
                         {'trin':'modeldownload', 'returkode':1, 'fejltype':'HTTPError'})
        self.assertNotIn('Private request-data', str(error.exception))

    def test_newsletter_structured_status_overrides_old_markers_and_filters_private_data(self):
        def run(command, **kwargs):
            status = Path(command[command.index('--status-fil') + 1])
            status.write_text(json.dumps({'trin':'modeldownload', 'fejltype':'HTTPError',
                                          'http_status':503, 'errno':28,
                                          'message':'Private request-data', 'headers':{'Authorization':'Private token'}}))
            return SimpleNamespace(returncode=1, stdout='CUTOUT_STAGE=biblioteker\n',
                                   stderr='CUTOUT_ERROR=ValueError\nPrivate request-data')
        with patch('subprocess.run', side_effect=run), self.assertRaises(CutoutError) as error:
            cutout_png(self.bytes)
        self.assertEqual(error.exception.details, {'trin':'modeldownload', 'returkode':1,
                                                  'fejltype':'HTTPError', 'http_status':503, 'errno':28})
        self.assertNotIn('Private', str(error.exception))

    def test_newsletter_ignores_invalid_metadata_types(self):
        def run(command, **kwargs):
            status = Path(command[command.index('--status-fil') + 1])
            status.write_text(json.dumps({'trin':'modeldownload', 'fejltype':'HTTPError',
                                          'http_status':'Private request-data', 'errno':True,
                                          'returkode':'Private request-data'}))
            return SimpleNamespace(returncode=1, stdout='', stderr='')
        with patch('subprocess.run', side_effect=run), self.assertRaises(CutoutError) as error:
            cutout_png(self.bytes)
        self.assertEqual(error.exception.details,
                         {'trin':'modeldownload', 'returkode':1, 'fejltype':'HTTPError'})

    def test_newsletter_timeout_keeps_last_status_and_custom_limit(self):
        def run(command, **kwargs):
            status = Path(command[command.index('--status-fil') + 1])
            status.write_text(json.dumps({'trin':'modelindlaesning'}))
            self.assertEqual(kwargs['timeout'], 600)
            raise subprocess.TimeoutExpired(command, kwargs['timeout'],
                                            output=b'CUTOUT_STAGE=modeldownload\nPrivate request-data',
                                            stderr=b'Private request-data')
        with patch('subprocess.run', side_effect=run), self.assertRaises(CutoutError) as error:
            cutout_png(self.bytes, timeout=600)
        self.assertEqual(error.exception.details,
                         {'trin':'modelindlaesning', 'returkode':None, 'fejltype':'TimeoutExpired'})
        self.assertNotIn('Private request-data', str(error.exception))

    def test_newsletter_timeout_uses_byte_markers_without_status_file(self):
        timeout = subprocess.TimeoutExpired('test', 180,
                                            output=b'CUTOUT_STAGE=modeldownload\nPrivate request-data')
        with patch('subprocess.run', side_effect=timeout), self.assertRaises(CutoutError) as error:
            cutout_png(self.bytes)
        self.assertEqual(error.exception.details,
                         {'trin':'modeldownload', 'returkode':None, 'fejltype':'TimeoutExpired'})

    def test_main_reports_stage_and_safe_error_metadata_in_status_file(self):
        http_error = RuntimeError('Private request-data')
        http_error.response = SimpleNamespace(status_code=503, headers={'Authorization':'Private token'})
        for exception, extras in [(http_error, {'http_status':503}),
                                  (OSError(28, 'Private request-data'), {'errno':28}),
                                  (SystemExit('Private request-data'), {})]:
            with self.subTest(error=type(exception).__name__):
                status = Path(self.tmp.name) / 'status.json'
                stdout, stderr = io.StringIO(), io.StringIO()
                def fail(source, destination, progress):
                    progress('modeldownload')
                    # Trinnet skal være gemt allerede før fejlen eller en procesafbrydelse.
                    self.assertEqual(json.loads(status.read_text()), {'trin':'modeldownload'})
                    raise exception
                with patch.object(f, 'fritlaeg', side_effect=fail), redirect_stdout(stdout), redirect_stderr(stderr):
                    code = f.main([str(self.path), str(self.path.with_suffix('.webp')), '--status-fil', str(status)])
                self.assertEqual(code, 1)
                self.assertEqual(json.loads(status.read_text()),
                                 {'trin':'modeldownload', 'fejltype':type(exception).__name__, **extras})
                self.assertNotIn('Private', status.read_text() + stdout.getvalue() + stderr.getvalue())
                self.assertTrue(stderr.getvalue().startswith('\nCUTOUT_ERROR='))
                self.assertFalse(status.with_suffix('.tmp').exists())


@unittest.skipUnless(importlib.util.find_spec('pooch'), 'Modeltests kræver det valgfrie billedbibliotek Pooch')
class ModelKlargoring(unittest.TestCase):
    def setUp(self):
        import pooch
        self.pooch = pooch
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.folder = self.root / 'models' / f.MODEL
        self.existing = None
        self.valid = b'A tiny verified model fixture'
        self.stages = []
        session = SimpleNamespace(resolve_existing=lambda name:self.existing,
                                  model_dir=lambda:self.folder)
        self.addCleanup(patch.stopall)
        patch.dict(sys.modules, {'rembg.sessions.birefnet_general':
                                SimpleNamespace(BiRefNetSessionGeneral=session)}).start()
        patch.object(f, 'MODEL_MD5', hashlib.md5(self.valid).hexdigest()).start()
        patch('pooch.core.time.sleep').start()

    def test_verified_nested_and_legacy_cache_need_no_download(self):
        for folder in [self.folder, self.root]:
            with self.subTest(folder=folder):
                folder.mkdir(parents=True, exist_ok=True)
                self.existing = folder / (f.MODEL + '.onnx')
                self.existing.write_bytes(self.valid)
                with patch.object(self.pooch, 'HTTPDownloader', side_effect=AssertionError('No network')):
                    result = f.klargoer_model(self.stages.append)
                self.assertEqual(result, self.existing)
                self.assertEqual(result.read_bytes(), self.valid)
        self.assertNotIn('modeldownload', self.stages)

    def test_corrupt_cache_is_replaced_only_after_valid_download(self):
        self.folder.mkdir(parents=True)
        self.existing = self.folder / (f.MODEL + '.onnx')
        self.existing.write_bytes(b'corrupt cached model')
        def download(url, output_file, pooch):
            self.assertEqual(self.existing.read_bytes(), b'corrupt cached model')
            self.assertNotEqual(Path(output_file), self.existing)
            self.assertEqual(url, f.MODEL_URL)
            Path(output_file).write_bytes(self.valid)
        with patch.object(self.pooch, 'HTTPDownloader', return_value=download) as downloader:
            result = f.klargoer_model(self.stages.append)
        self.assertEqual(result.read_bytes(), self.valid)
        self.assertEqual(self.stages, ['modelkontrol', 'modeldownload'])
        self.assertEqual(list(self.folder.iterdir()), [result])
        self.assertFalse(downloader.call_args.kwargs['progressbar'])

    def test_transient_download_failure_is_retried_without_partial_model(self):
        import requests
        attempts = []
        def download(url, output_file, pooch):
            attempts.append(Path(output_file))
            if len(attempts) == 1:
                Path(output_file).write_bytes(b'partial download')
                raise requests.exceptions.ReadTimeout('Temporary network failure')
            Path(output_file).write_bytes(self.valid)
        with patch.object(self.pooch, 'HTTPDownloader', return_value=download):
            result = f.klargoer_model(self.stages.append)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(result.read_bytes(), self.valid)
        self.assertEqual(list(self.folder.iterdir()), [result])

    def test_terminal_download_failure_has_three_attempts_and_preserves_old_cache(self):
        import requests
        self.folder.mkdir(parents=True)
        self.existing = self.folder / (f.MODEL + '.onnx')
        self.existing.write_bytes(b'corrupt cached model')
        attempts = []
        def download(url, output_file, pooch):
            attempts.append(output_file)
            Path(output_file).write_bytes(b'partial download')
            raise requests.exceptions.ReadTimeout('Temporary network failure')
        with patch.object(self.pooch, 'HTTPDownloader', return_value=download):
            with self.assertRaises(requests.exceptions.ReadTimeout):
                f.klargoer_model(self.stages.append)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(self.existing.read_bytes(), b'corrupt cached model')
        self.assertEqual(list(self.folder.iterdir()), [self.existing])


if __name__=='__main__': unittest.main(verbosity=2)
