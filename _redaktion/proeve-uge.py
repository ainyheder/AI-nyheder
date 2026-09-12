"""Rullende periode, redaktørens fortælling og separat fredagsbrev. Intet netværk."""
import json,sys,tempfile,unittest
from contextlib import contextmanager,ExitStack
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import crawler as c
import ugeoverblik as u
import redaktion as r

ROOT=Path(__file__).resolve().parent.parent
ZONE=ZoneInfo('Europe/Copenhagen')
NU=datetime(2026,9,13,12,tzinfo=ZONE)
def artikel(n,alder=1,nu=NU):
 return {'link':f'https://example.com/{n}','rubrik':f'Nyhed {n} med konkret indhold',
         'titel':f'News {n}', 'resume_da':'Kildens sammenfatning af nyheden med en konkret ny oplysning.',
         'dato':(nu-timedelta(days=alder)).isoformat(),'prio':7,'kategori':'Forskning','kilde':'Test'}
def svar(arts):
 links=[a['link'] for a in arts]
 return {'rubrik':'Ugens konkrete udviklinger','indledning':'De største historier forbindes af nye måder at arbejde med AI på.',
         'historier':[{'overskrift':a['rubrik'],'tekst':'Her er en forklaring på den konkrete nyhed med oplysninger fra kilden.','link':a['link']} for a in arts],
         'overblik':[{'tekst':'Periodens første udvikling giver en ny måde at udføre en opgave på. Den skal ses i sammenhæng med de øvrige historier og deres begrænsninger.','links':links},
                     {'tekst':'Det samlede billede afhænger også af adgang og dokumentation. Historiernes forskelle fortæller, hvilke muligheder læseren faktisk kan bruge.','links':links[:1]}], 'tendens':''}

@contextmanager
def workspace(api='test'):
 with tempfile.TemporaryDirectory() as tmp,ExitStack() as stack:
  root=Path(tmp);(root/'data').mkdir();(root/'_redaktion').mkdir()
  (root/'_redaktion/uge-skabelon.html').write_text((ROOT/'_redaktion/uge-skabelon.html').read_text())
  (root/'feed-uge.xml').write_text('Tidligere fredagsfeed')
  for name,value in {'ROOT':root,'UGE_JSON':root/'data/uge.json','UGE_HTML':root/'uge.html',
                     'UGE_FEED':root/'feed-uge.xml','UGE_UDSENDELSE':root/'data/uge-udsendelse.json','API_KEY':api}.items():
   stack.enter_context(patch.object(c,name,value))
  stack.enter_context(patch.object(c,'hjerne_prompt',return_value=c.SYSTEM_UGE))
  stack.enter_context(patch.object(c.urllib.request,'urlopen',side_effect=AssertionError('Intet netværk i test')))
  yield root

def seed(arts,nu=NU):
 d=u.kontroller_svar(svar(arts),arts);start,slut=r.ugeperiode(nu)
 d.update(dato=nu.isoformat(),periode_fra=start.isoformat(),periode_til=slut.isoformat(),metode='ai',
          basis_signatur=u.signatur(u.kandidater(arts,nu),c.SYSTEM_UGE))
 c._skriv_uge(d);return d

class UgeTests(unittest.TestCase):
 def test_den_13_daekker_6_til_12_og_udelukker_i_dag(self):
  start,slut=r.ugeperiode(NU)
  self.assertEqual(start.astimezone(ZONE).isoformat(),'2026-09-06T00:00:00+02:00')
  self.assertEqual(slut.astimezone(ZONE).isoformat(),'2026-09-13T00:00:00+02:00')
  arts=[{**artikel(i),'dato':d.isoformat()} for i,d in enumerate([start-timedelta(microseconds=1),start,slut-timedelta(microseconds=1),slut,NU])]
  self.assertEqual({a['link'] for a in u.kandidater(arts,NU)},{arts[1]['link'],arts[2]['link']})
 def test_maaned_aar_og_sommertid(self):
  for nu in [datetime(2027,1,1,12,tzinfo=ZONE),datetime(2026,4,1,12,tzinfo=ZONE),datetime(2026,10,28,12,tzinfo=ZONE)]:
   start,slut=r.ugeperiode(nu)
   self.assertEqual((slut.astimezone(ZONE).date()-start.astimezone(ZONE).date()).days,7)
   self.assertEqual(start.astimezone(ZONE).hour,0);self.assertEqual(slut.astimezone(ZONE).hour,0)
  # Perioden følger kalenderdage, ikke en forkert fast UTC-grænse ved sommertid.
  a,b=r.ugeperiode(datetime(2026,4,1,12,tzinfo=ZONE));self.assertEqual((b-a).total_seconds()/3600,167)
 def test_hele_puljen_sendes_med_artikeltekst(self):
  arts=[artikel(n) for n in range(40)];arts[0]['sektioner']=[{'tekst':'Vigtig kildeoplysning'}]
  arts[1]['sektioner']=None;arts[1]['brief']=None;arts[1]['detaljer']=None
  p=u.materiale(u.kandidater(arts,NU));self.assertEqual(len(p),40)
  self.assertTrue(any(a['artikeltekst']=='Vigtig kildeoplysning' for a in p))
 def test_gammel_stor_nyhed_faar_ikke_aldersstraf(self):
  a=artikel(1,7);a['prio']=9;b=artikel(2,1)
  self.assertEqual(u.kandidater([b,a],NU)[0]['link'],a['link'])
 def test_ugyldige_links_og_tomme_tekster_afvises(self):
  arts=[artikel(n) for n in range(3)]
  for felt,value in [('link','https://unknown.invalid/'),('link','javascript:alert(1)'),('tekst',''),('overskrift',{})]:
   d=svar(arts);d['historier'][0][felt]=value
   with self.assertRaises(ValueError):u.kontroller_svar(d,arts)
 def test_fortaelling_er_paakraevet_og_kun_bygger_paa_valgte(self):
  arts=[artikel(n) for n in range(3)]
  d=svar(arts);d['overblik']=[]
  with self.assertRaisesRegex(ValueError,'overordnede historie'):u.kontroller_svar(d,arts)
  d=svar(arts);d['overblik'][0]['links']=['https://unknown.invalid/']
  with self.assertRaisesRegex(ValueError,'valgte historier'):u.kontroller_svar(d,arts)
  d=svar(arts);d['overblik'][0]['links']=[arts[0]['link']]
  with self.assertRaisesRegex(ValueError,'Alle valgte'):u.kontroller_svar(d,arts)
 def test_samme_begivenhed_fra_to_kilder_afvises(self):
  a,b,z=artikel(1),artikel(2),artikel(3);a['andre']=[{'link':b['link'],'kilde':'Anden'}]
  with self.assertRaisesRegex(ValueError,'flere gange'):u.kontroller_svar(svar([a,b,z]),[a,b,z])
 def test_samme_input_genbruger_ai_men_flytter_perioden(self):
  arts=[artikel(n,3) for n in range(3)]
  with workspace():
   seed(arts)
   with patch.object(c,'hjerne_kald') as ai,patch.object(c,'_send_nyhedsbrev') as mail:
    d=c.lav_ugens_overblik(arts,nu=NU+timedelta(days=1),send_brev=False)
    self.assertEqual(len(d['historier']),3);self.assertEqual(d['periode_fra'],r.ugeperiode(NU+timedelta(days=1))[0].isoformat())
    ai.assert_not_called();mail.assert_not_called()
 def test_nye_gaarsdagsnyheder_udloeser_redaktoer_ogsaa_mandag(self):
  mandag=datetime(2026,9,14,12,tzinfo=ZONE);arts=[artikel(n,3) for n in range(3)]
  ny=artikel(99,1,mandag);dagens=artikel(100,0,mandag)
  with workspace():
   seed(arts)
   with patch.object(c,'hjerne_kald',return_value=json.dumps(svar([ny,*arts[:2]]))) as ai:
    d=c.lav_ugens_overblik([*arts,ny,dagens],nu=mandag,send_brev=False)
    ai.assert_called_once();payload=json.loads(ai.call_args.args[2]);links={a['link'] for a in payload['artikler']}
    self.assertIn(ny['link'],links);self.assertNotIn(dagens['link'],links)
    self.assertEqual(d['historier'][0]['link'],ny['link']);self.assertEqual(len(d['overblik']),2)
 def test_nyheder_fra_i_dag_udloeser_ikke_nyt_ugekald(self):
  arts=[artikel(n) for n in range(3)]
  with workspace():
   seed(arts)
   with patch.object(c,'hjerne_kald') as ai:
    c.lav_ugens_overblik([*arts,artikel(99,0)],nu=NU,send_brev=False);ai.assert_not_called()
 def test_en_eller_to_historier_vises_uden_ai(self):
  for antal in (1,2):
   with workspace(api=''),patch.object(c,'hjerne_kald') as ai:
    d=c.lav_ugens_overblik([artikel(n) for n in range(antal)],nu=NU,send_brev=False)
    self.assertEqual(len(d['historier']),antal);ai.assert_not_called()
 def test_ai_fejl_fjerner_udloebne_og_fylder_med_aktuelle(self):
  gamle=[artikel(n,7) for n in range(3)];nu=NU+timedelta(days=1);ny=artikel(99,1,nu)
  with workspace():
   seed(gamle)
   with patch.object(c,'hjerne_kald',return_value='{}'),patch.object(c,'_send_nyhedsbrev') as mail:
    d=c.lav_ugens_overblik([*gamle,ny],nu=nu)
    self.assertEqual([h['link'] for h in d['historier']],[ny['link']]);self.assertEqual(d['overblik'],[]);mail.assert_not_called()
 def test_tom_periode_viser_ikke_udloebne_historier(self):
  arts=[artikel(n,7) for n in range(3)]
  with workspace(api=''):
   seed(arts);d=c.lav_ugens_overblik(arts,nu=NU+timedelta(days=2),send_brev=False)
   self.assertEqual(d['historier'],[]);self.assertEqual(d['overblik'],[])
 def test_forkert_ai_svar_repareres(self):
  arts=[artikel(n) for n in range(3)];bad=svar(arts);bad['overblik']=[]
  with workspace(),patch.object(c,'hjerne_kald',side_effect=[json.dumps(bad),json.dumps(svar(arts))]) as ai:
   d=c.lav_ugens_overblik(arts,nu=NU,send_brev=False)
   self.assertEqual(ai.call_count,2);self.assertIn('overordnede historie',ai.call_args.args[2]);self.assertEqual(d['metode'],'ai')
 def test_cache_foelger_nyt_billede_uden_nyt_ai_kald(self):
  arts=[artikel(n) for n in range(3)]
  with workspace():
   seed(arts);arts[0]['billede']='data/img/new.webp'
   with patch.object(c,'hjerne_kald') as ai:
    d=c.lav_ugens_overblik(arts,nu=NU,send_brev=False);ai.assert_not_called()
    self.assertEqual(next(h for h in d['historier'] if h['link']==arts[0]['link'])['billede'],'data/img/new.webp')
 def test_webopdatering_aendrer_ikke_fredagsfeed(self):
  with workspace() as root:
   c.lav_ugens_overblik([artikel(1)],nu=NU,brug_ai=False,send_brev=False)
   self.assertEqual((root/'feed-uge.xml').read_text(),'Tidligere fredagsfeed')
 def test_brev_hoejst_en_gang_pr_uge_selvom_siden_opdateres(self):
  fredag=datetime(2026,9,11,12,tzinfo=ZONE);d=svar([artikel(n) for n in range(3)]);d['dato']=fredag.isoformat()
  with workspace(),patch.object(c,'_send_nyhedsbrev',return_value='sendt') as mail:
   for delta in (0,0,1,2,3):c._udgiv_fredagsbrev(d,fredag+timedelta(days=delta))
   self.assertEqual(mail.call_count,1)
   c._udgiv_fredagsbrev(d,fredag+timedelta(days=7));self.assertEqual(mail.call_count,2)
 def test_usikkert_mailresultat_bliver_ikke_sendt_igen(self):
  fredag=datetime(2026,9,11,12,tzinfo=ZONE);d=svar([artikel(n) for n in range(3)])
  with workspace(),patch.object(c,'_send_nyhedsbrev',return_value='ukendt') as mail:
   c._udgiv_fredagsbrev(d,fredag);c._udgiv_fredagsbrev(d,fredag+timedelta(hours=1));mail.assert_called_once()
 def test_migration_gensender_ikke_det_gamle_ugebrev(self):
  fredag=datetime(2026,9,11,12,tzinfo=ZONE)
  with workspace(),patch.object(c,'_send_nyhedsbrev') as mail:
   c._overtag_gammelt_ugebrev({'version':2,'uge':'2026-37','dato':fredag.isoformat()})
   c._udgiv_fredagsbrev(svar([artikel(n) for n in range(3)]),fredag);mail.assert_not_called()
 def test_oedelagt_udsendelsesstatus_blokerer_mail(self):
  with workspace(),patch.object(c,'_send_nyhedsbrev') as mail:
   c.UGE_UDSENDELSE.write_text('{broken');c._udgiv_fredagsbrev(svar([artikel(n) for n in range(3)]),NU);mail.assert_not_called()
 def test_render_viser_perioden_uden_i_dag_og_escape_fortaelling(self):
  arts=[artikel(n) for n in range(3)];d=u.kontroller_svar(svar(arts),arts);a,b=r.ugeperiode(NU)
  d.update(dato=NU.isoformat(),periode_fra=a.isoformat(),periode_til=b.isoformat());d['overblik'][0]['tekst']='<script>alert(1)</script>'
  page=u.render(d,ROOT,lambda _: '/artikel/test.html')
  self.assertIn('6. sep. – 12. sep. 2026',page);self.assertIn('De seneste 7 dage',page)
  self.assertIn('&lt;script&gt;',page);self.assertNotIn('<script>alert',page)
  self.assertLess(page.index('class="week-narrative"'),page.index('class="week-stories"'))

if __name__=='__main__':unittest.main(verbosity=2)
