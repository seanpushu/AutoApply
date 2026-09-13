// IndexedDB holds the larger workspace; the legacy localStorage copy is never deleted.
import {KEY} from './storage.mjs';
const DB='summer27-workspace-v2';
export const BROWSER_CONFLICT='BROWSER_CONFLICT';
let expectedRevision;
let pending=Promise.resolve();

function open(){return new Promise((resolve,reject)=>{const r=indexedDB.open(DB,1);r.onupgradeneeded=()=>{if(!r.result.objectStoreNames.contains('workspace'))r.result.createObjectStore('workspace');};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
function revisionOf(value){if(value===undefined)return 0;if(!Number.isSafeInteger(value)||value<0)throw Error('The browser save revision is invalid. Export a backup before continuing.');return value;}
function enqueue(operation){const result=pending.then(operation);pending=result.catch(()=>{});return result;}
function conflict(){const error=Error('Another tab saved newer records. Export this tab’s backup, then reload before saving again.');error.code=BROWSER_CONFLICT;return error;}

export function readBrowserState(){return enqueue(async()=>{
 let db;
 try{
  db=await open();
  const snapshot=await new Promise((resolve,reject)=>{
   const tx=db.transaction('workspace','readonly'),store=tx.objectStore('workspace');
   const stateRequest=store.get('current'),revisionRequest=store.get('revision');
   tx.oncomplete=()=>{try{resolve({state:stateRequest.result,revision:revisionOf(revisionRequest.result)});}catch(error){reject(error);}};
   tx.onerror=()=>reject(tx.error||Error('Browser read failed'));
   tx.onabort=()=>reject(tx.error||Error('Browser read aborted'));
  });
  expectedRevision=snapshot.revision;
  if(snapshot.state!==undefined&&snapshot.state!==null)return snapshot.state;
 }catch{expectedRevision=undefined;}finally{db?.close();}
 const legacy=localStorage.getItem(KEY);return legacy?JSON.parse(legacy):null;
});}

export function writeBrowserState(value){return enqueue(async()=>{
 if(expectedRevision===undefined){const error=Error('Browser records could not be read safely. Export a backup, then reload before saving.');error.code='BROWSER_NOT_READY';throw error;}
 const db=await open();
 try{
  const committedRevision=await new Promise((resolve,reject)=>{
   // The comparison and both writes share one transaction, so another tab
   // cannot commit between checking the revision and replacing the state.
   const tx=db.transaction('workspace','readwrite'),store=tx.objectStore('workspace');
   let failure,nextRevision;
   tx.oncomplete=()=>resolve(nextRevision);
   tx.onerror=()=>reject(failure||tx.error||Error('Browser save failed'));
   tx.onabort=()=>reject(failure||tx.error||Error('Browser save aborted'));
   const request=store.get('revision');
   request.onsuccess=()=>{
    try{
     const actual=revisionOf(request.result);
     if(actual!==expectedRevision)throw conflict();
     if(actual===Number.MAX_SAFE_INTEGER)throw Error('Browser save revision limit reached. Export a backup before continuing.');
     nextRevision=actual+1;
     store.put(value,'current');
     store.put(nextRevision,'revision');
    }catch(error){failure=error;tx.abort();}
   };
  });
  expectedRevision=committedRevision;
 }finally{db.close();}
});}
