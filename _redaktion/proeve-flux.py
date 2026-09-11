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
