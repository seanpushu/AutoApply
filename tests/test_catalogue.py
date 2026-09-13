import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalogue import community_jobs,merge_catalogue,parse_board,board_from_url,is_us_location,infer_term,canonical,tracks_for,published_keys,finalize_records,strip_data_images,catalogue_changes

class CatalogueTests(unittest.TestCase):
 def record(self,**patch):
  return {'id':'a','active':True,'is_visible':True,'terms':['Summer 2027'],'category':'Software','company_name':'Acme','title':'Software Engineer Intern','locations':['New York, NY'],'url':'https://jobs.ashbyhq.com/acme/abc',**patch}
 def test_wrong_year_country_and_non_target_disciplines_do_not_enter_target_pool(self):
  rows=[self.record(),self.record(id='b',terms=['Summer 2026']),self.record(id='c',locations=['Toronto, Canada']),self.record(id='d',category='Hardware',title='Mechanical Engineer Intern')]
  self.assertEqual(len(community_jobs(rows,{'id':'repo','name':'Test','url':'https://github.com/test/repo'})),1)
 def test_community_record_is_a_lead_not_a_fake_full_jd(self):
  j=community_jobs([self.record()],{'id':'repo','name':'Test','url':'https://github.com/test/repo'})[0]
  self.assertEqual(j['jd'],'');self.assertEqual(j['sourceState'],'community');self.assertEqual(j['yearBasis'],'community-term')
 def test_sources_merge_without_duplicate_and_keep_official_text(self):
  a={'id':'a','company':'Acme','title':'Intern','url':'https://boards.greenhouse.io/acme/jobs/123','jd':'Python required','sourceState':'live-api','sources':[{'url':'https://boards.greenhouse.io/acme/jobs/123','title':'Employer'}]}
  b={**a,'id':'b','url':'https://job-boards.greenhouse.io/acme/jobs/123?gh_src=x','jd':'','sourceState':'community','sources':[{'url':'https://github.com/x/y','title':'Community'}]}
  out=merge_catalogue([a],[b]);self.assertEqual(len(out),1);self.assertEqual(out[0]['jd'],'Python required');self.assertEqual(len(out[0]['sources']),2)
 def test_repeat_refresh_reuses_a_verified_application_alias(self):
  old_url='https://example.wd1.myworkdayjobs.com/site/job/Intern_R123-1'
  current_url='https://example.wd1.myworkdayjobs.com/site/job/Boston/Intern_R123-2'
  a={'id':'saved','title':'Summer 2027 Software Intern','company':'Example','url':current_url,'urlAliases':[old_url,current_url],'jd':'Employer requirements','sourceState':'live-api'}
  b={**a,'id':'community','url':old_url,'urlAliases':[],'jd':'','sourceState':'community'}
  out=merge_catalogue([a],[b]);self.assertEqual(len(out),1);self.assertEqual(out[0]['id'],'saved');self.assertEqual(out[0]['jd'],'Employer requirements')
  for _ in range(3):out=merge_catalogue(out,[b])
  self.assertEqual(len(out),1)
 def test_change_counts_exclude_verified_aliases_and_retained_duplicates(self):
  old={'id':'old','company':'Acme','title':'Software Intern','url':'https://jobs.ashbyhq.com/acme/abc','urlAliases':['https://example.com/verified-alias'],'jd':'Same requirements'}
  current={**old,'id':'current','url':'https://example.com/verified-alias'}
  duplicate={**old,'duplicateOf':'current'}
  self.assertEqual(catalogue_changes([current,duplicate],[old]),[])
  current['jd']='Updated requirements'
  changes=catalogue_changes([current,duplicate],[old]);self.assertEqual(len(changes),1);self.assertEqual(changes[0]['kind'],'updated');self.assertEqual(changes[0]['fields'],['jd'])
 def test_change_baseline_uses_previous_primary_after_alias_id_switch(self):
  alias={'id':'saved-alias','company':'Acme','title':'Software Intern','url':'https://example.com/alias','jd':'summary','duplicateOf':'official-id'}
  primary={**alias,'id':'official-id','url':'https://example.com/current','jd':'full requirements','urlAliases':[alias['url']]};primary.pop('duplicateOf')
  current={**primary,'id':'saved-alias'}
  self.assertEqual(catalogue_changes([current],[alias,primary]),[])
 def test_provider_requisition_identity_handles_new_locale_alias_without_new_row(self):
  a={'id':'saved','title':'Summer 2027 Software Intern','company':'Example','url':'https://example.wd1.myworkdayjobs.com/site/job/Boston/Intern_R123-1','jd':'Employer requirements','sourceState':'live-api'}
  b={**a,'id':'new-alias','url':'https://example.wd1.myworkdayjobs.com/en-US/site/job/Intern_R123-2','jd':'','sourceState':'community'}
  out=merge_catalogue([a],[b]);self.assertEqual(len(out),1);self.assertIn(b['url'],out[0]['urlAliases'])
 def test_failed_sources_do_not_remove_previous_records(self):
  a=self.record();self.assertEqual(merge_catalogue([a],[]),[a])
 def test_ashby_only_listed_jobs_are_used_and_employer_season_wins(self):
  board={'id':'ashby:acme','kind':'ashby','token':'acme','name':'Acme','url':'https://jobs.ashbyhq.com/acme'}
  rows={'jobs':[{'id':'x','title':'Software Intern Summer 2026','isListed':True,'location':'New York, NY','jobUrl':'https://jobs.ashbyhq.com/acme/x','descriptionPlain':'Intern Summer 2026','employmentType':'Intern'},{'id':'y','title':'SWE Intern Summer 2027','isListed':False,'location':'New York, NY','jobUrl':'https://jobs.ashbyhq.com/acme/y','descriptionPlain':'Python'}]}
  parsed=parse_board(rows,board);self.assertEqual(len(parsed),1);self.assertEqual(parsed[0]['year'],2026)
 def test_real_board_url_discovers_correct_provider(self):
  self.assertEqual(board_from_url('https://job-boards.greenhouse.io/waymo/jobs/123')['token'],'waymo')
  self.assertEqual(board_from_url('https://jobs.ashbyhq.com/Notion/abc')['kind'],'ashby')
  self.assertIsNone(board_from_url('https://example.com/jobs'))
 def test_us_detection_does_not_confuse_canada_and_remote_unknown(self):
  self.assertFalse(is_us_location('Ontario, Canada'));self.assertFalse(is_us_location('Remote'));self.assertTrue(is_us_location('Remote - United States'));self.assertTrue(is_us_location('San Francisco, CA'))
 def test_graduation_year_does_not_replace_internship_year(self):
  self.assertEqual(infer_term('Software Engineering Intern','Students graduating between December 2026 and Summer 2028. This internship will take place in Summer 2027.'),(2027,'Summer'))
 def test_multiple_offered_cohorts_use_the_requested_summer_without_overriding_explicit_title(self):
  body='Internship cohorts: Fall 2026, Spring 2027, Summer 2027.'
  self.assertEqual(infer_term('Software Internship',body),(2027,'Summer'))
  self.assertEqual(infer_term('Software Internship Fall 2026',body),(2026,'Fall'))
 def test_future_posting_notice_does_not_become_an_available_summer_cohort(self):
  title='2026 Intern Conversion: 2027 FT Data Scientist III- Sunnyvale'
  body='THIS POSITION IS POSTED FOR INTERNS WHO INTERNED IN SUMMER 2026. NEW ROLES FOR SUMMER 2027 WILL BE POSTED SOON.'
  self.assertEqual(infer_term(title,body),(2026,'Summer'))
 def test_explicit_available_start_window_includes_summer_without_cohort_word(self):
  body='These 12-week internships are available to start between winter of 2026 and summer of 2027.'
  self.assertEqual(infer_term('Software Engineering Internship',body),(2027,'Summer'))
 def test_embedded_image_payload_cannot_displace_the_actual_jd(self):
  board={'id':'ashby:acme','kind':'ashby','token':'acme','name':'Acme','url':'https://jobs.ashbyhq.com/acme'}
  body='[data:image/png;base64,'+'A'*40000+']\nSummer 2027 internship. Masters students. Python required.'
  p={'jobs':[{'id':'x','title':'Software Intern','isListed':True,'location':'Boston, MA','jobUrl':'https://jobs.ashbyhq.com/acme/x','descriptionPlain':body}]}
  j=parse_board(p,board)[0];self.assertIn('Masters students',j['jd']);self.assertNotIn('data:image',j['jd']);self.assertLess(len(j['jd']),200)
 def test_unbracketed_image_cannot_consume_next_line_sponsorship_negation(self):
  self.assertEqual(strip_data_images('data:image/png;base64,QUFB\nNo sponsorship.'),'No sponsorship.')
  self.assertEqual(strip_data_images('[data:image/png;base64,QUFB\nQUFB]\nNo sponsorship.'),'No sponsorship.')
 def test_category_does_not_turn_sales_electrical_or_product_roles_into_ml(self):
  for title in ['Operations Intern','Electrical Engineer Intern','Sales Analyst','Product Manager Intern']:
   self.assertEqual(tracks_for(title,'AI/ML/Data'),[])
 def test_application_links_and_details_have_the_same_identity(self):
  self.assertEqual(canonical('https://jobs.lever.co/acme/abc/apply'),canonical('https://jobs.lever.co/acme/abc'))
  self.assertEqual(canonical('https://jobs.ashbyhq.com/Notion/abc/application?embed=true'),canonical('https://jobs.ashbyhq.com/Notion/abc'))
 def test_published_identity_includes_records_outside_target_title_filter(self):
  p={'jobs':[{'id':'abc','title':'Software Engineer','isListed':True,'jobUrl':'https://jobs.ashbyhq.com/acme/abc'}]}
  self.assertIn(canonical('https://jobs.ashbyhq.com/acme/abc/application'),published_keys(p,{'kind':'ashby'}))
 def test_us_state_names_remote_and_multiple_locations_are_recognized(self):
  for place in ['Reston Virginia','McLean, Virginia','Los Angeles','Kent Washington','Remote - US','New York, NY / London, UK']:
   self.assertTrue(is_us_location(place),place)
 def test_duplicate_primary_uses_official_facts_and_retains_old_alias_record(self):
  old={'id':'old','title':'Software Intern','company':'Acme','url':'https://jobs.ashbyhq.com/acme/uuid/application?embed=true','jd':'','year':2027,'season':'Summer','location':'NYC','sourceState':'community'}
  official={**old,'id':'official','url':'https://jobs.ashbyhq.com/acme/uuid','jd':'Expected to graduate in 2028. Summer 2027 internship.','sourceState':'live-api'}
  rows=finalize_records([old,official]);self.assertEqual(len(rows),2);self.assertEqual(rows[0]['duplicateOf'],'official');self.assertEqual(rows[1]['graduationMin'],'2028-01')
 def test_shorter_current_employer_text_wins_over_a_stale_long_duplicate(self):
  old={'id':'old','title':'Software Intern','company':'Acme','url':'https://jobs.ashbyhq.com/acme/uuid/application','jd':'A'*28000,'year':2026,'season':'Fall','location':'NYC','sourceState':'live-api','officialVerifiedAt':'2026-09-06T09:00:00+00:00'}
  current={**old,'id':'current','url':'https://jobs.ashbyhq.com/acme/uuid','jd':'Summer 2027 internship. Masters students.','year':2027,'season':'Summer','officialVerifiedAt':'2026-09-06T06:00:00-04:00'}
  rows=finalize_records([old,current]);self.assertEqual(rows[0].get('duplicateOf'),'current');self.assertNotIn('duplicateOf',rows[1]);self.assertEqual(len(rows),2)
if __name__=='__main__':unittest.main()
