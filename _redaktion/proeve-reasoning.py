"""Offline integration: provider routing, reasoning settings and invalid responses."""
import sys
import json
import io
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crawler as c
import redaktoer_agent as agent
from _redaktion.ai_indstillinger import validate_thinking, gemini_thinking

class ReasoningTests(unittest.TestCase):
    def setUp(self):
        self.sent = []
        def fake(url, data=None, headers=None, **kwargs):
            self.sent.append((url, json.loads(data), headers))
            if 'googleapis' in url:
                return json.dumps({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'private thought','thought':True},{'text':'{}'}]}}]}).encode()
            return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]}).encode()
        self.ctx = [patch.object(c,'hent_url',fake),patch.object(c,'GEMINI_PAUSE_SEK',0),
                    patch.object(c,'XIAOMI_KEY','X-TEST'),patch.object(c,'DEEPSEEK_KEY','D-TEST'),
                    patch.object(c,'GEMINI_KEY','G-TEST'),patch.object(c,'_hjerner_cache',{}),
                    patch.object(c,'_doede_modeller',set()),patch.object(c,'_model_fejl',{})]
        for ctx in self.ctx: ctx.start()
        self.addCleanup(lambda: [ctx.stop() for ctx in reversed(self.ctx)])

    def call(self,model,thinking,step='brief',**kwargs):
        c._hjerner_cache[step]={'model':model,'thinking':thinking}
        self.assertEqual(c.hjerne_kald(step,'system','user',4000,**kwargs),'{}')
        return self.sent[-1]

    def test_deepseek_levels_and_json_are_independent(self):
        for level in ['low','high','max','disabled']:
            _,body,headers=self.call('deepseek-flash',level)
            self.assertEqual(body['thinking']['type'],'disabled' if level=='disabled' else 'enabled')
            self.assertEqual(body.get('reasoning_effort'),None if level=='disabled' else level)
            self.assertNotIn('response_format',body)
            self.assertEqual(headers['Authorization'],'Bearer D-TEST')
        _,body,_=self.call('deepseek-flash','low',step='nyhedsbrev',reasoning_effort='high')
        self.assertEqual(body['reasoning_effort'],'low')
        self.assertEqual(body['response_format'],{'type':'json_object'})

    def test_xiaomi_routing_and_modes(self):
        for model in ['mimo-v2.6-flash','mimo-v2.6-pro','mimo-v2.6-pro-ultraspeed']:
            for mode in ['enabled','disabled']:
                url,body,headers=self.call(model,mode)
                self.assertEqual(url,'https://api.xiaomimimo.com/v1/chat/completions')
                self.assertEqual(headers['api-key'],'X-TEST')
                self.assertEqual(body['model'],model)
                self.assertEqual(body['thinking'],{'type':mode})
                self.assertNotIn('reasoning_effort',body)
        with patch.object(c,'XIAOMI_KEY',''),patch.object(c,'kald_ai',return_value='{}') as fallback:
            self.call('mimo-v2.6-flash','enabled')
            self.assertEqual(fallback.call_args.kwargs,{})

    def test_gemini_levels_budgets_and_final_text(self):
        for model,setting,expected in [('gemini-3.6-flash','medium',{'thinkingLevel':'medium'}),
                                      ('gemini-3.1-pro-preview','high',{'thinkingLevel':'high'}),
                                      ('gemini-2.5-flash','budget:2048',{'thinkingBudget':2048}),
                                      ('gemini-2.5-pro','dynamic',{'thinkingBudget':-1}),
                                      ('gemini-2.5-flash-lite','disabled',{'thinkingBudget':0})]:
            _,body,headers=self.call(model,setting)
            self.assertEqual(body['generationConfig']['thinkingConfig'],expected)
            self.assertEqual(headers['x-goog-api-key'],'G-TEST')
        self.assertEqual(gemini_thinking('gemini-3.1-flash-lite-image','high'),{'thinkingConfig':{'thinkingLevel':'high'}})

    def test_invalid_settings_rejected_before_network(self):
        for model,setting in [('mimo-v2.6-pro','high'),('gemini-3.8-flash','minimal'),
                              ('gemini-3.1-pro-preview','minimal'),('gemini-2.5-pro','disabled'),
                              ('gemini-2.5-flash-lite','budget:511'),('gemini-2.5-flash','budget:24577'),
                              ('gemini-new-unknown','high'),('deepseek-flash','medium')]:
            with self.subTest(model=model,setting=setting),self.assertRaises(ValueError):
                self.call(model,setting)
        self.assertEqual(self.sent,[])

    def test_xiaomi_rejects_truncation(self):
        with patch.object(c,'hent_url',return_value=json.dumps({'choices':[{'finish_reason':'length','message':{'content':'partial'}}]})):
            with self.assertRaises(ValueError): c.kald_xiaomi_model('s','u',100,'mimo-v2.6-pro')

    def test_agent_transport(self):
        def fake(req,**kwargs):
            self.sent.append(json.loads(req.data))
            return io.BytesIO(json.dumps({'choices':[{'finish_reason':'tool_calls','message':{'tool_calls':[]}}]}).encode())
        with patch.object(agent.urllib.request,'urlopen',fake):
            agent.deepseek_kald('test','deepseek-flash',[],[],thinking='low')
        self.assertEqual(self.sent[0]['reasoning_effort'],'low')

    def test_xiaomi_agent_transport(self):
        history = [{"role":"assistant","content":None,"reasoning_content":"private","tool_calls":[]},
                   {"role":"user","content":"fortsæt"}]
        sent = []
        def fake(req, **kwargs):
            sent.append((req, json.loads(req.data)))
            return io.BytesIO(json.dumps({'choices':[{'finish_reason':'tool_calls','message':{'tool_calls':[]}}]}).encode())
        with patch.object(agent.urllib.request,'urlopen',fake):
            for mode in ['enabled','disabled']:
                agent.xiaomi_kald('x-test','mimo-v2.6-pro',history,agent.TOOLS,thinking=mode)
                req,body=sent[-1]
                self.assertEqual(req.full_url,'https://api.xiaomimimo.com/v1/chat/completions')
                self.assertEqual(req.get_header('Api-key'),'x-test')
                self.assertEqual(body['thinking'],{'type':mode})
                self.assertEqual(body['tool_choice'],'auto')
                self.assertEqual(body['messages'],history)
                self.assertEqual(body['tools'],agent.TOOLS)
                self.assertNotIn('reasoning_effort',body)

    def test_xiaomi_catalog_excludes_audio(self):
        spec=importlib.util.spec_from_file_location('catalog',Path(__file__).with_name('opdater-modeller.py'))
        catalog=importlib.util.module_from_spec(spec);spec.loader.exec_module(catalog)
        def fake(req,**kwargs):
            self.assertEqual(req.full_url,'https://api.xiaomimimo.com/v1/models')
            self.assertEqual(req.get_header('Api-key'),'test')
            return io.StringIO(json.dumps({'data':[{'id':m} for m in ['mimo-v2.6-pro','mimo-v2.5-tts','mimo-v2.5-asr','foreign-model']]}))
        self.assertEqual(catalog.hent('Xiaomi','test',fake),['mimo-v2.6-pro'])

if __name__=='__main__': unittest.main()
