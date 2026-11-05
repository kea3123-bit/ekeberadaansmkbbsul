'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const script=fs.readFileSync('mysql-ui/Scripts.html','utf8');
const page=fs.readFileSync('mysql-ui/Index.html','utf8');
const api=fs.readFileSync('php/api.php','utf8');
new Function(script);
assert(api.includes("case 'getAdminPendingActions':"),'Authenticated admin pending RPC missing');
assert(api.includes("require_user($a[0]??'',true)"),'API must enforce admin authorization');
assert(page.includes('id="homeAdminPendingNotice"'),'Missing Home admin card');
assert(page.includes('onclick="openAdminPendingActions()"'),'Missing Home card action');
for(const part of [
 'function renderAdminPendingNotice()', 'async function refreshAdminPendingNotice(force=false)',
 'async function openAdminPendingActions()', 'function openAdminPendingAction(index)',
 "runServer('getAdminPendingActions',token)",
 'if(!state.boot?.user?.isAdmin)return toast',
 "navigate('absencemanage')","navigate('timereview')",
 "document.getElementById('absenceManageStatus').value='MENUNGGU'",
 "document.getElementById('timeReviewStatus').value='BELUM DIAMBIL MAKLUM'",
 'refreshAdminPendingNotice(true).catch(()=>{})'
])assert(script.includes(part),'Missing admin notification feature: '+part);
assert(script.includes("if(state.boot?.user?.isAdmin)setTimeout(()=>refreshAdminPendingNotice"),
 'Only admins should fetch Home pending actions');
const block=script.slice(script.indexOf('// ---------- Notifikasi tindakan tertunggak'),script.indexOf('// ---------- Sebab Lewat / Balik Awal'));
assert(!block.includes("reviewAbsenceRequest"),'Notification must not approve automatically');
assert(!block.includes("reviewTimeException"),'Notification must not acknowledge automatically');
console.log('ADMIN_PENDING_ACTIONS_HOME_AND_NAVIGATION_OK');
