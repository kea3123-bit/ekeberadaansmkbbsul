from pathlib import Path
import re

P=Path('Code.gs')
s=P.read_text(encoding='utf-8')

def one(old,new,label):
    global s
    n=s.count(old)
    if n!=1: raise SystemExit(f'{label}: expected 1, found {n}')
    s=s.replace(old,new,1)

def sub(pattern,repl,label,flags=re.S):
    global s
    s2,n=re.subn(pattern,repl,s,count=1,flags=flags)
    if n!=1: raise SystemExit(f'{label}: expected 1, found {n}')
    s=s2

sub(r"  ABSENCE_TYPES: \[[^\n]+\],\n  PRESENCE_TYPES: \[[^\n]+\],",
"  ABSENCE_TYPES: ['CUTI REHAT KHAS', 'CUTI REHAT', 'CUTI SAKIT (AWAM)', 'CUTI SAKIT (SWASTA)', 'CUTI TANPA REKOD KELOMPOK', 'KURSUS', 'BENGKEL', 'TAKLIMAT', 'MESYUARAT', 'SEMINAR', 'AKTIVITI KOKURIKULUM', 'AKTIVITI SUKAN/PERMAINAN', 'LAIN-LAIN'],\n  PRESENCE_TYPES: ['PROGRAM DALAMAN SEKOLAH - KEBERADAAN', 'URUSAN PERIBADI (MASUK LEWAT) - KEBERADAAN', 'MESYUARAT DALAM SEKOLAH - KEBERADAAN', 'BENGKEL/KURSUS/SEMINAR (PPD)', 'BENGKEL/KURSUS/SEMINAR (JPN)', 'BENGKEL/KURSUS/SEMINAR (KPM)', 'MESYUARAT/TAKLIMAT (PPD)', 'MESYUARAT/TAKLIMAT (JPN)', 'MESYUARAT/TAKLIMAT (KPM)', 'LAIN-LAIN - KEBERADAAN'],",
'absence types',flags=0)

one("    DEFAULT_S2_OUT: '',\n    ABSENT_AFTER: '10:00',",
"    DEFAULT_S2_OUT: '',\n    ALLOW_OPTIONAL_SECOND_SESSION: 'TRUE',\n    THURSDAY_WBF_ENABLED: 'TRUE',\n    THURSDAY_WBF_IN_FROM: '07:30',\n    THURSDAY_WBF_IN_TO: '09:00',\n    THURSDAY_WBF_OUT_FROM: '15:00',\n    THURSDAY_WBF_OUT_TO: '16:30',\n    THURSDAY_WBF_DURATION_MINUTES: '450',\n    ABSENT_AFTER: '10:00',",'default settings')

sub(r"function getEffectiveSchedule_\(user, settings\) \{.*?\n\}\n\n// ---------- Attendance data ----------",'''function getEffectiveSchedule_(user, settings) {
  const s1In = user.s1In || user.lateAfter || settings.DEFAULT_S1_IN || settings.DEFAULT_LATE_AFTER;
  const s1Out = user.s1Out || user.punchOutFrom || settings.DEFAULT_S1_OUT || settings.DEFAULT_PUNCH_OUT_FROM;
  const s2In = user.s2In || settings.DEFAULT_S2_IN || '';
  const s2Out = user.s2Out || settings.DEFAULT_S2_OUT || '';
  const maxPunchIn = user.maxPunchIn || settings.DEFAULT_MAX_PUNCH_IN || '10:00';
  const allowSecondSession = String(settings.ALLOW_OPTIONAL_SECOND_SESSION || 'TRUE').toUpperCase() !== 'FALSE';
  return {s1In,s1Out,s2In,s2Out,maxPunchIn,allowSecondSession,lateAfter:s1In,punchOutFrom:s1Out};
}

function minutesToTime_(minutes) {
  minutes = Math.max(0, Math.min(1439, Math.round(Number(minutes) || 0)));
  return `${String(Math.floor(minutes / 60)).padStart(2,'0')}:${String(minutes % 60).padStart(2,'0')}`;
}
function isThursdayWbfUser_(user) {
  return !!user && (String(user.category||'').trim().toUpperCase()==='AKP' || /\\bPENGETUA\\b/i.test(String(user.jobTitle||'')));
}
function getThursdayWbfOutReference_(user,settings,dateKey,values) {
  if (!isThursdayWbfUser_(user) || String(settings.THURSDAY_WBF_ENABLED||'TRUE').toUpperCase()==='FALSE') return '';
  if (new Date(`${dateKey}T12:00:00+08:00`).getDay() !== 4) return '';
  const v=padAttendanceValues_(values||[]); if(!v[4]) return '';
  const inM=timeToMinutes_(formatTime_(v[4]));
  const from=timeToMinutes_(settings.THURSDAY_WBF_IN_FROM||'07:30'), to=timeToMinutes_(settings.THURSDAY_WBF_IN_TO||'09:00');
  if(![inM,from,to].every(Number.isFinite)||inM<from||inM>to) return '';
  const expected=inM+Math.max(1,Number(settings.THURSDAY_WBF_DURATION_MINUTES||450));
  const outFrom=timeToMinutes_(settings.THURSDAY_WBF_OUT_FROM||'15:00'), outTo=timeToMinutes_(settings.THURSDAY_WBF_OUT_TO||'16:30');
  if(![expected,outFrom,outTo].every(Number.isFinite)||expected<outFrom||expected>outTo) return '';
  return minutesToTime_(expected);
}
function getPunchReferenceTime_(type,session,schedule,user,settings,dateKey,values) {
  if(type==='OUT'&&Number(session)===1){const wbf=getThursdayWbfOutReference_(user,settings,dateKey,values);if(wbf)return wbf;}
  if(type==='IN')return Number(session)===1?schedule.s1In:schedule.s2In;
  return Number(session)===1?schedule.s1Out:schedule.s2Out;
}

// ---------- Attendance data ----------''','effective schedule')

sub(r"function nextAttendanceStep_\(values, schedule\) \{.*?\n\}",'''function nextAttendanceStep_(values, schedule) {
  const v=padAttendanceValues_(values);
  if(!v[4]) return {type:'IN',session:1,complete:false};
  if(!v[9]) return {type:'OUT',session:1,complete:false};
  const hasSession2=!!(schedule&&(schedule.allowSecondSession||schedule.s2In||schedule.s2Out));
  if(!hasSession2) return {type:'',session:1,complete:true};
  if(!v[22]) return {type:'IN',session:2,complete:false,optional:true};
  if(!v[27]) return {type:'OUT',session:2,complete:false};
  return {type:'',session:2,complete:true};
}''','next step')

one("  const effective = getEffectiveSchedule_(user, settings);\n  let locationReady = true;",
"  const effective = getEffectiveSchedule_(user, settings);\n  const displaySchedule = Object.assign({}, effective);\n  if (rec) displaySchedule.s1Out = getPunchReferenceTime_('OUT',1,effective,user,settings,today,rec.values) || effective.s1Out;\n  let locationReady = true;",'bootstrap display')
one("    schedule: effective,","    schedule: displaySchedule,",'bootstrap schedule')

one("    const refTime = type === 'IN'\n      ? (session === 1 ? schedule.s1In : schedule.s2In)\n      : (session === 1 ? schedule.s1Out : schedule.s2Out);\n    let exceptionType = '';",
"    const refTime = getPunchReferenceTime_(type,session,schedule,user,settings,dateKey,values);\n    if (!isTestMode && type === 'IN') {\n      const latestAllowed = session === 1 ? schedule.maxPunchIn : (schedule.s2Out || '');\n      if (latestAllowed && nowMinutes > timeToMinutes_(latestAllowed)) throw new Error(`Tempoh Rekod Waktu Masuk Sesi ${session} telah tamat pada ${latestAllowed}.`);\n    }\n    let exceptionType = '';",'punch ref')

one("    DEFAULT_MAX_PUNCH_IN: '23:59',","    DEFAULT_MAX_PUNCH_IN: normalizeTime_(payload.defaultMaxPunchIn || currentSettings.DEFAULT_MAX_PUNCH_IN || '10:00'),",'max punch in save')
one("    DEFAULT_S2_OUT: normalizeOptionalTime_(payload.defaultS2Out),\n    ABSENT_AFTER: normalizeTime_(payload.absentAfter),",
"    DEFAULT_S2_OUT: normalizeOptionalTime_(payload.defaultS2Out),\n    ALLOW_OPTIONAL_SECOND_SESSION: String(payload.allowOptionalSecondSession || currentSettings.ALLOW_OPTIONAL_SECOND_SESSION || 'TRUE').toUpperCase() === 'FALSE' ? 'FALSE' : 'TRUE',\n    THURSDAY_WBF_ENABLED: String(payload.thursdayWbfEnabled || currentSettings.THURSDAY_WBF_ENABLED || 'TRUE').toUpperCase() === 'FALSE' ? 'FALSE' : 'TRUE',\n    THURSDAY_WBF_IN_FROM: normalizeTime_(payload.thursdayWbfInFrom || currentSettings.THURSDAY_WBF_IN_FROM || '07:30'),\n    THURSDAY_WBF_IN_TO: normalizeTime_(payload.thursdayWbfInTo || currentSettings.THURSDAY_WBF_IN_TO || '09:00'),\n    THURSDAY_WBF_OUT_FROM: normalizeTime_(payload.thursdayWbfOutFrom || currentSettings.THURSDAY_WBF_OUT_FROM || '15:00'),\n    THURSDAY_WBF_OUT_TO: normalizeTime_(payload.thursdayWbfOutTo || currentSettings.THURSDAY_WBF_OUT_TO || '16:30'),\n    THURSDAY_WBF_DURATION_MINUTES: String(Math.max(1, Math.min(1440, Number(payload.thursdayWbfDurationMinutes || currentSettings.THURSDAY_WBF_DURATION_MINUTES || 450)))),\n    ABSENT_AFTER: normalizeTime_(payload.absentAfter),",'WBF save')
one("  if (next.DEFAULT_S2_OUT && !next.DEFAULT_S2_IN) throw new Error('Tetapkan Sesi 2 Masuk sebelum Sesi 2 Keluar.');",
"  if (next.DEFAULT_S2_OUT && !next.DEFAULT_S2_IN) throw new Error('Tetapkan Sesi 2 Masuk sebelum Sesi 2 Keluar.');\n  if (timeToMinutes_(next.THURSDAY_WBF_IN_TO) <= timeToMinutes_(next.THURSDAY_WBF_IN_FROM)) throw new Error('Julat WBF Khamis: waktu masuk akhir mesti selepas waktu masuk mula.');\n  if (timeToMinutes_(next.THURSDAY_WBF_OUT_TO) <= timeToMinutes_(next.THURSDAY_WBF_OUT_FROM)) throw new Error('Julat WBF Khamis: waktu pulang akhir mesti selepas waktu pulang mula.');",'WBF validation')
one("    defaultS2Out: s.DEFAULT_S2_OUT || '',\n    absentAfter: s.ABSENT_AFTER,",
"    defaultS2Out: s.DEFAULT_S2_OUT || '',\n    allowOptionalSecondSession: String(s.ALLOW_OPTIONAL_SECOND_SESSION || 'TRUE').toUpperCase() !== 'FALSE' ? 'TRUE' : 'FALSE',\n    thursdayWbfEnabled: String(s.THURSDAY_WBF_ENABLED || 'TRUE').toUpperCase() !== 'FALSE' ? 'TRUE' : 'FALSE',\n    thursdayWbfInFrom: s.THURSDAY_WBF_IN_FROM || '07:30',\n    thursdayWbfInTo: s.THURSDAY_WBF_IN_TO || '09:00',\n    thursdayWbfOutFrom: s.THURSDAY_WBF_OUT_FROM || '15:00',\n    thursdayWbfOutTo: s.THURSDAY_WBF_OUT_TO || '16:30',\n    thursdayWbfDurationMinutes: Number(s.THURSDAY_WBF_DURATION_MINUTES || 450),\n    absentAfter: s.ABSENT_AFTER,",'public settings')

marker="function getReviewerNameFromEmail_(email) {\n"
if marker not in s: raise SystemExit('reviewer marker missing')
s=s.replace(marker,"function getReviewerJobTitleFromEmail_(email) {\n  const em=normalizeEmail_(email), u=em?getUserByEmail_(em,false):null;\n  return u?String(u.jobTitle||(u.isAdmin?'Pentadbir Sistem':u.category||'')).trim():'';\n}\n\n"+marker,1)

one("function publicAbsenceManagement_(r){return {id:r.id,submittedAt:r.submittedAt?formatDateTime_(r.submittedAt):'',email:r.email,name:r.name,jobTitle:r.jobTitle||'',category:r.category,type:r.type,mode:r.mode,startDate:r.startDate,endDate:r.endDate,startTime:r.startTime,endTime:r.endTime,note:r.note,status:r.status,reviewedBy:r.reviewedBy,reviewedAt:r.reviewedAt?formatDateTime_(r.reviewedAt):'',comment:r.comment};}",
"function publicAbsenceManagement_(r){return {id:r.id,submittedAt:r.submittedAt?formatDateTime_(r.submittedAt):'',email:r.email,name:r.name,jobTitle:r.jobTitle||'',category:r.category,type:r.type,mode:r.mode,startDate:r.startDate,endDate:r.endDate,startTime:r.startTime,endTime:r.endTime,note:r.note,status:r.status,reviewerJobTitle:getReviewerJobTitleFromEmail_(r.reviewedBy),reviewedAt:r.reviewedAt?formatDateTime_(r.reviewedAt):'',comment:r.comment};}",'absence reviewer DTO')
one("function publicUnexplainedAbsenceManagement_(r) {\n  return {id:r.id,submittedAt:r.startDate,email:r.email,name:r.name,jobTitle:r.jobTitle||'',category:r.category,mode:'TIDAK_HADIR',type:'TIADA PENJELASAN',startDate:r.startDate,endDate:r.endDate,note:r.note,status:'TIDAK MOHON',reviewedBy:'',reviewedAt:'',comment:'',synthetic:true};\n}",
"function publicUnexplainedAbsenceManagement_(r) {\n  return {id:r.id,submittedAt:r.startDate,email:r.email,name:r.name,jobTitle:r.jobTitle||'',category:r.category,mode:'TIDAK_HADIR',type:'TIADA PENJELASAN',startDate:r.startDate,endDate:r.endDate,note:r.note,status:'TIDAK MOHON',reviewerJobTitle:'',reviewedAt:'',comment:'',synthetic:true};\n}",'unexplained DTO')
sub(r"function publicTimeReview_\(r\) \{\n  return \{.*?\n\}",'''function publicTimeReview_(r) {
  return {id:r.id,date:r.date,email:r.email,name:r.name,jobTitle:r.jobTitle||'',category:r.category,type:r.type,session:r.session,recordTime:r.recordTime,referenceTime:r.referenceTime,
    reviewStatus:r.reviewStatus||'BELUM DIAMBIL MAKLUM',reviewerJobTitle:getReviewerJobTitleFromEmail_(r.reviewedBy),reviewedAt:r.reviewedAt?formatDateTime_(r.reviewedAt):'',comment:r.comment||'',createdAt:r.createdAt?formatDateTime_(r.createdAt):''};
}''','time review DTO')
sub(r"function timeReviewStatementForCard_\(reviews, flags\) \{.*?\n\}",'''function timeReviewStatementForCard_(reviews, flags) {
  flags=Array.isArray(flags)?flags:splitAttendanceFlags_(flags); if(!flags.length)return '';
  const relevant=(reviews||[]).filter(r=>flags.includes(String(r.type||'').toUpperCase()));
  const statement=r=>[r.reviewStatus||'',getReviewerJobTitleFromEmail_(r.reviewedBy)||'Pentadbir Sistem',r.comment||'',r.reviewedAt?formatDateTime_(r.reviewedAt):''].filter(Boolean).join(' · ');
  if(relevant.some(r=>r.reviewStatus==='DITOLAK'))return statement(relevant.find(r=>r.reviewStatus==='DITOLAK'));
  if(relevant.length&&relevant.every(r=>r.reviewStatus==='DIAMBIL MAKLUM'))return relevant.map(statement).join(' | ');
  return 'BELUM DIAMBIL MAKLUM';
}''','card statement')
one("  records.forEach(r => {\n    const dayReviews = reviewRows.filter(x => x.date === r.date);\n    r.reviewState = timeReviewStatementForCard_(dayReviews, r.statusFlags || []);\n  });",
"  records.forEach(r => {\n    const dayReviews = reviewRows.filter(x => x.date === r.date);\n    r.reviewState = timeReviewStatementForCard_(dayReviews, r.statusFlags || []);\n    r.reviewItems = dayReviews.map(x => ({type:x.type,session:Number(x.session||1),reviewStatus:x.reviewStatus||'',reviewerJobTitle:getReviewerJobTitleFromEmail_(x.reviewedBy),reviewedAt:x.reviewedAt?formatDateTime_(x.reviewedAt):'',comment:x.comment||''}));\n  });",'card review items')
one("    ['Nama','Jawatan','Kategori','Mod','Jenis','Tarikh','Masa','Status','Disemak Oleh','Ulasan'],\n    rows.map(r=>[r.name,r.jobTitle||'',r.category,r.mode==='KEBERADAAN'?'Keberadaan':'Tidak Hadir',r.type,r.startDate===r.endDate?r.startDate:`${r.startDate} - ${r.endDate}`,r.mode==='KEBERADAAN'?`${r.startTime} - ${r.endTime}`:'—',r.status,r.reviewedBy||'',r.comment||'']),",
"    ['Nama','Jawatan','Kategori','Mod','Jenis','Tarikh','Masa','Status','Jawatan Pelulus','Ulasan'],\n    rows.map(r=>[r.name,r.jobTitle||'',r.category,r.mode==='KEBERADAAN'?'Keberadaan':'Tidak Hadir',r.type,r.startDate===r.endDate?r.startDate:`${r.startDate} - ${r.endDate}`,r.mode==='KEBERADAAN'?`${r.startTime} - ${r.endTime}`:'—',r.status,r.reviewerJobTitle||'',r.comment||'']),",'absence PDF')
one("    ['Tarikh','Nama','Jawatan','Jenis','Sesi','Rekod','Rujukan','Status Semakan','Pelulus','Ulasan'],\n    rows.map(r=>[r.date,r.name,r.jobTitle,r.type,r.session,r.recordTime,r.referenceTime,r.reviewStatus,r.reviewerName||'',r.comment||'']),",
"    ['Tarikh','Nama','Jawatan','Jenis','Sesi','Rekod','Rujukan','Status Semakan','Jawatan Pelulus','Ulasan'],\n    rows.map(r=>[r.date,r.name,r.jobTitle,r.type,r.session,r.recordTime,r.referenceTime,r.reviewStatus,r.reviewerJobTitle||'',r.comment||'']),",'time review PDF')

P.write_text(s,encoding='utf-8')
