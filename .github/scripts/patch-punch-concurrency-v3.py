from pathlib import Path

# 1) Attendance helpers: daily row slots + lightweight keyed locks.
p = Path('apps-script/41_AttendanceData.gs')
text = p.read_text()
marker = '\n\nfunction groupContiguousRows_(rows) {'
if marker not in text:
    raise SystemExit('attendance insertion marker missing')
helper = r'''

// ---------- Launch burst v3: daily row slots + keyed punch locks ----------
// Google Apps Script exposes only one ScriptLock for the whole deployment. A
// full attendance write under that lock serializes 100 different staff. We use
// the ScriptLock only as a very short gate for named CacheService leases. Each
// staff member then writes to their own pre-allocated KEHADIRAN row.
const EK_ATT_KEY_LOCK_PREFIX_ = 'EK_ATT_KLOCK_V1:';
const EK_ATT_SLOT_READY_PREFIX_ = 'EK_ATT_SLOTS_V1:';
const EK_ATT_KEY_LOCK_LEASE_SEC_ = 30;

function attendanceKeyLockCacheKey_(scope, key) {
  const safeScope = String(scope || 'ATT').replace(/[^A-Za-z0-9_-]/g, '_').slice(0, 24);
  const safeKey = String(key || '').replace(/[^A-Za-z0-9@._|:-]/g, '_').slice(0, 180);
  return `${EK_ATT_KEY_LOCK_PREFIX_}${safeScope}:${safeKey}`;
}

function acquireAttendanceKeyLock_(scope, key, timeoutMs) {
  const started = Date.now();
  const deadline = started + Math.max(500, Number(timeoutMs || 5000));
  const cache = getScriptCache_();
  const cacheKey = attendanceKeyLockCacheKey_(scope, key);
  const token = Utilities.getUuid();

  while (Date.now() < deadline) {
    const gate = LockService.getScriptLock();
    if (gate.tryLock(250)) {
      try {
        if (!cache.get(cacheKey)) {
          cache.put(cacheKey, token, EK_ATT_KEY_LOCK_LEASE_SEC_);
          return {cacheKey, token, waitMs:Date.now() - started};
        }
      } finally {
        gate.releaseLock();
      }
    }
    Utilities.sleep(20 + Math.floor(Math.random() * 25));
  }
  throw new Error('Sistem sedang memproses rekod waktu anda. Sila cuba semula sebentar lagi.');
}

function releaseAttendanceKeyLock_(lease) {
  if (!lease || !lease.cacheKey || !lease.token) return;
  const gate = LockService.getScriptLock();
  if (!gate.tryLock(1000)) return; // lease expires automatically after 30s
  try {
    const cache = getScriptCache_();
    if (cache.get(lease.cacheKey) === lease.token) cache.remove(lease.cacheKey);
  } finally {
    gate.releaseLock();
  }
}

function registerAttendanceRowsBatch_(idx, dateKey, users, startRow, previousLastRow) {
  if (!idx || !idx.byDate || !idx.byMonth || !idx.byKey || Number(idx.lastRow || 0) !== Number(previousLastRow || 0)) {
    invalidateAttendanceIndex_();
    return false;
  }
  const monthKey = dateKey.slice(0, 7);
  const pushUnique = (map, k, row) => {
    const list = map[k] || (map[k] = []);
    if (!list.includes(row)) list.push(row);
  };
  users.forEach((user, i) => {
    const row = startRow + i;
    const email = normalizeEmail_(user.email);
    pushUnique(idx.byDate, dateKey, row);
    pushUnique(idx.byMonth, monthKey, row);
    pushUnique(idx.byKey, dateKey + '|' + email, row);
  });
  idx.lastRow = previousLastRow + users.length;
  EK_RUNTIME_ATT_INDEX_ = idx;
  cachePutJson_(EK_ATT_INDEX_CACHE_KEY_, idx, EK_ATT_INDEX_TTL_SEC_);
  return true;
}

/**
 * Ensure today's active users already own a physical row in KEHADIRAN.
 * The first missing user creates all missing active-user rows in ONE batch.
 * Other simultaneous requests observe the ready cache and never queue through
 * one Spreadsheet write per staff member.
 */
function ensureAttendanceSlotForUser_(dateKey, user) {
  dateKey = validateDateKey_(dateKey);
  let rec = findAttendanceRecord_(dateKey, user.email);
  if (rec) return {record:rec, createdSlots:0, createdForUser:false, slotWaitMs:0};

  const started = Date.now();
  const cache = getScriptCache_();
  const readyKey = EK_ATT_SLOT_READY_PREFIX_ + dateKey;
  const deadline = started + 8000;

  while (Date.now() < deadline) {
    // Once the first request has created the batch, waiting executions can
    // refresh their per-execution index and leave without acquiring ScriptLock.
    if (cache.get(readyKey)) {
      EK_RUNTIME_ATT_INDEX_ = null;
      rec = findAttendanceRecord_(dateKey, user.email);
      if (rec) return {record:rec, createdSlots:0, createdForUser:false, slotWaitMs:Date.now()-started};
      // A user may have been activated after today's batch was created.
      cache.remove(readyKey);
    }

    const gate = LockService.getScriptLock();
    if (gate.tryLock(300)) {
      try {
        // Recheck from source/cache after acquiring the one-time slot gate.
        EK_RUNTIME_ATT_INDEX_ = null;
        rec = findAttendanceRecord_(dateKey, user.email);
        if (rec) {
          cache.put(readyKey, '1', 21600);
          return {record:rec, createdSlots:0, createdForUser:false, slotWaitMs:Date.now()-started};
        }

        // Correctness first for the once-per-day allocation: rebuild the small
        // A:B index once, then extend it incrementally for the whole batch.
        invalidateAttendanceIndex_();
        const sh = getSheetOrThrow_(EK.SHEETS.ATTENDANCE);
        const idx = getAttendanceRowIndex_();
        const activeUsers = getAllUsers_().filter(u => u.active);
        if (!activeUsers.some(u => normalizeEmail_(u.email) === normalizeEmail_(user.email))) activeUsers.push(user);
        const missing = activeUsers.filter(u => !((idx.byKey[dateKey + '|' + normalizeEmail_(u.email)] || []).length));

        if (missing.length) {
          const previousLastRow = sh.getLastRow();
          const startRow = previousLastRow + 1;
          const rows = missing.map(u => {
            const v = Array(EK.ATT_HEADERS.length).fill('');
            v[0] = dateKey;
            v[1] = normalizeEmail_(u.email);
            v[2] = u.name || '';
            v[3] = u.category || '';
            return v;
          });
          sh.getRange(startRow, 1, rows.length, EK.ATT_HEADERS.length).setValues(rows);
          registerAttendanceRowsBatch_(idx, dateKey, missing, startRow, previousLastRow);
        }

        cache.put(readyKey, '1', 21600);
        EK_RUNTIME_ATT_INDEX_ = null;
        rec = findAttendanceRecord_(dateKey, user.email);
        if (!rec) throw new Error('Slot rekod waktu tidak dapat disediakan. Cuba semula.');
        return {
          record:rec,
          createdSlots:missing.length,
          createdForUser:missing.some(u => normalizeEmail_(u.email) === normalizeEmail_(user.email)),
          slotWaitMs:Date.now()-started
        };
      } finally {
        gate.releaseLock();
      }
    }
    Utilities.sleep(25 + Math.floor(Math.random() * 25));
  }
  throw new Error('Penyediaan rekod waktu mengambil masa terlalu lama. Sila cuba semula.');
}
'''
if 'function ensureAttendanceSlotForUser_' not in text:
    text = text.replace(marker, helper + marker, 1)
p.write_text(text)

# 2) Replace production punch hot path.
p = Path('apps-script/20_UserApi.gs')
text = p.read_text()
start = text.find('function punch(token, type, location, clientInfo) {')
if start < 0:
    raise SystemExit('punch function start missing')
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
  const presenceRequest = type === 'IN'
    ? findRelevantPresenceForDate_(user.email,dateKey,readAbsenceRows_())
    : null;

  // One batched row allocation per day removes appendRow from the morning hot
  // path. Existing blank slot rows are intentionally treated as BELUM HADIR by
  // reporting/card code until the first real punch is written.
  const slot = ensureAttendanceSlotForUser_(dateKey, user);

  let values = null;
  let session = 1;
  let refTime = '';
  let exceptionType = '';
  let ipCheck = {note:'',warning:'',blocked:false,registry:null,audit:null};
  let punchError = null;
  let lockWaitMs = 0;
  let lockHeldMs = 0;
  let writeMs = 0;
  let userLease = null;
  let strictIpLock = null;

  try {
    // This is a logical lock for this staff/date only. Its ScriptLock gate is
    // held for milliseconds during lease acquisition, not during the Sheet write.
    userLease = acquireAttendanceKeyLock_('PUNCH', dateKey + '|' + user.email, 6000);
    lockWaitMs = userLease.waitMs || 0;
    const userLockAcquiredAt = Date.now();
    try {
      const sh = getSheetOrThrow_(EK.SHEETS.ATTENDANCE);
      const rec = findAttendanceRecord_(dateKey,user.email);
      if (!rec) throw new Error('Rekod waktu hari ini tidak dapat dikenal pasti. Cuba semula.');
      values = padAttendanceValues_(rec.values);

      if (String(values[15] || '').toUpperCase() === 'TIDAK_HADIR' && !values[4]) {
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

      // BLOCK must preserve strict shared-IP ordering. WARN/OFF may evaluate
      // concurrently because they do not reject a punch; registry updates are
      // serialized briefly after the Sheet write instead of serializing writes.
      const ipPolicy = normalizeIpPunchPolicy_(settings.IP_PUNCH_POLICY || 'WARN');
      if (ipPolicy === 'BLOCK' && recordIp) {
        strictIpLock = LockService.getScriptLock();
        strictIpLock.waitLock(20000);
      }
      ipCheck = evaluatePunchIp_(user,type,recordIp,now,settings,isTestMode);
      if (ipCheck.blocked) throw new Error(ipCheck.error || 'Rakaman waktu ditolak oleh Polisi IP.');

      values[2]=user.name; values[3]=user.category;
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

      const writeStarted = Date.now();
      sh.getRange(rec.row,1,1,EK.ATT_HEADERS.length).setValues([values]);
      writeMs = Date.now() - writeStarted;

      if (strictIpLock) {
        registerPunchIpUse_(ipCheck,user,type,session,recordIp,now);
      } else {
        // WARN/OFF registry update is a cache-only critical section. Even on a
        // shared school NAT IP it is far shorter than a Spreadsheet write.
        let ipLease = null;
        try {
          ipLease = acquireAttendanceKeyLock_('IPREG', dateKey + '|' + (recordIp || '-'), 3000);
          registerPunchIpUse_(ipCheck,user,type,session,recordIp,now);
        } finally {
          releaseAttendanceKeyLock_(ipLease);
        }
      }
    } finally {
      if (strictIpLock) {
        try { strictIpLock.releaseLock(); } catch (_e) {}
        strictIpLock = null;
      }
      lockHeldMs = Date.now() - userLockAcquiredAt;
      releaseAttendanceKeyLock_(userLease);
      userLease = null;
    }
  } catch (err) {
    punchError = err;
    if (strictIpLock) { try { strictIpLock.releaseLock(); } catch (_e) {} }
    releaseAttendanceKeyLock_(userLease);
  }

  if (ipCheck && ipCheck.audit) {
    audit_(ipCheck.audit.action,user.email,ipCheck.audit.details,user.email);
  }
  if (punchError) throw punchError;

  const action = `REKOD_${type === 'IN' ? 'MASUK' : 'KELUAR'}_SESI_${session}`;
  audit_(action,user.email,`${exceptionType || 'TEPAT MASA'}; mod=${isTestMode ? 'TEST' : 'REAL'}; jarak ${loc.distanceM}m; IP=${recordIp || '-'}; ${ipCheck.note || 'IP tiada isu'}; keyLockWaitMs=${lockWaitMs}; keyLockHeldMs=${lockHeldMs}; writeMs=${writeMs}; slotWaitMs=${slot.slotWaitMs}; slotsCreated=${slot.createdSlots}`,user.email);

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
    performance:{lockWaitMs,lockHeldMs,writeMs,slotWaitMs:slot.slotWaitMs,totalMs:Date.now()-perfStarted}
  };
}
'''
text = text[:start] + new_punch
p.write_text(text)

# 3) Make the safe PERF_BURST_TEST emulate preallocated distinct-row writes.
p = Path('apps-script/96_PerformanceBurstTest.gs')
text = p.read_text()
old_reset = r'''function resetPerformanceBurstSheet_() {
  const sh = ensurePerformanceBurstSheet_();
  sh.clearContents();
  sh.getRange(1, 1, 1, 7).setValues([[
    'RunID', 'Stage', 'Request', 'StartedAt', 'LockWaitMs', 'PreflightMs', 'Server'
  ]]);
  sh.setFrozenRows(1);
  return sh;
}'''
new_reset = r'''function resetPerformanceBurstSheet_() {
  const sh = ensurePerformanceBurstSheet_();
  sh.clearContents();
  sh.getRange(1, 1, 1, 7).setValues([[
    'RunID', 'Stage', 'Request', 'StartedAt', 'LockWaitMs', 'PreflightMs', 'Server'
  ]]);
  // Reserve one distinct row per request across the 20/50/100 stages. This
  // mirrors the production v3 daily-slot architecture without touching KEHADIRAN.
  const reserved = Array.from({length:170}, (_, i) => [`RESERVED-${i+1}`,'','','','','','']);
  sh.getRange(2, 1, reserved.length, 7).setValues(reserved);
  sh.setFrozenRows(1);
  return sh;
}

function performanceBurstReservedRow_(stage, requestNo) {
  const s = Number(stage || 0), n = Number(requestNo || 0);
  if (s === 20) return 1 + n;      // 2..21
  if (s === 50) return 21 + n;     // 22..71
  if (s === 100) return 71 + n;    // 72..171
  throw new Error('Stage ujian prestasi tidak sah.');
}'''
if old_reset not in text:
    raise SystemExit('burst reset block missing')
text = text.replace(old_reset, new_reset, 1)

old_probe_start = text.find('function performanceBurstProbe(probeToken, runId, stage, requestNo, sentAtMs) {')
old_probe_end = text.find('\nfunction performanceBurstPercentile_', old_probe_start)
if old_probe_start < 0 or old_probe_end < 0:
    raise SystemExit('burst probe markers missing')
new_probe = r'''function performanceBurstProbe(probeToken, runId, stage, requestNo, sentAtMs) {
  verifyPerformanceBurstToken_(probeToken, runId);
  const started = Date.now();

  const preflightStarted = Date.now();
  getSettings_();
  getAllUsers_();
  getAttendanceRowIndex_();
  readAbsenceRows_();
  const preflightMs = Date.now() - preflightStarted;

  let lease = null;
  let lockWaitMs = 0;
  let lockHeldMs = 0;
  let writeMs = 0;
  try {
    lease = acquireAttendanceKeyLock_('PERF', runId + '|' + requestNo, 6000);
    lockWaitMs = lease.waitMs || 0;
    const acquiredAt = Date.now();
    try {
      const sh = getSpreadsheet_().getSheetByName(EK_PERF_BURST_SHEET_);
      if (!sh) throw new Error('Sheet PERF_BURST_TEST belum disediakan. Jalankan suite dari editor.');
      const row = performanceBurstReservedRow_(stage, requestNo);
      const writeStarted = Date.now();
      sh.getRange(row, 1, 1, 7).setValues([[
        String(runId || ''), Number(stage)||0, Number(requestNo)||0,
        new Date(started), lockWaitMs, preflightMs, 'WEB_APP_PARALLEL'
      ]]);
      writeMs = Date.now() - writeStarted;
    } finally {
      lockHeldMs = Date.now() - acquiredAt;
      releaseAttendanceKeyLock_(lease);
      lease = null;
    }
  } finally {
    releaseAttendanceKeyLock_(lease);
  }

  const finished = Date.now();
  return {
    ok:true, runId:String(runId||''), stage:Number(stage)||0, requestNo:Number(requestNo)||0,
    arrivalLagMs:Math.max(0, started-(Number(sentAtMs)||started)),
    preflightMs, lockWaitMs, lockHeldMs, writeMs, totalMs:finished-started
  };
}
'''
text = text[:old_probe_start] + new_probe + text[old_probe_end:]
p.write_text(text)

print('PUNCH_CONCURRENCY_V3_PATCH_OK')
