import test from 'node:test';import assert from 'node:assert/strict';
import {initialState,applyCatalogue,upgradeProfile} from '../lib/storage.mjs';
test('catalogue refresh preserves personal records and applies new source facts',()=>{const s=initialState(),j=s.jobs[0];j.status='OA received';j.notes='Keep';j.followUp='2026-09-15';j.packetVersions=[{id:'v1',text:'Edited draft'}];const c={schemaVersion:2,updatedAt:'2026-09-10',jobs:[{...j,title:'Updated title',status:'Not started',notes:'',followUp:'',packetVersions:[],sourceState:'unlisted',openStatus:'No longer listed in employer feed'}],sources:[],changes:[],summary:{}};const r=applyCatalogue(s,c).jobs.find(x=>x.id===j.id);assert.equal(r.status,'OA received');assert.equal(r.title,'Updated title');assert.equal(r.sourceState,'unlisted');assert.equal(r.notes,'Keep');assert.equal(r.followUp,'2026-09-15');assert.equal(r.packetVersions[0].text,'Edited draft');});
test('manual JD is retained beside a new official source revision',()=>{const s=initialState(),j=s.jobs[0];j.jd='Manually reviewed JD';j.manualFields={jd:true};const c={schemaVersion:2,updatedAt:'2026-09-10',jobs:[{...j,jd:'New employer text',manualFields:{}}],sources:[],changes:[],summary:{}};const r=applyCatalogue(s,c).jobs[0];assert.equal(r.jd,'Manually reviewed JD');assert.equal(r.pendingSourceUpdate.jd,'New employer text');});
test('profile hydration never invents immigration or authorization answers',()=>{const original={email:'keep@example.com',authorization:'unknown',sponsorship:'unknown'};const p=upgradeProfile(original);assert.deepEqual(p,original);assert.equal(p.visaStatus,undefined);const confirmed={...original,authorization:'no',visaStatus:'F-1'};assert.deepEqual(upgradeProfile(confirmed),confirmed);});
test('catalogue aliases cannot hide the primary role or overwrite an edited draft',()=>{const s=initialState(),j=s.jobs[0];j.draftPacket={text:'My final edits'};const c={schemaVersion:2,jobs:[{...j,id:'alias',duplicateOf:'primary'},{...j,id:'primary',duplicateOf:undefined,draftPacket:{text:'Old source'},title:'Official role'}],sources:[],changes:[]};const r=applyCatalogue(s,c);const same=r.jobs.filter(x=>x.url===j.url&&!x.duplicateOf);assert.equal(same.length,1);assert.equal(same[0].title,'Official role');assert.equal(same[0].draftPacket.text,'My final edits');});

const role=(id,url,extra={})=>({id,url,company:'Example',title:'Software Engineering Intern Summer 2027',jd:'Python and SQL',year:2027,season:'Summer',tracks:['SDE'],status:'Not started',history:[],notes:'',...extra});
const state=jobs=>({...initialState(),jobs});
const catalogue=jobs=>({schemaVersion:2,updatedAt:'2026-09-10T12:00:00Z',jobs,sources:[],changes:[]});
const legacyUrl='https://example.com/careers/old-req-42';
const officialUrl='https://example.com/careers/req-42';

test('a verified URL alias upgrades the existing record without replacing its ID or application',()=>{
 const old=role('my-saved-job',legacyUrl,{status:'Applied',appliedAt:'2026-09-08',history:[{at:'2026-09-08',to:'Applied'}],deadline:'2026-09-22',manualFields:{deadline:true}});
 const source=role('catalog-primary',officialUrl,{urlAliases:[legacyUrl],title:'Official title',deadline:'2026-09-18',checkedAt:'2026-09-10'});
 const original=structuredClone(old),r=applyCatalogue(state([old]),catalogue([source]));
 assert.equal(r.jobs.length,1);assert.equal(r.jobs[0].id,'my-saved-job');assert.equal(r.jobs[0].url,officialUrl);
 assert.equal(r.jobs[0].status,'Applied');assert.equal(r.jobs[0].deadline,'2026-09-22');assert.equal(r.jobs[0].pendingSourceUpdate.deadline,'2026-09-18');
 assert.ok(r.jobs[0].urlAliases.includes(legacyUrl));assert.deepEqual(old,original);
});

test('two saved aliases retain both IDs and consolidate their personal work on one visible record',()=>{
 const alias=role('tracked-alias',legacyUrl,{status:'OA received',history:[{at:'2026-09-09',to:'OA received'}],notes:'Recruiter replied',appliedAt:'2026-09-07',oaReceivedAt:'2026-09-09',oaDue:'2026-09-20',packetVersions:[{id:'v1',text:'First packet',at:'2026-09-08'}],draftPacket:{text:'Older draft',at:'2026-09-08'},preparation:{resume:true,questions:true},updatedAt:'2026-09-09'});
 const official=role('saved-official',officialUrl,{status:'Applied',history:[{at:'2026-09-07',to:'Applied'}],notes:'Ask about conversion',followUp:'2026-09-21',interviewDate:'2026-09-25',materialLabel:'AIE reviewed',reviewedAt:'2026-09-10',packetVersions:[{id:'v2',text:'Reviewed packet',at:'2026-09-10'}],draftPacket:{text:'Latest personal edits',at:'2026-09-10'},preparation:{resume:false,portfolio:true},updatedAt:'2026-09-10'});
 const c=catalogue([role('catalog-primary',officialUrl,{urlAliases:[legacyUrl],status:'Not started',draftPacket:{text:'Source draft',at:'2026-09-11'},preparation:{questions:false}})]);
 const before=structuredClone([alias,official]),r=applyCatalogue(state([alias,official]),c),visible=r.jobs.filter(j=>!j.duplicateOf);
 assert.deepEqual(r.jobs.map(j=>j.id),['tracked-alias','saved-official']);assert.equal(visible.length,1);
 const main=visible[0];assert.equal(main.id,'tracked-alias');assert.equal(r.jobs[1].duplicateOf,main.id);assert.equal(main.status,'OA received');
 assert.deepEqual(main.history.map(h=>h.to),['Applied','OA received']);assert.match(main.notes,/Recruiter replied/);assert.match(main.notes,/Ask about conversion/);
 assert.deepEqual(main.packetVersions.map(v=>v.id),['v1','v2']);assert.equal(main.draftPacket.text,'Latest personal edits');
 assert.equal(main.oaDue,'2026-09-20');assert.equal(main.followUp,'2026-09-21');assert.equal(main.interviewDate,'2026-09-25');assert.equal(main.materialLabel,'AIE reviewed');
 assert.deepEqual(main.preparation,{resume:false,questions:true,portfolio:true});assert.deepEqual([alias,official],before);
 const again=applyCatalogue(r,c);assert.deepEqual(again.jobs,r.jobs);
});

test('catalogue duplicate ID chains resolve old URLs even when the primary does not list their aliases',()=>{
 const old=role('browser-id',legacyUrl,{status:'Draft ready',notes:'Do not lose me'});
 const leaf=role('catalog-old',legacyUrl,{duplicateOf:'catalog-middle'}),middle=role('catalog-middle','https://example.com/careers/middle-42',{duplicateOf:'catalog-primary'}),primary=role('catalog-primary',officialUrl,{title:'Verified primary'});
 for(const order of [[leaf,middle,primary],[primary,middle,leaf]]){
  const r=applyCatalogue(state([old]),catalogue(order));assert.equal(r.jobs.length,1);assert.equal(r.jobs[0].id,'browser-id');assert.equal(r.jobs[0].url,officialUrl);assert.equal(r.jobs[0].title,'Verified primary');assert.equal(r.jobs[0].notes,'Do not lose me');
 }
});

test('a secondary saved record keeps its manual JD and coherent qualification facts during consolidation',()=>{
 const main=role('applied-id',officialUrl,{status:'Applied',history:[{at:'2026-09-10',to:'Applied'}]});
 const edited=role('edited-alias',legacyUrl,{jd:'My reviewed master’s eligibility',manualFields:{jd:true,deadline:true},degree:undefined,graduationMin:undefined,graduationMax:undefined,requirementsClassified:false,deadline:'',checkedAt:'2026-09-09',sourceState:'user-import'});
 const c=catalogue([role('catalog-primary',officialUrl,{urlAliases:[legacyUrl],jd:'New PhD-only source text',degree:'phd',graduationMin:'2028-01',requirementsClassified:true,deadline:'2026-09-20',checkedAt:'2026-09-10'})]);
 const r=applyCatalogue(state([main,edited]),c).jobs.find(j=>!j.duplicateOf);
 assert.equal(r.id,'applied-id');assert.equal(r.jd,'My reviewed master’s eligibility');assert.equal(r.degree,undefined);assert.equal(r.graduationMin,undefined);assert.equal(r.requirementsClassified,false);assert.equal(r.deadline,'');
 assert.equal(r.manualFields.jd,true);assert.equal(r.pendingSourceUpdate.jd,'New PhD-only source text');assert.equal(r.pendingSourceUpdate.degree,'phd');
});

test('an older catalogue cannot overwrite newer user-imported facts even before per-field flags existed',()=>{
 const old=role('human-id',legacyUrl,{jd:'Fresh recruiter-confirmed facts',title:'Human confirmed title',degree:'master',graduationMin:'2027-12',deadline:'2026-09-30',sourceState:'user-import',checkedAt:'2026-09-12'});
 const c=catalogue([role('catalog-primary',officialUrl,{urlAliases:[legacyUrl],jd:'Stale bachelor listing',title:'Old title',degree:'bachelor',graduationMin:'2028-01',deadline:'2026-09-18',checkedAt:'2026-09-10'})]);
 const r=applyCatalogue(state([old]),c).jobs[0];assert.equal(r.url,officialUrl);assert.equal(r.jd,'Fresh recruiter-confirmed facts');assert.equal(r.title,'Human confirmed title');assert.equal(r.degree,'master');assert.equal(r.graduationMin,'2027-12');assert.equal(r.deadline,'2026-09-30');
});

test('shared discovery sources, guessed identities and empty URLs do not merge separate jobs',()=>{
 const shared=[{title:'Community list',url:'https://github.com/example/internships'}];
 const old=role('one','https://example.com/one',{sources:shared,identityKey:'unverified-shared'});
 const fresh=role('two','https://example.com/two',{sources:shared,identityKey:'unverified-shared',urlAliases:['javascript:alert(1)','']});
 const r=applyCatalogue(state([old,role('no-url-one','')]),catalogue([fresh,role('no-url-two','')]));
 assert.deepEqual(r.jobs.map(j=>j.id),['one','no-url-one','two','no-url-two']);assert.equal(r.jobs.filter(j=>!j.duplicateOf).length,4);
});
