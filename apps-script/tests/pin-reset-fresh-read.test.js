'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const users=fs.readFileSync(path.join(root,'40_UsersData.gs'),'utf8');
const auth=fs.readFileSync(path.join(root,'10_Auth.gs'),'utf8');
const emailA='first@example.test',emailB='second@example.test';
function row(email,name){
  const a=Array(24).fill('');
  a[0]=true;a[1]=name;a[2]=email;a[3]='AKP';
  a[9]='oldSalt';a[10]='oldHash';a[11]=false;a[12]=3;a[18]='PIN_V1';
  return a;
}
const data=[row(emailB,'Second'),row(emailA,'First')];
let suppressWrites=false,flushes=0,revoked=[],notified=0;
const sh={
  getLastRow:()=>data.length+1,
  getRange(row,col,nrows=1,ncols=1){
    return {
      getValues:()=>Array.from({length:nrows},(_,i)=>data[row-2+i].slice(col-1,col-1+ncols)),
      getValue:()=>data[row-2][col-1],
      setValues(v){if(!suppressWrites) v.forEach((vals,i)=>vals.forEach((x,j)=>data[row-2+i][col-1+j]=x));return this;},
      setValue(v){if(!suppressWrites)data[row-2][col-1]=v;return this;},
      insertCheckboxes(){return this;},
      setNumberFormat(){return this;}
    };
  }
};
const ctx={
  EK:{SHEETS:{USERS:'PENGGUNA'},USER_HEADERS:Array(24).fill('header'),
    PASSWORD:{AUTH_TYPE:'PIN_V1',PEPPER_KEY:'EK_PASSWORD_PEPPER',PIN_LENGTH:6}},
  getSheetOrThrow_:()=>sh,
  SpreadsheetApp:{flush:()=>flushes++},
  normalizeEmail_:v=>String(v||'').trim().toLowerCase(),
  normalizeOptionalTime_:v=>String(v||''),
  toBool_:v=>v===true||v==='TRUE',
  invalidateUsersCache_:()=>{},
  revokeAllTrustedDevicesForUser_:(email,reason)=>revoked.push({email,reason}),
  PropertiesService:{getScriptProperties:()=>({getProperty:()=> 'a'.repeat(64)})},
  hasUserEverLoggedIn_:()=>true,
  normalizeClientInfo_:x=>x||{},
  isValidEmail_:x=>x.includes('@'),
  createPasswordChangeTicket_:()=> 'a'.repeat(64),
  recordLoginEventSafe_:()=>{},
  audit_:()=>{},
  sendPasswordResetPromptEmail_:()=>notified++,
  requireSessionAdmin_:()=>({email:'admin@example.test'}),
  getAllUsers_:()=>[],
  console
};
vm.createContext(ctx);
vm.runInContext(users+'\n'+auth,ctx,{filename:'auth-reset.gs'});
// Override real auditing/ticket/history routines, which are intentionally not
// under test and depend on separate Apps Script services.
vm.runInContext(`
  hasUserEverLoggedIn_=()=>true;
  createPasswordChangeTicket_=()=> 'a'.repeat(64);
  recordLoginEventSafe_=()=>{};
  requireSessionAdmin_=()=>({email:'admin@example.test'});
`,ctx);

// Simulate a stale in-memory user object before Sheet was sorted.
const obsolete={email:emailA,row:2,sessionVersion:3};
const reset=ctx.preparePasswordSetupState_(obsolete);
assert.equal(reset.email,emailA);
assert.equal(reset.row,3,'must locate moved user by email');
assert.equal(data[1][9],'');
assert.equal(data[1][10],'');
assert.equal(data[1][11],true);
assert.equal(data[1][18],'');
assert.equal(data[0][10],'oldHash','another user PIN must be unchanged');
assert.equal(flushes,1,'write must be flushed before verification');
assert.equal(revoked[0].email,emailA);

const result=ctx.checkDelimaAccount(emailA,{});
assert.equal(result.pinReady,false,'reset account must never ask for old PIN');
assert.equal(result.directPinSetup,true);
assert.equal(result.setupPurpose,'ADMIN_RESET');
assert.equal(result.changeTicket.length,64);
assert.equal(data[0][10],'oldHash');

// The email must never be sent when the reset write cannot be verified.
suppressWrites=true;
assert.throws(()=>ctx.adminResetPassword('token',emailB),
  /Reset PIN tidak dapat disahkan/);
assert.equal(notified,0,'no success email after failed write');
assert.equal(data[0][10],'oldHash');
suppressWrites=false;
const ok=ctx.adminResetPassword('token',emailB);
assert.equal(ok.ok,true);
assert.equal(ok.emailSent,true);
assert.equal(notified,1);
assert.equal(data[0][10],'');
assert.equal(data[0][11],true);
assert.equal(data[0][18],'');
assert.equal(data[1][10],'');
console.log('PASS reset survives sheet sort; login immediately offers new PIN; failed reset never sends misleading email; other account preserved');
