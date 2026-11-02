'use strict';
const fs=require('node:fs');
const assert=require('node:assert/strict');
const js=fs.readFileSync('mysql-ui/Scripts.html','utf8');
new Function(js);
const pub=js.slice(js.indexOf('function applyAbsencePublicFilters()'),js.indexOf('async function generatePublicAbsencePresencePdfClient()'));
assert(pub.includes('formatDateRange(r.originalStartDate||r.startDate,r.originalEndDate||r.endDate)'),
 'Public list must show original multi-day request duration even when filtering a single day');
assert(pub.includes("r.mode==='KEBERADAAN'"),'Presence time-of-day rendering must remain');
const manage=js.slice(js.indexOf('function applyAbsenceManageFilters()'),js.indexOf('function openReviewAbsence('));
assert(manage.includes("r.reviewerJobTitle"),'Reviewer actual job title missing');
assert(manage.includes("'Diluluskan oleh'"),'Approved row label missing');
assert(manage.includes("'Ditolak oleh'"),'Rejected row label missing');
assert(manage.includes("'Jawatan tidak direkodkan'"),'Missing reviewer job must have truthful fallback');
assert(!manage.includes("r.reviewerJobTitle||'Pengurusan'"),'Category Pengurusan is not reviewer job title');
assert(manage.includes("r.status==='MENUNGGU'"),'Pending approval actions must remain');
assert(manage.includes("r.status==='DIBATALKAN'"),'Cancelled request must not masquerade as approved');
console.log('ABSENCE_UI_REVIEWER_ROLE_AND_FULL_DATE_RANGE_OK');
