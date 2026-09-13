import sys, os, json, base64
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import crawler as c
calls=[]
def fake(url, data, headers):
    calls.append((url,data,headers))
    return json.dumps({'success':True,'result':{'image':base64.b64encode(b'image bytes').decode()}}).encode()
with patch.dict(os.environ,{'CLOUDFLARE_AI_TOKEN':'test-only','CLOUDFLARE_ACCOUNT_ID':'a'*32}), patch.object(c,'hent_url',fake):
    assert c.lav_flux_billede('Dansk motiv æøå')==b'image bytes'
    url,body,headers=calls[0]
    assert url.endswith(c.FLUX_MODEL)
    assert b'name="width"\r\n\r\n1024' in body and b'name="height"\r\n\r\n576' in body
    assert 'Dansk motiv æøå' in body.decode()
    assert headers['Authorization']=='Bearer test-only'
    assert 'boundary=' in headers['Content-Type']
with patch.dict(os.environ,{'CLOUDFLARE_AI_TOKEN':'test','CLOUDFLARE_ACCOUNT_ID':'a'*32}), patch.object(c,'hent_url',return_value=b'{"success":false}'):
    try: c.lav_flux_billede('test'); raise AssertionError('Accepted failure')
    except ValueError: pass
with patch.object(c,'_hjerner_cache',{'billedgenerator':{'model':c.FLUX_MODEL}}):
    assert c.special_model('billedgenerator',c.BILLED_MODEL,'gemini')==c.FLUX_MODEL
print('OK: FLUX routing, multipart, 16:9, decoding and failure handling')

# Eksisterende billeder genbruges. Kun nye billeder går gennem fritlægningen.
import tempfile
from contextlib import ExitStack
with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
    root = Path(folder)
    images = root / 'data' / 'img'
    images.mkdir(parents=True)
    article = {'link':'https://example.com/launch','rubrik':'Ny model','kategori':'Lanceringer'}
    archive = {'link':'https://example.com/archive','rubrik':'Arkiv'}
    name = c._billed_navn(archive['link'], 'v5')
    (images / name).write_bytes(b'old image')
    archive['billede'] = 'data/img/' + name
    old_archive = archive['billede']
    for name, value in [('ROOT',root),('ARTIKEL_MAPPE',root/'artikel'),('BILLED_MAPPE',images)]:
        stack.enter_context(patch.object(c,name,value))
    stack.enter_context(patch.object(c,'special_model',return_value=c.FLUX_MODEL))
    stack.enter_context(patch.object(c,'cloudflare_billedadgang',return_value=('test','test')))
    stack.enter_context(patch.object(c,'hjerne_prompt',side_effect=lambda name,default:default))
    def save(data,path):
        path.write_bytes(data)
        output=path.with_suffix('.webp'); output.write_bytes(b'cutout'); return output
    stack.enter_context(patch.object(c,'_gem_artikelbillede',side_effect=save))
    with patch.object(c,'lav_flux_billede',side_effect=ValueError('test failure')) as api:
        c.lav_billeder([article,archive])
        assert api.call_count == 1 and not article.get('billede')
        assert archive['billede'] == old_archive and (root / old_archive).is_file()
    with patch.object(c,'lav_flux_billede',return_value=b'new image') as api:
        c.lav_billeder([article,archive])
        assert api.call_count == 1
        assert '#171a21' in api.call_args.args[0] and '#d5ff5f' in api.call_args.args[0]
        assert article['billede'].endswith('.webp') and (root / article['billede']).is_file()
        assert (root / article['billede']).with_suffix('.jpg').is_file()
        c.lav_billeder([article,archive])
        assert api.call_count == 1, 'Nyt billede skal genbruges ved næste kørsel'
        # Ny hovedkilde genbruger et allerede betalt billede fra en anden kilde.
        donor = article['link']; article['link'] = 'https://example.com/another-source'
        article['andre'] = [{'link':donor}]
        c.lav_billeder([article,archive])
        assert api.call_count == 1, 'Arvede billeder skal genbruges'
        # Gamle JPG'er må heller ikke genlaves, når de bliver forsidehistorier.
        c.lav_billeder([article,archive])
        assert api.call_count == 1
        # Arkiveret WebP og tilhørende original bevares, også uden artikel i feedet.
        (root/'archive.html').write_text('<img src="'+article['billede']+'">')
        c.lav_billeder([archive])
        assert (root/article['billede']).is_file()
        assert (root/article['billede']).with_suffix('.jpg').is_file()
print('OK: Nye WebP-billeder, fejlbevaring, alle historier, arkiv og genbrug')

# En billedkø skal nå forbi de tre topkort og fortsætte næste kørsel.
from datetime import datetime, timezone, timedelta
nu = datetime(2026, 9, 13, tzinfo=timezone.utc)
with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
    root = Path(folder); images = root / 'data' / 'img'; images.mkdir(parents=True)
    articles = [{'link': 'https://example.com/' + name, 'rubrik': name,
                 'kategori': 'Hverdags-AI', 'dato': (nu-timedelta(hours=i+1)).isoformat()}
                for i, name in enumerate(['Teleskop', 'Robot', 'Musik', 'Medicin', 'Programmering', 'Kontor'])]
    articles[0]['billede'] = 'data/img/tidligere.jpg'
    (root / articles[0]['billede']).write_bytes(b'existing')
    for name, value in [('ROOT', root), ('ARTIKEL_MAPPE', root/'artikel'), ('BILLED_MAPPE', images),
                        ('MAX_BILLEDER_PR_KOERSEL', 2), ('API_KEY', 'test')]:
        stack.enter_context(patch.object(c, name, value))
    stack.enter_context(patch.object(c, 'special_model', return_value=c.FLUX_MODEL))
    stack.enter_context(patch.object(c, 'cloudflare_billedadgang', return_value=('test','test')))
    stack.enter_context(patch.object(c, 'hjerne_prompt', side_effect=lambda name,default:default))
    stack.enter_context(patch.object(c, '_gem_artikelbillede', side_effect=save))
    motif = stack.enter_context(patch.object(c, 'hjerne_kald', side_effect=lambda name,prompt,body,budget:
        json.dumps([{'motiv': item['rubrik']} for item in json.loads(body)])))
    api = stack.enter_context(patch.object(c, 'lav_flux_billede', return_value=b'image'))
    assert len(c._billedartikler(articles, nu=nu)) == 6
    for count in (2, 2, 1):
        before = api.call_count
        c.udfyld_billedmotiver(articles, nu=nu)
        batch = json.loads(motif.call_args.args[2])
        assert len(batch) == count, 'Kun denne kørsels billedportion skal have nye motiver'
        assert all(item['rubrik'] != 'Teleskop' for item in batch), 'Et eksisterende billede skal ikke have nyt motiv'
        c.lav_billeder(articles, nu=nu)
        assert api.call_count - before == count
    assert api.call_count == 5 and all(c._gemt_artikelbillede(a) for a in articles)
    c.udfyld_billedmotiver(articles, nu=nu); c.lav_billeder(articles, nu=nu)
    assert motif.call_count == 3 and api.call_count == 5, 'Hele køen skal genbruges efter indhentning'

    # Også mislykkede API-forsøg tæller mod loftet; ingen skjult ekstra portion.
    for a in articles[1:]:
        (root / a.pop('billede')).unlink()
        (images / c._billed_navn(a['link'])).unlink()
    api.reset_mock(); api.side_effect = [ValueError('test'), b'image', b'not reached']
    c.lav_billeder(articles, nu=nu)
    assert api.call_count == 2
print('OK: Alle seks historier, portioner, motivbudget, indhentning og genbrug')
