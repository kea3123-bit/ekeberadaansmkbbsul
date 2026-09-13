from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 match, got {count}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')


# 1) Run the one-time legacy migration for Farhan on bootstrap after the
# effective-dated baseline has been established.
replace_once(
    'apps-script/20_UserApi.gs',
    "  try { ensureScheduleHistoryBaseline_(user, getSettings_(), new Date(), 'BOOTSTRAP'); }\n"
    "  catch (e) { try { audit_('SEJARAH_JADUAL_BASELINE_GAGAL', user.email, String(e && e.message ? e.message : e), 'SISTEM'); } catch (_e) {} }\n",
    "  try { ensureScheduleHistoryBaseline_(user, getSettings_(), new Date(), 'BOOTSTRAP'); }\n"
    "  catch (e) { try { audit_('SEJARAH_JADUAL_BASELINE_GAGAL', user.email, String(e && e.message ? e.message : e), 'SISTEM'); } catch (_e) {} }\n"
    "  try { ensureKnownLegacyScheduleMigrations_(user); }\n"
    "  catch (e) { try { audit_('MIGRASI_JADUAL_LEGASI_GAGAL', user.email, String(e && e.message ? e.message : e), 'SISTEM'); } catch (_e) {} }\n",
    'bootstrap legacy schedule migration'
)

# 2) Punch Card must only expose reviews that correspond to the CURRENTLY
# effective timing flags for that historical day.
old_reviews = """  const reviewRows = readTimeReviewRows_().filter(r => r.email === user.email && r.date >= systemStartDate && String(r.date || '').slice(0,7) === monthKey);
  records.forEach(r => {
    const dayReviews = reviewRows.filter(x => x.date === r.date);
    r.reviewState = timeReviewStatementForCard_(dayReviews, r.statusFlags || []);
    r.reviewItems = dayReviews.map(x => ({type:x.type,session:Number(x.session||1),reviewStatus:x.reviewStatus||'',reviewerJobTitle:getReviewerJobTitleFromEmail_(x.reviewedBy),reviewedAt:x.reviewedAt?formatDateTime_(x.reviewedAt):'',comment:x.comment||''}));
  });
"""
new_reviews = """  const reviewRows = readTimeReviewRows_().filter(r => r.email === user.email && r.date >= systemStartDate && String(r.date || '').slice(0,7) === monthKey);
  records.forEach(r => {
    const activeFlags = new Set((r.statusFlags || []).map(x => String(x || '').toUpperCase()));
    const dayReviews = reviewRows.filter(x => x.date === r.date && activeFlags.has(String(x.type || '').toUpperCase()));
    r.reviewState = timeReviewStatementForCard_(dayReviews, r.statusFlags || []);
    r.reviewItems = dayReviews.map(x => ({type:x.type,session:Number(x.session||1),reviewStatus:x.reviewStatus||'',reviewerJobTitle:getReviewerJobTitleFromEmail_(x.reviewedBy),reviewedAt:x.reviewedAt?formatDateTime_(x.reviewedAt):'',comment:x.comment||''}));
  });
"""
replace_once('apps-script/20_UserApi.gs', old_reviews, new_reviews, 'punch card review filtering')

# 3) Frontend hardening: never paint a punch red solely because a stale review
# object leaked through. The record's active statusFlags must also contain it.
replace_once(
    'Scripts.html',
    "      const reviews=r.reviewItems||[], flagged=(type,session)=>reviews.some(x=>String(x.type||'').toUpperCase()===type&&Number(x.session||1)===session), tc=(v,bad)=>`<td class=\\\"${bad?'pc-time-alert':''}\\\">${esc(shortTime(v))}</td>`;",
    "      const reviews=r.reviewItems||[], activeFlags=(r.statusFlags||[]).map(x=>String(x||'').toUpperCase()), flagged=(type,session)=>activeFlags.includes(type)&&reviews.some(x=>String(x.type||'').toUpperCase()===type&&Number(x.session||1)===session), tc=(v,bad)=>`<td class=\\\"${bad?'pc-time-alert':''}\\\">${esc(shortTime(v))}</td>`;",
    'frontend punch card red-state guard'
)

# 4) Add a generic helper to delete stale review rows for one user after a
# known-history correction, including rows that had already been reviewed.
time_review = Path('apps-script/60_TimeReview.gs')
text = time_review.read_text(encoding='utf-8')
marker = 'function cleanupInvalidTimeReviewsForUser_('
if marker not in text:
    text += r'''

/** Remove review rows whose type is no longer valid under the effective-dated schedule. */
function cleanupInvalidTimeReviewsForUser_(email,from,to) {
  email=normalizeEmail_(email);if(!email)return 0;
  from=validateDateKey_(from);to=validateDateKey_(to);if(to<from)return 0;
  const user=getUserByEmail_(email,false);if(!user)return 0;
  const settings=getSettings_(), stale=[];
  readTimeReviewRows_().filter(r=>r.email===email&&r.date>=from&&r.date<=to).forEach(r=>{
    const rec=findAttendanceRecord_(r.date,email);if(!rec)return;
    const flags=inferAttendanceFlags_(rec.values,user,settings,r.date);
    if(!flags.includes(String(r.type||'').toUpperCase()))stale.push(r);
  });
  if(!stale.length)return 0;
  const sh=getTimeReviewSheet_();
  stale.sort((a,b)=>b.row-a.row).forEach(r=>sh.deleteRow(r.row));
  invalidateTimeReviewRows_();
  audit_('AUTO_BATAL_SEMAKAN_WAKTU_SEJARAH',`${email} ${from}..${to}`,`${stale.length} rekod semakan dibuang kerana tidak lagi sah selepas pembetulan sejarah jadual`,'SISTEM');
  return stale.length;
}
'''
    time_review.write_text(text, encoding='utf-8')

# 5) One-time migration for the exact legacy change reported by Farhan:
# Sesi 1 Masuk was 08:30 through 12 Sep 2026, then 07:30 from 13 Sep 2026.
# It is idempotent and runs only for the owner/Farhan account while the current
# schedule still matches 07:30.
schedule = Path('apps-script/43_ScheduleHistory.gs')
text = schedule.read_text(encoding='utf-8')
marker = 'function ensureKnownLegacyScheduleMigrations_('
if marker not in text:
    text += r'''

// ---------- Known legacy schedule migrations ----------
// Before effective-dated history existed, a current-schedule repair could have
// rewritten old StatusWaktu. This one-time migration restores the known Farhan
// schedule boundary reported on 13 Sep 2026, then recalculates only the dates
// before that boundary. Future changes are handled by normal schedule history.
function ensureKnownLegacyScheduleMigrations_(user) {
  if(!user||!user.email)return false;
  const email=normalizeEmail_(user.email);
  const owner=normalizeEmail_(EK.EMAIL.OWNER_EMAIL);
  const isFarhan=email===owner||String(user.name||'').trim().toUpperCase()==='MUHAMMAD FARHAN BIN SHOFFI';
  if(!isFarhan)return false;

  const propKey='EK_MIGRATION_FARHAN_0830_TO_0730_20260913_V1_'+email.replace(/[^a-z0-9]/g,'_');
  const props=PropertiesService.getScriptProperties();
  if(props.getProperty(propKey)==='DONE')return false;

  const settings=getSettings_();
  const current=makeScheduleSnapshot_(user,settings);
  if(String((current.schedule||{}).s1In||'')!=='07:30')return false;

  const before=JSON.parse(JSON.stringify(current));
  before.schedule.s1In='08:30';
  const fromDate=getSystemStartDate_(settings);
  const changeDate='2026-09-13';
  const previousDate='2026-09-12';
  if(fromDate>previousDate)return false;

  const oldAt=new Date(`${fromDate}T00:00:00+08:00`);
  const newAt=new Date(`${changeDate}T00:00:00+08:00`);
  const oldSig=scheduleSnapshotSignature_(before), newSig=scheduleSnapshotSignature_(current);
  const history=getScheduleHistoryForUser_(email), rows=[];
  const hasOld=history.some(r=>Math.abs(Number(r.effectiveMs||0)-oldAt.getTime())<1000&&scheduleSnapshotSignature_(r.snapshot)===oldSig);
  const hasNewBoundary=history.some(r=>Math.abs(Number(r.effectiveMs||0)-newAt.getTime())<1000&&scheduleSnapshotSignature_(r.snapshot)===newSig);
  if(!hasOld)rows.push(scheduleHistoryRow_(email,before,oldAt,'SISTEM','MIGRASI_LEGASI_0830'));
  if(!hasNewBoundary)rows.push(scheduleHistoryRow_(email,current,newAt,'SISTEM','MIGRASI_LEGASI_0730'));
  if(rows.length)appendScheduleHistoryRows_(rows);

  const repaired=repairAttendanceTimingStatuses_({from:fromDate,to:previousDate,actor:'SISTEM',audit:true});
  const reviewsRemoved=cleanupInvalidTimeReviewsForUser_(email,fromDate,previousDate);
  props.setProperty(propKey,'DONE');
  audit_('MIGRASI_JADUAL_LEGASI',email,`S1 08:30 hingga ${previousDate}; S1 07:30 mulai ${changeDate}; status dikemas kini=${repaired.rowsUpdated||0}; semakan dibuang=${reviewsRemoved}`,'SISTEM');
  return {ok:true,fromDate,changeDate,repaired,reviewsRemoved};
}
'''
    schedule.write_text(text, encoding='utf-8')

print('Punch Card history sync patch applied.')
