from pathlib import Path
import re

def read(path): return Path(path).read_text(encoding='utf-8')
def write(path,s): Path(path).write_text(s,encoding='utf-8')
def one(s,old,new,label):
    n=s.count(old)
    if n!=1: raise SystemExit(f'{label}: expected 1, found {n}')
    return s.replace(old,new,1)
def sub(s,pat,repl,label,flags=re.S):
    s2,n=re.subn(pat,repl,s,count=1,flags=flags)
    if n!=1: raise SystemExit(f'{label}: expected 1, found {n}')
    return s2

# 00_Core.gs: new types + settings defaults
p='apps-script/00_Core.gs'; s=read(p)
s=sub(s,r"  ABSENCE_TYPES: \[[^\n]+\],\n  PRESENCE_TYPES: \[[^\n]+\],",
"  ABSENCE_TYPES: ['CUTI REHAT KHAS', 'CUTI REHAT', 'CUTI SAKIT (AWAM)', 'CUTI SAKIT (SWASTA)', 'CUTI TANPA REKOD KELOMPOK', 'KURSUS', 'BENGKEL', 'TAKLIMAT', 'MESYUARAT', 'SEMINAR', 'AKTIVITI KOKURIKULUM', 'AKTIVITI SUKAN/PERMAINAN', 'LAIN-LAIN'],\n  PRESENCE_TYPES: ['PROGRAM DALAMAN SEKOLAH - KEBERADAAN', 'URUSAN PERIBADI (MASUK LEWAT) - KEBERADAAN', 'MESYUARAT DALAM SEKOLAH - KEBERADAAN', 'BENGKEL/KURSUS/SEMINAR (PPD)', 'BENGKEL/KURSUS/SEMINAR (JPN)', 'BENGKEL/KURSUS/SEMINAR (KPM)', 'MESYUARAT/TAKLIMAT (PPD)', 'MESYUARAT/TAKLIMAT (JPN)', 'MESYUARAT/TAKLIMAT (KPM)', 'LAIN-LAIN - KEBERADAAN'],",'types',flags=0)
s=one(s,"    DEFAULT_S2_OUT: '',\n    ABSENT_AFTER: '10:00',",
"    DEFAULT_S2_OUT: '',\n    ALLOW_OPTIONAL_SECOND_SESSION: 'TRUE',\n    THURSDAY_WBF_ENABLED: 'TRUE',\n    THURSDAY_WBF_IN_FROM: '07:30',\n    THURSDAY_WBF_IN_TO: '09:00',\n    THURSDAY_WBF_OUT_FROM: '15:00',\n    THURSDAY_WBF_OUT_TO: '16:30',\n    THURSDAY_WBF_DURATION_MINUTES: '450',\n    ABSENT_AFTER: '10:00',",'defaults')
write(p,s)

# 40_UsersData.gs: optional second session + Thursday WBF reference
p='apps-script/40_UsersData.gs'; s=read(p)
s=sub(s,r"function getEffectiveSchedule_\(user, settings\) \{.*?\n\}",'''function getEffectiveSchedule_(user, settings) {
  const s1In = user.s1In || user.lateAfter || settings.DEFAULT_S1_IN || settings.DEFAULT_LATE_AFTER;
  const s1Out = user.s1Out || user.punchOutFrom || settings.DEFAULT_S1_OUT || settings.DEFAULT_PUNCH_OUT_FROM;
  const s2In = user.s2In || settings.DEFAULT_S2_IN || '';
  const s2Out = user.s2Out || settings.DEFAULT_S2_OUT || '';
  const maxPunchIn = user.maxPunchIn || settings.DEFAULT_MAX_PUNCH_IN || '10:00';
  const allowSecondSession = String(settings.ALLOW_OPTIONAL_SECOND_SESSION || 'TRUE').toUpperCase() !== 'FALSE';
  return {s1In,s1Out,s2In,s2Out,maxPunchIn,allowSecondSession,lateAfter:s1In,punchOutFrom:s1Out};
}

function minutesToTime_(minutes) {
  minutes=Math.max(0,Math.min(1439,Math.round(Number(minutes)||0)));
  return `${String(Math.floor(minutes/60)).padStart(2,'0')}:${String(minutes%60).padStart(2,'0')}`;
}
function isThursdayWbfUser_(user) {
  return !!user && (String(user.category||'').trim().toUpperCase()==='AKP' || /\\bPENGETUA\\b/i.test(String(user.jobTitle||'')));
}
function getThursdayWbfOutReference_(user,settings,dateKey,values) {
  if(!isThursdayWbfUser_(user) || String(settings.THURSDAY_WBF_ENABLED||'TRUE').toUpperCase()==='FALSE') return '';
  if(new Date(`${dateKey}T12:00:00+08:00`).getDay()!==4) return '';
  const v=padAttendanceValues_(values||[]); if(!v[4]) return '';
  const inM=timeToMinutes_(formatTime_(v[4]));
  const inFrom=timeToMinutes_(settings.THURSDAY_WBF_IN_FROM||'07:30'), inTo=timeToMinutes_(settings.THURSDAY_WBF_IN_TO||'09:00');
  if(![inM,inFrom,inTo].every(Number.isFinite)||inM<inFrom||inM>inTo) return '';
  const expected=inM+Math.max(1,Number(settings.THURSDAY_WBF_DURATION_MINUTES||450));
  const outFrom=timeToMinutes_(settings.THURSDAY_WBF_OUT_FROM||'15:00'), outTo=timeToMinutes_(settings.THURSDAY_WBF_OUT_TO||'16:30');
  if(![expected,outFrom,outTo].every(Number.isFinite)||expected<outFrom||expected>outTo) return '';
  return minutesToTime_(expected);
}
function getPunchReferenceTime_(type,session,schedule,user,settings,dateKey,values) {
  if(type==='OUT'&&Number(session)===1){const wbf=getThursdayWbfOutReference_(user,settings,dateKey,values);if(wbf)return wbf;}
  if(type==='IN') return Number(session)===1?schedule.s1In:schedule.s2In;
  return Number(session)===1?schedule.s1Out:schedule.s2Out;
}''','schedule')
write(p,s)

# 41_AttendanceData.gs: session 2 is optional but available when enabled
p='apps-script/41_AttendanceData.gs'; s=read(p)
s=one(s,"  const hasSession2 = !!(schedule && (schedule.s2In || schedule.s2Out));","  const hasSession2 = !!(schedule && (schedule.allowSecondSession || schedule.s2In || schedule.s2Out));",'second session')
write(p,s)

# 10_Auth.gs: expose dynamic Thursday WBF reference after first punch
p='apps-script/10_Auth.gs'; s=read(p)
s=one(s,"  const effective = getEffectiveSchedule_(user, settings);\n  let locationReady = true;",
"  const effective = getEffectiveSchedule_(user, settings);\n  const displaySchedule = Object.assign({}, effective);\n  if (rec) displaySchedule.s1Out = getPunchReferenceTime_('OUT',1,effective,user,settings,today,rec.values) || effective.s1Out;\n  let locationReady = true;",'bootstrap display')
s=one(s,"    schedule: effective,","    schedule: displaySchedule,",'bootstrap schedule')
write(p,s)

# 20_UserApi.gs: card review details + 4 punch sequence + configured time windows
p='apps-script/20_UserApi.gs'; s=read(p)
s=one(s,"    r.reviewState = timeReviewStatementForCard_(dayReviews, r.statusFlags || []);\n  });",
"    r.reviewState = timeReviewStatementForCard_(dayReviews, r.statusFlags || []);\n    r.reviewItems = dayReviews.map(x => ({type:x.type,session:Number(x.session||1),reviewStatus:x.reviewStatus||'',reviewerJobTitle:getReviewerJobTitleFromEmail_(x.reviewedBy),reviewedAt:x.reviewedAt?formatDateTime_(x.reviewedAt):'',comment:x.comment||''}));\n  });",'card reviews')
s=one(s,"    const refTime = type === 'IN'\n      ? (session === 1 ? schedule.s1In : schedule.s2In)\n      : (session === 1 ? schedule.s1Out : schedule.s2Out);\n    let exceptionType = '';",
"    const refTime = getPunchReferenceTime_(type,session,schedule,user,settings,dateKey,values);\n    if (!isTestMode && type === 'IN') {\n      const latestAllowed = session === 1 ? schedule.maxPunchIn : (schedule.s2Out || '');\n      if (latestAllowed && nowMinutes > timeToMinutes_(latestAllowed)) throw new Error(`Tempoh Rekod Waktu Masuk Sesi ${session} telah tamat pada ${latestAllowed}.`);\n    }\n    let exceptionType = '';",'punch reference')
write(p,s)

# 21_AdminApi.gs: persist new settings and apply WBF to manual attendance too
p='apps-script/21_AdminApi.gs'; s=read(p)
s=one(s,"    DEFAULT_MAX_PUNCH_IN: '23:59',","    DEFAULT_MAX_PUNCH_IN: normalizeTime_(payload.defaultMaxPunchIn || currentSettings.DEFAULT_MAX_PUNCH_IN || '10:00'),",'max punch save')
s=one(s,"    DEFAULT_S2_OUT: normalizeOptionalTime_(payload.defaultS2Out),\n    ABSENT_AFTER: normalizeTime_(payload.absentAfter),",
"    DEFAULT_S2_OUT: normalizeOptionalTime_(payload.defaultS2Out),\n    ALLOW_OPTIONAL_SECOND_SESSION: String(payload.allowOptionalSecondSession || currentSettings.ALLOW_OPTIONAL_SECOND_SESSION || 'TRUE').toUpperCase() === 'FALSE' ? 'FALSE' : 'TRUE',\n    THURSDAY_WBF_ENABLED: String(payload.thursdayWbfEnabled || currentSettings.THURSDAY_WBF_ENABLED || 'TRUE').toUpperCase() === 'FALSE' ? 'FALSE' : 'TRUE',\n    THURSDAY_WBF_IN_FROM: normalizeTime_(payload.thursdayWbfInFrom || currentSettings.THURSDAY_WBF_IN_FROM || '07:30'),\n    THURSDAY_WBF_IN_TO: normalizeTime_(payload.thursdayWbfInTo || currentSettings.THURSDAY_WBF_IN_TO || '09:00'),\n    THURSDAY_WBF_OUT_FROM: normalizeTime_(payload.thursdayWbfOutFrom || currentSettings.THURSDAY_WBF_OUT_FROM || '15:00'),\n    THURSDAY_WBF_OUT_TO: normalizeTime_(payload.thursdayWbfOutTo || currentSettings.THURSDAY_WBF_OUT_TO || '16:30'),\n    THURSDAY_WBF_DURATION_MINUTES: String(Math.max(1,Math.min(1440,Number(payload.thursdayWbfDurationMinutes || currentSettings.THURSDAY_WBF_DURATION_MINUTES || 450)))),\n    ABSENT_AFTER: normalizeTime_(payload.absentAfter),",'settings save')
s=one(s,"  if (next.DEFAULT_S2_OUT && !next.DEFAULT_S2_IN) throw new Error('Tetapkan Sesi 2 Masuk sebelum Sesi 2 Keluar.');",
"  if (next.DEFAULT_S2_OUT && !next.DEFAULT_S2_IN) throw new Error('Tetapkan Sesi 2 Masuk sebelum Sesi 2 Keluar.');\n  if (timeToMinutes_(next.THURSDAY_WBF_IN_TO) <= timeToMinutes_(next.THURSDAY_WBF_IN_FROM)) throw new Error('Julat WBF Khamis: waktu masuk akhir mesti selepas waktu masuk mula.');\n  if (timeToMinutes_(next.THURSDAY_WBF_OUT_TO) <= timeToMinutes_(next.THURSDAY_WBF_OUT_FROM)) throw new Error('Julat WBF Khamis: waktu pulang akhir mesti selepas waktu pulang mula.');",'WBF validation')
write(p,s)

# 42_Settings.gs: return new settings to frontend
p='apps-script/42_Settings.gs'; s=read(p)
s=one(s,"    defaultS2Out: s.DEFAULT_S2_OUT || '',\n    absentAfter: s.ABSENT_AFTER,",
"    defaultS2Out: s.DEFAULT_S2_OUT || '',\n    allowOptionalSecondSession: String(s.ALLOW_OPTIONAL_SECOND_SESSION || 'TRUE').toUpperCase() !== 'FALSE' ? 'TRUE' : 'FALSE',\n    thursdayWbfEnabled: String(s.THURSDAY_WBF_ENABLED || 'TRUE').toUpperCase() !== 'FALSE' ? 'TRUE' : 'FALSE',\n    thursdayWbfInFrom: s.THURSDAY_WBF_IN_FROM || '07:30',\n    thursdayWbfInTo: s.THURSDAY_WBF_IN_TO || '09:00',\n    thursdayWbfOutFrom: s.THURSDAY_WBF_OUT_FROM || '15:00',\n    thursdayWbfOutTo: s.THURSDAY_WBF_OUT_TO || '16:30',\n    thursdayWbfDurationMinutes: Number(s.THURSDAY_WBF_DURATION_MINUTES || 450),\n    absentAfter: s.ABSENT_AFTER,",'public settings')
write(p,s)

# 60_TimeReview.gs: no reviewer name/email in UI DTO; use job-title tag, note, timestamp
p='apps-script/60_TimeReview.gs'; s=read(p)
marker="function publicTimeReview_(r) {\n"
if marker not in s: raise SystemExit('publicTimeReview marker missing')
s=s.replace(marker,"function getReviewerJobTitleFromEmail_(email) {\n  const em=normalizeEmail_(email), u=em?getUserByEmail_(em,false):null;\n  return u?String(u.jobTitle||(u.isAdmin?'Pentadbir Sistem':u.category||'')).trim():'';\n}\n\n"+marker,1)
s=sub(s,r"function publicTimeReview_\(r\) \{\n  return \{.*?\n\}",'''function publicTimeReview_(r) {
  return {id:r.id,date:r.date,email:r.email,name:r.name,jobTitle:r.jobTitle||'',category:r.category,type:r.type,session:r.session,recordTime:r.recordTime,referenceTime:r.referenceTime,
    reviewStatus:r.reviewStatus||'BELUM DIAMBIL MAKLUM',reviewerJobTitle:getReviewerJobTitleFromEmail_(r.reviewedBy),reviewedAt:r.reviewedAt?formatDateTime_(r.reviewedAt):'',comment:r.comment||'',createdAt:r.createdAt?formatDateTime_(r.createdAt):''};
}''','time review DTO')
s=sub(s,r"function timeReviewStatementForCard_\(reviews, flags\) \{.*?\n\}",'''function timeReviewStatementForCard_(reviews, flags) {
  flags=Array.isArray(flags)?flags:splitAttendanceFlags_(flags); if(!flags.length)return '';
  const relevant=(reviews||[]).filter(r=>flags.includes(String(r.type||'').toUpperCase()));
  const statement=r=>[r.reviewStatus||'',getReviewerJobTitleFromEmail_(r.reviewedBy)||'Pentadbir Sistem',r.comment||'',r.reviewedAt?formatDateTime_(r.reviewedAt):''].filter(Boolean).join(' · ');
  if(relevant.some(r=>r.reviewStatus==='DITOLAK')) return statement(relevant.find(r=>r.reviewStatus==='DITOLAK'));
  if(relevant.length&&relevant.every(r=>r.reviewStatus==='DIAMBIL MAKLUM')) return relevant.map(statement).join(' | ');
  return 'BELUM DIAMBIL MAKLUM';
}''','card statement')
s=one(s,"  return {ok:true,status:decision,reviewerName:admin.name,reviewedAt:formatDateTime_(now)};","  return {ok:true,status:decision,reviewerJobTitle:admin.jobTitle||'Pentadbir Sistem',reviewedAt:formatDateTime_(now)};",'review response')
s=one(s,"    ['Tarikh','Nama','Jawatan','Jenis','Sesi','Rekod','Rujukan','Status Semakan','Pelulus','Ulasan'],\n    rows.map(r=>[r.date,r.name,r.jobTitle,r.type,r.session,r.recordTime,r.referenceTime,r.reviewStatus,r.reviewerName||'',r.comment||'']),",
"    ['Tarikh','Nama','Jawatan','Jenis','Sesi','Rekod','Rujukan','Status Semakan','Jawatan Pelulus','Ulasan'],\n    rows.map(r=>[r.date,r.name,r.jobTitle,r.type,r.session,r.recordTime,r.referenceTime,r.reviewStatus,r.reviewerJobTitle||'',r.comment||'']),",'time PDF')
# Historical inference/backfill must honor Thursday WBF for S1 OUT
s=one(s,"    {type:'BALIK AWAL', value:v[9], ref:schedule.s1Out, cmp:(a,b)=>a<b},","    {type:'BALIK AWAL', value:v[9], ref:getPunchReferenceTime_('OUT',1,schedule,user,settings,dateCellToKey_(v[0]),v), cmp:(a,b)=>a<b},",'infer WBF')
s=one(s,"      {type:'BALIK AWAL',session:1,value:v[9],ref:schedule.s1Out,cmp:(a,b)=>a<b},","      {type:'BALIK AWAL',session:1,value:v[9],ref:getPunchReferenceTime_('OUT',1,schedule,user,settings,date,v),cmp:(a,b)=>a<b},",'backfill WBF')
write(p,s)

# 61_Absence.gs: management review exposes role tag rather than reviewer identity
p='apps-script/61_Absence.gs'; s=read(p)
s=one(s,"function publicAbsenceManagement_(r){return {id:r.id,submittedAt:r.submittedAt?formatDateTime_(r.submittedAt):'',email:r.email,name:r.name,jobTitle:r.jobTitle||'',category:r.category,type:r.type,mode:r.mode,startDate:r.startDate,endDate:r.endDate,startTime:r.startTime,endTime:r.endTime,note:r.note,status:r.status,reviewedBy:r.reviewedBy,reviewedAt:r.reviewedAt?formatDateTime_(r.reviewedAt):'',comment:r.comment};}",
"function publicAbsenceManagement_(r){return {id:r.id,submittedAt:r.submittedAt?formatDateTime_(r.submittedAt):'',email:r.email,name:r.name,jobTitle:r.jobTitle||'',category:r.category,type:r.type,mode:r.mode,startDate:r.startDate,endDate:r.endDate,startTime:r.startTime,endTime:r.endTime,note:r.note,status:r.status,reviewerJobTitle:getReviewerJobTitleFromEmail_(r.reviewedBy),reviewedAt:r.reviewedAt?formatDateTime_(r.reviewedAt):'',comment:r.comment};}",'absence DTO')
# synthetic rows may use reviewedBy; replace when exact helper exists
s=s.replace("reviewedBy:'',reviewedAt:'',comment:'',synthetic:true","reviewerJobTitle:'',reviewedAt:'',comment:'',synthetic:true")
write(p,s)
