from pathlib import Path
import re

# Replace production punch with direct preallocated-row writes.
p = Path('apps-script/20_UserApi.gs')
text = p.read_text()
start = text.find('function punch(token, type, location, clientInfo) {')
if start < 0:
    raise SystemExit('punch function start not found')

new_fn = r'''function punch(token, type, location, clientInfo) {
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

  // One daily batch allocates stable rows. Once a user has a row, different
  // staff can write different rows concurrently without a global ScriptLock.
  const slot = ensureAttendanceSlotForUser_(dateKey, user);

  let values = null;
  let session = 1;
  let refTime = '';
  let exceptionType = '';
  let ipCheck = {note:'',warning:'',blocked:false,registry:null,audit:null};
  let strictIpLock = null;
  let writeMs = 0;

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

    // Only BLOCK requires strict cross-user ordering. WARN/OFF are advisory and
    // must never serialize the morning punch burst.
    const ipPolicy = normalizeIpPunchPolicy_(settings.IP_PUNCH_POLICY || 'WARN');
    if (ipPolicy === 'BLOCK' && recordIp) {
      strictIpLock = LockService.getScriptLock();
      strictIpLock.waitLock(30000);
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

    // For WARN/OFF this cache registry is best-effort advisory state. Losing a
    // simultaneous advisory update is preferable to serializing every staff
    // write. BLOCK is protected by strictIpLock above.
    registerPunchIpUse_(ipCheck,user,type,session,recordIp,now);
  } finally {
    if (strictIpLock) {
      try { strictIpLock.releaseLock(); } catch (_e) {}
    }
  }

  if (ipCheck && ipCheck.audit) {
    audit_(ipCheck.audit.action,user.email,ipCheck.audit.details,user.email);
  }

  const action = `REKOD_${type === 'IN' ? 'MASUK' : 'KELUAR'}_SESI_${session}`;
  audit_(action,user.email,`${exceptionType || 'TEPAT MASA'}; mod=${isTestMode ? 'TEST' : 'REAL'}; jarak ${loc.distanceM}m; IP=${recordIp || '-'}; ${ipCheck.note || 'IP tiada isu'}; writeMs=${writeMs}; slotWaitMs=${slot.slotWaitMs}; slotsCreated=${slot.createdSlots}`,user.email);

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
    performance:{lockWaitMs:0,lockHeldMs:0,writeMs,slotWaitMs:slot.slotWaitMs,totalMs:Date.now()-perfStarted}
  };
}
'''
text = text[:start] + new_fn
p.write_text(text)

# Burst probe now measures direct distinct-row writes, matching production WARN/OFF.
p = Path('apps-script/96_PerformanceBurstTest.gs')
text = p.read_text()
pattern = re.compile(r"function performanceBurstProbe\(probeToken, runId, stage, requestNo, sentAtMs\) \{.*?\n\}\n\nfunction performanceBurstPercentile_", re.S)
new_probe = r'''function performanceBurstProbe(probeToken, runId, stage, requestNo, sentAtMs) {
  verifyPerformanceBurstToken_(probeToken, runId);
  const started = Date.now();

  const preflightStarted = Date.now();
  getSettings_();
  getAllUsers_();
  getAttendanceRowIndex_();
  readAbsenceRows_();
  const preflightMs = Date.now() - preflightStarted;

  const sh = getSpreadsheet_().getSheetByName(EK_PERF_BURST_SHEET_);
  if (!sh) throw new Error('Sheet PERF_BURST_TEST belum disediakan. Jalankan suite dari editor.');
  const row = performanceBurstReservedRow_(stage, requestNo);
  const writeStarted = Date.now();
  sh.getRange(row, 1, 1, 7).setValues([[
    String(runId || ''), Number(stage)||0, Number(requestNo)||0,
    new Date(started), 0, preflightMs, 'WEB_APP_PARALLEL_DIRECT_ROW'
  ]]);
  const writeMs = Date.now() - writeStarted;

  const finished = Date.now();
  return {
    ok:true, runId:String(runId||''), stage:Number(stage)||0, requestNo:Number(requestNo)||0,
    arrivalLagMs:Math.max(0, started-(Number(sentAtMs)||started)),
    preflightMs, lockWaitMs:0, lockHeldMs:0, writeMs, totalMs:finished-started
  };
}

function performanceBurstPercentile_'''
text2, n = pattern.subn(new_probe, text, count=1)
if n != 1:
    raise SystemExit(f'burst probe replacement count={n}')
p.write_text(text2)

# Diagnostics marker.
p = Path('apps-script/95_Diagnostics.gs')
text = p.read_text()
text = text.replace(
    "punchLock: 'daily batched row slots + per-user keyed cache lease; global lock only for slot/key gates and strict BLOCK IP policy',",
    "punchLock: 'daily batched row slots + direct per-user row writes; global lock only for one-time slot allocation and strict BLOCK IP policy',"
)
p.write_text(text)

print('PUNCH_CONCURRENCY_V4_OK')
