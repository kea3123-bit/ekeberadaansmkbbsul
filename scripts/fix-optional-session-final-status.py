from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    src = p.read_text()
    if old not in src:
        raise SystemExit(f'pattern not found in {path}: {old[:120]!r}')
    if src.count(old) != 1:
        raise SystemExit(f'pattern occurs {src.count(old)} times in {path}')
    p.write_text(src.replace(old, new, 1))

# 1) Make the optional-session semantics explicit in the punch state machine.
replace_once(
    'apps-script/41_AttendanceData.gs',
    """  // Sesi 2 hanya diwajibkan apabila sekurang-kurangnya satu waktu Sesi 2\n  // ditetapkan. Ini membolehkan sekolah menggunakan sama ada 2 atau 4 rakaman\n  // sehari tanpa mengubah struktur Kad Perakam Waktu.\n  const hasSession2 = !!(schedule && (schedule.allowSecondSession || schedule.s2In || schedule.s2Out));\n""",
    """  // Sesi 2 boleh menjadi sambungan OPTIONAL walaupun waktu Sesi 2 tidak\n  // dikonfigurasi. Ini penting untuk pegawai yang pada sesetengah hari keluar\n  // rehat dan masuk semula, tetapi pada hari lain hanya menggunakan Sesi 1.\n  // Jika Sesi 2 tidak digunakan, pengguna tidak perlu membuat apa-apa lagi.\n  const hasSession2 = !!(schedule && (schedule.allowSecondSession || schedule.s2In || schedule.s2Out));\n"""
)

# 2) Document the final-departure rule in the schedule helper.
replace_once(
    'apps-script/40_UsersData.gs',
    """function hasSecondAttendanceSession_(schedule) {\n  return !!(schedule && (schedule.allowSecondSession || schedule.s2In || schedule.s2Out));\n}\n\nfunction getFinalOutReference_(schedule,user,settings,dateKey,values) {\n  const wbf=getThursdayWbfOutReference_(user,settings,dateKey,values);\n  if(wbf)return wbf;\n  return String((schedule&&(schedule.s2Out||schedule.s1Out))||'').trim();\n}\n""",
    """function hasSecondAttendanceSession_(schedule) {\n  // TRUE means the user MAY continue with Sesi 2; it does not mean Sesi 2 is\n  // compulsory on every day. Blank s2In/s2Out therefore remains valid for an\n  // optional break/return workflow.\n  return !!(schedule && (schedule.allowSecondSession || schedule.s2In || schedule.s2Out));\n}\n\nfunction getFinalOutReference_(schedule,user,settings,dateKey,values) {\n  const wbf=getThursdayWbfOutReference_(user,settings,dateKey,values);\n  if(wbf)return wbf;\n  // A configured S2 out is authoritative. For an optional/unconfigured S2,\n  // the employee still owes the normal S1 end time, so a later S2 departure is\n  // compared against s1Out rather than inventing a second-session reference.\n  return String((schedule&&(schedule.s2Out||schedule.s1Out))||'').trim();\n}\n"""
)

# 3) Add a safe reconciliation routine for stale Status/StatusWaktu cells.
anchor = """function getTimeReviewData(token,fromDate,toDate) {\n"""
insert = r'''/**
 * Recalculate persisted Status / StatusWaktu from the actual punch sequence.
 *
 * This is deliberately separate from inferAttendanceFlags_(): reads already use
 * the effective status, while this routine repairs older physical sheet values
 * written by pre-fix deployments. Only columns O (Status) and AI (StatusWaktu)
 * are touched, so GPS/IP/timestamps are never rewritten.
 */
function repairAttendanceTimingStatuses_(options) {
  options=options||{};
  const settings=getSettings_();
  let from=clampToSystemStart_(options.from||options.fromDate||getSystemStartDate_(settings),settings);
  let to=validateDateKey_(options.to||options.toDate||todayKey_());
  if(to<from)return {rowsChecked:0,rowsUpdated:0,reviewsRemoved:0,fromDate:from,toDate:to};

  const usersByEmail={};
  getAllUsers_().forEach(u=>usersByEmail[u.email]=u);
  const changes=[];
  let checked=0;

  dateKeysBetween_(from,to).forEach(date=>{
    getAttendanceByDate_(date).forEach(rec=>{
      const v=padAttendanceValues_(rec.values);
      const email=normalizeEmail_(v[1]);
      const user=usersByEmail[email];
      if(!user||!v[4]||String(v[14]||'').toUpperCase()==='TIDAK HADIR')return;
      checked++;
      const flags=inferAttendanceFlags_(v,user,settings,date);
      const nextFlags=joinAttendanceFlags_(flags);
      const nextStatus=attendanceStatusFromFlags_(flags);
      const oldFlags=joinAttendanceFlags_(splitAttendanceFlags_(v[34]));
      const oldStatus=String(v[14]||'').trim().toUpperCase();
      if(oldFlags!==nextFlags||oldStatus!==nextStatus.toUpperCase()){
        changes.push({row:rec.row,status:nextStatus,flags:nextFlags});
      }
    });
  });

  if(changes.length){
    const sh=getSheetOrThrow_(EK.SHEETS.ATTENDANCE);
    const byRow=new Map(changes.map(x=>[x.row,x]));
    groupContiguousRows_(changes.map(x=>x.row)).forEach(g=>{
      const statuses=[],flags=[];
      for(let row=g.start;row<=g.end;row++){
        const x=byRow.get(row);
        statuses.push([x.status]);
        flags.push([x.flags]);
      }
      sh.getRange(g.start,15,g.end-g.start+1,1).setValues(statuses);
      sh.getRange(g.start,35,g.end-g.start+1,1).setValues(flags);
    });
    SpreadsheetApp.flush();
  }

  const reviewsRemoved=cleanupSupersededSession1EarlyReviews_(from,to);
  const result={rowsChecked:checked,rowsUpdated:changes.length,reviewsRemoved,fromDate:from,toDate:to};
  if(options.audit!==false&&changes.length){
    audit_('BAIKI_STATUS_WAKTU',`${from}..${to}`,`Semak=${checked}; kemas kini=${changes.length}; semakan S1 dibuang=${reviewsRemoved}`,options.actor||'SISTEM');
  }
  return result;
}

function repairAttendanceTimingStatusesFromMenu() {
  const admin=requireGoogleAdmin_();
  const settings=getSettings_();
  const result=repairAttendanceTimingStatuses_({
    from:getSystemStartDate_(settings),
    to:todayKey_(),
    actor:admin.email,
    audit:true
  });
  try{
    SpreadsheetApp.getUi().alert(
      'Baiki status waktu',
      `${result.rowsUpdated} rekod dikemas kini daripada ${result.rowsChecked} rekod yang disemak. ${result.reviewsRemoved} semakan Balik Awal Sesi 1 lama dibuang.`,
      SpreadsheetApp.getUi().ButtonSet.OK
    );
  }catch(e){}
  return result;
}

'''
p = Path('apps-script/60_TimeReview.gs')
src = p.read_text()
if anchor not in src:
    raise SystemExit('getTimeReviewData anchor not found')
if 'function repairAttendanceTimingStatuses_(' in src:
    raise SystemExit('repairAttendanceTimingStatuses_ already exists')
p.write_text(src.replace(anchor, insert + anchor, 1))

# 4) Auto-reconcile the selected report date before returning admin data.
replace_once(
    'apps-script/21_AdminApi.gs',
    """  const settings = getSettings_();\n  const report = buildDailyReport_(dateKey, activeUsers, settings);\n""",
    """  const settings = getSettings_();\n  // Self-heal stale BALIK AWAL written by older deployments. The effective\n  // report was already correct; this also keeps the physical KEHADIRAN sheet\n  // consistent with the final-departure rule.\n  try { repairAttendanceTimingStatuses_({from:dateKey,to:dateKey,audit:false}); } catch (_e) {}\n  const report = buildDailyReport_(dateKey, activeUsers, settings);\n"""
)

# 5) Expose a one-click full historical repair from the Google Sheet menu.
replace_once(
    'apps-script/00_Core.gs',
    """    .addItem('Baiki rekod duplikat', 'repairAttendanceDuplicatesFromMenu')\n    .addItem('Jana laporan hari ini', 'generateTodayReportFromMenu')\n""",
    """    .addItem('Baiki rekod duplikat', 'repairAttendanceDuplicatesFromMenu')\n    .addItem('Baiki status waktu tersimpan', 'repairAttendanceTimingStatusesFromMenu')\n    .addItem('Jana laporan hari ini', 'generateTodayReportFromMenu')\n"""
)

# 6) Prevent duplicate repair merge from reintroducing stale BALIK AWAL flags.
replace_once(
    'apps-script/41_AttendanceData.gs',
    """  const mergedFlags = []; rows.forEach(v => splitAttendanceFlags_(v[34]).forEach(f => { if (!mergedFlags.includes(f)) mergedFlags.push(f); }));\n  merged[34] = joinAttendanceFlags_(mergedFlags);\n  if (merged[4] && String(merged[14] || '').toUpperCase() !== 'TIDAK HADIR') merged[14] = attendanceStatusFromFlags_(mergedFlags);\n\n  merged[0] = dateKey;\n""",
    """  const mergedFlags = []; rows.forEach(v => splitAttendanceFlags_(v[34]).forEach(f => { if (!mergedFlags.includes(f)) mergedFlags.push(f); }));\n  merged[34] = joinAttendanceFlags_(mergedFlags);\n  if (merged[4] && String(merged[14] || '').toUpperCase() !== 'TIDAK HADIR') merged[14] = attendanceStatusFromFlags_(mergedFlags);\n\n  merged[0] = dateKey;\n"""
)

# The duplicate-merge recalculation must happen after identity/date are final.
p = Path('apps-script/41_AttendanceData.gs')
src = p.read_text()
old = """  merged[3] = user ? user.category : (rows.slice().reverse().map(v => String(v[3] || '').trim()).find(Boolean) || String(first[3] || ''));\n\n  const latestUpdated = group.slice().sort((a, b) =>\n"""
new = """  merged[3] = user ? user.category : (rows.slice().reverse().map(v => String(v[3] || '').trim()).find(Boolean) || String(first[3] || ''));\n\n  // Recompute timing flags from the merged punch sequence instead of keeping\n  // the union of historical flags (which may contain an obsolete S1 early-out).\n  if (user && merged[4] && String(merged[14] || '').toUpperCase() !== 'TIDAK HADIR') {\n    const effectiveFlags = inferAttendanceFlags_(merged,user,getSettings_(),dateKey);\n    merged[34] = joinAttendanceFlags_(effectiveFlags);\n    merged[14] = attendanceStatusFromFlags_(effectiveFlags);\n  }\n\n  const latestUpdated = group.slice().sort((a, b) =>\n"""
if old not in src:
    raise SystemExit('duplicate merge identity anchor not found')
p.write_text(src.replace(old,new,1))

print('optional-session final-status patch applied')
