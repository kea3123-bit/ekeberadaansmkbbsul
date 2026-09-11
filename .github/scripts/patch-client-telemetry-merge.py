from pathlib import Path
import re

# Preserve previously-known telemetry when a fast resume sends only partial metadata.
p=Path('apps-script/11_Sessions.gs')
text=p.read_text()
old=r'''function trustedDeviceTelemetryValues_(ci) {
  return [
    ci.clientInstanceId || '', ci.deviceType || '', ci.deviceModel || '',
    ci.screen || '', ci.viewport || '', ci.pixelRatio === '' ? '' : ci.pixelRatio,
    ci.touchPoints === '' ? '' : ci.touchPoints,
    ci.hardwareConcurrency === '' ? '' : ci.hardwareConcurrency,
    ci.deviceMemoryGb === '' ? '' : ci.deviceMemoryGb,
    trustedDeviceNetworkLabel_(ci), ci.publicIpv4 || '', ci.publicIpv6 || '',
    ci.userAgent || '', ci.timezone || '', ci.language || ''
  ];
}'''
new=r'''function trustedDeviceTelemetryValues_(ci, rec) {
  rec = rec || {};
  const pick = (incoming, existing) => incoming === '' || incoming == null ? (existing == null ? '' : existing) : incoming;
  return [
    pick(ci.clientInstanceId,rec.clientInstanceId), pick(ci.deviceType,rec.deviceType), pick(ci.deviceModel,rec.model),
    pick(ci.screen,rec.screen), pick(ci.viewport,rec.viewport), pick(ci.pixelRatio,rec.pixelRatio),
    pick(ci.touchPoints,rec.touchPoints), pick(ci.hardwareConcurrency,rec.cpu), pick(ci.deviceMemoryGb,rec.ramGb),
    trustedDeviceNetworkLabel_(ci) || rec.network || '', pick(ci.publicIpv4,rec.publicIpv4), pick(ci.publicIpv6,rec.publicIpv6),
    pick(ci.userAgent,rec.userAgent), pick(ci.timezone,rec.timezone), pick(ci.language,rec.language)
  ];
}'''
if old not in text: raise SystemExit('telemetry values anchor not found')
text=text.replace(old,new,1)
pattern=re.compile(r"function touchTrustedDevice_\(rec, clientInfo, extendExpiry\) \{.*?\n\}\n\nfunction cleanupTrustedDevices_",re.S)
new_touch=r'''function touchTrustedDevice_(rec, clientInfo, extendExpiry) {
  const ci = normalizeClientInfo_(clientInfo);
  const now = new Date();
  const nextPlatform = platformNameFromClientInfo_(ci);
  const nextBrowser = browserNameFromUa_(ci.userAgent);
  const nextName = `${nextPlatform} · ${nextBrowser}`;
  const nextIp = ci.ip || rec.lastIp || '';
  const telemetry = trustedDeviceTelemetryValues_(ci, rec);
  const [nextClientInstanceId,nextDeviceType,nextModel,nextScreen,nextViewport,nextPixelRatio,nextTouchPoints,nextCpu,nextRamGb,nextNetwork,nextIpv4,nextIpv6,nextUserAgent,nextTimezone,nextLanguage] = telemetry;
  const lastSeenMs = dateMillis_(rec.lastSeenAt);
  const recent = lastSeenMs > 0 && (now.getTime() - lastSeenMs) < EK_TRUSTED_TOUCH_MIN_INTERVAL_MS_;
  const sameFingerprint = nextName === String(rec.deviceName || '') &&
    nextPlatform === String(rec.platform || '') && nextBrowser === String(rec.browser || '') &&
    nextIp === String(rec.lastIp || '') && String(nextClientInstanceId || '') === String(rec.clientInstanceId || '') &&
    String(nextDeviceType || '') === String(rec.deviceType || '') && String(nextModel || '') === String(rec.model || '') &&
    String(nextScreen || '') === String(rec.screen || '') && String(nextIpv4 || '') === String(rec.publicIpv4 || '') &&
    String(nextIpv6 || '') === String(rec.publicIpv6 || '');

  if (extendExpiry && recent && sameFingerprint) return rec;

  const previousExpiryMs = dateMillis_(rec.expiresAt);
  const sh = ensureTrustedDevicesSheet_();
  const exp = extendExpiry ? new Date(Date.now() + EK.SESSION.REMEMBER_DAYS * 24 * 60 * 60 * 1000) : rec.expiresAt;
  sh.getRange(rec.row, 3, 1, 7).setValues([[
    nextName, nextPlatform, nextBrowser, nextIp,
    rec.createdAt || now, now, exp
  ]]);
  sh.getRange(rec.row, 14, 1, telemetry.length).setValues([telemetry]);
  rec.deviceName=nextName; rec.platform=nextPlatform; rec.browser=nextBrowser; rec.lastIp=nextIp;
  rec.lastSeenAt=now; rec.expiresAt=exp; rec.clientInstanceId=nextClientInstanceId || '';
  rec.deviceType=nextDeviceType || ''; rec.model=nextModel || ''; rec.screen=nextScreen || ''; rec.viewport=nextViewport || '';
  rec.pixelRatio=nextPixelRatio; rec.touchPoints=nextTouchPoints; rec.cpu=nextCpu; rec.ramGb=nextRamGb;
  rec.network=nextNetwork || ''; rec.publicIpv4=nextIpv4 || ''; rec.publicIpv6=nextIpv6 || '';
  rec.userAgent=nextUserAgent || ''; rec.timezone=nextTimezone || ''; rec.language=nextLanguage || '';
  if (extendExpiry && previousExpiryMs && previousExpiryMs - now.getTime() < 5 * 60 * 1000) invalidateTrustedDevicesCache_();
  return rec;
}

function cleanupTrustedDevices_'''
text2,n=pattern.subn(new_touch,text,count=1)
if n!=1: raise SystemExit(f'touch replace count={n}')
p.write_text(text2)

# Avoid formatting/header writes on every trusted-device access; self-heal schema at most once per cache window.
p=Path('apps-script/90_Setup.gs')
text=p.read_text()
old=r'''  } else {
    // Self-heal appended telemetry headers for an existing production sheet.
    ensureHeaders_(sh, EK.TRUSTED_DEVICE_HEADERS);
    styleHeader_(sh, EK.TRUSTED_DEVICE_HEADERS.length);
  }
  EK_RUNTIME_SHEETS_[EK.SHEETS.TRUSTED_DEVICES] = sh;'''
new=r'''  } else {
    // Self-heal appended telemetry headers once per cache window, not on every
    // login/resume. This keeps device telemetry off the hot path.
    const schemaKey = 'EK_SCHEMA_TRUSTED_DEVICE_V2';
    let ready = false;
    try { ready = getScriptCache_().get(schemaKey) === '1'; } catch (e) {}
    if (!ready) {
      ensureHeaders_(sh, EK.TRUSTED_DEVICE_HEADERS);
      try { getScriptCache_().put(schemaKey, '1', 21600); } catch (e) {}
    }
  }
  EK_RUNTIME_SHEETS_[EK.SHEETS.TRUSTED_DEVICES] = sh;'''
if old not in text: raise SystemExit('schema self-heal anchor not found')
p.write_text(text.replace(old,new,1))

# Actual browser timezone is telemetry; official attendance timezone remains fixed server-side in EK.TIMEZONE.
p=Path('Scripts.html')
text=p.read_text()
text=text.replace("      timezone:'Asia/Kuala_Lumpur',\n      browserTimezone:(Intl.DateTimeFormat().resolvedOptions().timeZone||''),", "      timezone:(Intl.DateTimeFormat().resolvedOptions().timeZone||''),\n      browserTimezone:(Intl.DateTimeFormat().resolvedOptions().timeZone||''),",1)
p.write_text(text)
print('CLIENT_TELEMETRY_MERGE_OK')
