"""Public employer detail adapters verified against real requisitions in this project."""
import concurrent.futures,re,urllib.parse
from catalogue import request,plain,infer_term,tracks_for,is_us_location,country_for_location,NOW,TODAY,canonical

def detail_spec(url):
 p=urllib.parse.urlsplit(url);host=p.hostname or '';parts=p.path.strip('/').split('/')
 if host.endswith('.myworkdayjobs.com'):
  if parts and re.fullmatch(r'[a-z]{2}-[A-Z]{2}',parts[0]):parts=parts[1:]
  if len(parts)<3 or parts[1]!='job':return None
  tenant=host.split('.')[0];site=parts[0]
  return {'kind':'workday','tenant':tenant,'host':host,'url':f'https://{host}/wday/cxs/{tenant}/{site}/job/'+ '/'.join(parts[2:])}
 if host.endswith('.oraclecloud.com') and '/job/' in p.path:
  job_id=p.path.split('/job/')[1].split('/')[0]
  if not job_id.isdigit():return None
  return {'kind':'oracle','host':host,'jobId':job_id,'url':f'https://{host}/hcmRestApi/resources/11.13.18.05/recruitingCEJobRequisitionDetails?onlyData=true&finder=ById;Id={job_id}'}
 if host=='jobs.smartrecruiters.com' and len(parts)>=2:
  m=re.match(r'\d+',parts[1])
  if m:return {'kind':'smartrecruiters','host':host,'tenant':parts[0],'jobId':m.group(),'url':f'https://api.smartrecruiters.com/v1/companies/{parts[0]}/postings/{m.group()}'}
 return None
def graduation_window(body):
 months={m.lower():f'{i:02d}' for i,m in enumerate(['January','February','March','April','May','June','July','August','September','October','November','December'],1)}
 for line in re.split(r'\n|(?<=[.!?])\s',body):
  if not re.search(r'graduat',line,re.I):continue
  pairs=re.findall(r'('+'|'.join(months)+r')\s+(202[6-9])',line,re.I)
  if len(pairs)>=2:return {'graduationMin':pairs[0][1]+'-'+months[pairs[0][0].lower()],'graduationMax':pairs[1][1]+'-'+months[pairs[1][0].lower()]}
  y=re.search(r'(?:expected to graduate|graduating|graduation date|graduate)\s+(?:in\s+)?(202[6-9])\b',line,re.I)
  if y:return {'graduationMin':y.group(1)+'-01','graduationMax':y.group(1)+'-12'}
 return {}
def parse_detail(payload,spec,old):
 kind=spec['kind'];deadline='';aliases=[old['url']];url=old['url'];active=True;identity='';apply_confirmed=False
 if kind=='workday':
  r=payload.get('jobPostingInfo')
  if not r or not r.get('title') or not r.get('jobDescription'):raise ValueError('Missing public Workday job description')
  title=r['title'];body=plain(r['jobDescription']);location=r.get('location','');extra=r.get('additionalLocations') or []
  if isinstance(extra,list):location+=' / '+' / '.join(str(x) for x in extra)
  identity='workday:'+spec['tenant'].lower()+':'+str(r.get('jobReqId') or r.get('id'))
  active=r.get('canApply') is not False;apply_confirmed=r.get('canApply') is True;url=r.get('externalUrl') or url
 elif kind=='oracle':
  items=payload.get('items',[])
  if not items:raise ValueError('Oracle public requisition not returned')
  r=items[0]
  if str(r.get('Id'))!=spec['jobId']:raise ValueError('Oracle requisition identity mismatch')
  title=r['Title'];body='\n'.join(plain(r.get(k,'')) for k in ['ExternalDescriptionStr','ExternalResponsibilitiesStr','ExternalQualificationsStr','OrganizationDescriptionStr','CorporateDescriptionStr']);location=r.get('PrimaryLocation','');deadline=r.get('ExternalPostedEndDate','');identity='oracle:'+spec['host']+':'+spec['jobId']
 elif kind=='smartrecruiters':
  r=payload
  if not r.get('name') or not r.get('jobAd'):raise ValueError('Missing public SmartRecruiters description')
  title=r['name'];sections=r['jobAd'].get('sections',{});body='\n'.join(plain(sections.get(k,{}).get('text','')) for k in ['companyDescription','jobDescription','qualifications','additionalInformation'])
  loc=r.get('location',{});location=', '.join(str(loc.get(k,'')) for k in ['city','region','country'] if loc.get(k));url=r.get('postingUrl') or url;identity='smartrecruiters:'+spec['tenant'].lower()+':'+str(r.get('jobId') or r['id']);active=r.get('active') is not False and r.get('visibility','PUBLIC')=='PUBLIC'
 else:raise ValueError('Unsupported detail source')
 canonical(url);aliases.append(url);year,season=infer_term(title,body)
 if year==2027 and season=='Unknown' and re.search(r'(?:may|june).{0,25}(?:august|aug\b)',body,re.I):season='Summer'
 location=location.strip(' /')
 result={**old,'title':title,'url':url,'urlAliases':list(dict.fromkeys(old.get('urlAliases',[])+aliases)),'identityKey':identity,'jd':body[:28000],'location':location or old.get('location',''),'country':country_for_location(location) if location else old.get('country','Unconfirmed'),'year':year,'season':season,'yearBasis':'employer-text' if year and season!='Unknown' else 'employer-year-unconfirmed','tracks':tracks_for(title),'source':'Employer · '+kind.title(),'sourceState':'live-api' if active else 'closed','jdTextKind':'Public employer requisition text; requirements and dates still require review.','checkedAt':TODAY(),'officialVerifiedAt':NOW(),'lastSeenAt':NOW(),'openStatus':('Employer application available' if apply_confirmed else 'Public employer detail returned; check application page') if active else 'Employer reports unavailable','requirementsClassified':False,'detailApiUrl':spec.get('url',''),'sources':list({s['url']:s for s in old.get('sources',[])+[{'title':'Employer job page','url':url}]}.values())}
 if deadline:result['deadline']=deadline
 result.update(graduation_window(body))
 return result
def enrich_details(jobs):
 output=[dict(j) for j in jobs];stats={};tasks=[];seen=set()
 for i,j in enumerate(output):
  if not tracks_for(j.get('title','')):continue
  s=detail_spec(j.get('url',''))
  if not s or s['url'] in seen:continue
  seen.add(s['url']);tasks.append((i,j,s))
 def fetch(j,s):return parse_detail(request(s['url'],timeout=14),s,j)
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
  futures={pool.submit(fetch,j,s):(i,j,s) for i,j,s in tasks}
  for future,(i,j,s) in futures.items():
   key='detail:'+s['host'];h=stats.setdefault(key,{'id':key,'kind':s['kind'],'name':j.get('company',s['host'])+' · requisitions','url':'https://'+s['host'],'count':0,'failedJobs':0,'status':'ok','checkedAt':NOW()})
   try:output[i]=future.result();h['count']+=1;h['lastSuccessAt']=NOW()
   except Exception as e:
    h['failedJobs']+=1;h['error']=str(e)[:180];output[i]['detailCheckError']=str(e)[:180];output[i]['detailAttemptAt']=NOW()
 for h in stats.values():
  if h['failedJobs']:h['status']='partial' if h['count'] else 'failed'
 return output,list(stats.values())
