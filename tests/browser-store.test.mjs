import test from 'node:test';
import assert from 'node:assert/strict';
import {KEY} from '../lib/storage.mjs';

// Node has no IndexedDB. This minimal transaction harness serializes access to
// one shared object store; it does not implement the application's revision rule.
function memoryIndexedDB(initial) {
 const records=new Map(initial===undefined?[]:[['current',structuredClone(initial)]]);
 let tail=Promise.resolve();
 const db={objectStoreNames:{contains:()=>true},close(){},transaction(){
  const operations=[];
  const tx={error:null,aborted:false,abort(){this.aborted=true;},objectStore(){return {
   get(key){const request={};operations.push(()=>{request.result=structuredClone(records.get(key));request.onsuccess?.();});return request;},
   put(value,key){const copy=structuredClone(value);operations.push(()=>{if(!tx.aborted)pending.set(key,copy);});return {};}
  };}};
  const pending=new Map();
  const run=async()=>{
   await Promise.resolve();
   while(operations.length&&!tx.aborted){operations.shift()();await Promise.resolve();}
   if(tx.aborted){tx.onabort?.();return;}
   for(const [key,value] of pending)records.set(key,value);
   tx.oncomplete?.();
  };
  tail=tail.then(run,run);return tx;
 }};
 return {records,open(){const request={};queueMicrotask(()=>{request.result=db;request.onsuccess?.();});return request;}};
}

let sequence=0;
async function client(){return import(`../lib/browser-store.mjs?test-client=${++sequence}`);}
function install(t,{current,legacy}={}){
 const previousIndexedDB=globalThis.indexedDB,previousLocalStorage=globalThis.localStorage;
 const idb=memoryIndexedDB(current),legacyValues=new Map(legacy===undefined?[]:[[KEY,JSON.stringify(legacy)]]);
 globalThis.indexedDB=idb;
 globalThis.localStorage={getItem:key=>legacyValues.get(key)??null};
 t.after(()=>{globalThis.indexedDB=previousIndexedDB;globalThis.localStorage=previousLocalStorage;});
 return {idb,legacyValues};
}

test('two tabs reading one version cannot overwrite each other with a stale snapshot',async t=>{
 install(t,{current:{jobs:[{id:'job',notes:'Original'}]}});
 const first=await client(),second=await client();
 const a=await first.readBrowserState(),b=await second.readBrowserState();
 a.jobs[0].notes='Saved by first tab';
 await first.writeBrowserState(a);
 b.jobs[0].notes='Stale second tab edit';
 await assert.rejects(second.writeBrowserState(b),error=>error.code==='BROWSER_CONFLICT');
 const observer=await client();
 assert.equal((await observer.readBrowserState()).jobs[0].notes,'Saved by first tab');
 const latest=await second.readBrowserState();
 latest.jobs[0].notes='Second tab after explicitly reloading';
 await second.writeBrowserState(latest);
 assert.equal((await observer.readBrowserState()).jobs[0].notes,'Second tab after explicitly reloading');
});

test('one tab can save successive versions without conflicting with itself',async t=>{
 install(t,{current:{step:0}});
 const tab=await client();await tab.readBrowserState();
 await tab.writeBrowserState({step:1});
 await tab.writeBrowserState({step:2});
 assert.deepEqual(await (await client()).readBrowserState(),{step:2});
});

test('overlapping saves from the same tab complete in invocation order',async t=>{
 install(t,{current:{step:0}});
 const tab=await client();await tab.readBrowserState();
 await Promise.all([tab.writeBrowserState({step:1}),tab.writeBrowserState({step:2})]);
 assert.deepEqual(await (await client()).readBrowserState(),{step:2});
});

test('legacy localStorage data migrates on save while the original remains intact',async t=>{
 const legacy={jobs:[{id:'legacy',notes:'Keep this'}]};
 const {legacyValues}=install(t,{legacy});const original=legacyValues.get(KEY);
 const tab=await client();assert.deepEqual(await tab.readBrowserState(),legacy);
 await tab.writeBrowserState({...legacy,migrated:true});
 assert.deepEqual(await (await client()).readBrowserState(),{...legacy,migrated:true});
 assert.equal(legacyValues.get(KEY),original);
});
