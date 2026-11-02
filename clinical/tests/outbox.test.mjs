import 'fake-indexeddb/auto';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {enqueue,pending,remove} from '../src/outbox.ts';

const draft=(owner)=>({id:crypto.randomUUID(),owner,caseId:'synthetic-case',label:'Review',path:'/cases/synthetic-case/review',body:{event_id:crypto.randomUUID(),expected_version:1,notes:'Private fictional notes'},created:new Date().toISOString()});
const db=()=>new Promise((resolve,reject)=>{const r=indexedDB.open('shwaas-clinical-outbox',1);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});
const raw=async(id)=>{const d=await db();return new Promise(resolve=>{const r=d.transaction('queue').objectStore('queue').get(id);r.onsuccess=()=>resolve(r.result)})};
test('draft persists encrypted and can be replayed without changing its event',async()=>{
 const m=draft('doctor-a');await enqueue(m);const stored=await raw(m.id);
 assert.ok(stored.ciphertext instanceof ArrayBuffer);assert.equal(stored.body,undefined);
 assert.ok(!new TextDecoder().decode(stored.ciphertext).includes('Private fictional notes'));
 assert.deepEqual(await pending(m.owner),[m]);assert.deepEqual(await pending('other-doctor'),[]);
 await remove(m.id);assert.deepEqual(await pending(m.owner),[]);
});
test('blocked conflict survives a page module reload',async()=>{
 const m={...draft('doctor-b'),blocked:'Version conflict'};await enqueue(m);
 const reload=await import('../src/outbox.ts?fresh-module');assert.deepEqual(await reload.pending(m.owner),[m]);
 await remove(m.id);
});
test('two tabs agree on the first account encryption key',async()=>{
 const tab2=await import('../src/outbox.ts?another-tab');const a=draft('doctor-race'),b=draft('doctor-race');
 await Promise.all([enqueue(a),tab2.enqueue(b)]);
 const values=await pending(a.owner);assert.equal(values.length,2);assert.ok(values.some(x=>x.id===a.id));assert.ok(values.some(x=>x.id===b.id));
 await remove(a.id);await remove(b.id);
});
test('tampered ciphertext is rejected rather than returned as a valid draft',async()=>{
 const m=draft('doctor-tamper');await enqueue(m);const stored=await raw(m.id);
 const bytes=new Uint8Array(stored.ciphertext);bytes[0]^=1;
 const d=await db();await new Promise((resolve,reject)=>{const tx=d.transaction('queue','readwrite');tx.objectStore('queue').put(stored);tx.oncomplete=resolve;tx.onerror=reject});
 await assert.rejects(()=>pending(m.owner));await remove(m.id);
});
