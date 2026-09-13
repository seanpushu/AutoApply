import unittest,csv,io
from unittest.mock import patch
from sheet_source import sheet_jobs
from catalogue import merge_catalogue,collect

SOURCE={'id':'sheet','kind':'google-sheet-csv','name':'Sheet','url':'https://docs.google.com/spreadsheets/d/test/edit','feedUrl':'https://docs.google.com/spreadsheets/d/test/export?format=csv'}
def fixture(rows):
 s=io.StringIO();w=csv.writer(s);w.writerow(['Organization','Job/Internship Title','Role Category','Link to Apply or Handshake Job ID','Full-Time ','Internship','Application Deadline if Listed','Date Added to S/S']);w.writerows(rows);return s.getvalue()
class SheetTests(unittest.TestCase):
 def test_source_dates_are_not_internship_year_and_handshake_ids_are_preserved(self):
  jobs,report=sheet_jobs(fixture([['Acme','Software Engineer Intern','Software','12345678','','X','9/30/26','8/4/26']]),SOURCE)
  self.assertEqual(jobs[0]['year'],None);self.assertEqual(jobs[0]['country'],'Unconfirmed');self.assertEqual(jobs[0]['jd'],'');self.assertEqual(jobs[0]['deadline'],'2026-09-30');self.assertEqual(jobs[0]['url'],'https://app.joinhandshake.com/stu/jobs/12345678');self.assertEqual(report['rowsRead'],1)
 def test_bad_access_or_changed_headers_fail_and_bad_links_are_reported(self):
  with self.assertRaises(ValueError):sheet_jobs('<html>Sign in</html>',SOURCE)
  jobs,r=sheet_jobs(fixture([['Acme','SWE Intern','Software','javascript:alert(1)','','X','','']]),SOURCE);self.assertFalse(jobs);self.assertEqual(len(r['issues']),1)
 def test_only_internships_are_imported(self):
  rows=[['Acme','SWE','Software','https://example.com/full','X','','',''],['Acme','Summer 2027 Graduate Engineer','Software','https://example.com/grad','','FALSE','',''],['Acme','SWE Intern','Software','https://example.com/intern','','X','','']]
  jobs,r=sheet_jobs(fixture(rows),SOURCE);self.assertEqual(len(jobs),1);self.assertEqual(r['rowsSkippedNonInternship'],2)
 def test_repeat_import_preserves_employer_evidence_and_application_history(self):
  rows,_=sheet_jobs(fixture([['Acme','Software Intern Summer 2027','Software','https://example.com/job','','X','','']]),SOURCE)
  old={**rows[0],'id':'saved','jd':'Official description','sourceState':'live-api','country':'US','status':'Applied','history':[{'at':'2026-09-01'}]}
  out=merge_catalogue([old],rows);out=merge_catalogue(out,rows)
  self.assertEqual(len(out),1);self.assertEqual(out[0]['id'],'saved');self.assertEqual(out[0]['jd'],'Official description');self.assertEqual(out[0]['status'],'Applied')
 def test_future_collect_fetches_sheet_and_failure_retains_previous_rows(self):
  payload=fixture([['Acme','Software Intern Summer 2027','Software','https://example.com/job','','X','','']]);config={'sources':[SOURCE],'enrichEmployerDetails':False}
  with patch('catalogue.request',return_value=payload) as fetch:
   c=collect(config,[]);self.assertEqual(len(c['jobs']),1);fetch.assert_called_once_with(SOURCE['feedUrl'],json_data=False)
  with patch('catalogue.request',side_effect=ValueError('Login required')):
   retry=collect(config,c['jobs']);self.assertEqual(len(retry['jobs']),1);self.assertEqual(retry['sources'][0]['status'],'failed')
 def test_sparse_sheet_does_not_erase_existing_community_location_or_cohort(self):
  rows,_=sheet_jobs(fixture([['Acme','Software Intern','Software','https://example.com/job','','X','','']]),SOURCE)
  previous={**rows[0],'source':'Existing list','country':'US','location':'New York','year':2027,'season':'Summer','deadline':'2026-10-01'}
  merged=merge_catalogue([previous],rows)[0]
  self.assertEqual(merged['country'],'US');self.assertEqual(merged['year'],2027);self.assertEqual(merged['deadline'],'2026-10-01')
