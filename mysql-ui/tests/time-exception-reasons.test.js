'use strict';
const fs=require('node:fs');
const assert=require('node:assert/strict');
const js=fs.readFileSync('mysql-ui/Scripts.html','utf8');
const html=fs.readFileSync('mysql-ui/Index.html','utf8');
new Function(js);
for(const needle of [
 'getMyTimeExceptionReasons','saveMyTimeExceptionReason','loadMyTimeExceptionReasons(res.timeException)',
 "state.timeReasonPromptShown.add(row.id)","r.userReason","esc(r.userReason)",
 "state.timeReasonCurrent=null","if(res.timeException)","runServer('getMyTimeExceptionReasons',state.token,justPunched)"
])assert(js.includes(needle),'Missing UI behavior: '+needle);
assert(!js.includes("setTimeout(()=>loadMyTimeExceptionReasons().catch(()=>{}),450)"),'Login must never open the popup');
assert(!js.includes("if(name==='home')setTimeout(()=>loadMyTimeExceptionReasons"),'Opening Home must never open the popup');
assert(!js.includes("setTimeout(()=>loadMyTimeExceptionReasons().catch(()=>{}),200)"),'Submitting a reason must not reopen old prompts');
assert(js.includes("justPunched.date!==state.boot?.today"),'Only same-day incidents may trigger');
assert(js.includes("r.recordTime===justPunched.recordTime"),'Only current punch time may trigger');
assert(html.includes('<th>Sebab pengguna</th>'),'Admin review needs separate user reason column');
assert(js.includes('colspan="9"'),'Empty admin rows need 9 columns');
assert(js.includes('Tiada permohonan Tidak Hadir / Keberadaan'),'Popup must explain the absence check');
assert(js.includes('setButtonBusy(submit,true'),'Prevent accidental double submissions');
assert(!js.includes('name="reason" rows="4"'),'Input must have length constraints');
console.log('SELF_TIME_REASON_FRONTEND_REGRESSION_OK');
