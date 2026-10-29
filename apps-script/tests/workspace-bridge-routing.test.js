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

function signedCall(action, nonce, issuedAt=Math.floor(Date.now()/1000)) {
  const payload=JSON.stringify({v:1,action,issuedAt,nonce,data:{}});
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

console.log('PASS Workspace JSON route, signed ping, replay, HMAC, expiry and legacy HTML transport');
