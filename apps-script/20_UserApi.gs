// ---------- User functions ----------

function getBootstrapData(token) {
  const user = requireSessionUser_(token);
  // Migrasi selamat untuk deployment sedia ada: trigger Keberadaan baharu
  // dipasang sekali pada login pertama selepas versi ini tanpa menggagalkan login
  // jika akaun pemilik belum memberi permission ScriptApp.
  try { ensurePresenceDeadlineTrigger_(); }
  catch (e) { audit_('TRIGGER_KEBERADAAN_AUTO_INSTALL_GAGAL', user.email, String(e && e.message ? e.message : e), 'SISTEM'); }
  return buildBootstrap_(user);
}

/**
 * Data Punch Card bulanan untuk pengguna yang sedang log masuk sahaja.
 * monthKey mesti dalam format YYYY-MM.
 */
function getMyPunchCardMonth(token, monthKey) {
  const user = requireSessionUser_(token);
  // Gunakan builder yang sama seperti paparan Pentadbir supaya rekod
  // TIDAK HADIR (termasuk TIADA PENJELASAN dan permohonan MENUNGGU/DILULUSKAN)
  // sentiasa muncul pada Punch Card Digital pengguna sendiri.
  return buildPunchCardMonthForUser_(user, monthKey);
}

function adminGetPunchCardMonth(token, email, monthKey) {
  requireSessionAdmin_(token);
  const user = getUserByEmail_(normalizeEmail_(email), false);
  if (!user) throw new Error('Pengguna tidak dijumpai.');
  return buildPunchCardMonthForUser_(user, monthKey);
}

function buildPunchCardMonthForUser_(user, monthKey) {
  monthKey = String(monthKey || todayKey_().slice(0, 7)).trim();
  if (!/^\d{4}-\d{2}$/.test(monthKey)) throw new Error('Bulan tidak sah.');
  const parts = monthKey.split('-').map(Number);
  const year = parts[0], month = parts[1];
  if (year < 2000 || year > 2100 || month < 1 || month > 12) throw new Error('Bulan tidak sah.');
  const daysInMonth = new Date(year, month, 0).getDate();
  let records = [];
  {
    const rows = getAttendanceValuesForUserMonth_(user.email, monthKey);
    records = rows
      .map(v => {
        const dateKey = dateCellToKey_(v[0]);
        v = padAttendanceValues_(v);
        return {
          day: Number(dateKey.slice(8, 10)), date: dateKey, status: String(v[14] || ''),
          inTime: v[4] ? formatTime_(v[4]) : '', outTime: v[9] ? formatTime_(v[9]) : '',
          inTime2: v[22] ? formatTime_(v[22]) : '', outTime2: v[27] ? formatTime_(v[27]) : '',
          statusFlags: inferAttendanceFlags_(v, user, getSettings_()),
          source: String(v[15] || ''), editedBy: String(v[16] || ''), reason: String(v[17] || '')
        };
      }).sort((a, b) => a.day - b.day);
  }
  const settings = getSettings_();
  const systemStartDate = getSystemStartDate_(settings);
  records = records.filter(r => r.date >= systemStartDate);

  // v10.10: Tandakan cuti hujung minggu Jumaat/Sabtu pada Punch Card Digital.
  // Jika pegawai benar-benar punch pada hari tersebut, rekod punch sebenar
  // sentiasa diberi keutamaan dan label JUMAAT/SABTU tidak dipaparkan.
  // Label hanya digunakan jika hari tersebut memang bukan hari bekerja dalam
  // WORKING_DAYS supaya konfigurasi Pentadbir tetap dihormati.
  const existingByDay = new Map(records.map(r => [Number(r.day), r]));
  for (let day = 1; day <= daysInMonth; day++) {
    const dateKey = `${monthKey}-${String(day).padStart(2,'0')}`;
    if (dateKey < systemStartDate) continue;
    const weekendLabel = weekendLabelForDateKey_(dateKey, settings);
    if (!weekendLabel) continue;

    const existing = existingByDay.get(day);
    if (existing && (existing.inTime || existing.outTime)) continue;

    if (existing) {
      existing.status = 'WEEKEND';
      existing.source = 'WEEKEND';
      existing.editedBy = 'SISTEM';
      existing.reason = weekendLabel;
    } else {
      const added = {
        day, date: dateKey, status: 'WEEKEND', inTime: '', outTime: '',
        source: 'WEEKEND', editedBy: 'SISTEM', reason: weekendLabel
      };
      records.push(added);
      existingByDay.set(day, added);
    }
  }

  // Paparkan status hari tanpa Punch Masuk secara dinamik.
  // Keberadaan aktif mendapat pengecualian khas daripada ABSENT_AFTER:
  // kekal BELUM HADIR sehingga waktu akhir Keberadaan. Hanya proses alert
  // Pengurusan boleh menulis TIDAK HADIR bagi kes Keberadaan.
  const today = todayKey_();
  const nowMinutes = minutesNow_(new Date());
  const absentMinutes = timeToMinutes_(settings.ABSENT_AFTER);
  const absenceRowsForCard = readAbsenceRows_();
  const userAbsences = absenceRowsForCard.filter(r => r.email === user.email && r.mode !== 'KEBERADAAN' && ['MENUNGGU','DILULUSKAN'].includes(r.status));
  const userPresences = absenceRowsForCard.filter(r => r.email === user.email && r.mode === 'KEBERADAAN' && ['MENUNGGU','DILULUSKAN'].includes(r.status));
  for (let day = 1; day <= daysInMonth; day++) {
    const dateKey = `${monthKey}-${String(day).padStart(2,'0')}`;
    if (dateKey < systemStartDate || dateKey > today) continue;
    if (!isWorkingDay_(dateKey, settings)) continue;

    const due = dateKey < today || (dateKey === today && nowMinutes >= absentMinutes);
    const req = userAbsences.find(r => r.startDate <= dateKey && r.endDate >= dateKey) || null;
    const presenceReq = userPresences.find(r => r.startDate <= dateKey && r.endDate >= dateKey) || null;
    const existing = existingByDay.get(day);

    // Jika rekod fizikal sudah menjadi TIDAK HADIR (contohnya selepas alert
    // Keberadaan berjaya dihantar), jangan timpa status tersebut.
    if (existing && String(existing.status || '').trim().toUpperCase() === 'TIDAK HADIR') {
      continue;
    }

    if (presenceReq) {
      // Keberadaan tidak terus ditukar kepada TIDAK HADIR pada ABSENT_AFTER.
      // Ia kekal sebagai Belum Hadir sehingga punch sebenar atau proses tamat
      // Keberadaan menghantar alert dan menulis rekod fizikal.
      const presenceReason = presenceRequestReason_(presenceReq, '');
      if (existing) {
        if (!existing.inTime && !existing.outTime) {
          existing.status = 'BELUM HADIR';
          existing.source = 'KEBERADAAN';
          existing.editedBy = presenceReq.reviewedBy || '';
          existing.reason = presenceReason;
        }
      } else {
        const added = {
          day, date: dateKey, status: 'BELUM HADIR', inTime: '', outTime: '',
          source: 'KEBERADAAN', editedBy: presenceReq.reviewedBy || '',
          reason: presenceReason
        };
        records.push(added);
        existingByDay.set(day, added);
      }
      continue;
    }

    // Permohonan Tidak Hadir aktif dipaparkan walaupun belum melepasi
    // ABSENT_AFTER. Tanpa permohonan, hanya tarikh yang telah due ditanda.
    if (!req && !due) continue;
    const absenceReason = req
      ? `${req.type}${req.status === 'MENUNGGU' ? ' — MENUNGGU KELULUSAN' : ''}`
      : 'TIADA PENJELASAN';

    if (existing) {
      if (!existing.inTime && !existing.outTime) {
        existing.status = 'TIDAK HADIR';
        existing.source = req ? 'TIDAK_HADIR' : 'AUTO_TIDAK_HADIR';
        existing.editedBy = req && req.reviewedBy ? req.reviewedBy : 'SISTEM';
        existing.reason = absenceReason;
      }
      continue;
    }

    const added = {
      day, date: dateKey, status: 'TIDAK HADIR', inTime: '', outTime: '',
      source: req ? 'TIDAK_HADIR' : 'AUTO_TIDAK_HADIR', editedBy: req && req.reviewedBy ? req.reviewedBy : 'SISTEM',
      reason: absenceReason
    };
    records.push(added);
    existingByDay.set(day, added);
  }

  const reviewRows = readTimeReviewRows_().filter(r => r.email === user.email && r.date >= systemStartDate && String(r.date || '').slice(0,7) === monthKey);
  records.forEach(r => {
    const dayReviews = reviewRows.filter(x => x.date === r.date);
    r.reviewState = timeReviewStatementForCard_(dayReviews, r.statusFlags || []);
    r.reviewItems = dayReviews.map(x => ({type:x.type,session:Number(x.session||1),reviewStatus:x.reviewStatus||'',reviewerJobTitle:getReviewerJobTitleFromEmail_(x.reviewedBy),reviewedAt:x.reviewedAt?formatDateTime_(x.reviewedAt):'',comment:x.comment||''}));
  });
  records.sort((a,b) => a.day - b.day);
  return {
    month: monthKey, daysInMonth,
    cardNumber: String(Math.max(1, Number(user.row || 2) - 1)).padStart(3, '0'),
    schoolName: settings.SCHOOL_NAME, department: settings.SCHOOL_NAME,
    user: publicUser_(user), records
  };
}

function punch(token, type, location, clientInfo) {
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
