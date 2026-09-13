import importlib.util,json,unittest,uuid,threading,urllib.request,urllib.error
from pathlib import Path
APP=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('local_service',APP/'local_service.py')
service=importlib.util.module_from_spec(spec);spec.loader.exec_module(service)
class LocalServiceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=APP.parents[1]/'work'/('test-state-'+uuid.uuid4().hex)
  cls.folder.mkdir(parents=True)
  cls.store=service.StateStore(cls.folder,{'schemaVersion':1,'jobs':[],'profile':{'name':'Test','evidence':[]}})
  cls.server=service.make_server(0,store=cls.store)
  threading.Thread(target=cls.server.serve_forever,daemon=True).start()
  cls.url='http://127.0.0.1:'+str(cls.server.server_port)
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
 def request(self,path='/api/state',data=None,origin=None):
  headers={'Content-Type':'application/json','X-Internship-OS':'1'}
  if origin:headers['Origin']=origin
  req=urllib.request.Request(self.url+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
  try:
   with urllib.request.urlopen(req) as r:return r.status,json.load(r)
  except urllib.error.HTTPError as e:return e.code,json.load(e)
 def test_1_save_survives_restart_and_snapshots_are_retained(self):
  status,p=self.request();s=p['state'];s['jobs']=[{'id':'t1','title':'Intern','url':'https://example.com/job','status':'Applied'}]
  status,r=self.request(data={'state':s,'revision':p['revision']});self.assertEqual(status,200)
  reopened=service.StateStore(self.folder,{})
  self.assertEqual(reopened.read()['state']['jobs'][0]['status'],'Applied')
  self.assertGreaterEqual(len(list(self.folder.glob('state-*.json*'))),1)
 def test_2_stale_revision_cannot_overwrite(self):
  status,r=self.request(data={'state':{'schemaVersion':1,'jobs':[],'profile':{'evidence':[]}},'revision':-1});self.assertEqual(status,409)
 def test_3_cross_origin_write_rejected(self):
  status,r=self.request(data={'state':{},'revision':0},origin='https://attacker.example');self.assertEqual(status,403)
 def test_4_private_source_files_not_served(self):
  for path in ['/data/local-profile.json','/data/application-memory.json','/data/resume-files.json']:
   status,r=self.request(path);self.assertEqual(status,404)
 def test_5_dropping_existing_jobs_is_rejected(self):
  _,p=self.request();p['state']['jobs']=[]
  status,r=self.request(data={'state':p['state'],'revision':p['revision']});self.assertEqual(status,400)
 def test_6_incomplete_snapshot_retains_last_complete_record(self):
  before=self.store.read()
  (self.folder/'state-9999999999-interrupted.json.gz').write_bytes(b'\x1f\x8b\x08')
  self.assertEqual(self.store.read(),before)
 def test_7_refresh_route_returns_new_catalogue_contract(self):
  from unittest.mock import patch
  import sys
  sys.path.insert(0,str(APP))
  sample={'schemaVersion':2,'jobs':[],'sources':[],'changes':[],'summary':{'new':0,'updated':0,'sourcesSucceeded':1}}
  with patch('scripts.refresh_jobs.refresh',return_value=sample) as refresh:
   status,result=self.request('/api/refresh',data={'confirmed':True})
   self.assertEqual(status,200);self.assertEqual(result,sample);refresh.assert_called_once()
 def test_8_refresh_requires_explicit_confirmation_before_any_collection(self):
  from unittest.mock import patch
  with patch('scripts.refresh_jobs.refresh') as refresh:
   status,result=self.request('/api/refresh',data={});self.assertEqual(status,400);refresh.assert_not_called()
if __name__=='__main__':unittest.main()
