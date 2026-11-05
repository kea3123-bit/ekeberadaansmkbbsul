'use strict';
const fs=require('node:fs');
const assert=require('node:assert/strict');
const js=fs.readFileSync('mysql-ui/Scripts.html','utf8');
const css=fs.readFileSync('mysql-ui/Styles.html','utf8');
const html=fs.readFileSync('mysql-ui/Index.html','utf8');
new Function(js);
const reason=js.slice(js.indexOf('function showMyTimeReasonTable(rows)'),js.indexOf('async function openMyTimeReasonTable()'));
const admin=js.slice(js.indexOf('async function openAdminPendingActions()'),js.indexOf('function openAdminPendingAction(index)'));
assert(reason.includes('ek-responsive-notice-table ek-reason-list'),'Reason popup needs mobile-specific table class');
assert(admin.includes('ek-responsive-notice-table ek-admin-list'),'Admin popup needs mobile-specific table class');
assert(reason.includes('ek-record-times'),'Incident record and reference times must stay separately readable');
assert(reason.includes("onclick=\"openMyTimeReasonForm('+i+')\""),'Explain button must still open exact selected incident');
assert(admin.includes("onclick=\"openAdminPendingAction('+(offset+i)+')\""),'Admin button must still open exact selected item');
assert(reason.includes('<thead><tr><th>Tarikh</th>'),'Desktop reason table must remain');
assert(admin.includes('<th>Pegawai</th>'),'Desktop admin table must remain');
assert(css.includes('@media (max-width:760px)'),'Mobile breakpoint missing');
for(const name of ['.ek-notice-scroll .ek-responsive-notice-table','min-width:0!important','.ek-notice-scroll .ek-reason-list tr','.ek-notice-scroll .ek-admin-list tr','.ek-reason-list td:nth-child(4) .btn{width:100%}']){
  assert(css.includes(name),'Missing compact card layout '+name);
}
assert(css.includes('.ek-responsive-notice-table thead{display:none}'),'Table headers should be hidden only on mobile');
assert(css.includes('min-height:44px'),'Actions need touch-size minimum');
assert(html.includes('id="homeTimeReasonNotice"')&&html.includes('id="homeAdminPendingNotice"'),'Both Home notification cards must remain');
console.log('MOBILE_RESPONSIVE_REASON_AND_ADMIN_NOTICE_OK');
