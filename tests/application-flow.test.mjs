import test from 'node:test';
import assert from 'node:assert/strict';
import {jobIdentity,platformFor,isSensitiveQuestion,makeApplicationKit,importApplicationEvents} from '../lib/application-flow.mjs';
import {applyCatalogue,initialState,restoreState} from '../lib/storage.mjs';
const job={id:'j1',title:'Software Intern',company:'Example',url:'https://jobs.ashbyhq.com/example/abc',status:'Shortlisted',match:{eligibility:'review'}};
const resume={name:'resume.pdf',type:'application/pdf',size:3,base64:'YWJj',sha256:'a'.repeat(64)};
test('ATS identity is requisition scoped, supports apply aliases, and rejects lookalike hosts',()=>{
 assert.equal(jobIdentity(job.url),jobIdentity(job.url+'/application'));
 assert.notEqual(jobIdentity(job.url),jobIdentity(job.url.replace('abc','def')));
 assert.equal(platformFor('https://jobs.ashbyhq.com.evil.example/example/abc'),null);
 assert.equal(jobIdentity('https://boards.greenhouse.io/embed/job_app?for=example&token=123'),'greenhouse:example:123');
});
test('application kit excludes sensitive answer reuse and never includes inferred eligibility answers',()=>{
 const kit=makeApplicationKit({profile:{name:'Example Applicant',email:'test@example.com',authorization:'yes',sponsorship:'yes'},jobs:[job],resume,answers:[{question:'GitHub URL',answer:'https://github.com/example'},{question:'Do you require sponsorship?',answer:'No'}],factsReviewed:true});
 assert.equal(kit.jobs.length,1);assert.equal(kit.profile.authorization,undefined);assert.equal(kit.answers.length,1);
 assert.ok(isSensitiveQuestion('Are you legally authorized to work in the US?'));
 assert.throws(()=>makeApplicationKit({jobs:[job],resume,profile:{},factsReviewed:false}),/review/i);
 assert.throws(()=>makeApplicationKit({jobs:[{...job,match:{eligibility:'blocked'}}],resume,profile:{},factsReviewed:true}),/conflict/i);
});
test('events are idempotent and submit-click alone never marks Applied',()=>{
 const e={id:'e1',jobKey:jobIdentity(job.url),url:job.url,at:'2026-09-07T10:00:00Z',status:'attempted'};
 const state={jobs:[job]};const pending=importApplicationEvents(state,{kind:'summer27-application-events',events:[e]});
 assert.equal(pending.jobs[0].status,'Shortlisted');
 const done={...e,id:'e2',status:'confirmed',userConfirmedReceipt:true,receipt:'Employer displayed application received'};
 const applied=importApplicationEvents(pending,{kind:'summer27-application-events',events:[done,done]});
 assert.equal(applied.jobs[0].status,'Applied');assert.equal(applied.jobs[0].applicationEvents.length,2);
 assert.throws(()=>importApplicationEvents(state,{kind:'summer27-application-events',events:[{...done,url:'https://evil.example/x'}]}),/identity/i);
});
test('queue and application receipts survive catalogue alias consolidation',()=>{
 const s=initialState();s.jobs=[{...job,history:[],application:{queued:true,at:'2026-09-07'},applicationEvents:[{id:'e1',status:'attempted'}]}];
 const next=applyCatalogue(s,{schemaVersion:2,jobs:[{...job,id:'new',url:job.url+'/application',jd:'New description',checkedAt:'2026-09-08'}]});
 assert.equal(next.jobs[0].application.queued,true);assert.equal(next.jobs[0].applicationEvents[0].id,'e1');
});
test('secondary aliases and older backups retain application work without replacing a newer queue choice',()=>{
 const s=initialState();s.updatedAt='2026-09-09';s.jobs=[{...job,history:[],application:{queued:false,at:'2026-09-09'},applicationEvents:[{id:'a'}]},{...job,id:'alias',url:job.url+'/application',history:[],application:{queued:true,at:'2026-09-08'},applicationEvents:[{id:'b'}]}];
 const merged=applyCatalogue(s,{schemaVersion:2,jobs:[{...job,id:'fresh',urlAliases:[job.url+'/application'],checkedAt:'2026-09-10'}]});
 const main=merged.jobs.find(j=>!j.duplicateOf);assert.equal(main.application.queued,false);assert.deepEqual(main.applicationEvents.map(e=>e.id).sort(),['a','b']);
 const older={...s,updatedAt:'2026-09-08',jobs:[{...job,history:[],application:{queued:true,at:'2026-09-08'},applicationEvents:[{id:'c'}]}]};
 const restored=restoreState({...s,jobs:[main]},older);assert.equal(restored.jobs[0].application.queued,false);assert.deepEqual(restored.jobs[0].applicationEvents.map(e=>e.id).sort(),['a','b','c']);
});
