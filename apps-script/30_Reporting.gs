// ---------- Reporting ----------

function buildDailyReport_(dateKey, users, settings) {
  settings = settings || getSettings_();
  if (!isOnOrAfterSystemStart_(dateKey, settings)) return [];
  const records = getAttendanceByDate_(dateKey);
  const byEmail = {};
  records.forEach(r => byEmail[r.email] = r);
  const absenceRows = readAbsenceRows_();

  const today = todayKey_();
  const nowMins = minutesNow_(new Date());
  const absentMins = timeToMinutes_(settings.ABSENT_AFTER);
  const publicHoliday = getPublicHolidayByDate_(dateKey);

  return users.map(u => {
    const rec = byEmail[u.email];
    const v = rec ? padAttendanceValues_(rec.values) : null;
    const hasPunch = !!(v && v[4]);
    const presenceRequest = !hasPunch ? findRelevantPresenceForDate_(u.email, dateKey, absenceRows) : null;
    let status;
    if (hasPunch) {
      status = effectiveAttendanceStatus_(v,u,settings,dateKey);
    } else if (publicHoliday) {
      status = 'CUTI UMUM';
    } else if (v && String(v[14] || '').toUpperCase() === 'TIDAK HADIR') {
      status = 'TIDAK HADIR';
    } else if (presenceRequest) {
      // Keberadaan aktif mengatasi ABSENT_AFTER. Status hanya bertukar
      // TIDAK HADIR selepas alert Pengurusan berjaya dan rekod fizikal ditulis.
      status = 'BELUM HADIR';
    } else if (isWorkingDay_(dateKey, settings) && (dateKey < today || (dateKey === today && nowMins >= absentMins))) {
      status = 'TIDAK HADIR';
    } else {
      status = 'BELUM HADIR';
    }

    const coveringRequest = (!v || !v[4]) ? findRelevantAbsenceForDate_(u.email, dateKey, absenceRows, 'TIDAK_HADIR') : null;
    return {
      date: dateKey,
      name: u.name,
      email: u.email,
      jobTitle: u.jobTitle || '',
      category: u.category,
      status,
      statusFlags: v ? inferAttendanceFlags_(v,u,settings,dateKey) : [],
      inTime: v && v[4] ? formatTime_(v[4]) : '',
      outTime: v && v[9] ? formatTime_(v[9]) : '',
      inTime2: v && v[22] ? formatTime_(v[22]) : '',
      outTime2: v && v[27] ? formatTime_(v[27]) : '',
      inDistanceM: v && v[7] !== '' ? Number(v[7]) : null,
      outDistanceM: v && v[12] !== '' ? Number(v[12]) : null,
      inDistanceM2: v && v[25] !== '' ? Number(v[25]) : null,
      outDistanceM2: v && v[30] !== '' ? Number(v[30]) : null,
      source: hasPunch ? String(v[15] || '') : (publicHoliday ? 'CUTI_UMUM' : (coveringRequest ? 'TIDAK_HADIR' : (presenceRequest ? 'KEBERADAAN' : ''))),
      editedBy: hasPunch ? String(v[16] || '') : (presenceRequest ? String(presenceRequest.reviewedBy || '') : ''),
      reason: hasPunch ? String(v[17] || '') : (publicHoliday ? publicHoliday.name : (coveringRequest ? `${coveringRequest.type}${coveringRequest.status === 'MENUNGGU' ? ' — MENUNGGU KELULUSAN' : ''}` : (presenceRequest ? presenceRequestReason_(presenceRequest, '') : '')))
    };
  }).sort((a, b) => {
    const rank = st => st === 'TIDAK HADIR' ? 0 : st.includes('LEWAT') || st.includes('BALIK AWAL') ? 1 : st === 'BELUM HADIR' ? 2 : 3;
    return (rank(a.status) - rank(b.status)) || a.name.localeCompare(b.name);
  });
}

function summarizeReport_(report) {
  const s = {total: report.length, hadir: 0, lewat: 0, balikAwal: 0, tidakHadir: 0, belumHadir: 0, cutiUmum: 0};
  report.forEach(r => {
    const st = String(r.status || '');
    if (st === 'TIDAK HADIR') s.tidakHadir++;
    else if (st === 'BELUM HADIR') s.belumHadir++;
    else if (st === 'CUTI UMUM') s.cutiUmum++;
    else {
      if (st.includes('LEWAT')) s.lewat++;
      if (st.includes('BALIK AWAL')) s.balikAwal++;
      if (!st.includes('LEWAT') && !st.includes('BALIK AWAL')) s.hadir++;
    }
  });
  return s;
}

function normalizeAttendancePresenceRange_(payload) {
  payload = payload || {};
  const settings = getSettings_();
  let fromDate = validateDateKey_(payload.fromDate || todayKey_());
  const toDate = validateDateKey_(payload.toDate || fromDate);
  if (toDate < fromDate) throw new Error('Tarikh akhir tidak boleh sebelum tarikh mula.');
  const systemStartDate = getSystemStartDate_(settings);
  if (toDate < systemStartDate) throw new Error(`Tiada data sistem sebelum ${systemStartDate}. Ubah SYSTEM_START_DATE di sheet TETAPAN jika perlu.`);
  fromDate = clampToSystemStart_(fromDate, settings);
  if (daysBetweenKeys_(fromDate, toDate) > 366) throw new Error('Tempoh laporan maksimum ialah 367 hari.');
  return {fromDate, toDate, type:String(payload.type || 'RANGE').toUpperCase(), systemStartDate};
}

function buildAttendancePresencePeriodReport_(fromDate, toDate) {
  const users = getAllUsers_().filter(u => u.active);
  const settings = getSettings_();
  const attendanceValues = getAttendanceValuesInDateRange_(fromDate, toDate);
  const attendanceMap = {};
  const attendanceDates = {};
  attendanceValues.forEach(raw => {
    const v = padAttendanceValues_(raw);
    const dateKey = dateCellToKey_(v[0]);
    const email = normalizeEmail_(v[1]);
    if (!dateKey || !email) return;
    attendanceMap[`${dateKey}|${email}`] = v;
    attendanceDates[dateKey] = true;
  });

  const absenceRows = readAbsenceRows_();
  const presence = absenceRows.filter(r => r.mode === 'KEBERADAAN' && r.endDate >= fromDate && r.startDate <= toDate && r.status !== 'DIBATALKAN');
  const dates = dateKeysBetween_(fromDate, toDate);
  const today = todayKey_();
  const nowMins = minutesNow_(new Date());
  const absentMins = timeToMinutes_(settings.ABSENT_AFTER);
  const detail = [];
  const summaryByEmail = {};

  users.forEach(u => summaryByEmail[u.email] = {
    name:u.name, email:u.email, jobTitle:u.jobTitle || '', category:u.category,
    expectedDays:0, normal:0, late:0, early:0, absent:0, pending:0, presence:0
  });

  presence.forEach(r => {
    const s = summaryByEmail[r.email];
    if (s) s.presence++;
  });

  dates.forEach(dateKey => {
    const working = isWorkingDay_(dateKey, settings);
    users.forEach(u => {
      const v = attendanceMap[`${dateKey}|${u.email}`] || null;
      if (!working && !v) return;
      const s = summaryByEmail[u.email];
      if (working) s.expectedDays++;
      let status = '';
      const presenceRequest = (!v || !v[4]) ? findRelevantPresenceForDate_(u.email, dateKey, absenceRows) : null;
      if (v && String(v[14] || '').toUpperCase() === 'TIDAK HADIR') status = 'TIDAK HADIR';
      else if (v && v[4]) status = effectiveAttendanceStatus_(v,u,settings,dateKey);
      else if (presenceRequest) status = 'BELUM HADIR';
      else if (working && (dateKey < today || (dateKey === today && nowMins >= absentMins))) status = 'TIDAK HADIR';
      else status = 'BELUM HADIR';

      const coveringRequest = (!v || !v[4]) ? findRelevantAbsenceForDate_(u.email, dateKey, absenceRows, 'TIDAK_HADIR') : null;
      const st = String(status || '');
      if (working || (v && v[4])) {
        if (st === 'TIDAK HADIR') s.absent++;
        else if (st === 'BELUM HADIR') s.pending++;
        else {
          if (st.includes('LEWAT')) s.late++;
          if (st.includes('BALIK AWAL')) s.early++;
          if (!st.includes('LEWAT') && !st.includes('BALIK AWAL')) s.normal++;
        }
      }
      detail.push({
        date:dateKey, name:u.name, email:u.email, jobTitle:u.jobTitle || '', category:u.category, status,
        inTime:v && v[4] ? formatTime_(v[4]) : '', outTime:v && v[9] ? formatTime_(v[9]) : '',
        inTime2:v && v[22] ? formatTime_(v[22]) : '', outTime2:v && v[27] ? formatTime_(v[27]) : '',
        source:v ? String(v[15] || '') : (coveringRequest ? 'TIDAK_HADIR' : (presenceRequest ? 'KEBERADAAN' : '')),
        reason:v ? String(v[17] || '') : (coveringRequest ? `${coveringRequest.type}${coveringRequest.status === 'MENUNGGU' ? ' — MENUNGGU KELULUSAN' : ''}` : (presenceRequest ? presenceRequestReason_(presenceRequest, '') : ''))
      });
    });
  });

  const summary = users.map(u => summaryByEmail[u.email]);
  const presenceRows = presence.sort((a,b) => a.startDate.localeCompare(b.startDate) || a.name.localeCompare(b.name)).map(r => ({
    name:r.name, email:r.email, jobTitle:r.jobTitle || '', category:r.category, type:r.type,
    startDate:r.startDate < fromDate ? fromDate : r.startDate, endDate:r.endDate > toDate ? toDate : r.endDate, startTime:r.startTime, endTime:r.endTime,
    status:r.status, note:r.note || '', reviewedBy:r.reviewedBy || ''
  }));
  return {fromDate, toDate, workingDays:dates.filter(d => isWorkingDay_(d,settings)).length, summary, detail, presence:presenceRows, attendanceValues};
}


// ---------- Attendance report templates ----------
// Layout is adapted from the two reference workbooks supplied for eKeberadaan:
// Summary Table / Abnormal Report / Punch / Daily Attendance.
const EK_REPORT_TEMPLATE_COLORS_ = Object.freeze({
  title:'#C9F5F5',
  header:'#91C6F4',
  subHeader:'#C9F5F5',
  border:'#2D9D68',
  orange:'#FFD09B',
  yellow:'#FFF2CC',
  red:'#FF2A20',
  soft:'#F7FBFF',
  white:'#FFFFFF',
  greenText:'#26985E',
  ink:'#172033'
});

function attendanceReportSchoolName_() {
  const s=getSettings_();
  return String(s.SCHOOL_NAME || 'e-Keberadaan').trim() || 'e-Keberadaan';
}

function reportPeriodLabel_(data) {
  return data.fromDate===data.toDate ? data.fromDate : data.fromDate+' hingga '+data.toDate;
}

function reportTemplateChunk_(items,size) {
  const out=[];size=Math.max(1,Number(size)||31);
  for(let i=0;i<items.length;i+=size)out.push(items.slice(i,i+size));
  return out;
}

function reportDayLabel_(dateKey) {
  const names=['Ahd','Isn','Sel','Rab','Kha','Jum','Sab'];
  const d=new Date(String(dateKey)+'T12:00:00');
  return names[d.getDay()]||'';
}

function reportShortDate_(dateKey) {
  const x=String(dateKey||'').split('-');
  return x.length===3 ? x[2]+'/'+x[1] : String(dateKey||'');
}

function attendanceReportDetailKey_(email,dateKey) {
  return normalizeEmail_(email)+'|'+String(dateKey||'');
}

function buildAttendanceAbnormalTemplateRows_(data,usersByEmail) {
  const abnormalMap={},settings=getSettings_();
  (data.attendanceValues||[]).forEach(raw=>{
    const v=padAttendanceValues_(raw),date=dateCellToKey_(v[0]),email=normalizeEmail_(v[1]),user=usersByEmail[email];
    if(!date||!email||!user||String(v[14]||'').toUpperCase()==='TIDAK HADIR'||String(v[15]||'').toUpperCase()==='TEST')return;
    const flags=inferAttendanceFlags_(v,user,settings,date);
    if(!flags.length)return;
    const checks=[];
    if(flags.includes('LEWAT')){
      if(v[4])checks.push({type:'LEWAT',session:1,value:v[4],key:'s1In'});
      if(v[22])checks.push({type:'LEWAT',session:2,value:v[22],key:'s2In'});
    }
    if(flags.includes('BALIK AWAL')){
      const usesSession2=!!v[22],value=usesSession2?v[27]:v[9],session=usesSession2?2:1;
      if(value)checks.push({type:'BALIK AWAL',session,value,key:'FINAL_OUT'});
    }
    checks.forEach(x=>{
      const ctx=getScheduleTimingContext_(user,settings,x.value);
      if(!ctx.known)return;
      const ref=x.key==='FINAL_OUT'
        ? getFinalOutReferenceFromTimingContext_(ctx,date,v)
        : String(ctx.schedule[x.key]||'').trim();
      if(!ref)return;
      const recordTime=formatTime_(x.value),actual=timeToMinutes_(recordTime),expected=timeToMinutes_(ref);
      if(!Number.isFinite(actual)||!Number.isFinite(expected))return;
      const minutes=x.type==='LEWAT'?Math.max(0,actual-expected):Math.max(0,expected-actual);
      if(minutes<=0)return;
      const key=attendanceReportDetailKey_(email,date),detail=(data.detailMap||{})[key]||{};
      if(!abnormalMap[key]){
        abnormalMap[key]={
          email,date,name:user.name||email,jobTitle:user.jobTitle||'',category:user.category||'',
          inTime:detail.inTime||'',outTime:detail.outTime||'',inTime2:detail.inTime2||'',outTime2:detail.outTime2||'',
          missingOut:detail.inTime2 ? !detail.outTime2 : (!!detail.inTime && !detail.outTime),
          lateMinutes:0,earlyMinutes:0,lateSessions:[],earlySessions:[],reason:detail.reason||''
        };
      }
      const row=abnormalMap[key];
      if(x.type==='LEWAT'){
        row.lateMinutes+=minutes;
        if(!row.lateSessions.includes(x.session))row.lateSessions.push(x.session);
      }else{
        row.earlyMinutes+=minutes;
        if(!row.earlySessions.includes(x.session))row.earlySessions.push(x.session);
      }
    });
  });
  return Object.values(abnormalMap).sort((a,b)=>a.date.localeCompare(b.date)||a.name.localeCompare(b.name));
}

function decorateAttendanceTemplateData_(data) {
  data=data||{};
  const fromDate=data.fromDate,toDate=data.toDate;
  const users=getAllUsers_().filter(u=>u.active).sort((a,b)=>String(a.name||'').localeCompare(String(b.name||'')));
  const usersByEmail={};users.forEach((u,index)=>{usersByEmail[u.email]=u;u._reportNumber=index+1;});
  const dates=dateKeysBetween_(fromDate,toDate);
  const detailMap={};
  (data.detail||[]).forEach(r=>detailMap[attendanceReportDetailKey_(r.email,r.date)]=r);

  // Report generation is read-only: derive exception minutes from attendance
  // + timestamped schedule history without creating/updating review rows.
  const abnormal=buildAttendanceAbnormalTemplateRows_(data,usersByEmail);

  const statByEmail={};
  users.forEach(u=>statByEmail[u.email]={attendedDays:0,lateCount:0,lateMinutes:0,earlyCount:0,earlyMinutes:0});
  (data.detail||[]).forEach(r=>{
    if((r.inTime||r.outTime||r.inTime2||r.outTime2)&&statByEmail[r.email])statByEmail[r.email].attendedDays++;
  });
  abnormal.forEach(r=>{
    const st=statByEmail[r.email];if(!st)return;
    if(r.lateMinutes>0||r.lateSessions.length){st.lateCount+=r.lateSessions.length||1;st.lateMinutes+=r.lateMinutes;}
    if(r.earlyMinutes>0||r.earlySessions.length){st.earlyCount+=r.earlySessions.length||1;st.earlyMinutes+=r.earlyMinutes;}
  });
  (data.summary||[]).forEach(r=>Object.assign(r,statByEmail[r.email]||{}));

  const settings=getSettings_(),holidayByDate={},workingByDate={};
  dates.forEach(dateKey=>{
    holidayByDate[dateKey]=getPublicHolidayByDate_(dateKey)||null;
    workingByDate[dateKey]=isWorkingDay_(dateKey,settings);
  });
  data.users=users;
  data.usersByEmail=usersByEmail;
  data.dates=dates;
  data.detailMap=detailMap;
  data.abnormal=abnormal;
  data.settings=settings;
  data.holidayByDate=holidayByDate;
  data.workingByDate=workingByDate;
  data.summary=(data.summary||[]).slice().sort((a,b)=>String(a.name||'').localeCompare(String(b.name||'')));
  return data;
}

function resetAttendanceTemplateSheet_(ss,name) {
  let sh=ss.getSheetByName(name);
  if(!sh)sh=ss.insertSheet(name);
  try{sh.getDataRange().breakApart();}catch(e){}
  sh.clear();
  sh.setHiddenGridlines(true);
  return sh;
}

function ensureAttendanceTemplateGrid_(sh,minRows,minCols) {
  minRows=Math.max(1,Number(minRows)||1);minCols=Math.max(1,Number(minCols)||1);
  const maxRows=sh.getMaxRows(),maxCols=sh.getMaxColumns();
  if(maxRows<minRows)sh.insertRowsAfter(maxRows,minRows-maxRows);
  if(maxCols<minCols)sh.insertColumnsAfter(maxCols,minCols-maxCols);
}

function templateBorder_(range) {
  range.setBorder(true,true,true,true,true,true,EK_REPORT_TEMPLATE_COLORS_.border,SpreadsheetApp.BorderStyle.SOLID);
  return range;
}

function styleTemplateTitle_(range) {
  range.setBackground(EK_REPORT_TEMPLATE_COLORS_.title)
    .setFontColor(EK_REPORT_TEMPLATE_COLORS_.greenText)
    .setFontWeight('bold')
    .setFontSize(18)
    .setHorizontalAlignment('center')
    .setVerticalAlignment('middle');
}

function styleTemplateHeader_(range) {
  templateBorder_(range);
  range.setBackground(EK_REPORT_TEMPLATE_COLORS_.header)
    .setFontColor(EK_REPORT_TEMPLATE_COLORS_.greenText)
    .setFontWeight('bold')
    .setHorizontalAlignment('center')
    .setVerticalAlignment('middle')
    .setWrap(true);
}

function writeAttendanceSummaryTemplate_(sh,data) {
  const c=EK_REPORT_TEMPLATE_COLORS_,school=attendanceReportSchoolName_(),lastCol=12;
  ensureAttendanceTemplateGrid_(sh,Math.max(10,5+(data.summary||[]).length),lastCol);
  sh.getRange(1,1,1,lastCol).merge();
  sh.getRange(1,1).setValue(school+' — Ringkasan Kehadiran');
  styleTemplateTitle_(sh.getRange(1,1,1,lastCol));sh.setRowHeight(1,38);

  sh.getRange(2,1).setValue('Tempoh Kehadiran:').setFontWeight('bold').setFontColor(c.greenText);
  sh.getRange(2,2,1,4).merge().setValue(reportPeriodLabel_(data)).setFontWeight('bold').setFontColor(c.greenText);
  sh.getRange(2,10,1,3).merge().setValue('Dijana: '+formatDateTime_(new Date())).setHorizontalAlignment('right');

  const merges=['A3:A4','B3:B4','C3:C4','D3:E3','F3:G3','H3:I3','J3:J4','K3:K4','L3:L4'];
  merges.forEach(a=>sh.getRange(a).merge());
  sh.getRange('A3').setValue('Bil.');
  sh.getRange('B3').setValue('Nama');
  sh.getRange('C3').setValue('Jawatan / Kategori');
  sh.getRange('D3').setValue('Kehadiran');
  sh.getRange('D4:E4').setValues([['Hari Kerja','Hari Hadir']]);
  sh.getRange('F3').setValue('Lewat');
  sh.getRange('F4:G4').setValues([['Bil.','Min.']]);
  sh.getRange('H3').setValue('Balik Awal');
  sh.getRange('H4:I4').setValues([['Bil.','Min.']]);
  sh.getRange('J3').setValue('Tidak Hadir\n(Hari)');
  sh.getRange('K3').setValue('Keberadaan\n(Rekod)');
  sh.getRange('L3').setValue('Catatan');
  styleTemplateHeader_(sh.getRange(3,1,2,lastCol));

  const rows=(data.summary||[]).map((r,i)=>[
    i+1,r.name,[r.jobTitle,r.category].filter(Boolean).join(' / '),
    r.expectedDays,Number(r.attendedDays||0),Number(r.lateCount||0),Number(r.lateMinutes||0),
    Number(r.earlyCount||0),Number(r.earlyMinutes||0),r.absent,r.presence,''
  ]);
  if(rows.length){
    const rg=sh.getRange(5,1,rows.length,lastCol);rg.setValues(rows);templateBorder_(rg);rg.setVerticalAlignment('middle');
    sh.getRange(5,12,rows.length,1).setBackground(c.orange);
  }
  sh.setFrozenRows(4);
  sh.setColumnWidth(1,48);sh.setColumnWidth(2,180);sh.setColumnWidth(3,210);
  sh.setColumnWidths(4,8,82);sh.setColumnWidth(12,200);
}

function writeAttendanceAbnormalTemplate_(sh,data) {
  const c=EK_REPORT_TEMPLATE_COLORS_,school=attendanceReportSchoolName_(),lastCol=12;
  ensureAttendanceTemplateGrid_(sh,Math.max(10,5+(data.abnormal||[]).length),lastCol);
  sh.getRange(1,1,1,lastCol).merge();sh.getRange(1,1).setValue(school+' — Laporan Lewat / Balik Awal');
  styleTemplateTitle_(sh.getRange(1,1,1,lastCol));sh.setRowHeight(1,38);
  sh.getRange(2,1).setValue('Tempoh Statistik:').setFontWeight('bold').setFontColor(c.greenText);
  sh.getRange(2,2,1,4).merge().setValue(reportPeriodLabel_(data)).setFontWeight('bold').setFontColor(c.greenText);

  ['A3:A4','B3:B4','C3:C4','D3:D4','E3:F3','G3:H3','I3:I4','J3:J4','K3:K4','L3:L4'].forEach(a=>sh.getRange(a).merge());
  sh.getRange('A3').setValue('Bil.');sh.getRange('B3').setValue('Nama');sh.getRange('C3').setValue('Jawatan / Kategori');sh.getRange('D3').setValue('Tarikh');
  sh.getRange('E3').setValue('Sesi 1');sh.getRange('E4:F4').setValues([['Masuk','Keluar']]);
  sh.getRange('G3').setValue('Sesi 2');sh.getRange('G4:H4').setValues([['Masuk','Keluar']]);
  sh.getRange('I3').setValue('Lewat\n(Min.)');sh.getRange('J3').setValue('Balik Awal\n(Min.)');sh.getRange('K3').setValue('Jumlah\n(Min.)');sh.getRange('L3').setValue('Catatan');
  styleTemplateHeader_(sh.getRange(3,1,2,lastCol));

  const rows=(data.abnormal||[]).map((r,i)=>[
    i+1,r.name,[r.jobTitle,r.category].filter(Boolean).join(' / '),r.date,
    r.inTime||'',r.outTime||'',r.inTime2||'',r.outTime2||'',
    r.lateMinutes,r.earlyMinutes,r.lateMinutes+r.earlyMinutes,
    r.reason||''
  ]);
  if(rows.length){
    const rg=sh.getRange(5,1,rows.length,lastCol);rg.setValues(rows);templateBorder_(rg);rg.setVerticalAlignment('middle');
    const bg=Array.from({length:rows.length},()=>Array(lastCol).fill(c.white));
    (data.abnormal||[]).forEach((r,i)=>{
      (r.lateSessions||[]).forEach(session=>{bg[i][session===2?6:4]=c.red;});
      (r.earlySessions||[]).forEach(session=>{bg[i][session===2?7:5]=c.red;});
      if(r.missingOut)bg[i][r.inTime2?7:5]=c.yellow;
    });
    rg.setBackgrounds(bg);
  }else{
    sh.getRange(5,1,1,lastCol).merge().setValue('Tiada rekod Lewat / Balik Awal dalam tempoh ini.').setHorizontalAlignment('center');
    templateBorder_(sh.getRange(5,1,1,lastCol));
  }
  sh.setFrozenRows(4);sh.setColumnWidth(1,48);sh.setColumnWidth(2,180);sh.setColumnWidth(3,210);sh.setColumnWidth(4,90);
  sh.setColumnWidths(5,7,82);sh.setColumnWidth(12,250);
}

function templateCellForDate_(data,user,dateKey) {
  const detail=data.detailMap[attendanceReportDetailKey_(user.email,dateKey)]||null;
  const holiday=(data.holidayByDate||{})[dateKey]||null,working=!!(data.workingByDate||{})[dateKey];
  if(!detail){
    if(holiday)return {text:'CUTI UMUM\n'+holiday.name,status:'CUTI UMUM',holiday:true};
    if(!working)return {text:'HUJUNG MINGGU',status:'HUJUNG MINGGU',holiday:true};
    return {text:'—',status:'BELUM HADIR'};
  }
  if(detail.status==='TIDAK HADIR')return {text:'TIDAK HADIR'+(detail.reason?'\n'+detail.reason:''),status:detail.status,absence:true,detail};
  const times=[detail.inTime,detail.outTime,detail.inTime2,detail.outTime2].filter(Boolean);
  const missingOut=detail.inTime2 ? !detail.outTime2 : (!!detail.inTime && !detail.outTime);
  return {text:times.length?times.join('\n'):(detail.status||'—'),status:detail.status,detail,missingOut};
}

function writeAttendancePunchTemplate_(sh,data,dates) {
  const c=EK_REPORT_TEMPLATE_COLORS_,count=Math.max(1,dates.length),school=attendanceReportSchoolName_();
  ensureAttendanceTemplateGrid_(sh,Math.max(12,3+(data.users||[]).length*4),count);
  sh.getRange(1,1,1,count).merge();sh.getRange(1,1).setValue('Laporan Perakam Waktu');
  sh.getRange(1,1,1,count).setFontWeight('bold').setFontSize(15).setHorizontalAlignment('center').setBackground(c.title).setFontColor(c.greenText);
  sh.getRange(2,1,1,count).merge();sh.getRange(2,1).setValue(school+' · '+reportPeriodLabel_({fromDate:dates[0],toDate:dates[dates.length-1]}));
  sh.getRange(2,1,1,count).setFontWeight('bold').setHorizontalAlignment('center').setBackground(c.soft);
  let row=3;
  (data.users||[]).forEach((u,index)=>{
    sh.getRange(row,1,1,count).merge().setValue('Bil:'+(index+1)+'   Nama:'+u.name+'   Jawatan:'+(u.jobTitle||'—')+'   Kategori:'+u.category);
    templateBorder_(sh.getRange(row,1,1,count));sh.getRange(row,1).setFontWeight('bold').setBackground(c.soft);
    const headers=dates.map(d=>reportShortDate_(d)+'\n'+reportDayLabel_(d));
    sh.getRange(row+1,1,1,count).setValues([headers]);styleTemplateHeader_(sh.getRange(row+1,1,1,count));
    const cells=dates.map(d=>templateCellForDate_(data,u,d));
    sh.getRange(row+2,1,1,count).setValues([cells.map(x=>x.text)]).setWrap(true).setVerticalAlignment('top').setHorizontalAlignment('center');
    templateBorder_(sh.getRange(row+2,1,1,count));
    const bgs=[cells.map(x=>x.holiday||x.absence?c.orange:(x.missingOut?c.yellow:(x.status&&(/LEWAT|BALIK AWAL/.test(x.status))?c.red:c.white)))];
    sh.getRange(row+2,1,1,count).setBackgrounds(bgs);
    sh.setRowHeight(row+2,52);
    row+=4;
  });
  sh.setFrozenRows(2);sh.setColumnWidths(1,count,68);
}

function writeAttendanceDailyTemplate_(sh,data,dates) {
  const c=EK_REPORT_TEMPLATE_COLORS_,half=16,school=attendanceReportSchoolName_();
  ensureAttendanceTemplateGrid_(sh,Math.max(24,1+(data.users||[]).length*23),16);
  let row=1;
  (data.users||[]).forEach((u,index)=>{
    const left=dates.slice(0,half),right=dates.slice(half,31);
    sh.getRange(row,1,1,3).merge().setValue('Bil:'+(index+1));
    sh.getRange(row,4,1,3).merge().setValue('Nama:'+u.name);
    sh.getRange(row,7,1,3).merge().setValue('Jawatan/Kategori:'+[u.jobTitle,u.category].filter(Boolean).join(' / '));
    sh.getRange(row,10,1,7).merge().setValue('Tempoh:'+reportPeriodLabel_({fromDate:dates[0],toDate:dates[dates.length-1]}));
    sh.getRange(row,1,1,16).setBackground(c.header).setFontWeight('bold');templateBorder_(sh.getRange(row,1,1,16));

    sh.getRange(row+1,3,1,2).merge().setValue('Sesi 1');sh.getRange(row+1,5,1,2).merge().setValue('Sesi 2');sh.getRange(row+1,7,1,2).merge().setValue('Status / Catatan');
    sh.getRange(row+1,11,1,2).merge().setValue('Sesi 1');sh.getRange(row+1,13,1,2).merge().setValue('Sesi 2');sh.getRange(row+1,15,1,2).merge().setValue('Status / Catatan');
    sh.getRange(row+1,1,1,16).setBackground(c.subHeader).setHorizontalAlignment('center');templateBorder_(sh.getRange(row+1,1,1,16));

    const hdr=['Tarikh','Hari','Masuk','Keluar','Masuk','Keluar','Status','Catatan','Tarikh','Hari','Masuk','Keluar','Masuk','Keluar','Status','Catatan'];
    sh.getRange(row+2,1,1,16).setValues([hdr]);styleTemplateHeader_(sh.getRange(row+2,1,1,16));

    const values=[],backgrounds=[];
    for(let i=0;i<half;i++){
      const pair=[left[i]||'',right[i]||''],rowVals=[],rowBg=[];
      pair.forEach((dateKey,side)=>{
        const offset=side*8;
        if(!dateKey){for(let j=0;j<8;j++){rowVals[offset+j]='';rowBg[offset+j]=c.white;}return;}
        const cell=templateCellForDate_(data,u,dateKey),d=cell.detail||{};
        rowVals[offset]=reportShortDate_(dateKey);rowVals[offset+1]=reportDayLabel_(dateKey);
        rowVals[offset+2]=d.inTime||'';rowVals[offset+3]=d.outTime||'';rowVals[offset+4]=d.inTime2||'';rowVals[offset+5]=d.outTime2||'';
        rowVals[offset+6]=cell.status||'';rowVals[offset+7]=d.reason||((cell.holiday||cell.absence)?cell.text:'');
        for(let j=0;j<8;j++)rowBg[offset+j]=(cell.holiday||cell.absence)?c.orange:c.white;
        if(cell.status&&/LEWAT/.test(cell.status)){rowBg[offset+2]=c.red;if(d.inTime2)rowBg[offset+4]=c.red;}
        if(cell.status&&/BALIK AWAL/.test(cell.status)){rowBg[offset+(d.inTime2?5:3)]=c.red;}
        if(cell.missingOut){
          // Highlight only the missing final return cell: Keluar 2 if Sesi 2
          // exists, otherwise Keluar 1.
          rowBg[offset+(d.inTime2?5:3)]=c.yellow;
        }
      });
      values.push(rowVals);backgrounds.push(rowBg);
    }
    const body=sh.getRange(row+3,1,half,16);body.setValues(values);body.setBackgrounds(backgrounds);body.setWrap(true).setVerticalAlignment('middle');templateBorder_(body);

    const sum=(data.summary||[]).find(x=>x.email===u.email)||{};
    const summaryText='Hari bekerja: '+Number(sum.expectedDays||0)+'   Hari hadir: '+Number(sum.attendedDays||0)+'   Tidak hadir: '+Number(sum.absent||0)+'   Lewat: '+Number(sum.lateCount||0)+' ('+Number(sum.lateMinutes||0)+' min)   Balik awal: '+Number(sum.earlyCount||0)+' ('+Number(sum.earlyMinutes||0)+' min)   Keberadaan: '+Number(sum.presence||0);
    sh.getRange(row+19,1,1,16).merge().setValue(summaryText);templateBorder_(sh.getRange(row+19,1,1,16));
    sh.getRange(row+20,1,1,16).merge().setValue('Petunjuk: Merah = Lewat / Balik Awal · Kuning = Tiada Waktu Balik · Jingga = Cuti / Tidak Hadir / Hujung Minggu');templateBorder_(sh.getRange(row+20,1,1,16));
    sh.getRange(row+21,1,1,16).merge().setValue('Disahkan oleh:                                      Diluluskan oleh:');templateBorder_(sh.getRange(row+21,1,1,16));
    row+=23;
  });
  sh.setColumnWidths(1,16,72);
  sh.setColumnWidth(7,95);sh.setColumnWidth(8,180);sh.setColumnWidth(15,95);sh.setColumnWidth(16,180);
}

function writeAttendanceTemplatePack_(ss,data,prefix) {
  prefix=String(prefix||'').trim();
  const name=s=>prefix?prefix+' '+s:s;
  const names=[];
  let sh=resetAttendanceTemplateSheet_(ss,name('RINGKASAN'));writeAttendanceSummaryTemplate_(sh,data);names.push(sh.getName());
  sh=resetAttendanceTemplateSheet_(ss,name('LEWAT AWAL'));writeAttendanceAbnormalTemplate_(sh,data);names.push(sh.getName());

  const chunks=reportTemplateChunk_(data.dates||[],31);
  chunks.forEach((dates,i)=>{
    const suffix=chunks.length>1?' '+String(i+1).padStart(2,'0'):'';
    let p=resetAttendanceTemplateSheet_(ss,name('PERAKAM WAKTU')+suffix);writeAttendancePunchTemplate_(p,data,dates);names.push(p.getName());
    let d=resetAttendanceTemplateSheet_(ss,name('INDIVIDU')+suffix);writeAttendanceDailyTemplate_(d,data,dates);names.push(d.getName());
  });
  return names;
}

function buildTemporaryAttendanceTemplateSpreadsheet_(data) {
  const name='eKeberadaan Laporan '+data.fromDate+' '+data.toDate;
  const ss=SpreadsheetApp.create(name);
  const first=ss.getSheets()[0];first.setName('RINGKASAN');
  writeAttendanceSummaryTemplate_(first,data);
  const abnormal=ss.insertSheet('LEWAT AWAL');writeAttendanceAbnormalTemplate_(abnormal,data);

  const dateChunks=reportTemplateChunk_(data.dates||[],31);
  let perakamPage=0,individualPage=0;

  dateChunks.forEach((dates,dateIndex)=>{
    // Keep every employee name together with their Perakam Waktu table.
    // Six compact employee blocks fit comfortably on one landscape PDF page;
    // separate sheets act as explicit page boundaries for Drive PDF export.
    const userPages=reportTemplateChunk_(data.users||[],6);
    userPages.forEach(users=>{
      perakamPage++;
      const pageData=Object.assign({},data,{users});
      const sheetName='PERAKAM '+String(perakamPage).padStart(2,'0');
      const p=ss.insertSheet(sheetName);
      writeAttendancePunchTemplate_(p,pageData,dates);
    });

    // Individual report: one employee per sheet/page. The template is only
    // 22 rows high and uses 1–16 on the left / 17–31 on the right, so it
    // remains a single printable page and can never break mid-person.
    (data.users||[]).forEach(user=>{
      individualPage++;
      const pageData=Object.assign({},data,{users:[user]});
      const sheetName='IND '+String(individualPage).padStart(3,'0');
      const d=ss.insertSheet(sheetName);
      writeAttendanceDailyTemplate_(d,pageData,dates);
    });
  });
  SpreadsheetApp.flush();
  return ss;
}


function setPdfLandscape_(body) {
  // A4 landscape in points (297 mm × 210 mm at 72 pt/in).
  // Apply modest margins so wide report tables have more usable space.
  return body
    .setPageWidth(841.89)
    .setPageHeight(595.28)
    .setMarginTop(36)
    .setMarginBottom(36)
    .setMarginLeft(36)
    .setMarginRight(36);
}

function generateAttendancePresenceReportPdf(token, payload) {
  requireSessionAdmin_(token);
  const range=normalizeAttendancePresenceRange_(payload);
  const data=decorateAttendanceTemplateData_(buildAttendancePresencePeriodReport_(range.fromDate,range.toDate));
  const fileName='Laporan_eKeberadaan_'+data.fromDate+'_'+data.toDate+'.pdf';
  const temp=buildTemporaryAttendanceTemplateSpreadsheet_(data);
  let blob;
  try{
    Utilities.sleep(700);
    blob=DriveApp.getFileById(temp.getId()).getAs(MimeType.PDF).setName(fileName);
  }finally{
    try{DriveApp.getFileById(temp.getId()).setTrashed(true);}catch(e){}
  }
  audit_('JANA_LAPORAN_TEMPLATE_PDF',reportPeriodLabel_(data),'Template=Ringkasan/LewatAwal/PerakamWaktu/Individu; pegawai='+data.users.length);
  return {fileName,mimeType:'application/pdf',base64:Utilities.base64Encode(blob.getBytes())};
}

function generateAttendancePresenceReportSheet(token, payload) {
  requireSessionAdmin_(token);
  const range=normalizeAttendancePresenceRange_(payload);
  const data=decorateAttendanceTemplateData_(buildAttendancePresencePeriodReport_(range.fromDate,range.toDate));
  const ss=getSpreadsheet_();
  const sheetNames=writeAttendanceTemplatePack_(ss,data,'LAP');
  audit_('JANA_LAPORAN_TEMPLATE_SHEET',reportPeriodLabel_(data),'Sheets='+sheetNames.join(',')+'; pegawai='+data.users.length);
  return {
    ok:true,
    sheetName:sheetNames[0]||'LAP RINGKASAN',
    sheetNames,
    fromDate:data.fromDate,
    toDate:data.toDate,
    summaryCount:data.summary.length,
    abnormalCount:data.abnormal.length
  };
}

function writeReportSheet_(dateKey, report) {
  const sh = getSheetOrThrow_(EK.SHEETS.REPORT);
  sh.clearContents();
  const summary = summarizeReport_(report);
  const headers = ['Tarikh', 'Nama', 'Jawatan', 'Emel', 'Kategori', 'Status', 'Masuk 1', 'Keluar 1', 'Masuk 2', 'Keluar 2', 'Sumber', 'Disunting Oleh', 'Sebab'];
  sh.getRange(1, 1).setValue(`LAPORAN KEBERADAAN — ${dateKey}`).setFontWeight('bold').setFontSize(14);
  sh.getRange(2, 1, 1, 6).setValues([['Jumlah', 'Hadir', 'Lewat', 'Balik Awal', 'Tidak Hadir', 'Belum Hadir']]);
  sh.getRange(3, 1, 1, 6).setValues([[summary.total, summary.hadir, summary.lewat, summary.balikAwal, summary.tidakHadir, summary.belumHadir]]);
  sh.getRange(5, 1, 1, headers.length).setValues([headers]);
  if (report.length) {
    sh.getRange(6, 1, report.length, headers.length).setValues(report.map(r => [
      r.date, r.name, r.jobTitle || '', r.email, r.category, r.status,
      r.inTime, r.outTime, r.inTime2, r.outTime2,
      r.source, r.editedBy, r.reason
    ]));
  }
  styleReportSheet_(sh, report.length);
}
