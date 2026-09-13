import test from 'node:test';import assert from 'node:assert/strict';import {JSDOM} from 'jsdom';import {webcrypto} from 'node:crypto';
import {pageBridge} from '../extension/page-bridge.mjs';import {approvalFor,assertApproval} from '../extension/core.mjs';
const job={url:'https://jobs.lever.co/example/abc/apply',jobKey:'lever:example:abc'};
function page(extra='',url=job.url){const dom=new JSDOM(`<h1>Software Intern</h1><form><label>Full name<input name="name"></label><label>Email<input type="email" required></label>${extra}<button type="submit">Submit application</button></form>`,{url,runScripts:'outside-only'});Object.defineProperty(dom.window,'crypto',{value:webcrypto});dom.window.TextEncoder=TextEncoder;let submits=0;dom.window.document.querySelector('form').addEventListener('submit',e=>{e.preventDefault();submits++;});return {dom,submits:()=>submits,run:(action,p={})=>dom.window.eval(`(${pageBridge.toString()})`) (action,{job,...p})};}
test('preparation fills only exact neutral fields, keeps manual answers and never submits',async()=>{
 const p=page('<label>Do you require sponsorship?<textarea></textarea></label><label>GitHub URL<input value="https://github.com/keep"></label>');
 const r=await p.run('prepare',{kit:{profile:{name:'Example Applicant',email:'test@example.com',github:'https://github.com/new'},answers:[{question:'Do you require sponsorship?',answer:'No'}]}});
 assert.equal(p.dom.window.document.querySelector('input').value,'Example Applicant');assert.equal(p.dom.window.document.querySelector('textarea').value,'');assert.equal(p.dom.window.document.querySelector('input[value]').value,'https://github.com/keep');assert.equal(p.submits(),0);assert.equal(r.filled.length,2);
});
test('review binds company job, answers and form to a single expiring confirmation',async()=>{
 const p=page();p.dom.window.document.querySelector('[type=email]').value='test@example.com';
 const s=await p.run('inspect');const approval=approvalFor(s);assertApproval(s,approval);
 p.dom.window.document.querySelector('input').value='Changed';await assert.rejects(p.run('submit',{approval}),/changed/i);assert.equal(p.submits(),0);
 const fresh=await p.run('inspect');await p.run('submit',{approval:approvalFor(fresh)});assert.equal(p.submits(),1);
 await assert.rejects(p.run('submit',{approval:approvalFor(fresh)}),/already|attempt/i);assert.equal(p.submits(),1);
});
test('missing required fields, checkboxes, wrong job and expired review cannot submit',async()=>{
 const p=page('<label><input type="checkbox" required>I certify these answers</label>');const s=await p.run('inspect');assert.ok(s.blockers.length);assert.throws(()=>approvalFor(s),/complete/i);
 assert.equal(p.dom.window.document.querySelector('[type=checkbox]').checked,false);
 const other=page('',job.url.replace('/abc/','/def/'));await assert.rejects(other.run('inspect'),/job|identity/i);
 const p2=page();p2.dom.window.document.querySelector('[type=email]').value='test@example.com';const ready=await p2.run('inspect');await assert.rejects(p2.run('submit',{approval:{...approvalFor(ready),expiresAt:0}}),/expired|changed/i);assert.equal(p2.submits(),0);
});
test('ambiguous forms or submit controls stop instead of guessing',async()=>{
 const p=page('<button type="submit">Apply now</button>');const s=await p.run('inspect');assert.ok(s.blockers.some(x=>/submit/i.test(x)));assert.equal(s.submitReady,false);
});
test('two simultaneous confirmation calls can click at most once',async()=>{
 const p=page();p.dom.window.document.querySelector('[type=email]').value='test@example.com';const s=await p.run('inspect'),approval=approvalFor(s);
 const results=await Promise.allSettled([p.run('submit',{approval}),p.run('submit',{approval})]);assert.equal(p.submits(),1);assert.equal(results.filter(r=>r.status==='fulfilled').length,1);
});
test('a resume must be verifiable before an assisted submit is enabled',async()=>{
 const p=page();p.dom.window.document.querySelector('[type=email]').value='test@example.com';const s=await p.run('inspect',{expectedResume:{name:'resume.pdf',sha256:'a'.repeat(64)}});assert.equal(s.submitReady,false);assert.ok(s.blockers.some(x=>x.includes('resume')));
});
test('a matching file in the cover-letter slot cannot approve a different resume',async()=>{
 const p=page('<label>Resume<input type="file" id="resume"></label><label>Cover letter<input type="file" id="cover"></label>');p.dom.window.document.querySelector('[type=email]').value='test@example.com';
 const right=new File(['correct'],'resume.pdf',{type:'application/pdf'}),wrong=new File(['wrong'],'other.pdf',{type:'application/pdf'});
 Object.defineProperty(p.dom.window.document.querySelector('#resume'),'files',{value:[wrong]});Object.defineProperty(p.dom.window.document.querySelector('#cover'),'files',{value:[right]});
 const sha256=[...new Uint8Array(await webcrypto.subtle.digest('SHA-256',await right.arrayBuffer()))].map(v=>v.toString(16).padStart(2,'0')).join('');
 const s=await p.run('inspect',{expectedResume:{name:right.name,sha256}});assert.equal(s.submitReady,false);assert.ok(s.blockers.some(x=>/resume/i.test(x)));
});
test('preparation selects verified resume bytes only in the resume field and does not submit',async()=>{
 const p=page('<label>Resume<input type="file" id="resume" accept=".pdf"></label><label>Cover letter<input type="file" id="cover"></label>');
 p.dom.window.File=File;p.dom.window.DataTransfer=class {constructor(){this.files=[];this.items={add:f=>this.files.push(f)};}};
 const input=p.dom.window.document.querySelector('#resume');let selected=[];Object.defineProperty(input,'files',{get:()=>selected,set:v=>{selected=v;}});
 const sha256=[...new Uint8Array(await webcrypto.subtle.digest('SHA-256',new TextEncoder().encode('abc')))].map(v=>v.toString(16).padStart(2,'0')).join('');
 await p.run('prepare',{kit:{profile:{email:'test@example.com'},resume:{name:'resume.pdf',type:'application/pdf',size:3,base64:'YWJj',sha256}}});
 assert.equal(selected.length,1);assert.equal(await selected[0].text(),'abc');assert.equal(p.dom.window.document.querySelector('#cover').files.length,0);assert.equal(p.submits(),0);
 const review=await p.run('inspect',{expectedResume:{name:'resume.pdf',sha256}});assert.equal(review.submitReady,true);
});
test('company-specific motivation cannot be reused across employers',async()=>{
 const p=page('<label>Why do you want to join our company?<textarea></textarea></label>');await p.run('prepare',{kit:{profile:{},answers:[{question:'Why do you want to join our company?',answer:'Because I love the previous employer'}]}});assert.equal(p.dom.window.document.querySelector('textarea').value,'');
});
