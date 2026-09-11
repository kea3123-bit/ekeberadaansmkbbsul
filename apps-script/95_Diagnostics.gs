// ---------- Read-only runtime diagnostics ----------
// Run manually from the Apps Script editor after a deployment.
// This function is intentionally NOT exposed through the GitHub Pages bridge.
// Launch-performance Phase 4 + client telemetry source marker: 2026-09-11.
function diagnosePerformanceBackend() {
  const started = Date.now();
  const marks = {};
  const measure = (name, fn) => {
    const t = Date.now();
    const value = fn();
    marks[name] = Date.now() - t;
    return value;
  };

  const settings = measure('settingsMs', () => getSettings_());
  const users = measure('usersMs', () => getAllUsers_());
  const attendanceIndex = measure('attendanceIndexMs', () => getAttendanceRowIndex_());
  const todayRows = measure('attendanceTodayMs', () => getAttendanceByDate_(todayKey_()));
  const absenceRows = measure('absenceRowsMs', () => readAbsenceRows_());
  const timeReviewRows = measure('timeReviewRowsMs', () => readTimeReviewRows_());

  measure('settingsWarmMs', () => getSettings_());
  measure('usersWarmMs', () => getAllUsers_());
  measure('attendanceIndexWarmMs', () => getAttendanceRowIndex_());
  measure('attendanceTodayWarmMs', () => getAttendanceByDate_(todayKey_()));
  measure('absenceRowsWarmMs', () => readAbsenceRows_());
  measure('timeReviewRowsWarmMs', () => readTimeReviewRows_());

  const result = {
    ok: true,
    timezone: EK.TIMEZONE,
    spreadsheetTimezone: getSpreadsheet_().getSpreadsheetTimeZone(),
    today: todayKey_(),
    systemMode: settings.SYSTEM_MODE,
    counts: {
      users: users.length,
      attendanceRows: Math.max(0, Number(attendanceIndex.lastRow || 1) - 1),
      attendanceToday: todayRows.length,
      absenceRows: absenceRows.length,
      timeReviewRows: timeReviewRows.length
    },
    launchReadiness: {
      targetDailyUsers: 100,
      attendanceIndex: 'date+email direct lookup / daily batched row slots',
      ipCheck: 'hour registry cache; strict global ordering only for BLOCK policy',
      punchLock: 'daily batched row slots + direct per-user row writes; global lock only for one-time slot allocation and strict BLOCK IP policy',
      clientTelemetry: 'GitHub Pages public IPv4/IPv6 lookup + trusted-device background metadata sync',
      note: 'Phase 4 burst harness is the launch gate; client telemetry is best-effort and does not block app entry.'
    },
    timingsMs: marks,
    totalMs: Date.now() - started
  };

  console.log(JSON.stringify(result));
  return result;
}
