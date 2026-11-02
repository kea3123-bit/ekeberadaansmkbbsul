'use strict';
const fs=require('node:fs');
const assert=require('node:assert/strict');
const js=fs.readFileSync('mysql-ui/Scripts.html','utf8');
const html=fs.readFileSync('mysql-ui/Index.html','utf8');
new Function(js);
for(const needle of [
 'getMyTimeExceptionReasons','saveMyTimeExceptionReason','loadMyTimeExceptionReasons()',
 "state.timeReasonPromptShown.add(row.id)","r.userReason","esc(r.userReason)",
 "state.timeReasonCurrent=null","if(name==='home')","setTimeout(()=>loadMyTimeExceptionReasons().catch(()=>{}),200)"
])assert(js.includes(needle),'Missing UI behavior: '+needle);
assert(html.includes('<th>Sebab pengguna</th>'),'Admin review needs separate user reason column');
assert(js.includes('colspan="9"'),'Empty admin rows need 9 columns');
assert(js.includes('Tiada permohonan Tidak Hadir / Keberadaan'),'Popup must explain the absence check');
assert(js.includes('setButtonBusy(submit,true'),'Prevent accidental double submissions');
assert(!js.includes('name="reason" rows="4"'),'Input must have length constraints');
console.log('SELF_TIME_REASON_FRONTEND_REGRESSION_OK');
