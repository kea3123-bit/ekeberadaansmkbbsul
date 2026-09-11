from pathlib import Path


def read(path):
    return Path(path).read_text(encoding="utf-8")


def write(path, text):
    Path(path).write_text(text, encoding="utf-8")


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 match, got {count}")
    return text.replace(old, new, 1)


def replace_between(text, start, end, replacement, label):
    i = text.find(start)
    if i < 0:
        raise SystemExit(f"{label}: start marker not found")
    j = text.find(end, i)
    if j < 0:
        raise SystemExit(f"{label}: end marker not found")
    return text[:i] + replacement.rstrip() + "\n\n" + text[j:]


# 40_UsersData.gs: final-departure reference + provisional S1 break helpers.
path = "apps-script/40_UsersData.gs"
src = read(path)
src = replace_between(
    src,
    "function getPunchReferenceTime_(type,session,schedule,user,settings,dateKey,values) {",
    "\n}",
    r'''function hasSecondAttendanceSession_(schedule) {
  return !!(schedule && (schedule.allowSecondSession || schedule.s2In || schedule.s2Out));
}

function getFinalOutReference_(schedule,user,settings,dateKey,values) {
  const wbf=getThursdayWbfOutReference_(user,settings,dateKey,values);
  if(wbf)return wbf;
  return String((schedule&&(schedule.s2Out||schedule.s1Out))||'').trim();
}

function isProvisionalSession1Out_(dateKey,values,schedule,user,settings) {
  const v=padAttendanceValues_(values);
  if(!hasSecondAttendanceSession_(schedule)||v[22])return false;
  const key=dateCellToKey_(dateKey||v[0])||todayKey_();
  const today=todayKey_();
  if(key<today)return false;
  if(key>today)return true;
  const ref=getFinalOutReference_(schedule,user,settings,key,v);
  if(!ref)return true;
  return minutesNow_(new Date())<timeToMinutes_(ref);
}

function getPunchReferenceTime_(type,session,schedule,user,settings,dateKey,values) {
  if(type==='IN')return Number(session)===1?schedule.s1In:schedule.s2In;
  if(type==='OUT')return getFinalOutReference_(schedule,user,settings,dateKey,values);
  return '';
}''',
    "replace punch reference helpers",
)
write(path, src)


# 60_TimeReview.gs: derive effective flags from the final departure only.
path = "apps-script/60_TimeReview.gs"
src = read(path)
src = replace_between(
    src,
    "function inferAttendanceFlags_(values, user, settings) {",
    "function ensureTimeReviewRowsForRange_(from, to) {",
    r'''function inferAttendanceFlags_(values,user,settings,dateKey) {
  const v=padAttendanceValues_(values);
  const stored=splitAttendanceFlags_(v[34]);
  const status=String(v[14]||'').toUpperCase();
  if(status==='TIDAK HADIR')return [];

  if(!user||String(v[15]||'').toUpperCase()==='TEST') {
    const fallback=stored.slice();
    if(!fallback.length){
      if(status.includes('LEWAT'))fallback.push('LEWAT');
      if(status.includes('BALIK AWAL'))fallback.push('BALIK AWAL');
    }
    return fallback;
  }

  settings=settings||getSettings_();
  dateKey=dateCellToKey_(dateKey||v[0])||todayKey_();
  const schedule=getEffectiveSchedule_(user,settings);
  const flags=[];
  const add=flag=>{if(flag&&!flags.includes(flag))flags.push(flag);};

  // LEWAT kekal sebagai pengecualian pada mana-mana sesi.
  if(stored.includes('LEWAT')||status.includes('LEWAT'))add('LEWAT');
  if(v[4]&&schedule.s1In&&timeToMinutes_(formatTime_(v[4]))>timeToMinutes_(schedule.s1In))add('LEWAT');
  if(v[22]&&schedule.s2In&&timeToMinutes_(formatTime_(v[22]))>timeToMinutes_(schedule.s2In))add('LEWAT');

  // BALIK AWAL hanya dinilai pada pergerakan keluar TERAKHIR hari tersebut.
  // Keluar Sesi 1 dianggap keluar rehat selagi Sesi 2 masih boleh disambung.
  const usesSession2=!!v[22];
  const finalOutValue=usesSession2?v[27]:v[9];
  const provisional=!usesSession2&&isProvisionalSession1Out_(dateKey,v,schedule,user,settings);
  const finalRef=getFinalOutReference_(schedule,user,settings,dateKey,v);
  if(finalOutValue&&finalRef&&!provisional){
    const outMins=timeToMinutes_(formatTime_(finalOutValue));
    const refMins=timeToMinutes_(finalRef);
    if(Number.isFinite(outMins)&&Number.isFinite(refMins)&&outMins<refMins)add('BALIK AWAL');
  }
  return flags;
}

function effectiveAttendanceStatus_(values,user,settings,dateKey) {
  const v=padAttendanceValues_(values);
  const storedStatus=String(v[14]||'');
  if(storedStatus.toUpperCase()==='TIDAK HADIR')return 'TIDAK HADIR';
  if(!v[4])return storedStatus;
  return attendanceStatusFromFlags_(inferAttendanceFlags_(v,user,settings,dateKey));
}''',
    "replace effective timing flags",
)

src = replace_between(
    src,
    "function ensureTimeReviewRowsForRange_(from, to) {",
    "function getTimeReviewData(token, fromDate, toDate) {",
    r'''function ensureTimeReviewRowsForRange_(from,to) {
  const settings=getSettings_(),usersByEmail={};getAllUsers_().forEach(u=>usersByEmail[u.email]=u);
  const absenceRows=readAbsenceRows_();
  const existingRows=readTimeReviewRows_(),existingIds=new Set(existingRows.map(r=>r.id)),toAppend=[];
  getAttendanceValuesInDateRange_(from,to).forEach(raw=>{
    const v=padAttendanceValues_(raw),date=dateCellToKey_(v[0]),email=normalizeEmail_(v[1]),user=usersByEmail[email];
    if(!date||!user||String(v[14]||'').toUpperCase()==='TIDAK HADIR'||String(v[15]||'').toUpperCase()==='TEST')return;
    const schedule=getEffectiveSchedule_(user,settings);
    const checks=[
      {type:'LEWAT',session:1,value:v[4],ref:schedule.s1In,cmp:(a,b)=>a>b},
      {type:'LEWAT',session:2,value:v[22],ref:schedule.s2In,cmp:(a,b)=>a>b}
    ];
    const usesSession2=!!v[22];
    const finalOutValue=usesSession2?v[27]:v[9];
    const finalSession=usesSession2?2:1;
    const finalRef=getFinalOutReference_(schedule,user,settings,date,v);
    const provisional=!usesSession2&&isProvisionalSession1Out_(date,v,schedule,user,settings);
    if(finalOutValue&&finalRef&&!provisional)checks.push({type:'BALIK AWAL',session:finalSession,value:finalOutValue,ref:finalRef,cmp:(a,b)=>a<b});

    checks.forEach(x=>{
      if(!x.value||!x.ref)return;
      const recordTime=formatTime_(x.value),mins=timeToMinutes_(recordTime),refMins=timeToMinutes_(x.ref);
      if(!Number.isFinite(mins)||!Number.isFinite(refMins)||!x.cmp(mins,refMins))return;
      const id=timeReviewId_(user,date,x.type,x.session);if(existingIds.has(id))return;
      existingIds.add(id);const now=new Date();
      let reviewStatus='BELUM DIAMBIL MAKLUM',reviewedBy='',reviewerName='',reviewedAt='',comment='';
      if(x.type==='LEWAT'){
        const approvedPresence=absenceRows.find(r=>r.email===email&&r.mode==='KEBERADAAN'&&r.status==='DILULUSKAN'&&r.startDate<=date&&r.endDate>=date&&r.endTime&&mins>=timeToMinutes_(r.endTime))||null;
        if(approvedPresence){
          reviewedBy=normalizeEmail_(approvedPresence.reviewedBy||'');
          reviewerName=getReviewerNameFromEmail_(reviewedBy);
          reviewedAt=approvedPresence.reviewedAt||now;
          reviewStatus='DIAMBIL MAKLUM';
          comment=`Diambil maklum melalui Keberadaan ${approvedPresence.id}: ${approvedPresence.type}${approvedPresence.note?` — ${approvedPresence.note}`:''}`;
        }
      }
      toAppend.push([id,now,date,user.email,user.name,user.jobTitle||'',user.category,x.type,x.session,recordTime,x.ref,reviewStatus,reviewedBy,reviewerName,reviewedAt,comment]);
    });
  });
  if(toAppend.length){
    const sh=getTimeReviewSheet_();
    sh.getRange(sh.getLastRow()+1,1,toAppend.length,EK.TIME_REVIEW_HEADERS.length).setValues(toAppend);
    invalidateTimeReviewRows_();
    audit_('MIGRASI_SEMAKAN_WAKTU',`${from}..${to}`,`${toAppend.length} rekod semakan lama diwujudkan`,'SISTEM');
  }
  return toAppend.length;
}

function cleanupSupersededSession1EarlyReviews_(from,to) {
  const session2Keys=new Set();
  getAttendanceValuesInDateRange_(from,to).forEach(raw=>{
    const v=padAttendanceValues_(raw);
    if(!v[22])return;
    const date=dateCellToKey_(v[0]),email=normalizeEmail_(v[1]);
    if(date&&email)session2Keys.add(`${date}|${email}`);
  });
  if(!session2Keys.size)return 0;
  const stale=readTimeReviewRows_().filter(r=>r.type==='BALIK AWAL'&&Number(r.session||1)===1&&r.date>=from&&r.date<=to&&session2Keys.has(`${r.date}|${r.email}`)).sort((a,b)=>b.row-a.row);
  if(!stale.length)return 0;
  const sh=getTimeReviewSheet_();
  stale.forEach(r=>sh.deleteRow(r.row));
  invalidateTimeReviewRows_();
  audit_('AUTO_BATAL_BALIK_AWAL_SESI_1',`${from}..${to}`,`${stale.length} semakan Sesi 1 dibuang kerana pengguna kembali untuk Sesi 2`,'SISTEM');
  return stale.length;
}''',
    "replace time review generation",
)

src = replace_between(
    src,
    "function getTimeReviewData(token, fromDate, toDate) {",
    "function reviewTimeException(token,id,decision,comment) {",
    r'''function getTimeReviewData(token,fromDate,toDate) {
  requireSessionAdmin_(token);
  ensureMalaysiaSpreadsheetTimeZone_();
  const today=todayKey_(),settings=getSettings_(),systemStartDate=getSystemStartDate_(settings);
  let from=validateDateKey_(fromDate||today);
  const to=validateDateKey_(toDate||today);
  if(to<from)throw new Error('Tarikh akhir tidak boleh sebelum tarikh mula.');
  if(to<systemStartDate)throw new Error(`Tiada data sistem sebelum ${systemStartDate}. Ubah SYSTEM_START_DATE di sheet TETAPAN jika perlu.`);
  from=clampToSystemStart_(from,settings);
  cleanupSupersededSession1EarlyReviews_(from,to);
  ensureTimeReviewRowsForRange_(from,to);
  const rows=readTimeReviewRows_().filter(r=>r.date>=from&&r.date<=to).map(publicTimeReview_).sort((a,b)=>b.date.localeCompare(a.date)||b.createdAt.localeCompare(a.createdAt));
  return {fromDate:from,toDate:to,rows};
}''',
    "replace time review API",
)
write(path, src)


# 41_AttendanceData.gs: public payload always exposes effective timing status.
path = "apps-script/41_AttendanceData.gs"
src = read(path)
src = replace_between(
    src,
    "function publicAttendance_(rec, schedule) {",
    "function padAttendanceValues_(values) {",
    r'''function publicAttendance_(rec,schedule) {
  if(!rec)return null;
  const v=padAttendanceValues_(rec.values);
  const dateKey=dateCellToKey_(v[0]);
  const user=getUserByEmail_(normalizeEmail_(v[1]),false);
  const settings=getSettings_();
  const effectiveFlags=inferAttendanceFlags_(v,user,settings,dateKey);
  const effectiveStatus=String(v[14]||'').toUpperCase()==='TIDAK HADIR'
    ? 'TIDAK HADIR'
    : (v[4]?attendanceStatusFromFlags_(effectiveFlags):String(v[14]||''));
  return {
    date:dateKey,
    inTime:v[4]?formatTime_(v[4]):'',
    outTime:v[9]?formatTime_(v[9]):'',
    inTime2:v[22]?formatTime_(v[22]):'',
    outTime2:v[27]?formatTime_(v[27]):'',
    status:effectiveStatus,
    statusFlags:effectiveFlags,
    inDistanceM:v[7]===''?null:Number(v[7]),
    outDistanceM:v[12]===''?null:Number(v[12]),
    inDistanceM2:v[25]===''?null:Number(v[25]),
    outDistanceM2:v[30]===''?null:Number(v[30]),
    source:String(v[15]||''),
    inIp:String(v[19]||''),
    outIp:String(v[20]||''),
    inIp2:String(v[32]||''),
    outIp2:String(v[33]||''),
    ipCheck:String(v[21]||''),
    nextRecord:nextAttendanceStep_(v,schedule)
  };
}''',
    "replace public attendance",
)
write(path, src)


# 20_UserApi.gs: do not tag S1 break as early; recalc stale flags on every punch.
path = "apps-script/20_UserApi.gs"
src = read(path)
src = replace_once(
    src,
    """        v = padAttendanceValues_(v);\n        return {\n          day: Number(dateKey.slice(8, 10)), date: dateKey, status: String(v[14] || ''),\n          inTime: v[4] ? formatTime_(v[4]) : '', outTime: v[9] ? formatTime_(v[9]) : '',\n          inTime2: v[22] ? formatTime_(v[22]) : '', outTime2: v[27] ? formatTime_(v[27]) : '',\n          statusFlags: inferAttendanceFlags_(v, user, getSettings_()),\n""",
    """        v = padAttendanceValues_(v);\n        const timingFlags = inferAttendanceFlags_(v, user, getSettings_(), dateKey);\n        const effectiveStatus = String(v[14] || '').toUpperCase() === 'TIDAK HADIR'\n          ? 'TIDAK HADIR'\n          : (v[4] ? attendanceStatusFromFlags_(timingFlags) : String(v[14] || ''));\n        return {\n          day: Number(dateKey.slice(8, 10)), date: dateKey, status: effectiveStatus,\n          inTime: v[4] ? formatTime_(v[4]) : '', outTime: v[9] ? formatTime_(v[9]) : '',\n          inTime2: v[22] ? formatTime_(v[22]) : '', outTime2: v[27] ? formatTime_(v[27]) : '',\n          statusFlags: timingFlags,\n""",
    "punch card effective status",
)
src = replace_once(
    src,
    """    if (!isTestMode && refTime) {\n      const refMinutes = timeToMinutes_(refTime);\n      if (type === 'IN' && nowMinutes > refMinutes) exceptionType = 'LEWAT';\n      if (type === 'OUT' && nowMinutes < refMinutes) exceptionType = 'BALIK AWAL';\n    }\n""",
    """    const provisionalSession1Out = type === 'OUT' && session === 1 && hasSecondAttendanceSession_(schedule);\n    if (!isTestMode && refTime) {\n      const refMinutes = timeToMinutes_(refTime);\n      if (type === 'IN' && nowMinutes > refMinutes) exceptionType = 'LEWAT';\n      if (type === 'OUT' && !provisionalSession1Out && nowMinutes < refMinutes) exceptionType = 'BALIK AWAL';\n    }\n""",
    "suppress early on session 1 break",
)
src = replace_once(
    src,
    """    const flags = splitAttendanceFlags_(values[34]);\n    if (exceptionType && !flags.includes(exceptionType)) flags.push(exceptionType);\n    values[34]=joinAttendanceFlags_(flags);\n    values[14]=attendanceStatusFromFlags_(flags);\n""",
    """    const flags = inferAttendanceFlags_(values,user,settings,dateKey);\n    if (exceptionType && !flags.includes(exceptionType)) flags.push(exceptionType);\n    values[34]=joinAttendanceFlags_(flags);\n    values[14]=attendanceStatusFromFlags_(flags);\n""",
    "recalculate punch flags",
)
src = replace_once(
    src,
    """    sh.getRange(rec.row,1,1,EK.ATT_HEADERS.length).setValues([values]);\n    writeMs = Date.now() - writeStarted;\n""",
    """    sh.getRange(rec.row,1,1,EK.ATT_HEADERS.length).setValues([values]);\n    writeMs = Date.now() - writeStarted;\n    if(session===2&&type==='IN'){\n      try{cleanupSupersededSession1EarlyReviews_(dateKey,dateKey);}catch(_e){}\n    }\n""",
    "cleanup stale review after session 2 in",
)
write(path, src)


# 21_AdminApi.gs: admin edits follow the same final-departure rule.
path = "apps-script/21_AdminApi.gs"
src = read(path)
src = replace_between(
    src,
    "function adminSaveAttendance(token, payload) {",
    "function adminRepairAttendanceDuplicates(token) {",
    r'''function adminSaveAttendance(token,payload) {
  const admin=requireSessionAdmin_(token);payload=payload||{};
  const email=normalizeEmail_(payload.email),dateKey=validateDateKey_(payload.date);
  assertSystemDate_(dateKey,getSettings_(),'Tarikh rekod');
  const inTime=normalizeOptionalTime_(payload.inTime),outTime=normalizeOptionalTime_(payload.outTime),inTime2=normalizeOptionalTime_(payload.inTime2),outTime2=normalizeOptionalTime_(payload.outTime2);
  const reason=String(payload.reason||'').trim();if(!reason)throw new Error('Sebab pembetulan wajib diisi untuk audit.');
  const user=getUserByEmail_(email,false);if(!user)throw new Error('Pengguna tidak dijumpai.');
  const presenceRequest=inTime?findRelevantPresenceForDate_(email,dateKey,readAbsenceRows_()):null;
  if(outTime&&!inTime)throw new Error('Keluar Sesi 1 memerlukan Masuk Sesi 1.');
  if(inTime2&&!outTime)throw new Error('Masuk Sesi 2 hanya boleh selepas Keluar Sesi 1.');
  if(outTime2&&!inTime2)throw new Error('Keluar Sesi 2 memerlukan Masuk Sesi 2.');

  const settings=getSettings_(),schedule=getEffectiveSchedule_(user,settings),sh=getSheetOrThrow_(EK.SHEETS.ATTENDANCE),rec=findAttendanceRecord_(dateKey,email),now=new Date();
  const v=rec?padAttendanceValues_(rec.values):Array(EK.ATT_HEADERS.length).fill('');
  v[0]=dateKey;v[1]=email;v[2]=user.name;v[3]=user.category;
  v[4]=inTime?dateAndTime_(dateKey,inTime):'';v[9]=outTime?dateAndTime_(dateKey,outTime):'';
  v[22]=inTime2?dateAndTime_(dateKey,inTime2):'';v[27]=outTime2?dateAndTime_(dateKey,outTime2):'';
  v[15]='ADMIN';v[16]=admin.email;v[17]=presenceRequest?mergeAttendanceReason_(reason,presenceRequestReason_(presenceRequest,'CATATAN')):reason;v[18]=now;

  const flags=[];
  if(inTime&&schedule.s1In&&timeToMinutes_(inTime)>timeToMinutes_(schedule.s1In))flags.push('LEWAT');
  if(inTime2&&schedule.s2In&&timeToMinutes_(inTime2)>timeToMinutes_(schedule.s2In)&&!flags.includes('LEWAT'))flags.push('LEWAT');
  const finalOutTime=inTime2?outTime2:outTime;
  const finalSession=inTime2?2:1;
  const finalOutRef=getFinalOutReference_(schedule,user,settings,dateKey,v);
  if(finalOutTime&&finalOutRef&&timeToMinutes_(finalOutTime)<timeToMinutes_(finalOutRef))flags.push('BALIK AWAL');
  const status=inTime?attendanceStatusFromFlags_(flags):'TIDAK HADIR';
  v[14]=status;v[34]=joinAttendanceFlags_(flags);

  if(!rec){sh.appendRow(v);invalidateAttendanceIndex_();}else sh.getRange(rec.row,1,1,EK.ATT_HEADERS.length).setValues([v]);
  if(inTime2){try{cleanupSupersededSession1EarlyReviews_(dateKey,dateKey);}catch(_e){}}

  const exceptionSpecs=[];
  if(inTime&&schedule.s1In&&timeToMinutes_(inTime)>timeToMinutes_(schedule.s1In))exceptionSpecs.push({type:'LEWAT',session:1,recordTime:inTime,referenceTime:schedule.s1In});
  if(inTime2&&schedule.s2In&&timeToMinutes_(inTime2)>timeToMinutes_(schedule.s2In))exceptionSpecs.push({type:'LEWAT',session:2,recordTime:inTime2,referenceTime:schedule.s2In});
  if(finalOutTime&&finalOutRef&&timeToMinutes_(finalOutTime)<timeToMinutes_(finalOutRef))exceptionSpecs.push({type:'BALIK AWAL',session:finalSession,recordTime:finalOutTime,referenceTime:finalOutRef});
  exceptionSpecs.forEach(x=>{
    let rr=createTimeReviewRecord_({date:dateKey,user,type:x.type,session:x.session,recordTime:x.recordTime,referenceTime:x.referenceTime});
    if(x.type==='LEWAT'&&presenceRequest&&presenceRequest.status==='DILULUSKAN')rr=autoAcknowledgeTimeReviewFromPresence_(rr,presenceRequest,admin);
    if(rr.isNew!==false&&!rr.autoAcknowledged)notifyTimeException_(rr);
  });
  audit_('UBAH_KEHADIRAN',`${email} ${dateKey}`,`${reason}; S1=${inTime||'-'}-${outTime||'-'}; S2=${inTime2||'-'}-${outTime2||'-'}; status=${status}`,admin.email);
  return {ok:true,status};
}''',
    "replace admin attendance save",
)
write(path, src)


# 30_Reporting.gs: reports must not trust a stale stored BALIK AWAL flag.
path = "apps-script/30_Reporting.gs"
src = read(path)
src = replace_once(
    src,
    "      status = String(v[14] || attendanceStatusFromFlags_(v[34]));",
    "      status = effectiveAttendanceStatus_(v,u,settings,dateKey);",
    "daily report effective status",
)
src = replace_once(
    src,
    "      statusFlags: v ? splitAttendanceFlags_(v[34]) : [],",
    "      statusFlags: v ? inferAttendanceFlags_(v,u,settings,dateKey) : [],",
    "daily report effective flags",
)
src = replace_once(
    src,
    "      else if (v && v[4]) status = String(v[14] || attendanceStatusFromFlags_(v[34]));",
    "      else if (v && v[4]) status = effectiveAttendanceStatus_(v,u,settings,dateKey);",
    "period report effective status",
)
write(path, src)

print("Session-break status fix applied successfully.")
