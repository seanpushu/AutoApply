"""Public job-source adapters. A community season tag is a lead, not employer proof."""
import concurrent.futures,datetime,hashlib,html,ipaddress,json,re,socket,urllib.parse,urllib.request
from html.parser import HTMLParser

NOW=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
TODAY=lambda:datetime.date.today().isoformat()
STATES='AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split()
US_CITIES=['nyc','sf','new york','san francisco','seattle','boston','pittsburgh','san jose','palo alto','menlo park','mountain view','sunnyvale','santa clara','redmond','bellevue','austin','chicago','san diego','atlanta','irvine','houston','dallas','san mateo','foster city','washington dc','wilmington','north reading']

class CleanText(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ['script','style']:self.skip+=1
  if tag in ['p','li','br','div','h1','h2','h3','h4']:self.parts.append('\n')
 def handle_endtag(self,tag):
  if tag in ['script','style']:self.skip=max(0,self.skip-1)
  if tag in ['p','li','div']:self.parts.append('\n')
 def handle_data(self,s):
  if not self.skip:self.parts.append(s)
def strip_data_images(s):
 s=re.sub(r'\[data:image/[\w.+-]+;base64,[A-Za-z0-9+/=\r\n]+\]', '',str(s or ''))
 return re.sub(r'data:image/[\w.+-]+;base64,[A-Za-z0-9+/=]+','',s).strip()
def plain(s):
 p=CleanText();p.feed(html.unescape(strip_data_images(s)));return re.sub(r'\n\s*\n+','\n',''.join(p.parts)).strip()
def canonical(url):
 p=urllib.parse.urlsplit(url);host=(p.hostname or '').lower()
 if p.scheme not in ['http','https'] or not host or p.username or p.password:raise ValueError('Invalid public URL')
 if host in ['boards.greenhouse.io','job-boards.greenhouse.io']:host='job-boards.greenhouse.io'
 query=urllib.parse.urlencode([(k,v) for k,v in urllib.parse.parse_qsl(p.query) if not k.lower().startswith('utm_') and k not in ['gh_src','source','sourceType','lever-source','lever-origin','ref','refId','trk','trackingId','embed','utm']])
 path=p.path.rstrip('/')
 if host in ['jobs.lever.co','jobs.ashbyhq.com']:path=re.sub(r'/(?:apply|application)$','',path);query=''
 return urllib.parse.urlunsplit(('https',host,path,query,''))
def job_id(url):return 'catalog-'+hashlib.sha256(canonical(url).encode()).hexdigest()[:18]

def provider_identity(url):
 p=urllib.parse.urlsplit(url);host=p.hostname or '';path=p.path
 if host.endswith('.myworkdayjobs.com'):
  m=re.search(r'_((?:JR|R)\d+|\d{4}-\d+)(?:-\d+)?/?$',path)
  if m:return 'workday:'+host.split('.')[0].lower()+':'+m.group(1)
 if host in ['www.google.com','google.com']:
  m=re.search(r'/jobs/results/(\d+)',path)
  if m:return 'google:'+m.group(1)
 if host=='jobs.intuit.com':
  m=re.search(r'/27595/(\d+)/?$',path)
  if m:return 'intuit:'+m.group(1)
 if host=='careers.gevernova.com':
  m=re.search(r'/job/(R\d+)',path)
  if m:return 'workday:gevernova:'+m.group(1)
 if host=='careers.withwaymo.com':
  q=urllib.parse.parse_qs(p.query)
  if q.get('gh_jid'):return 'greenhouse:waymo:'+q['gh_jid'][0]
  if path.startswith('/jobs/') and len(path.split('/')[-1])>15:return 'waymo-slug:'+path.rstrip('/')
 return None
def evidence_time(j):
 try:
  dt=datetime.datetime.fromisoformat((j.get('officialVerifiedAt') or j.get('checkedAt') or '').replace('Z','+00:00'))
  return (dt if dt.tzinfo else dt.replace(tzinfo=datetime.timezone.utc)).timestamp()
 except (ValueError,TypeError):return 0
def is_us_location(location):
 s=str(location or '').strip();low=s.lower()
 if ' / ' in s or ';' in s:return any(is_us_location(part) for part in re.split(r' / |;',s))
 if low=='us' or re.search(r'(?:^|\W)u\.s\.(?:\W|$)',low):return True
 if re.search(r'united states|\busa\b|\bu\.s\.\b|^us[, -]|remote\s*[-–,]?\s*us\b',low):return True
 if re.search(r'\b(?:california|virginia|massachusetts|pennsylvania|washington|texas|colorado|illinois|north carolina|new jersey|ohio|maryland|florida|arizona|oregon|utah)\b',low):return True
 if re.search(r',\s*(?:'+ '|'.join(STATES)+r')\b',s):return True
 if re.search(r'\blos angeles\b',low):return True
 if re.search(r'canada|toronto|vancouver|montreal|ontario|united kingdom|london|ireland|india|singapore|hong kong|germany|australia|poland|netherlands|japan|china|israel',low):return False
 if any(low==city or low.startswith(city+',') or low.startswith(city+' -') or low.startswith(city+' (') for city in US_CITIES):return True
 return False
def tracks_for(title,category=''):
 s=title.lower();tracks=[]
 if re.search(r'intern conversion|product manag|sales analyst|operations intern|electrical engineer|mechanical engineer|marketing|recruiting|human resources|software installation|it support|desktop support|help desk|technology support|technical support',s):return []
 if re.search(r'\bai\b|llm|agent|generative|artificial intelligence|nlp|natural language',s):tracks.append('AIE')
 if re.search(r'machine learning|data scien|deep learning|computer vision|research (?:engineer|scientist)|\bml\b|mlops',s):tracks.append('MLE')
 if re.search(r'software|\bswe\b|full.?stack|back.?end|front.?end|platform|developer|data engineer|devops|reliability|firmware|technology (?:intern|developer)',s):tracks.append('SDE')
 return tracks

def country_for_location(location):
 if is_us_location(location):return 'US'
 if re.search(r'canada|toronto|vancouver|montreal|ontario|united kingdom|london|ireland|india|singapore|hong kong|germany|australia|poland|netherlands|japan|china|israel|france|switzerland|spain|brazil|mexico',str(location),re.I):return 'Outside US'
 return 'Unconfirmed'
def infer_term(title,body=''):
 pattern=r'(summer|spring|fall|winter)\s*(?:of\s*)?(202[6-9])|(202[6-9])\s*[-–:]?\s*(summer|spring|fall|winter)'
 term=lambda m:(int(m.group(2) or m.group(3)),(m.group(1) or m.group(4)).title())
 m=re.search(pattern,title,re.I)
 if m:return term(m)
 terms=[term(m) for line in re.split(r'\n|(?<=[.!?])\s',body) if not re.search(r'graduat|degree completion|will be posted|not yet (?:open|available)|coming soon',line,re.I) for m in re.finditer(pattern,line,re.I)]
 available_window=re.search(r'available to start\b[^.!?]{0,160}\bbetween\b[^.!?]{0,100}\b(?:summer\s+(?:of\s+)?2027|2027\s+summer)\b',body,re.I)
 if (2027,'Summer') in terms and (re.search(r'cohorts?\b',body,re.I) or available_window):return 2027,'Summer'
 if terms:return terms[0]
 s=title+'\n'+body
 y=re.search(r'\b(202[6-9])\b',title)
 if y and any(re.search(r'internship.{0,60}(?:may|june).{0,25}(?:august|september)',line,re.I) for line in body.splitlines()):return int(y.group(1)),'Summer'
 return (int(y.group(1)) if y else None),'Summer' if re.search(r'\bsummer\b',s,re.I) else 'Unknown'
def community_jobs(payload,source):
 rows=payload if isinstance(payload,list) else payload.get('jobs',[]);out=[]
 for r in rows:
  if r.get('active') is False or r.get('is_visible') is False:continue
  title=str(r.get('title',''));category=r.get('category','');terms=r.get('terms',[]);text=' '.join(terms)+' '+r.get('season','')+' '+title
  if not re.search(r'2027',text) or not re.search(r'summer',text,re.I):continue
  if re.search(r'2026|2028',title) and not re.search(r'2027',title):continue
  tracks=tracks_for(title,category)
  if not tracks or re.search(r'hardware|mechanical|electrical',category,re.I) and not re.search(r'software|machine learning|\bAI\b',title,re.I):continue
  if re.search(r'data analyst|business analyst|business intelligence|marketing analytics|strategy.{0,12}analytics',title,re.I) and not re.search(r'machine learning|data scien|software',title,re.I):continue
  locations=r.get('locations') or [r.get('location','')];locations=[s for s in locations if is_us_location(s)]
  if not locations:continue
  url=r.get('listingUrl') or r.get('url','')
  try:canonical(url)
  except ValueError:continue
  out.append({'id':job_id(url),'company':r.get('company_name') or r.get('company','Unknown company'),'title':title,'url':url,'location':' / '.join(locations),'country':'US','year':2027,'season':'Summer','yearBasis':'community-term','tracks':tracks,'jd':'','source':source['name'],'sourceState':'community','jdTextKind':'Community listing only; full employer JD and summer dates need verification.','checkedAt':TODAY(),'lastSeenAt':NOW(),'firstSeenAt':NOW(),'openStatus':'Community lists active','communitySponsorship':r.get('sponsorship','Unknown'),'communityDegrees':r.get('degrees',[]),'communityId':str(r.get('id','')),'communitySourceId':source['id'],'postedAt':r.get('posted') or (datetime.datetime.fromtimestamp(r['date_posted'],datetime.timezone.utc).date().isoformat() if r.get('date_posted') else ''),'sources':[{'title':source['name'],'url':source['url']},{'title':'Employer application link','url':url}]})
 return out
def board_from_url(url):
 p=urllib.parse.urlsplit(url);host=p.hostname or '';parts=p.path.strip('/').split('/')
 kind='greenhouse' if host in ['boards.greenhouse.io','job-boards.greenhouse.io'] else 'ashby' if host=='jobs.ashbyhq.com' else 'lever' if host=='jobs.lever.co' else ''
 if not kind or not parts or not re.fullmatch(r'[A-Za-z0-9_.-]+',parts[0]):return None
 token=parts[0];return {'id':kind+':'+token.lower(),'kind':kind,'token':token,'name':token,'url':f'https://{host}/{token}'}
def request(url,json_data=True,timeout=18):
 p=urllib.parse.urlsplit(url)
 if p.scheme!='https' or not p.hostname or p.username:raise ValueError('Only public HTTPS sources are supported')
 for info in socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM):
  if not ipaddress.ip_address(info[4][0]).is_global:raise ValueError('Non-public source address')
 req=urllib.request.Request(url,headers={'User-Agent':'PersonalSummer27Research/2.0','Accept':'application/json' if json_data else 'text/html'})
 with urllib.request.urlopen(req,timeout=timeout) as r:
  data=r.read(30_000_001)
  if len(data)>30_000_000:raise ValueError('Source exceeds 30 MB safety bound')
  text=data.decode('utf-8',errors='replace')
 return json.loads(text) if json_data else text
def board_endpoint(board):
 k,t=board['kind'],urllib.parse.quote(board['token'],safe='')
 if k=='greenhouse':return f'https://boards-api.greenhouse.io/v1/boards/{t}/jobs?content=true'
 if k=='ashby':return f'https://api.ashbyhq.com/posting-api/job-board/{t}?includeCompensation=true'
 if k=='lever':return f'https://api.lever.co/v0/postings/{t}?mode=json'
 raise ValueError('Unsupported board')
def published_keys(payload,board):
 rows=payload if board['kind']=='lever' else payload.get('jobs',[]);keys=set()
 for row in rows:
  if row.get('isListed') is False:continue
  url=row.get('absolute_url') or row.get('jobUrl') or row.get('hostedUrl') or row.get('applyUrl')
  if url:keys.add(canonical(url))
 return keys
def parse_board(payload,board):
 kind=board['kind'];rows=payload if kind=='lever' else payload.get('jobs',[])
 if not isinstance(rows,list):raise ValueError('Job feed is not a list')
 out=[]
 for r in rows:
  if r.get('isListed') is False:continue
  title=r.get('title') or r.get('text','');employment=r.get('employmentType','')
  if not re.search(r'intern|co-op|coop',title+' '+employment,re.I):continue
  tracks=tracks_for(title)
  if not tracks:continue
  if kind=='greenhouse':url=r.get('absolute_url');body=plain(r.get('content'));location=r.get('location',{}).get('name','')
  elif kind=='ashby':url=r.get('jobUrl') or r.get('applyUrl');body=strip_data_images(r.get('descriptionPlain')) or plain(r.get('descriptionHtml'));location=r.get('location','');location+=' / '+' / '.join(x.get('location','') for x in r.get('secondaryLocations',[]))
  else:url=r.get('hostedUrl');body=strip_data_images(r.get('descriptionPlain')) or plain(r.get('description'));body+='\n'+'\n'.join(plain(x.get('text','')+'\n'+x.get('content','')) for x in r.get('lists',[]));body+='\n'+plain(r.get('additional'));location=r.get('categories',{}).get('location','')
  if not url:continue
  year,season=infer_term(title,body)
  out.append({'id':job_id(url),'company':board.get('company') or board['name'],'title':title,'url':url,'location':location.strip(' /'),'country':country_for_location(location),'jd':body[:28000],'year':year,'season':season,'yearBasis':'employer-text' if year and season!='Unknown' else 'employer-year-unconfirmed','tracks':tracks,'source':'Employer · '+board['kind'].title(),'sourceState':'live-api','jdTextKind':'Current published employer feed; verify unparsed qualification details.','checkedAt':TODAY(),'lastSeenAt':NOW(),'officialVerifiedAt':NOW(),'firstSeenAt':NOW(),'openStatus':'Published in employer feed','requirementsClassified':False,'boardId':board['id'],'providerJobId':str(r.get('id','')),'sourceUpdatedAt':r.get('updated_at') or r.get('publishedAt',''),'sources':[{'title':'Employer job page','url':url},{'title':board['kind'].title()+' job board','url':board['url']}]})
 return out
def merge_catalogue(existing,incoming):
 out=[dict(j) for j in existing];index={};identities={}
 def keys(j):return list(dict.fromkeys(canonical(u) for u in [j.get('url')]+j.get('urlAliases',[]) if u))
 def identity(j):return j.get('identityKey') or provider_identity(j.get('url',''))
 def rank(j):return (not bool(j.get('duplicateOf')),j.get('sourceState')=='live-api',len(j.get('jd','')))
 def register(i):
  j=out[i]
  for k in keys(j):
   if k not in index or rank(j)>=rank(out[index[k]]):index[k]=i
  k=identity(j)
  if k and (k not in identities or rank(j)>=rank(out[identities[k]])):identities[k]=i
 for i in range(len(out)):register(i)
 for j in incoming:
  if not j.get('url'):continue
  i=next((index[k] for k in keys(j) if k in index),identities.get(identity(j)))
  if i is None:out.append(dict(j));register(len(out)-1);continue
  old=out[i];official=j.get('sourceState') in ['live-api','live-page','verified','live']
  merged={**old,**j} if official or not old.get('jd') else {**j,**old}
  if j.get('sheetSourceId') and old.get('source')!=j.get('source'):
   # A sparse external sheet adds provenance, not replacements for known facts.
   merged={**j,**old,'sheetSourceId':j['sheetSourceId'],'sheetRow':j.get('sheetRow'),'sheetFields':j.get('sheetFields',{})}
  merged['id']=old.get('id') or j['id'];merged['firstSeenAt']=old.get('firstSeenAt') or j.get('firstSeenAt');merged['lastSeenAt']=j.get('lastSeenAt') or old.get('lastSeenAt')
  if official:
   # Never retain community Summer 2027 as employer-confirmed when official text differs.
   for k in ['year','season','yearBasis']:merged[k]=j.get(k)
  merged['sources']=list({s['url']:s for s in old.get('sources',[])+j.get('sources',[])}.values())
  merged['urlAliases']=list(dict.fromkeys([old['url'],j['url']]+old.get('urlAliases',[])+j.get('urlAliases',[])))
  for k in ['status','notes','history','appliedAt','oaReceivedAt','oaCompletedAt','followUp','packetVersions','preparation']: 
   if k in old:merged[k]=old[k]
  out[i]=merged;register(i)
 return out
def finalize_records(records):
 from employer_details import graduation_window
 rows=[dict(j) for j in records];alias_identity={};groups={}
 waymo_slugs={urllib.parse.urlsplit(j['url']).path.rstrip('/'):provider_identity(j['url']) for j in rows if urllib.parse.urlsplit(j['url']).hostname=='careers.withwaymo.com' and 'gh_jid=' in j['url'] and urllib.parse.urlsplit(j['url']).path.rstrip('/')!='/jobs'}
 for j in rows:
  derived=provider_identity(j['url'])
  if derived and derived.startswith('waymo-slug:'):derived=waymo_slugs.get(urllib.parse.urlsplit(j['url']).path.rstrip('/'),derived)
  if derived:j['identityKey']=derived
 for j in rows:
  if j.get('identityKey'):
   for url in [j['url']]+j.get('urlAliases',[]):alias_identity[canonical(url)]=j['identityKey']
 for j in rows:
  key=j.get('identityKey') or alias_identity.get(canonical(j['url'])) or canonical(j['url']);groups.setdefault(key,[]).append(j)
  j.pop('duplicateOf',None);j['scopeStatus']='target' if tracks_for(j.get('title','')) else 'outside-target';j['tracks']=tracks_for(j.get('title',''))
  location_country=country_for_location(j.get('location',''))
  if location_country!='Unconfirmed':j['country']=location_country
  elif j.get('country') in ['US','USA','United States']:j['country']='US'
  if j.get('sourceState') in ['live-api','live-page','official-page','verified','live'] and j.get('jd'):j.update(graduation_window(j['jd']))
 # Explicit aliases can bridge groups even when one website has no provider ID.
 parent={key:key for key in groups};seen_urls={};seen_ids={}
 def root(key):
  while parent[key]!=key:parent[key]=parent[parent[key]];key=parent[key]
  return key
 for key,group in groups.items():
  for j in group:
   identities=[(seen_ids,j['id'])]+[(seen_urls,canonical(u)) for u in [j['url']]+j.get('urlAliases',[])]
   for registry,value in identities:
    if value in registry:parent[root(key)]=root(registry[value])
    else:registry[value]=key
 merged_groups={}
 for key,group in groups.items():merged_groups.setdefault(root(key),[]).extend(group)
 for group in merged_groups.values():
  leader=max(group,key=lambda j:(3 if j.get('sourceState')=='live-api' else 2 if j.get('sourceState') in ['live-page','official-page','verified','live'] else 0,evidence_time(j),len(j.get('jd',''))))
  for j in group:
   if j is not leader:j['duplicateOf']=leader['id']
  leader['urlAliases']=list(dict.fromkeys(u for j in group for u in [j['url']]+j.get('urlAliases',[])))
  leader['sources']=list({s['url']:s for j in group for s in j.get('sources',[])}.values())
 return rows
def catalogue_summary(base,health,changes):
 target=lambda j:not j.get('duplicateOf') and j.get('year')==2027 and j.get('season')=='Summer' and j.get('scopeStatus')=='target' and j.get('sourceState') not in ['unlisted','closed'] and (j.get('country')=='US' or is_us_location(j.get('location')))
 official=lambda j:bool(j.get('jd')) and j.get('sourceState') in ['live-api','live-page','official-page','verified','live']
 full=lambda j:official(j) and not re.search(r'summary|not.*full',j.get('jdTextKind',''),re.I)
 return {'records':len(base),'uniqueRecords':sum(not j.get('duplicateOf') for j in base),'summer2027US':sum(target(j) for j in base),'officialTargetDescriptions':sum(target(j) and full(j) for j in base),'employerSummaryTargetLeads':sum(target(j) and official(j) and not full(j) for j in base),'officialDescriptions':sum(not j.get('duplicateOf') and full(j) for j in base),'communityTargetLeads':sum(target(j) and not official(j) for j in base),'sourcesSucceeded':sum(s['status'] in ['ok','partial'] for s in health),'sourcesFailed':sum(s['status']=='failed' for s in health),'new':sum(c['kind']=='new' for c in changes),'updated':sum(c['kind']=='updated' for c in changes)}
def catalogue_changes(base,previous):
 old_map={};changes=[]
 def keys(j):return [('id',j['id'])]+[('url',canonical(u)) for u in [j['url']]+j.get('urlAliases',[])]+[('provider',j.get('identityKey') or provider_identity(j['url']))]
 for j in sorted(previous,key=lambda j:(not bool(j.get('duplicateOf')),evidence_time(j))):
  for k in keys(j):
   if k[1]:old_map[k]=j
 fields=['title','location','jd','deadline','openStatus','year','season','degree','graduationMin','graduationMax','sponsorshipEvidence','cptEvidence']
 for j in base:
  if j.get('duplicateOf'):continue
  candidates=[old_map[k] for k in keys(j) if k[1] and k in old_map]
  old=max(candidates,key=lambda old:(not bool(old.get('duplicateOf')),evidence_time(old),len(old.get('jd','')))) if candidates else None
  changed=[k for k in fields if old and old.get(k)!=j.get(k)]
  if old is None or changed:
   j['catalogChangedAt']=NOW();j['catalogChange']='new' if old is None else 'updated';changes.append({'id':j['id'],'company':j['company'],'title':j['title'],'url':j['url'],'kind':j['catalogChange'],'fields':changed,'at':j['catalogChangedAt']})
  else:j.setdefault('catalogChangedAt',old.get('catalogChangedAt',NOW()));j.setdefault('catalogChange',old.get('catalogChange','existing'))
 return changes
def collect(config,previous,extra_jobs=None):
 started=NOW();health=[];fresh=[];communities=[s for s in config['sources'] if s['kind']=='community-json' and s.get('enabled',True)]
 for source in config['sources']:
  if source['kind']!='google-sheet-csv' or not source.get('enabled',True):continue
  try:
   from sheet_source import sheet_jobs
   rows,report=sheet_jobs(request(source['feedUrl'],json_data=False),source);fresh=merge_catalogue(fresh,rows)
   health.append({**source,'status':'partial' if report['issues'] else 'ok','checkedAt':NOW(),'lastSuccessAt':NOW(),'count':len(rows),**report})
  except Exception as error:health.append({**source,'status':'failed','checkedAt':NOW(),'error':str(error)[:220],'count':0})
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  futures={pool.submit(request,s['feedUrl']):s for s in communities}
  for future,s in futures.items():
   try:
    payload=future.result();jobs=community_jobs(payload,s);fresh=merge_catalogue(fresh,jobs);health.append({**s,'status':'ok','checkedAt':NOW(),'lastSuccessAt':NOW(),'count':len(jobs)})
   except Exception as e:health.append({**s,'status':'failed','checkedAt':NOW(),'error':str(e)[:220],'count':0})
 base=merge_catalogue(previous,fresh);base=merge_catalogue(base,extra_jobs or [])
 boards={s['id']:s for s in config['sources'] if s['kind'] in ['greenhouse','ashby','lever'] and s.get('enabled',True)}
 for j in base:
  b=board_from_url(j.get('url',''))
  if b:
   b['company']=j.get('company',b['name']);b['name']=b['company'];boards.setdefault(b['id'],b)
 def fetch(b):
  payload=request(board_endpoint(b));return parse_board(payload,b),published_keys(payload,b)
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
  futures={pool.submit(fetch,b):b for b in boards.values()}
  for future,b in futures.items():
   try:
    jobs,published=future.result();known={canonical(j['url']) for j in base};relevant=[j for j in jobs if canonical(j['url']) in known or (j['country']=='US' and j['year']==2027 and j['season']=='Summer')]
    base=merge_catalogue(base,relevant);fresh=merge_catalogue(fresh,relevant)
    health.append({**b,'status':'ok','checkedAt':NOW(),'lastSuccessAt':NOW(),'count':len(relevant),'publishedInternships':len(jobs)})
    for j in base:
     original=board_from_url(j.get('url',''))
     if original and original['id']==b['id'] and canonical(j['url']) not in published:
      # Public board successfully loaded; never infer closed from failed fetches.
      j['openStatus']='No longer listed in employer feed';j['sourceState']='unlisted';j['availabilityCheckedAt']=TODAY()
     elif original and original['id']==b['id'] and j.get('sourceState')=='unlisted':
      j['openStatus']='Employer lists this URL; internship details need review';j['sourceState']='community'
   except Exception as e:health.append({**b,'status':'failed','checkedAt':NOW(),'error':str(e)[:220],'count':0})
 if config.get('enrichEmployerDetails',True):
  from employer_details import enrich_details
  base,detail_health=enrich_details(base);health.extend(detail_health)
 base=finalize_records(base)
 changes=catalogue_changes(base,previous)
 return {'schemaVersion':2,'updatedAt':NOW(),'jobs':base,'sources':health,'changes':changes,'excludedJobIds':config.get('excludedJobIds',[]),'summary':catalogue_summary(base,health,changes)}
