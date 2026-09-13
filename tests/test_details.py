import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from employer_details import detail_spec,parse_detail
class EmployerDetailTests(unittest.TestCase):
 def test_employer_internship_may_september_window_is_summer(self):
  old={'id':'a','company':'Adobe','url':'https://adobe.wd5.myworkdayjobs.com/site/job/San-Jose/Intern_R1'}
  p={'jobPostingInfo':{'title':'2027 Intern - Machine Learning Engineer','jobReqId':'R1','location':'San Jose','additionalLocations':['San Francisco','Seattle'],'jobDescription':'Expected graduation December 2027 - June 2028.\nAbility to participate in a full-time internship between May–September.'}}
  j=parse_detail(p,{'kind':'workday','tenant':'adobe','host':'adobe.wd5.myworkdayjobs.com'},old)
  self.assertEqual(j['country'],'US');self.assertEqual((j['year'],j['season']),(2027,'Summer'))
 def test_official_foreign_location_replaces_community_us_label(self):
  old={'id':'x','company':'Example','url':'https://example.wd1.myworkdayjobs.com/site/job/Toronto/Intern_JR1','country':'US'}
  p={'jobPostingInfo':{'title':'Summer 2027 Software Intern','jobReqId':'JR1','jobDescription':'Software internship','location':'Toronto, Canada'}}
  j=parse_detail(p,{'kind':'workday','tenant':'example','host':'example.wd1.myworkdayjobs.com'},old)
  self.assertEqual(j['country'],'Outside US');self.assertNotEqual(j['openStatus'],'Employer application available')
 def test_workday_preserves_site_and_exact_job_path(self):
  s=detail_spec('https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/job/US-CA-Santa-Clara/NVIDIA-2027-Internships--Deep-Learning_JR2023497-1')
  self.assertEqual(s['url'],'https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/job/US-CA-Santa-Clara/NVIDIA-2027-Internships--Deep-Learning_JR2023497-1')
 def test_workday_without_location_segment_and_google_requisition_identity(self):
  from catalogue import provider_identity
  s=detail_spec('https://workiva.wd503.myworkdayjobs.com/en-US/careers/job/Summer-2027-Software_R12190')
  self.assertEqual(s['url'],'https://workiva.wd503.myworkdayjobs.com/wday/cxs/workiva/careers/job/Summer-2027-Software_R12190')
  self.assertEqual(provider_identity('https://example.wd1.myworkdayjobs.com/en-US/site/job/A/Intern_R12345-2'),'workday:example:R12345')
  self.assertEqual(provider_identity('https://www.google.com/about/careers/applications/jobs/results/12345-intern/'),'google:12345')
 def test_verified_cross_platform_alias_shares_the_authoritative_policy(self):
  from catalogue import finalize_records
  a={'id':'community','company':'Example','title':'Summer 2027 Software Intern','url':'https://jobs.example.com/1','jd':'','sourceState':'community'}
  b={'id':'official','company':'Example','title':'Summer 2027 Software Intern','url':'https://example.com/careers/1','urlAliases':[a['url']],'jd':'F1 students are not eligible.','sourceState':'official-page'}
  for rows in [[a,b],[b,a]]:
   result=finalize_records(rows);self.assertEqual(sum(not j.get('duplicateOf') for j in result),1);self.assertEqual(next(j for j in result if j['id']=='community')['duplicateOf'],'official')
 def test_program_year_without_summer_does_not_become_summer(self):
  old={'id':'x','company':'NVIDIA','url':'https://nvidia.wd5.myworkdayjobs.com/a/job/b/c_JR1','year':2027,'season':'Summer'}
  data={'jobPostingInfo':{'title':'NVIDIA 2027 Internships: Deep Learning','jobReqId':'JR1','jobDescription':'Pursuing a Masters degree. Internship opportunities in 2027.','location':'Santa Clara, CA','canApply':True}}
  j=parse_detail(data,{'kind':'workday','tenant':'nvidia','host':'nvidia.wd5.myworkdayjobs.com'},old)
  self.assertEqual(j['year'],2027);self.assertEqual(j['season'],'Unknown');self.assertEqual(j['identityKey'],'workday:nvidia:JR1')
 def test_oracle_external_sections_and_sponsorship_are_retained(self):
  old={'id':'x','company':'Amex','url':'https://example.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/123'}
  p={'items':[{'Id':123,'Title':'Summer 2027 AI Intern','PrimaryLocation':'New York, NY','ExternalDescriptionStr':'Build AI agents','ExternalQualificationsStr':'Master students. No sponsorship for this internship.','ExternalPostedEndDate':'2026-10-30T23:59:00-04:00'}]}
  j=parse_detail(p,{'kind':'oracle','jobId':'123','host':'example.oraclecloud.com'},old)
  self.assertIn('No sponsorship',j['jd']);self.assertEqual(j['deadline'],'2026-10-30T23:59:00-04:00')
 def test_smartrecruiters_alias_preserves_original_url(self):
  old={'id':'x','company':'WD','url':'https://jobs.smartrecruiters.com/WD/111-old'}
  p={'id':'111','jobId':'shared','name':'Summer 2027 Software Intern','active':True,'visibility':'PUBLIC','postingUrl':'https://jobs.smartrecruiters.com/WD/222-new','location':{'city':'San Jose','region':'CA','country':'us'},'jobAd':{'sections':{'qualifications':{'text':'Python'}}}}
  j=parse_detail(p,{'kind':'smartrecruiters','tenant':'WD'},old)
  self.assertEqual(j['identityKey'],'smartrecruiters:wd:shared');self.assertIn(old['url'],j['urlAliases'])
if __name__=='__main__':unittest.main()
