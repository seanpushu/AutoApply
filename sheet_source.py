"""Read the user-selected public Google Sheet as unverified job leads."""
import csv,io,re,datetime

def sheet_jobs(text,source):
 from catalogue import canonical,job_id,infer_term,tracks_for,TODAY,NOW
 reader=csv.DictReader(io.StringIO(text.replace('\r\r\n','\n'),newline=''))
 required={'Organization','Job/Internship Title','Link to Apply or Handshake Job ID','Internship'}
 if not required.issubset({str(x).strip() for x in reader.fieldnames or []}):raise ValueError('Sheet headers changed or access requires login; previous records retained.')
 jobs=[];issues=[];count=0;skipped=0
 def date(value):
  for fmt in ['%m/%d/%y','%m/%d/%Y','%Y-%m-%d']:
   try:return datetime.datetime.strptime(value.strip(),fmt).date().isoformat()
   except ValueError:pass
  return ''
 for number,raw in enumerate(reader,2):
  row={str(k).strip():str(v or '').strip() for k,v in raw.items() if k is not None}
  if not any(row.values()):continue
  count+=1;title=row.get('Job/Internship Title','');company=row.get('Organization','');link=row.get('Link to Apply or Handshake Job ID','')
  flagged=lambda value:str(value or '').strip().lower() in ['x','yes','true','1','✓','是']
  internship=flagged(row.get('Internship'));full=flagged(row.get('Full-Time'))
  if not internship and (full or not re.search(r'\bintern(?:ship)?\b|\bco-?op\b',title,re.I)):
   skipped+=1;continue
  if not title or not company:issues.append({'row':number,'reason':'Missing company or title'});continue
  match=re.fullmatch(r'(?:Handshake\s*(?:Job\s*)?(?:ID\s*)?[:#]?\s*)?(\d{5,})',link,re.I)
  url='https://app.joinhandshake.com/stu/jobs/'+match.group(1) if match else link
  try:canonical(url)
  except ValueError:issues.append({'row':number,'reason':'Unrecognized application link; inspect original sheet'});continue
  internship=True
  year,season=infer_term(title)
  jobs.append({'id':job_id(url),'company':company,'title':title,'url':url,'location':'Not specified in source sheet','country':'Unconfirmed','year':year,'season':season,'yearBasis':'community-sheet-title','tracks':tracks_for(title),'employmentType':'Internship' if internship else 'Full-time' if full else 'Unknown','jd':'','source':source['name'],'sourceState':'community','jdTextKind':'Source spreadsheet lead, not employer JD; verify location, cohort and eligibility.','checkedAt':TODAY(),'lastSeenAt':NOW(),'firstSeenAt':NOW(),'openStatus':'Listed in source sheet; current employer availability unverified','deadline':date(row.get('Application Deadline if Listed','')),'deadlineNote':'Sheet-reported deadline; verify on employer page.' if row.get('Application Deadline if Listed') else '', 'sheetSourceId':source['id'],'sheetRow':number,'sheetFields':row,'sources':[{'title':source['name']+' · row '+str(number),'url':source['url']},{'title':'Application link (unverified)','url':url}]})
 return jobs,{'rowsRead':count,'rowsImported':len(jobs),'rowsSkippedNonInternship':skipped,'issues':issues}
