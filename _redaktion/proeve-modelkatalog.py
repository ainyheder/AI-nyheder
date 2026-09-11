import importlib.util
import io
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crawler
spec = importlib.util.spec_from_file_location('catalog', Path(__file__).with_name('opdater-modeller.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
requests = []
responses = [ {'models':[{'name':'models/gemini-text','supportedGenerationMethods':['generateContent']}, {'name':'models/embedding','supportedGenerationMethods':['embedContent']}], 'nextPageToken':'two'}, {'models':[{'name':'models/gemini-image','supportedGenerationMethods':['generateContent']}]} ]
def fake(req, timeout):
    requests.append(req)
    return io.StringIO(json.dumps(responses.pop(0)))
assert m.hent('Gemini','test-secret',fake)==['gemini-image','gemini-text']
assert 'pageToken=two' in requests[1].full_url
assert all('test-secret' not in r.full_url for r in requests)
try:
    m.hent('DeepSeek','test',lambda *a,**k:io.StringIO('{"data":[]}'))
    raise AssertionError('Empty response accepted')
except ValueError:
    pass
crawler._hjerner_cache={'forside_agent':{'model':'deepseek-custom'},'billedgenerator':{'model':'gemini-custom-image'}}
assert crawler.special_model('forside_agent','default','deepseek')=='deepseek-custom'
assert crawler.special_model('billedgenerator','default','gemini')=='gemini-custom-image'
crawler._hjerner_cache['forside_agent']['model']='gemini-text'
crawler._hjerner_cache['billedgenerator']['model']='gemini-text'
assert crawler.special_model('forside_agent','default','deepseek')=='default'
assert crawler.special_model('billedgenerator','default','gemini')=='default'
print('OK: pagination, provider filtering, empty results, key handling and special model overrides')
