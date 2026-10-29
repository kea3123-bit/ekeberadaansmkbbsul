'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const legacy = fs.readFileSync(path.join(root, 'Bridges.gs'), 'utf8');
const workspace = fs.readFileSync(path.join(root, '97_WorkspaceBridge.gs'), 'utf8');
const secret = 'a'.repeat(64);
const cache = new Map();
const scriptCache = {
  get(key) { return cache.get(key) || null; },
  put(key, value) { cache.set(key, String(value)); }
};
const ctx = {
  EK: {TIMEZONE: 'Asia/Kuala_Lumpur'},
  getScriptCache_: () => scriptCache,
  CacheService: {getScriptCache: () => scriptCache},
  PropertiesService: {
    getScriptProperties: () => ({
      getProperty: key => key === 'EK_WORKSPACE_BRIDGE_SECRET' ? secret : null
    })
  },
  Utilities: {
    Charset: {UTF_8: 'UTF-8'},
    computeHmacSha256Signature: (payload, key) =>
      [...crypto.createHmac('sha256', key).update(payload, 'utf8').digest()],
    base64EncodeWebSafe: bytes => Buffer.from(bytes).toString('base64url'),
    base64Encode: bytes => Buffer.from(bytes).toString('base64')
  },
  ContentService: {
    MimeType: {JSON: 'application/json'},
    createTextOutput(body) {
      return {kind:'json',body,setMimeType(mime){this.mime=mime;return this;}};
    }
  },
  HtmlService: {
    XFrameOptionsMode: {ALLOWALL:'ALLOWALL'},
    createTemplateFromFile: () => ({
      evaluate() {
        return {
          kind:'html',
          setTitle(){return this;},
          setXFrameOptionsMode(){return this;},
          addMetaTag(){return this;}
        };
      }
    })
  }
};
vm.createContext(ctx);
vm.runInContext(legacy + '\n' + workspace, ctx, {filename:'workspace-bridge-routing.gs'});

function signedCall(action, nonce, issuedAt=Math.floor(Date.now()/1000), data={}) {
  const payload=JSON.stringify({v:1,action,issuedAt,nonce,data});
  const signature=crypto.createHmac('sha256',secret)
    .update(payload,'utf8').digest('base64url');
  return {parameter:{workspace:'1',payload,signature}};
}
function jsonResponse(event) {
  const response=ctx.doPost(event);
  assert.equal(response.kind,'json','Workspace calls must never use HtmlService');
  assert.equal(response.mime,'application/json');
  return JSON.parse(response.body);
}

const request=signedCall('ping','0123456789abcdef0123456789abcdef');
const ok=jsonResponse(request);
assert.equal(ok.ok,true,'signed Workspace ping must succeed');
assert.equal(ok.result.ready,true);
assert.equal(ok.result.timezone,'Asia/Kuala_Lumpur');

const replay=jsonResponse(request);
assert.equal(replay.ok,false,'replayed signed payload must be rejected');
assert.match(replay.error,/already used/);

const invalid=signedCall('ping','abcdef0123456789abcdef0123456789');
invalid.parameter.signature='A'.repeat(43);
const bad=jsonResponse(invalid);
assert.equal(bad.ok,false,'invalid HMAC must be rejected');
assert.match(bad.error,/signature rejected/);

const expired=jsonResponse(signedCall('ping','00000000000000000000000000000001',1));
assert.equal(expired.ok,false,'expired signatures must be rejected');
assert.match(expired.error,/expired/);

const legacyEvent={parameter:{
  bridge:'1',
  payload:JSON.stringify({
    id:'legacy-test',channel:'ui',origin:'https://kea3123-bit.github.io',
    method:'__ping__',args:[]
  })
}};
const legacyOutput=ctx.doPost(legacyEvent);
assert.equal(legacyOutput.kind,'html','old browser bridge must remain HTML transport');

// An imported MySQL user may have no Drive file ID. The signed bridge
// should resolve their own existing eoperasi.png without touching Sheets.
function iterator(entries) {
  let offset=0;
  return {hasNext:()=>offset<entries.length,next:()=>entries[offset++]};
}
const image={
  getName:()=> 'eoperasi.png',
  getId:()=> 'validPhotoFileId123456789'
};
const staffFolder={
  getName:()=> 'Pegawai  Ujian',
  getFiles:()=>iterator([image])
};
const categoryFolder={
  getFolders:()=>iterator([staffFolder])
};
ctx.DriveApp={
  getFolderById:id=>{
    assert.equal(id,'validRootFolderId123456789');
    return {
      getFoldersByName: name=>{
        assert.equal(name,'03 - Anggota Kumpulan Pelaksana');
        return iterator([categoryFolder]);
      }
    };
  }
};
const details={
  rootFolderId:'validRootFolderId123456789',
  name:'  Pegawai Ujian ',
  category:'AKP'
};
const found=jsonResponse(signedCall('findPhoto','abcdefabcdefabcdefabcdefabcdefab',Math.floor(Date.now()/1000),details));
assert.equal(found.ok,true,'signed findPhoto must succeed');
assert.equal(found.result.fileId,'validPhotoFileId123456789');
const missing=jsonResponse(signedCall('findPhoto','abcdefabcdefabcdefabcdefabcdefac',Math.floor(Date.now()/1000),{...details,name:'Tiada Pegawai'}));
assert.equal(missing.ok,true,'missing photo should return a diagnostic');
assert.equal(missing.result.fileId,'');
assert.match(missing.result.message,/Folder bernama/);
const unauthorized=jsonResponse(signedCall('findPhoto','abcdefabcdefabcdefabcdefabcdefad',Math.floor(Date.now()/1000),{...details,category:'unknown'}));
assert.equal(unauthorized.ok,true);
assert.equal(unauthorized.result.fileId,'');

console.log('PASS Workspace JSON route, HMAC, replay, expiry, legacy HTML, signed photo lookup and folder diagnostics');
