import {transitionJob} from './engine.mjs';
import {jobIdentity} from '../extension/core.mjs';
export {jobIdentity,platformFor,isSensitiveQuestion,makeApplicationKit,validateKit} from '../extension/core.mjs';
export function importApplicationEvents(state,payload){
 if(payload?.kind!=='summer27-application-events'||!Array.isArray(payload.events)||payload.events.length>500)throw Error('Invalid application receipt file.');
 let jobs=state.jobs.map(j=>({...j}));
 for(const e of payload.events){
  if(!e||typeof e.id!=='string'||e.id.length>100||e.jobKey!==jobIdentity(e.url)||!e.jobKey||!Number.isFinite(Date.parse(e.at))||!['attempted','confirmed','blocked'].includes(e.status))throw Error('Invalid receipt identity or status.');
  const i=jobs.findIndex(j=>!j.duplicateOf&&[j.url,...(j.urlAliases||[])].some(u=>jobIdentity(u)===e.jobKey));
  if(i<0)throw Error('A receipt does not match a saved job. Import that job first.');
  let j=jobs[i];if((j.applicationEvents||[]).some(v=>v.id===e.id))continue;
  const event={id:e.id,jobKey:e.jobKey,url:e.url,at:e.at,status:e.status,resumeName:String(e.resumeName||'').slice(0,150),receipt:String(e.receipt||'').slice(0,1000),userConfirmedReceipt:e.userConfirmedReceipt===true};
  if(e.status==='confirmed'&&(!event.userConfirmedReceipt||!event.receipt.trim()))throw Error('Receipt confirmation requires an explicit acknowledgement and evidence.');
  if(e.status==='confirmed'&&['Not started','Shortlisted','Draft ready'].includes(j.status))j=transitionJob(j,'Applied',e.at);
  jobs[i]={...j,applicationEvents:[...(j.applicationEvents||[]),event],application:{...j.application,lastEventAt:e.at},updatedAt:new Date().toISOString()};
 }
 return {...state,jobs};
}
