import seed from './seed.json' with { type: 'json' };
import {normalizeJob,mergeJobs,canonicalUrl} from './engine.mjs';
export const KEY='shu-internship-os-v1';
function mergeApplicationWork(target,entries){
 const ordered=[...entries].sort((a,b)=>(Date.parse(a.application?.at||a.updatedAt||'')||0)-(Date.parse(b.application?.at||b.updatedAt||'')||0));
 target.application=Object.assign({},...ordered.map(j=>j.application||{}));
 target.applicationEvents=[...new Map(entries.flatMap(j=>j.applicationEvents||[]).map(e=>[e.id||JSON.stringify(e),e])).values()].sort((a,b)=>(a.at||'').localeCompare(b.at||''));
 return target;
}
export function upgradeProfile(profile){return {...profile};}
export function initialState(){return {schemaVersion:1,profile:upgradeProfile(structuredClone(seed.profile)),jobs:seed.jobs.map(normalizeJob),resources:seed.resources,lastResearch:seed.lastResearch,answers:{},preferences:{},catalogue:{sources:[],changes:[]}};}
export function hydrateState(incoming){const checked=restoreState(initialState(),incoming);const saved=incoming.jobs.map(normalizeJob);const additions=initialState().jobs.filter(j=>!saved.some(s=>s.id===j.id||(s.url&&j.url&&canonicalUrl(s.url)===canonicalUrl(j.url))));return {...checked,profile:upgradeProfile(checked.profile),jobs:mergeJobs(saved,additions)};}
export function restoreState(current,incoming){
 if(incoming?.schemaVersion!==1||!Array.isArray(incoming.jobs)||!incoming.profile||typeof incoming.profile!=='object')throw Error('This is not a supported Internship OS backup.');
 if(incoming.jobs.length>10000||!Array.isArray(incoming.profile.evidence)||incoming.profile.evidence.length>200)throw Error('Backup exceeds supported size.');
 if(incoming.profile.evidence.some(e=>!e||typeof e.id!=='string'||typeof e.title!=='string'||typeof e.body!=='string'||!Array.isArray(e.skills)||e.skills.some(s=>typeof s!=='string')))throw Error('Backup contains malformed evidence.');
 if(incoming.resources!==undefined&&(!Array.isArray(incoming.resources)||incoming.resources.length>1000||incoming.resources.some(r=>!r||typeof r.title!=='string'||!canonicalUrl(r.url))))throw Error('Backup contains malformed resource links.');
 const validated=incoming.jobs.map(normalizeJob);
 const jobs=mergeJobs(current.jobs,validated).map(j=>{const source=validated.find(v=>v.id===j.id||(v.url&&j.url&&canonicalUrl(v.url)===canonicalUrl(j.url)));if(!source)return j;const last=a=>a?.at||'';const sourceNewer=last(source.history.at(-1))>last(j.history.at(-1))||(!j.history.length&&j.status==='Not started'&&source.status!=='Not started');if(sourceNewer)for(const key of ['status','appliedAt','oaReceivedAt','oaCompletedAt','interviewAt','offerAt','followUp'])if(source[key]!==undefined)j[key]=source[key];if((Date.parse(incoming.updatedAt||'')||0)>(Date.parse(current.updatedAt||'')||0))for(const key of ['followUp','oaDue','interviewDate','draftPacket','preparation','materialLabel','reviewedAt'])if(source[key]!==undefined)j[key]=source[key];j.packetVersions=[...new Map([...(j.packetVersions||[]),...(source.packetVersions||[])].map(v=>[v.id||JSON.stringify(v),v])).values()];j.history=[...new Map([...j.history,...source.history].map(h=>[JSON.stringify(h),h])).values()].sort((a,b)=>(a.at||'').localeCompare(b.at||''));if(source.notes&&!j.notes)j.notes=source.notes;else if(source.notes&&j.notes!==source.notes&&!j.notes.includes(source.notes))j.notes+='\n[Imported note]\n'+source.notes;return j;});
 for(const j of jobs){const previous=current.jobs.filter(v=>v.id===j.id||(v.url&&j.url&&canonicalUrl(v.url)===canonicalUrl(j.url)));const imported=validated.filter(v=>v.id===j.id||(v.url&&j.url&&canonicalUrl(v.url)===canonicalUrl(j.url)));mergeApplicationWork(j,[...previous,...imported]);}
 return {...current,...incoming,profile:{...current.profile,...incoming.profile},jobs};
}
export function reconcileStartup(browser,disk){const browserTime=Date.parse(browser.updatedAt||'')||0,diskTime=Date.parse(disk.updatedAt||'')||0;return hydrateState(browserTime>diskTime?restoreState(disk,browser):restoreState(browser,disk));}
export function applyCatalogue(current,catalogue){
 if(catalogue?.schemaVersion!==2||!Array.isArray(catalogue.jobs))throw Error('Unsupported catalogue. Your records were preserved.');
 const jobs=current.jobs.map(j=>({...j})),savedCount=jobs.length,freshJobs=catalogue.jobs.map(normalizeJob),records=[...jobs,...freshJobs];
 const parents=records.map((_,i)=>i),ids=new Map(),urls=new Map(),catalogueIds=new Map();
 const urlKey=value=>{try{return typeof value==='string'?canonicalUrl(value):'';}catch{return '';}};
 const aliases=j=>[j.url,...(Array.isArray(j.urlAliases)?j.urlAliases:[])].map(urlKey).filter(Boolean);
 const find=i=>{while(parents[i]!==i){parents[i]=parents[parents[i]];i=parents[i];}return i;};
 const join=(a,b)=>{a=find(a);b=find(b);if(a!==b)parents[b]=a;};
 const register=(map,key,i)=>{if(!key)return;if(map.has(key))join(i,map.get(key));else map.set(key,i);};
 // Only saved/catalogue IDs and explicit URL aliases establish identity. Shared
 // discovery pages, similar titles and an unverified identityKey do not.
 records.forEach((j,i)=>{register(ids,j.id,i);for(const url of aliases(j))register(urls,url,i);if(i>=savedCount)catalogueIds.set(j.id,i);});
 records.forEach((j,i)=>{const target=i>=savedCount?catalogueIds.get(j.duplicateOf):ids.get(j.duplicateOf);if(target!==undefined)join(i,target);});
 const groups=new Map();records.forEach((_,i)=>{const key=find(i);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(i);});
 const stamp=value=>Date.parse(value||'')||0;
 const historyTime=j=>Math.max(0,...(j.history||[]).map(h=>stamp(h.at)),...['appliedAt','oaReceivedAt','oaCompletedAt','interviewAt','offerAt'].map(k=>stamp(j[k])));
 const personalTime=j=>Math.max(stamp(j.updatedAt),stamp(j.reviewedAt),historyTime(j));
 const factTime=j=>Math.max(stamp(j.updatedAt),stamp(j.reviewedAt),stamp(j.checkedAt));
 const hasWork=j=>Number(j.status&&j.status!=='Not started')+Number(!!j.notes)+Number(!!j.draftPacket)+Number(!!j.packetVersions?.length);
 const personalFields=['appliedAt','oaReceivedAt','oaCompletedAt','interviewAt','offerAt','followUp','oaDue','interviewDate','reviewedAt','materialLabel','updatedAt'];
 const jdFacts=['jd','degree','graduation','graduationMin','graduationMax','authorization','requiredSkills','preferredSkills','requirementsClassified','year','season','yearBasis','sponsorshipEvidence','cptEvidence','jdTextKind'];
 const factFields=[...jdFacts,'title','company','location','deadline','deadlineNote','pay','scopeStatus','sourceState','checkedAt'];
 for(const group of groups.values()){
  const incoming=group.filter(i=>i>=savedCount);if(!incoming.length)continue;
  const candidates=incoming.filter(i=>!records[i].duplicateOf);
  // An incomplete or cyclic duplicate map must still leave one visible record.
  const sourceIndex=(candidates.length?candidates:incoming).sort((a,b)=>stamp(records[b].checkedAt)-stamp(records[a].checkedAt)||records[a].id.localeCompare(records[b].id))[0];
  const fresh=records[sourceIndex],saved=group.filter(i=>i<savedCount);
  if(!saved.length){jobs.push({...fresh,...Object.fromEntries(personalFields.map(key=>[key,fresh[key]])),duplicateOf:undefined,packetVersions:fresh.packetVersions||[],draftPacket:fresh.draftPacket,preparation:fresh.preparation||{},manualFields:fresh.manualFields||{},pendingSourceUpdate:fresh.pendingSourceUpdate,sources:[...new Map(group.flatMap(i=>records[i].sources||[]).filter(s=>urlKey(s.url)).map(s=>[urlKey(s.url),s])).values()],urlAliases:[...new Set(group.flatMap(i=>aliases(records[i])))].sort()});continue;}
  const mainIndex=[...saved].sort((a,b)=>Number(!!records[a].duplicateOf)-Number(!!records[b].duplicateOf)||historyTime(records[b])-historyTime(records[a])||hasWork(records[b])-hasWork(records[a])||a-b)[0];
  const old=records[mainIndex],existing=saved.map(i=>records[i]);
  const ordered=[...existing].sort((a,b)=>personalTime(a)-personalTime(b)||Number(a===old)-Number(b===old));
  let next={...old,...fresh,id:old.id,duplicateOf:undefined};
  for(const key of personalFields){next[key]=undefined;for(const entry of ordered)if(entry[key]!==undefined)next[key]=entry[key];}
  const statusOwner=[...existing].sort((a,b)=>historyTime(b)-historyTime(a)||Number(b.status!=='Not started')-Number(a.status!=='Not started')||Number(b===old)-Number(a===old))[0];
  next.status=statusOwner.status||'Not started';
  next.history=[...new Map(existing.flatMap(j=>j.history||[]).map(h=>[JSON.stringify(h),h])).values()].sort((a,b)=>stamp(a.at)-stamp(b.at));
  next.notes=old.notes||'';
  for(const entry of existing)if(entry.notes&&entry.notes!==next.notes&&!next.notes.includes(entry.notes))next.notes+=(next.notes?'\n[Consolidated note]\n':'')+entry.notes;
  const versions=new Map();
  for(const entry of ordered)for(const version of entry.packetVersions||[]){const key=version.id||JSON.stringify(version),previous=versions.get(key);if(!previous||stamp(version.at)>=stamp(previous.at))versions.set(key,version);}
  next.packetVersions=[...versions.values()].sort((a,b)=>stamp(a.at)-stamp(b.at));
  const drafts=ordered.filter(j=>j.draftPacket!==undefined).sort((a,b)=>stamp(a.draftPacket?.at)-stamp(b.draftPacket?.at)||personalTime(a)-personalTime(b)||Number(a===old)-Number(b===old));
  if(drafts.length)next.draftPacket=drafts.at(-1).draftPacket;else next.draftPacket=undefined;
  next.preparation=Object.assign({},...ordered.map(j=>j.preparation||{}));
  mergeApplicationWork(next,existing);
  next.manualFields=Object.assign({},...ordered.map(j=>j.manualFields||{}));
  next.pendingSourceUpdate=Object.assign({},...ordered.map(j=>j.pendingSourceUpdate||{}));
  const factOrder=[...existing].sort((a,b)=>factTime(b)-factTime(a)||Number(b===old)-Number(a===old));
  const protect=(key,owner)=>{next[key]=owner[key];if(JSON.stringify(owner[key])!==JSON.stringify(fresh[key]))next.pendingSourceUpdate={...next.pendingSourceUpdate,[key]:fresh[key],checkedAt:fresh.checkedAt};};
  const newerHuman=factOrder.find(j=>(j.sourceState==='user-import'||j.source==='Manual import')&&factTime(j)>stamp(fresh.checkedAt));
  if(newerHuman)for(const key of factFields)if(Object.hasOwn(newerHuman,key))protect(key,newerHuman);
  const manualJD=factOrder.find(j=>j.manualFields?.jd||j.sourceState==='user-import');
  if(manualJD){next.manualFields.jd=true;for(const key of jdFacts)protect(key,manualJD);}
  for(const key of factFields){const owner=factOrder.find(j=>j.manualFields?.[key]);if(owner)protect(key,owner);}
  if(!fresh.deadline&&!existing.some(j=>j.manualFields?.deadline)&&!(newerHuman&&Object.hasOwn(newerHuman,'deadline'))){const owner=[...ordered].reverse().find(j=>j.deadline);if(owner)next.deadline=owner.deadline;}
  if(!Object.keys(next.pendingSourceUpdate).length)next.pendingSourceUpdate=undefined;
  next.sources=[...new Map(group.flatMap(i=>records[i].sources||[]).filter(s=>urlKey(s.url)).map(s=>[urlKey(s.url),s])).values()];
  next.urlAliases=[...new Set(group.flatMap(i=>aliases(records[i])))].sort();
  jobs[mainIndex]=next;
  for(const i of saved)if(i!==mainIndex)jobs[i]={...jobs[i],duplicateOf:next.id};
 }
 const {jobs:ignore,...metadata}=catalogue;const resources=[...new Map([...(current.resources||[]),...(catalogue.resources||[])].map(r=>[r.url,r])).values()];
 return {...current,jobs,resources,catalogue:metadata,lastResearch:catalogue.updatedAt?.slice(0,10)||current.lastResearch};
}
