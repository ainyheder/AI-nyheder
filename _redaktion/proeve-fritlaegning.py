"""Masker, gennemsigtighed og fejlreserve; ingen modeldownload eller API-kald."""
import io
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crawler as c
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


if __name__=='__main__': unittest.main(verbosity=2)
