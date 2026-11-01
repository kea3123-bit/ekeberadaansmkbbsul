'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const script=fs.readFileSync('apps-script/97_WorkspaceBridge.gs','utf8');
const begin=script.indexOf('function workspaceSendEmail_(data)');
const end=script.indexOf('/**\n * Run ONCE',begin);
assert(begin>=0&&end>begin,'Signed Workspace email adapter not found');
const sends=[];
const cached=new Map();
const context={
 MailApp:{sendEmail:(args)=>sends.push(args)},
 CacheService:{getScriptCache:()=>({get:(k)=>cached.get(k),put:(k,v)=>cached.set(k,v)})},
 LockService:{getScriptLock:()=>({waitLock:()=>{},releaseLock:()=>{}})}
};
vm.createContext(context);
vm.runInContext(script.slice(begin,end),context);
const key='a'.repeat(64);
const html='<!doctype html><html><body><strong>Test</strong></body></html>';
const obj={to:'user@example.test',subject:'Peringatan waktu masuk',
  body:'Rekod masuk tiada',htmlBody:html,deliveryKey:key};
const r=context.workspaceSendEmail_(obj);
assert.equal(r.sent,true);
assert.equal(sends.length,1);
assert.equal(sends[0].htmlBody,html,'HTML was not forwarded to MailApp');
assert.equal(sends[0].body,'Rekod masuk tiada','Text fallback lost');
const dup=context.workspaceSendEmail_(obj);
assert.equal(dup.duplicate,true);
assert.equal(sends.length,1,'Duplicate delivery not blocked');
context.workspaceSendEmail_({...obj,htmlBody:'',deliveryKey:'b'.repeat(64)});
assert.equal(sends.length,2);
assert.equal(Object.hasOwn(sends[1],'htmlBody'),false,'Legacy text-only mail must still work');
assert.throws(()=>context.workspaceSendEmail_({...obj,htmlBody:'<script>alert(1)</script>',deliveryKey:'c'.repeat(64)}),/HTML invalid/);
assert.throws(()=>context.workspaceSendEmail_({...obj,htmlBody:'<a href="javascript:alert(1)">x</a>',deliveryKey:'d'.repeat(64)}),/HTML invalid/);
console.log('SIGNED_HTML_MAIL_BRIDGE_TESTS_OK');
