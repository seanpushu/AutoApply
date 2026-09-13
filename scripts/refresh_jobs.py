"""Rebuild the public catalogue while retaining all prior files and job records."""
import argparse,datetime,json,sys,uuid
from pathlib import Path
APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from catalogue import collect,merge_catalogue,canonical,NOW

def refresh(app=APP,apply=True):
 private=any((app/'data'/name).exists() for name in ['sources.private.json','catalog.private.json','researched-jobs.private.json','schedule.private.json'])
 config_path=app/'data/sources.private.json' if (app/'data/sources.private.json').exists() else app/'config/sources.json'
 config=json.loads(config_path.read_text(encoding='utf-8'))
 seed=json.loads((app/'lib/seed.json').read_text(encoding='utf-8'))
 old_path=app/'data/catalog.private.json' if private else app/'public/catalog.json'
 previous=old_path if old_path.exists() else app/'public/catalog.json'
 old=json.loads(previous.read_text(encoding='utf-8')) if previous.exists() else {'jobs':seed['jobs']}
 research_path=app/'data/researched-jobs.private.json' if (app/'data/researched-jobs.private.json').exists() else app/'config/researched-jobs.json'
 extra=json.loads(research_path.read_text(encoding='utf-8')).get('jobs',[]) if research_path.exists() else []
 result=collect(config,old['jobs'],extra)
 old_health={s['id']:s for s in old.get('sources',[])}
 for source in result['sources']:
  if source['status']=='failed':source['lastSuccessAt']=old_health.get(source['id'],{}).get('lastSuccessAt')
 result['resources']=config.get('resources',seed.get('resources',[]))
 schedule_path=app/'data/schedule.private.json' if (app/'data/schedule.private.json').exists() else app/'config/schedule.json'
 result['schedule']=json.loads(schedule_path.read_text(encoding='utf-8')) if schedule_path.exists() else {'status':'not-configured','intervalDays':3}
 if not result['summary']['sourcesSucceeded']:raise RuntimeError('Every source failed. Previous catalogue retained; no successful update was recorded.')
 if apply:
  archive=app/'data/catalogue-history';archive.mkdir(parents=True,exist_ok=True)
  stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:6]
  if old_path.exists():(archive/f'before-{stamp}.json').write_bytes(old_path.read_bytes())
  payload=json.dumps(result,ensure_ascii=False,separators=(',',':'))
  (archive/f'run-{stamp}.json').write_text(payload,encoding='utf-8')
  old_path.parent.mkdir(exist_ok=True);old_path.write_text(payload,encoding='utf-8')
  # Local service serves built assets. Update its catalogue immediately without a frontend rebuild.
  built=app/'dist/client/catalog.json'
  if built.parent.exists():built.write_text(payload,encoding='utf-8')
 return result

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--preview',action='store_true');args=parser.parse_args()
 try:
  result=refresh(app=APP,apply=args.apply and not args.preview)
  print(json.dumps({'summary':result['summary'],'updatedAt':result['updatedAt'],'applied':args.apply and not args.preview},ensure_ascii=False),flush=True)
 except Exception as error:
  print('Refresh failed; previous catalogue files retained: '+str(error),file=sys.stderr);sys.exit(1)
