"""Loopback-only personal job workspace. Saves append-only snapshots; no delete API."""
import argparse,concurrent.futures,datetime,gzip,html,json,mimetypes,re,threading,time,uuid,urllib.request,urllib.parse,webbrowser
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from html.parser import HTMLParser

APP=Path(__file__).resolve().parent
MAX_BODY=50_000_000
RESUME_CONFIG=APP/'data/resume-files.json'
FILES={k:Path(v) for k,v in json.loads(RESUME_CONFIG.read_text(encoding='utf-8')).items()} if RESUME_CONFIG.exists() else {}
class StateStore:
 def __init__(self,folder,seed):
  self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True);self.lock=threading.Lock();self.seed=seed
 def read(self):
  files=sorted(list(self.folder.glob('state-*.json'))+list(self.folder.glob('state-*.json.gz')))
  for f in reversed(files):
   try:
    if f.suffix=='.gz':
     with gzip.open(f,'rt',encoding='utf-8') as stream:return json.load(stream)
    return json.loads(f.read_text(encoding='utf-8'))
   except (ValueError,OSError,EOFError):continue
  return {'service':'internship-os','revision':0,'state':self.seed}
 def save(self,state,revision):
  if not isinstance(state,dict) or state.get('schemaVersion')!=1 or not isinstance(state.get('jobs'),list) or not isinstance(state.get('profile'),dict) or not isinstance(state['profile'].get('evidence'),list):raise ValueError('Invalid workspace backup.')
  if len(state['jobs'])>10000:raise ValueError('Too many records.')
  ids=[]
  for j in state['jobs']:
   if not isinstance(j,dict) or not j.get('id') or not j.get('title'):raise ValueError('Each job needs an ID and title.')
   ids.append(j['id'])
   u=urllib.parse.urlsplit(j.get('url',''))
   if j.get('url') and (u.scheme not in ['http','https'] or not u.netloc or u.username):raise ValueError('Invalid job URL.')
  if len(ids)!=len(set(ids)):raise ValueError('Duplicate job IDs.')
  with self.lock:
   old=self.read()
   if revision!=old['revision']:raise RuntimeError('Records changed in another window. Export this browser copy and reload before merging.')
   if not set(j['id'] for j in old['state'].get('jobs',[])).issubset(ids):raise ValueError('Records cannot be removed. Use Archived status.')
   record={'service':'internship-os','revision':old['revision']+1,'savedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'state':state}
   name=f"state-{record['revision']:010d}-{uuid.uuid4().hex[:8]}.json.gz"
   with gzip.open(self.folder/name,'xt',encoding='utf-8',compresslevel=5) as f:json.dump(record,f,ensure_ascii=False,separators=(',',':'))
   return record

class TextParser(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,s):self.parts.append(s)
 def handle_starttag(self,tag,attrs):
  if tag in ['p','li','br','h1','h2','h3','h4']:self.parts.append('\n')
 def handle_endtag(self,tag):
  if tag in ['p','li','h1','h2','h3','h4']:self.parts.append('\n')
def plain(value):
 p=TextParser();p.feed(html.unescape(value or ''));return re.sub(r'\n{3,}','\n\n',''.join(p.parts)).strip()
def default_boards():
 seed=json.loads((APP/'lib/seed.json').read_text(encoding='utf-8'));boards={}
 for j in seed['jobs']:
  u=urllib.parse.urlsplit(j.get('url',''));parts=u.path.strip('/').split('/')
  if u.hostname and u.hostname.endswith('greenhouse.io') and parts and re.fullmatch(r'[A-Za-z0-9_-]+',parts[0]):boards['greenhouse:'+parts[0]]={'kind':'greenhouse','token':parts[0],'company':j['company']}
  elif u.hostname=='jobs.lever.co' and parts:boards['lever:'+parts[0]]={'kind':'lever','token':parts[0],'company':j['company']}
 return list(boards.values())
def fetch_board(board):
 token=board['token'];kind=board['kind']
 if not re.fullmatch(r'[A-Za-z0-9_-]+',token):raise ValueError('Invalid board token.')
 url=f'https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true' if kind=='greenhouse' else f'https://api.lever.co/v0/postings/{token}?mode=json'
 request=urllib.request.Request(url,headers={'User-Agent':'PersonalInternshipWorkspace/1.0','Accept':'application/json'})
 with urllib.request.urlopen(request,timeout=18) as response:
  if urllib.parse.urlsplit(response.url).hostname not in ['boards-api.greenhouse.io','api.lever.co']:raise ValueError('Unexpected feed destination.')
  payload=json.loads(response.read(8_000_001))
 rows=payload.get('jobs',[]) if kind=='greenhouse' else payload
 result=[]
 for j in rows[:2000]:
  title=j.get('title') or j.get('text','');body=plain(j.get('content') or j.get('descriptionPlain') or j.get('description',''))
  if kind=='lever':body+='\n'+'\n'.join(plain(l.get('text','')+'\n'+l.get('content','')) for l in j.get('lists',[]))
  combined=title+'\n'+body
  if not re.search(r'intern|co-op',title,re.I) or not re.search(r'2027',combined) or not re.search(r'software|machine learning|data scien|AI|artificial intelligence',title,re.I):continue
  track='MLE' if re.search(r'machine learning|data scien',title,re.I) else 'AIE' if re.search(r'\bAI\b|artificial intelligence',title,re.I) else 'SDE'
  location=j.get('location',{}).get('name','') if kind=='greenhouse' else j.get('categories',{}).get('location','')
  result.append({'id':f'{kind}-{token}-{j["id"]}','company':board['company'],'title':title,'location':location,'url':j.get('absolute_url') or j.get('hostedUrl'),'jd':body[:60000],'year':2027,'season':'Summer' if re.search(r'summer',combined,re.I) else 'Unknown','tracks':[track],'checkedAt':datetime.date.today().isoformat(),'source':'Employer public feed','sourceState':'live-feed','openStatus':'Published in public feed','requirementsClassified':False,'jdTextKind':'Full employer public feed text. Country, dates and eligibility still need review.','sourceUpdatedAt':j.get('updated_at',''),'deadline':j.get('application_deadline','')})
 return result

def make_server(port=4318,store=None):
 if store is None:
  seed_path=APP/'data/seed-before-privacy-20260913.json'
  seed=json.loads((seed_path if seed_path.exists() else APP/'lib/seed.json').read_text(encoding='utf-8'))
  if (APP/'data/local-profile.json').exists():seed['profile'].update(json.loads((APP/'data/local-profile.json').read_text(encoding='utf-8')))
  # Keep evidence levels consistent with the validated web seed.
  for e in seed['profile']['evidence']:
   if 'listed' in e['title'].lower() or 'toolkit' in e['title'].lower():e['kind']='listed'
  store=StateStore(APP/'data/history',seed)
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def reply(self,status,data):
   b=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
  def host_ok(self):return self.headers.get('Host') in [f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}']
  def do_GET(self):
   if not self.host_ok():return self.reply(403,{'error':'Local access only.'})
   path=urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
   if path=='/api/state':return self.reply(200,store.read())
   if path=='/api/health':return self.reply(200,{'service':'internship-os','ok':True,'version':2,'catalogueRefresh':True})
   if path=='/catalog.json' and (APP/'data/catalog.private.json').exists():return self.reply(200,json.loads((APP/'data/catalog.private.json').read_text(encoding='utf-8')))
   if path.startswith('/api/') or path.startswith('/data/'):return self.reply(404,{'error':'Not found.'})
   if path.startswith('/files/'):
    f=FILES.get(path.split('/')[-1]);attachment=True
   else:
    public=(APP/'dist/client').resolve();f=(public/path.lstrip('/')).resolve();attachment=False
    if not f.is_relative_to(public):return self.reply(404,{'error':'Not found.'})
    if f.is_dir():f=f/'index.html'
   if not f or not f.is_file():return self.reply(404,{'error':'Not found. Build the local app first.'})
   b=f.read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(str(f))[0] or 'application/octet-stream');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-cache');self.send_header('Content-Length',str(len(b)))
   if attachment:self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+urllib.parse.quote(f.name))
   self.end_headers();self.wfile.write(b)
  def do_POST(self):
   origin=self.headers.get('Origin');allowed=[f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}']
   if not self.host_ok() or origin and origin not in allowed or self.headers.get('X-Internship-OS')!='1' or self.headers.get('Sec-Fetch-Site')=='cross-site':return self.reply(403,{'error':'Local same-origin requests only.'})
   if not self.headers.get('Content-Type','').startswith('application/json'):return self.reply(415,{'error':'JSON required.'})
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=MAX_BODY:raise ValueError('Invalid request size.')
    payload=json.loads(self.rfile.read(size))
    if self.path=='/api/state':
     saved=store.save(payload.get('state'),payload.get('revision'));return self.reply(200,{'revision':saved['revision']})
    if self.path=='/api/refresh':
     if payload.get('confirmed') is not True:return self.reply(400,{'error':'Confirm this update before collecting job sources.'})
     if time.monotonic()-self.server.last_refresh<30:return self.reply(429,{'error':'Wait 30 seconds before checking again.'})
     if not self.server.refresh_lock.acquire(blocking=False):return self.reply(409,{'error':'A source refresh is already running. Your records remain available.'})
     try:
      self.server.last_refresh=time.monotonic()
      from scripts.refresh_jobs import refresh
      catalogue=refresh(app=APP,apply=True)
      return self.reply(200,catalogue)
     finally:self.server.refresh_lock.release()
    return self.reply(404,{'error':'Not found.'})
   except RuntimeError as e:return self.reply(409,{'error':str(e)})
   except (ValueError,TypeError,AttributeError,KeyError):return self.reply(400,{'error':'Invalid workspace data. Existing records were preserved.'})
 server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.last_refresh=-1000;server.refresh_lock=threading.Lock();return server
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=4318);parser.add_argument('--open',action='store_true');args=parser.parse_args()
 server=make_server(args.port);url=f'http://127.0.0.1:{server.server_port}/'
 print('Internship OS ready at '+url,flush=True)
 if args.open:webbrowser.open(url)
 try:server.serve_forever()
 except KeyboardInterrupt:server.server_close()
