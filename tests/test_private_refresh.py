import json,unittest,uuid
from pathlib import Path
from unittest.mock import patch
from scripts.refresh_jobs import refresh

class PrivateRefreshTests(unittest.TestCase):
 def test_private_refresh_never_overwrites_public_catalogue(self):
  app=Path(__file__).resolve().parents[3]/'work'/('privacy-refresh-'+uuid.uuid4().hex)
  for folder in ['data','config','lib','public','dist/client']:(app/folder).mkdir(parents=True,exist_ok=True)
  def write(name,value):(app/name).write_text(json.dumps(value),encoding='utf-8')
  write('lib/seed.json',{'jobs':[],'resources':[]})
  write('config/sources.json',{'sources':[]})
  write('public/catalog.json',{'jobs':[],'marker':'public'})
  public=(app/'public/catalog.json').read_bytes()
  write('data/sources.private.json',{'sources':[{'id':'private-test'}]})
  write('data/catalog.private.json',{'jobs':[{'id':'private-job'}]})
  write('data/schedule.private.json',{'mode':'reminder-only'})
  result={'jobs':[{'id':'private-job'}],'sources':[],'summary':{'sourcesSucceeded':1}}
  with patch('scripts.refresh_jobs.collect',return_value=result) as collect:
   refresh(app,apply=True)
   self.assertEqual(collect.call_args.args[0]['sources'][0]['id'],'private-test')
   self.assertEqual(collect.call_args.args[1][0]['id'],'private-job')
  self.assertEqual((app/'public/catalog.json').read_bytes(),public)
  self.assertEqual(json.loads((app/'data/catalog.private.json').read_text())['jobs'][0]['id'],'private-job')
  self.assertEqual((app/'dist/client/catalog.json').read_bytes(),(app/'data/catalog.private.json').read_bytes())
