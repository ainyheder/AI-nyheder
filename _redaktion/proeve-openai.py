"""Offline-kontrol af OpenAI-modelvalg, kald, værktøjer og katalog."""
import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import patch
import crawler
import redaktoer_agent

spec = importlib.util.spec_from_file_location('catalog', Path(__file__).with_name('opdater-modeller.py'))
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)
assert crawler.model_udbyder('gpt-6.1-sol') == 'openai'
with patch.object(crawler, '_hjerner_cache', {'brief': {'model': 'gpt-6.1-sol'}, 'forside_agent': {'model': 'gpt-6-luna'}}), \
     patch.object(crawler, 'OPENAI_KEY', 'test-key'), patch.object(crawler, 'hent_url') as request:
    request.return_value = json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': 'svar'}}]})
    assert crawler.hjerne_kald('brief', 'system', 'input', 100) == 'svar'
    args, kwargs = request.call_args
    body = json.loads(kwargs['data'])
    assert args[0] == 'https://api.openai.com/v1/chat/completions'
    assert kwargs['headers']['Authorization'] == 'Bearer test-key'
    assert body['model'] == 'gpt-6.1-sol' and body['messages'][1]['content'] == 'input'
    assert crawler.special_model('forside_agent', 'default', 'deepseek') == 'gpt-6-luna'
    request.return_value = json.dumps({'choices': [{'finish_reason': 'length', 'message': {'content': 'afbrudt'}}]})
    try:
        crawler.kald_openai_model('s', 'u', 100, 'gpt-6-luna')
        raise AssertionError('Afbrudt svar accepteret')
    except ValueError:
        pass

class Response:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, size):
        return json.dumps({'choices': [{'finish_reason': 'tool_calls', 'message': {'tool_calls': []}}]}).encode()
with patch.object(redaktoer_agent.urllib.request, 'urlopen', return_value=Response()) as request:
    assert 'tool_calls' in redaktoer_agent.openai_kald('test-key', 'gpt-6-luna', [], redaktoer_agent.TOOLS)
    req = request.call_args.args[0]
    assert req.full_url == 'https://api.openai.com/v1/chat/completions'
    assert json.loads(req.data)['tools']
rows = {'data': [{'id': 'gpt-6-luna'}, {'id': 'gpt-audio'}, {'id': 'text-embedding-3-small'}]}
assert catalog.hent('OpenAI', 'test-key', lambda req, timeout: io.StringIO(json.dumps(rows))) == ['gpt-6-luna']
print('OK: OpenAI-tekst, afbrudte svar, redaktørværktøjer og modelkatalog')
