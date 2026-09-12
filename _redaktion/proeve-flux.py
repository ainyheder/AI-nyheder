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
    stack.enter_context(patch.object(c,'_kort_artikler',return_value={article['link']}))
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
        with patch.object(c,'_kort_artikler',return_value={article['link']}):
            c.lav_billeder([article,archive])
        assert api.call_count == 1, 'Arvede billeder skal genbruges'
        # Gamle JPG'er må heller ikke genlaves, når de bliver forsidehistorier.
        with patch.object(c,'_kort_artikler',return_value={archive['link']}):
            c.lav_billeder([article,archive])
        assert api.call_count == 1
        # Arkiveret WebP og tilhørende original bevares, også uden artikel i feedet.
        (root/'archive.html').write_text('<img src="'+article['billede']+'">')
        c.lav_billeder([archive])
        assert (root/article['billede']).is_file()
        assert (root/article['billede']).with_suffix('.jpg').is_file()
print('OK: Nye WebP-billeder, fejlbevaring, topkort-budget, arkiv og genbrug')
