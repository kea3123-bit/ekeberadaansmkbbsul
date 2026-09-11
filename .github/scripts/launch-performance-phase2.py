from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    s = p.read_text(encoding='utf-8')
    if old not in s:
        raise SystemExit(f'anchor not found: {path}: {old[:120]!r}')
    p.write_text(s.replace(old, new, 1), encoding='utf-8')

# ---------------------------------------------------------------------------
# Attendance index v3: direct date+email row lookup and incremental append.
# This removes the historical A:B rescan from the normal first-punch path.
# ---------------------------------------------------------------------------
p = Path('apps-script/41_AttendanceData.gs')
s = p.read_text(encoding='utf-8')
s = s.replace("const EK_ATT_INDEX_CACHE_KEY_ = 'EK_PERF_ATT_INDEX_V2';\nconst EK_ATT_INDEX_TTL_SEC_ = 30;", "const EK_ATT_INDEX_CACHE_KEY_ = 'EK_PERF_ATT_INDEX_V3';\nconst EK_ATT_INDEX_TTL_SEC_ = 120;", 1)
s = s.replace("  if (cached && cached.lastRow === lastRow && cached.byDate && cached.byMonth) {", "  if (cached && cached.lastRow === lastRow && cached.byDate && cached.byMonth && cached.byKey) {", 1)
s = s.replace("  const byDate = Object.create(null), byMonth = Object.create(null);", "  const byDate = Object.create(null), byMonth = Object.create(null), byKey = Object.create(null);", 1)
s = s.replace("      const row = i + 2, monthKey = dateKey.slice(0, 7);\n      (byDate[dateKey] || (byDate[dateKey] = [])).push(row);\n      (byMonth[monthKey] || (byMonth[monthKey] = [])).push(row);", "      const row = i + 2, monthKey = dateKey.slice(0, 7), email = normalizeEmail_(v[1]);\n      (byDate[dateKey] || (byDate[dateKey] = [])).push(row);\n      (byMonth[monthKey] || (byMonth[monthKey] = [])).push(row);\n      if (email) (byKey[dateKey + '|' + email] || (byKey[dateKey + '|' + email] = [])).push(row);", 1)
s = s.replace("  const out = {lastRow, byDate, byMonth};", "  const out = {lastRow, byDate, byMonth, byKey};", 1)
anchor = "function invalidateAttendanceIndex_(){\n  EK_RUNTIME_ATT_INDEX_ = null;\n  try { getScriptCache_().remove(EK_ATT_INDEX_CACHE_KEY_); } catch(e) {}\n}\n"
if anchor not in s:
    raise SystemExit('attendance invalidation anchor missing')
addition = anchor + "\nfunction registerAttendanceRow_(dateKey, email, row) {\n  dateKey = validateDateKey_(dateKey);\n  email = normalizeEmail_(email);\n  row = Number(row || 0);\n  if (!email || row < 2) { invalidateAttendanceIndex_(); return; }\n\n  // The normal punch path has already loaded the old index before append.\n  // Reuse that in-memory object instead of observing the new lastRow and\n  // rebuilding the entire historical A:B index.\n  let idx = EK_RUNTIME_ATT_INDEX_;\n  if (!idx || !idx.byDate || !idx.byMonth || !idx.byKey || Number(idx.lastRow || 0) !== row - 1) {\n    const cached = cacheGetJson_(EK_ATT_INDEX_CACHE_KEY_);\n    if (cached && cached.byDate && cached.byMonth && cached.byKey && Number(cached.lastRow || 0) === row - 1) idx = cached;\n  }\n  if (!idx || !idx.byDate || !idx.byMonth || !idx.byKey || Number(idx.lastRow || 0) !== row - 1) {\n    // Unusual/manual sheet mutation: correctness first. The next lookup will\n    // rebuild once from source data rather than risking a stale row map.\n    invalidateAttendanceIndex_();\n    return;\n  }\n\n  const monthKey = dateKey.slice(0, 7);\n  const key = dateKey + '|' + email;\n  const pushUnique = (map, k) => {\n    const list = map[k] || (map[k] = []);\n    if (!list.includes(row)) list.push(row);\n  };\n  pushUnique(idx.byDate, dateKey);\n  pushUnique(idx.byMonth, monthKey);\n  pushUnique(idx.byKey, key);\n  idx.lastRow = row;\n  EK_RUNTIME_ATT_INDEX_ = idx;\n  cachePutJson_(EK_ATT_INDEX_CACHE_KEY_, idx, EK_ATT_INDEX_TTL_SEC_);\n}\n"
s = s.replace(anchor, addition, 1)
old_find = "function findAttendanceRecord_(dateKey, email) {\n  email = normalizeEmail_(email);\n  const matches = getAttendanceByDate_(dateKey).filter(r => r.email === email);\n  if (!matches.length) return null;\n  if (matches.length === 1) return matches[0];\n\n  const sh = getSheetOrThrow_(EK.SHEETS.ATTENDANCE);\n  const merged = mergeAttendanceDuplicateGroup_(sh, matches);\n  audit_('AUTO_GABUNG_DUPLIKAT', `${email} ${dateKey}`, `${matches.length} rekod digabungkan menjadi 1`);\n  return merged;\n}"
new_find = "function findAttendanceRecord_(dateKey, email) {\n  dateKey = validateDateKey_(dateKey);\n  email = normalizeEmail_(email);\n  if (!email) return null;\n  const sh = getSheetOrThrow_(EK.SHEETS.ATTENDANCE);\n  const idx = getAttendanceRowIndex_();\n  const rowNumbers = (idx.byKey && idx.byKey[dateKey + '|' + email]) || [];\n  if (!rowNumbers.length) return null;\n  const matches = readAttendanceRowsByRowNumbers_(sh, rowNumbers)\n    .filter(r => r.email === email && dateCellToKey_(r.values[0]) === dateKey);\n  if (!matches.length) return null;\n  if (matches.length === 1) return matches[0];\n\n  const merged = mergeAttendanceDuplicateGroup_(sh, matches);\n  audit_('AUTO_GABUNG_DUPLIKAT', `${email} ${dateKey}`, `${matches.length} rekod digabungkan menjadi 1`);\n  return merged;\n}"
if old_find not in s:
    raise SystemExit('findAttendanceRecord_ anchor missing')
s = s.replace(old_find, new_find, 1)
# Structural row deletion must invalidate row-number maps.
s = s.replace("  group.slice(1)\n    .map(x => x.row)\n    .sort((a, b) => b - a)\n    .forEach(row => sh.deleteRow(row));\n\n  SpreadsheetApp.flush();", "  group.slice(1)\n    .map(x => x.row)\n    .sort((a, b) => b - a)\n    .forEach(row => sh.deleteRow(row));\n\n  invalidateAttendanceIndex_();\n  SpreadsheetApp.flush();", 1)
p.write_text(s, encoding='utf-8')

# ---------------------------------------------------------------------------
# Hour/IP registry: first request of an hour builds from today's rows once;
# subsequent punches do O(1) cache lookup instead of scanning all today's rows.
# The ScriptLock around punch serializes registry read/update for correctness.
# ---------------------------------------------------------------------------
p = Path('apps-script/10_Auth.gs')
s = p.read_text(encoding='utf-8')
start = s.index('function evaluatePunchIp_(')
end = s.index('\nfunction mergeIpCheckNote_', start)
new_ip = r'''const EK_PUNCH_IP_HOUR_CACHE_PREFIX_ = 'EK_PERF_PUNCH_IP_HOUR_V1_';
const EK_PUNCH_IP_HOUR_TTL_SEC_ = 2 * 60 * 60;

function punchIpRegistryCacheKey_(bucket) {
  return EK_PUNCH_IP_HOUR_CACHE_PREFIX_ + String(bucket || '').replace(/[^0-9]/g, '');
}

function buildPunchIpHourRegistry_(now) {
  const bucket = hourBucket_(now);
  const cacheKey = punchIpRegistryCacheKey_(bucket);
  const cached = cacheGetJson_(cacheKey);
  if (cached && cached.bucket === bucket && cached.ips && typeof cached.ips === 'object') {
    return {cacheKey, bucket, ips:cached.ips};
  }

  const ips = Object.create(null);
  const dateKey = bucket.slice(0, 10);
  const add = (ip, email, name, kind, value) => {
    ip = normalizeIp_(ip);
    email = normalizeEmail_(email);
    if (!ip || !email || !value || hourBucket_(value) !== bucket) return;
    (ips[ip] || (ips[ip] = [])).push({email,name:String(name || ''),kind,time:formatTime_(value)});
  };
  getAttendanceByDate_(dateKey).forEach(r => {
    const v = r.values;
    add(v[19],v[1],v[2],'MASUK',v[4]);
    add(v[20],v[1],v[2],'BALIK',v[9]);
    add(v[32],v[1],v[2],'MASUK 2',v[22]);
    add(v[33],v[1],v[2],'KELUAR 2',v[27]);
  });
  const stored = {bucket,ips};
  cachePutJson_(cacheKey,stored,EK_PUNCH_IP_HOUR_TTL_SEC_);
  return {cacheKey,bucket,ips};
}

function evaluatePunchIp_(user, type, ip, now, settings, isTestMode) {
  const tracking = String(settings.IP_TRACKING_ENABLED || 'TRUE').toUpperCase() !== 'FALSE';
  const policy = normalizeIpPunchPolicy_(settings.IP_PUNCH_POLICY || 'WARN');

  if (!tracking) return {note:'IP tracking tidak aktif',warning:'',blocked:false,registry:null,audit:null};
  if (!ip) {
    const note = 'IP awam tidak dapat dikesan';
    return {note,warning:note,blocked:false,registry:null,audit:{action:'IP_PUNCH_TIDAK_DIKESAN',details:`${type}; ${hourBucket_(now)}`}};
  }
  if (policy === 'OFF' || isTestMode) {
    return {note:isTestMode?`IP ${ip} direkodkan — semakan pertindihan diabaikan dalam MOD TEST`:`IP ${ip} direkodkan`,warning:'',blocked:false,registry:null,audit:null};
  }

  const registry = buildPunchIpHourRegistry_(now);
  const conflicts = (registry.ips[ip] || []).filter(c => normalizeEmail_(c.email) !== user.email);
  if (!conflicts.length) return {note:`IP ${ip} — unik dalam jam ini`,warning:'',blocked:false,registry,audit:null};

  const uniquePeople = [...new Set(conflicts.map(c => normalizeEmail_(c.email)).filter(Boolean))];
  const details = conflicts.slice(0,5).map(c => `${c.name || c.email} (${c.kind} ${c.time})`).join(', ');
  const hour = registry.bucket.slice(-2);
  const note = `IP SAMA: ${ip} digunakan ${uniquePeople.length} akaun lain dalam jam ${hour}:00–${hour}:59`;
  const audit = {action:'IP_PUNCH_BERTINDIH',details:`${note}; ${details}`};
  if (policy === 'BLOCK') {
    return {note,warning:'',blocked:true,registry,audit,error:'Rakaman waktu ditolak: IP awam yang sama telah digunakan oleh akaun lain dalam jam yang sama. Jika anda menggunakan Wi-Fi sekolah/shared network, minta Pentadbir Sistem tukar Polisi IP kepada AMARAN.'};
  }
  return {note,warning:`${note}. Rekod waktu diterima kerana Polisi IP = AMARAN.`,blocked:false,registry,audit};
}

function registerPunchIpUse_(ipCheck, user, type, session, ip, now) {
  const registry = ipCheck && ipCheck.registry;
  ip = normalizeIp_(ip);
  if (!registry || !ip) return;
  const kind = session === 2 ? (type === 'IN' ? 'MASUK 2' : 'KELUAR 2') : (type === 'IN' ? 'MASUK' : 'BALIK');
  const list = registry.ips[ip] || (registry.ips[ip] = []);
  list.push({email:user.email,name:user.name || '',kind,time:formatTime_(now)});
  cachePutJson_(registry.cacheKey,{bucket:registry.bucket,ips:registry.ips},EK_PUNCH_IP_HOUR_TTL_SEC_);
}
'''
s = s[:start] + new_ip + s[end:]
p.write_text(s, encoding='utf-8')

# ---------------------------------------------------------------------------
# Punch hot path: absence lookup before lock; under lock only direct row lookup,
# sequence/IP decision and one attendance write. Audit/review/email run after.
# ---------------------------------------------------------------------------
p = Path('apps-script/20_UserApi.gs')
s = p.read_text(encoding='utf-8')
start = s.index('function punch(token, type, location, clientInfo) {')
new_punch = r'''function punch(token, type, location, clientInfo) {
  const perfStarted = Date.now();
  const user = requireSessionUser_(token);
  const settings = getSettings_();
  const isTestMode = String(settings.SYSTEM_MODE || 'REAL').toUpperCase() === 'TEST';
  if (!isTestMode) validateLocationSettings_(settings);

  type = String(type || '').toUpperCase();
  if (!['IN', 'OUT'].includes(type)) throw new Error('Jenis rekod waktu tidak sah.');

  const ci = normalizeClientInfo_(clientInfo);
  const ipTracking = String(settings.IP_TRACKING_ENABLED || 'TRUE').toUpperCase() !== 'FALSE';
  const recordIp = ipTracking ? ci.ip : '';
  const loc = isTestMode
    ? {lat:'',lng:'',accuracyM:'',distanceM:0}
    : validateAndMeasureLocation_(location,settings);
  const now = new Date();
  const dateKey = todayKey_();
  const schedule = getEffectiveSchedule_(user,settings);
  const nowMinutes = minutesNow_(now);

  // TIDAK_HADIR is CacheService-backed. Resolve it before the global write
  // lock so a cache miss never keeps 100 morning punches waiting behind it.
  const presenceRequest = type === 'IN'
    ? findRelevantPresenceForDate_(user.email,dateKey,readAbsenceRows_())
    : null;

  let values = null;
  let session = 1;
  let refTime = '';
  let exceptionType = '';
  let ipCheck = {note:'',warning:'',blocked:false,registry:null,audit:null};
  let punchError = null;
  let wasNewRow = false;
  let lockWaitMs = 0;
  let lockHeldMs = 0;
  const lockRequestedAt = Date.now();
  const lock = LockService.getScriptLock();

  try {
    lock.waitLock(20000);
    lockWaitMs = Date.now() - lockRequestedAt;
    const lockAcquiredAt = Date.now();
    try {
      const sh = getSheetOrThrow_(EK.SHEETS.ATTENDANCE);
      const rec = findAttendanceRecord_(dateKey,user.email);
      values = rec ? padAttendanceValues_(rec.values) : Array(EK.ATT_HEADERS.length).fill('');

      if (rec && String(values[15] || '').toUpperCase() === 'TIDAK_HADIR' && !values[4]) {
        throw new Error('Anda mempunyai rekod Tidak Hadir yang telah diluluskan untuk hari ini. Hubungi pentadbir jika rekod itu perlu dibatalkan.');
      }

      const step = nextAttendanceStep_(values,schedule);
      if (step.complete) throw new Error('Semua rekod waktu hari ini sudah lengkap.');
      if (step.type !== type) {
        const expected = step.type === 'IN' ? 'Waktu Masuk' : 'Waktu Balik';
        throw new Error(`Turutan rekod waktu mesti berselang. Rekod seterusnya ialah ${expected}.`);
      }
      session = step.session;
      refTime = getPunchReferenceTime_(type,session,schedule,user,settings,dateKey,values);

      if (!isTestMode && type === 'IN') {
        const latestAllowed = session === 1 ? schedule.maxPunchIn : (schedule.s2Out || '');
        if (latestAllowed && nowMinutes > timeToMinutes_(latestAllowed)) {
          throw new Error(`Tempoh Rekod Waktu Masuk Sesi ${session} telah tamat pada ${latestAllowed}.`);
        }
      }
      if (!isTestMode && refTime) {
        const refMinutes = timeToMinutes_(refTime);
        if (type === 'IN' && nowMinutes > refMinutes) exceptionType = 'LEWAT';
        if (type === 'OUT' && nowMinutes < refMinutes) exceptionType = 'BALIK AWAL';
      }

      // Hour/IP cache is read and updated while the same short ScriptLock is
      // held, so concurrent punches see the preceding successful punch without
      // rescanning the entire attendance day on every request.
      ipCheck = evaluatePunchIp_(user,type,recordIp,now,settings,isTestMode);
      if (ipCheck.blocked) throw new Error(ipCheck.error || 'Rakaman waktu ditolak oleh Polisi IP.');

      if (!rec) {
        values[0]=dateKey; values[1]=user.email; values[2]=user.name; values[3]=user.category;
      } else {
        values[2]=user.name; values[3]=user.category;
      }

      if (session === 1 && type === 'IN') {
        values[4]=now; values[5]=loc.lat; values[6]=loc.lng; values[7]=loc.distanceM; values[8]=loc.accuracyM; values[19]=recordIp || '';
      } else if (session === 1 && type === 'OUT') {
        values[9]=now; values[10]=loc.lat; values[11]=loc.lng; values[12]=loc.distanceM; values[13]=loc.accuracyM; values[20]=recordIp || '';
      } else if (session === 2 && type === 'IN') {
        values[22]=now; values[23]=loc.lat; values[24]=loc.lng; values[25]=loc.distanceM; values[26]=loc.accuracyM; values[32]=recordIp || '';
      } else if (session === 2 && type === 'OUT') {
        values[27]=now; values[28]=loc.lat; values[29]=loc.lng; values[30]=loc.distanceM; values[31]=loc.accuracyM; values[33]=recordIp || '';
      }

      const flags = splitAttendanceFlags_(values[34]);
      if (exceptionType && !flags.includes(exceptionType)) flags.push(exceptionType);
      values[34]=joinAttendanceFlags_(flags);
      values[14]=attendanceStatusFromFlags_(flags);
      values[15]=isTestMode ? 'TEST' : 'GPS';
      values[18]=now;
      values[21]=mergeIpCheckNote_(values[21],ipCheck.note);
      if (presenceRequest && type === 'IN') {
        values[17]=mergeAttendanceReason_(values[17],presenceRequestReason_(presenceRequest,'CATATAN'));
      }

      if (!rec) {
        sh.appendRow(values);
        const row = sh.getLastRow();
        registerAttendanceRow_(dateKey,user.email,row);
        wasNewRow = true;
      } else {
        sh.getRange(rec.row,1,1,EK.ATT_HEADERS.length).setValues([values]);
      }
      registerPunchIpUse_(ipCheck,user,type,session,recordIp,now);
    } finally {
      lockHeldMs = Date.now() - lockAcquiredAt;
      lock.releaseLock();
    }
  } catch (err) {
    punchError = err;
    try { if (lock.hasLock()) lock.releaseLock(); } catch (_e) {}
  }

  // Audit writes, review-sheet reads/writes and email must never extend the
  // attendance critical section. This is the key launch-burst optimization.
  if (ipCheck && ipCheck.audit) {
    audit_(ipCheck.audit.action,user.email,ipCheck.audit.details,user.email);
  }
  if (punchError) throw punchError;

  const action = `REKOD_${type === 'IN' ? 'MASUK' : 'KELUAR'}_SESI_${session}`;
  audit_(action,user.email,`${exceptionType || 'TEPAT MASA'}; mod=${isTestMode ? 'TEST' : 'REAL'}; jarak ${loc.distanceM}m; IP=${recordIp || '-'}; ${ipCheck.note || 'IP tiada isu'}; lockWaitMs=${lockWaitMs}; lockHeldMs=${lockHeldMs}; row=${wasNewRow ? 'NEW' : 'UPDATE'}`,user.email);

  let timeReviewRecord = null;
  if (exceptionType) {
    timeReviewRecord = createTimeReviewRecord_({
      date:dateKey,user,type:exceptionType,session,
      recordTime:formatTime_(now),referenceTime:refTime
    });
    if (exceptionType === 'LEWAT' && presenceRequest && presenceRequest.status === 'DILULUSKAN') {
      timeReviewRecord = autoAcknowledgeTimeReviewFromPresence_(timeReviewRecord,presenceRequest);
    }
  }
  if (timeReviewRecord && timeReviewRecord.isNew !== false && !timeReviewRecord.autoAcknowledged) {
    notifyTimeException_(timeReviewRecord);
  }

  const label = type === 'IN' ? 'Masuk' : 'Balik';
  return {
    ok:true,
    message:`Rekod waktu ${label} berjaya${exceptionType ? ` — status ${exceptionType}` : ''}.`,
    attendance:publicAttendance_({values},schedule),
    distanceM:loc.distanceM,
    ip:recordIp || '',
    ipWarning:ipCheck.warning || '',
    timeException:timeReviewRecord ? publicTimeReview_(timeReviewRecord) : null,
    performance:{lockWaitMs,lockHeldMs,totalMs:Date.now()-perfStarted}
  };
}
'''
s = s[:start] + new_punch
p.write_text(s, encoding='utf-8')

# ---------------------------------------------------------------------------
# Diagnostics: expose static launch-readiness markers and timing guidance.
# ---------------------------------------------------------------------------
p = Path('apps-script/95_Diagnostics.gs')
s = p.read_text(encoding='utf-8')
s = s.replace("      timeReviewRows: timeReviewRows.length\n    },\n    timingsMs: marks,", "      timeReviewRows: timeReviewRows.length\n    },\n    launchReadiness: {\n      targetDailyUsers: 100,\n      attendanceIndex: 'date+email direct lookup / incremental punch append',\n      ipCheck: 'hour registry cache',\n      punchLock: 'attendance write critical section only',\n      note: 'Run a staged 20/50/100-user burst against the deployed Web App before launch.'\n    },\n    timingsMs: marks,", 1)
p.write_text(s, encoding='utf-8')

# ---------------------------------------------------------------------------
# Docs: mark Phase 2 complete in source and explain expected hot path.
# ---------------------------------------------------------------------------
p = Path('docs/PERFORMANCE_AUDIT_100_USERS.md')
s = p.read_text(encoding='utf-8')
if '## Phase 2 implemented' not in s:
    s += '''\n\n## Phase 2 implemented\n\n- Attendance index V3 includes a `date|email` row map, so punch reads only the target user's row.\n- First punch appends incrementally update the shared attendance index instead of invalidating and rebuilding it.\n- IP duplicate checks use one hour-level CacheService registry; the first request seeds it and subsequent requests are O(1) lookups.\n- The global ScriptLock now contains only row lookup, punch sequence/IP decision and the attendance write/cache update.\n- Audit, time-review creation and notification email run after the lock is released.\n- Successful punch responses include `performance.lockWaitMs`, `lockHeldMs` and `totalMs` for staged launch testing.\n\n### Launch gate\n\nDo not certify exact 100-at-once capacity from static analysis alone. Deploy the matching Apps Script version, then stage 20, 50 and 100 concurrent/near-concurrent punches and inspect lock timings, Apps Script execution errors and duplicate-row count.\n'''
p.write_text(s, encoding='utf-8')
