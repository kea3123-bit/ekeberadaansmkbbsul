from pathlib import Path
import re

# --- Frontend: robust public IPv4/IPv6 + richer device telemetry ---
p = Path('Scripts.html')
text = p.read_text()
start = text.index('  // ---------- Client info / public IP ----------')
end = text.index('  // ---------- Login (v12:', start)
new_block = r'''  // ---------- Client info / public IP / device telemetry ----------
  function getClientInstanceId(){
    const key='ek_client_instance_id';
    let id=safeLocalGet(key);
    if(id)return id;
    try{id=crypto.randomUUID();}catch(e){id='ci-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,12);}
    safeLocalSet(key,id);
    return id;
  }

  function inferClientDeviceType(){
    const ua=navigator.userAgent||'',touch=Number(navigator.maxTouchPoints||0);
    if(/iPad|Tablet/i.test(ua)||(navigator.platform==='MacIntel'&&touch>1))return 'Tablet';
    if(/iPhone|Android.+Mobile|Mobile/i.test(ua))return 'Telefon';
    if(/Android/i.test(ua))return 'Tablet/Android';
    return 'Komputer';
  }

  function clientDisplayMode(){
    try{
      if(window.matchMedia&&window.matchMedia('(display-mode: standalone)').matches)return 'PWA/Standalone';
      if(navigator.standalone===true)return 'PWA/Standalone';
    }catch(e){}
    return 'Browser';
  }

  function clientNetworkFields(){
    const c=navigator.connection||navigator.mozConnection||navigator.webkitConnection||{};
    return {
      networkType:String(c.effectiveType||c.type||''),
      networkDownlinkMbps:Number.isFinite(Number(c.downlink))?Number(c.downlink):'',
      networkRttMs:Number.isFinite(Number(c.rtt))?Number(c.rtt):'',
      saveData:!!c.saveData
    };
  }

  function baseClientInfo(ipv4='',ipv6='',extra={}){
    const sw=screen?.width||0,sh=screen?.height||0,
          vw=window.innerWidth||0,vh=window.innerHeight||0,
          net=clientNetworkFields();
    const v4=String(ipv4||'').trim(),v6=String(ipv6||'').trim();
    return {
      ip:v4||v6,
      publicIpv4:v4,
      publicIpv6:v6,
      ipSource:(v4||v6)?'browser-public-ip':'',
      clientInstanceId:getClientInstanceId(),
      userAgent:navigator.userAgent||'',
      platform:(navigator.userAgentData&&navigator.userAgentData.platform)||navigator.platform||'',
      vendor:navigator.vendor||'',
      timezone:'Asia/Kuala_Lumpur',
      browserTimezone:(Intl.DateTimeFormat().resolvedOptions().timeZone||''),
      language:navigator.language||'',
      deviceType:inferClientDeviceType(),
      deviceModel:String(extra.model||''),
      architecture:String(extra.architecture||''),
      platformVersion:String(extra.platformVersion||''),
      browserBrands:String(extra.browserBrands||''),
      screen:sw&&sh?`${sw}x${sh}`:'',
      viewport:vw&&vh?`${vw}x${vh}`:'',
      pixelRatio:Number(window.devicePixelRatio||1),
      touchPoints:Number(navigator.maxTouchPoints||0),
      hardwareConcurrency:Number(navigator.hardwareConcurrency||0)||'',
      deviceMemoryGb:Number(navigator.deviceMemory||0)||'',
      colorDepth:Number(screen?.colorDepth||0)||'',
      displayMode:clientDisplayMode(),
      networkType:net.networkType,
      networkDownlinkMbps:net.networkDownlinkMbps,
      networkRttMs:net.networkRttMs,
      saveData:net.saveData,
      _at:Date.now()
    };
  }

  async function getClientHintsExtra(){
    try{
      const uad=navigator.userAgentData;
      if(!uad?.getHighEntropyValues)return {};
      const v=await uad.getHighEntropyValues(['model','architecture','platformVersion','fullVersionList']);
      const brands=(v.fullVersionList||uad.brands||[]).map(x=>`${x.brand} ${x.version}`).join(', ');
      return {model:v.model||'',architecture:v.architecture||'',platformVersion:v.platformVersion||'',browserBrands:brands};
    }catch(e){return {};}
  }

  function getClientInfoFast(){
    const cached=state.networkInfo;
    if(cached&&Date.now()-(cached._at||0)<15*60*1000)return cached;
    getClientNetworkInfo(false).catch(()=>{});
    return baseClientInfo();
  }

  async function fetchPublicIpJson(url,timeoutMs=1600){
    const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),timeoutMs);
    try{
      const r=await fetch(url,{cache:'no-store',signal:ctrl.signal});
      if(!r.ok)return '';
      const j=await r.json();
      return String(j?.ip||'').trim();
    }catch(e){return '';}
    finally{clearTimeout(timer);}
  }

  async function getClientNetworkInfo(force=false){
    const cached=state.networkInfo;
    if(!force&&cached&&Date.now()-(cached._at||0)<15*60*1000)return cached;
    if(!force&&state.networkPromise)return state.networkPromise;

    const task=(async()=>{
      const [v4r,v6r,hintsr]=await Promise.allSettled([
        fetchPublicIpJson('https://api.ipify.org?format=json',1600),
        fetchPublicIpJson('https://api6.ipify.org?format=json',1600),
        getClientHintsExtra()
      ]);
      let ipv4=v4r.status==='fulfilled'?String(v4r.value||'').trim():'',
          ipv6=v6r.status==='fulfilled'?String(v6r.value||'').trim():'',
          hints=hintsr.status==='fulfilled'?(hintsr.value||{}):{};
      if(ipv4&&ipv4.includes(':')){if(!ipv6)ipv6=ipv4;ipv4='';}
      if(ipv6&&!ipv6.includes(':')){if(!ipv4)ipv4=ipv6;ipv6='';}
      if(!ipv4){try{ipv4=await getPublicIpJsonp();}catch(e){ipv4='';}}
      if(!ipv4&&!ipv6){
        const dual=await fetchPublicIpJson('https://api64.ipify.org?format=json',1200);
        if(dual.includes(':'))ipv6=dual;else ipv4=dual;
      }
      const info=baseClientInfo(ipv4,ipv6,hints);
      state.networkInfo=info;
      return info;
    })();

    if(!force)state.networkPromise=task;
    try{return await task;}
    finally{if(state.networkPromise===task)state.networkPromise=null;}
  }

  async function getClientInfoForAuth(){
    try{return await getClientNetworkInfo(false);}catch(e){return getClientInfoFast();}
  }

  async function syncClientTelemetry(){
    if(!state.token)return false;
    try{
      const info=await getClientNetworkInfo(false);
      await runServer('syncClientTelemetry',state.token,loadStoredDevice(),info);
      return true;
    }catch(e){return false;}
  }

  function getPublicIpJsonp(){
    return new Promise((resolve,reject)=>{
      const cb='ekIpCb_'+Math.random().toString(36).slice(2);
      const script=document.createElement('script');
      const timer=setTimeout(()=>cleanup(new Error('IP timeout')),1500);
      function cleanup(err,value){clearTimeout(timer);try{delete window[cb];}catch(e){}script.remove();err?reject(err):resolve(value||'');}
      window[cb]=data=>cleanup(null,String(data&&data.ip||'').trim());
      script.onerror=()=>cleanup(new Error('IP lookup gagal'));
      script.src='https://api.ipify.org?format=jsonp&callback='+encodeURIComponent(cb);
      document.head.appendChild(script);
    });
  }

'''
text = text[:start] + new_block + text[end:]
text = text.replace("const clientInfo=getClientInfoFast();\n      const res=await runServer('loginWithPin'", "const clientInfo=await getClientInfoForAuth();\n      const res=await runServer('loginWithPin'", 1)
text = text.replace("const clientInfo=getClientInfoFast();\n      const res=await runServer('setFirstPin'", "const clientInfo=await getClientInfoForAuth();\n      const res=await runServer('setFirstPin'", 1)
text = text.replace("setTimeout(()=>getClientNetworkInfo(false).catch(()=>{}),0);", "setTimeout(()=>syncClientTelemetry().catch(()=>{}),0);", 1)
old = "const rows=devices.length?devices.map(d=>`<tr><td><b>${esc(d.deviceName||'Peranti')}</b><small class=\"table-sub\">${esc(d.platform||'')} · ${esc(d.browser||'')}</small></td><td>${esc(d.lastSeenAt||'—')}<small class=\"table-sub\">IP: ${esc(d.lastIp||'—')}</small></td><td>${esc(d.expiresAt||'—')}</td><td><button class=\"action-link warn-link\" onclick='revokeTrustedDevice(${JSON.stringify(d.deviceId)},${JSON.stringify(email)},${JSON.stringify(name||email)})'>Logout peranti</button></td></tr>`).join(''):'<tr><td colspan=\"4\" class=\"empty-cell\">Tiada trusted device aktif.</td></tr>';"
new = "const rows=devices.length?devices.map(d=>{const meta=[d.deviceType,d.model,d.platform,d.browser].filter(Boolean).join(' · '),tech=[d.screen,d.network].filter(Boolean).join(' · '),ip4=d.publicIpv4||(!String(d.lastIp||'').includes(':')?d.lastIp:''),ip6=d.publicIpv6||(String(d.lastIp||'').includes(':')?d.lastIp:'');return `<tr><td><b>${esc(d.deviceName||'Peranti')}</b><small class=\"table-sub\">${esc(meta||'Maklumat peranti terhad')}</small>${tech?`<small class=\"table-sub\">${esc(tech)}</small>`:''}</td><td>${esc(d.lastSeenAt||'—')}<small class=\"table-sub\">IPv4: ${esc(ip4||'—')}</small><small class=\"table-sub\">IPv6: ${esc(ip6||'—')}</small></td><td>${esc(d.expiresAt||'—')}</td><td><button class=\"action-link warn-link\" onclick='revokeTrustedDevice(${JSON.stringify(d.deviceId)},${JSON.stringify(email)},${JSON.stringify(name||email)})'>Logout peranti</button></td></tr>`;}).join(''):'<tr><td colspan=\"4\" class=\"empty-cell\">Tiada trusted device aktif.</td></tr>';"
if old not in text:
    raise SystemExit('trusted device modal anchor not found')
text = text.replace(old,new,1)
p.write_text(text)

# --- Core schema: append telemetry columns, preserving legacy first 13 positions ---
p = Path('apps-script/00_Core.gs')
text = p.read_text()
old = "TRUSTED_DEVICE_HEADERS: ['DeviceID', 'Emel', 'NamaPeranti', 'Platform', 'Pelayar', 'IPTerakhir', 'DiciptaPada', 'DilihatTerakhir', 'TamatPada', 'Aktif', 'VersiSesi', 'TokenHash', 'SebabBatal'],"
new = "TRUSTED_DEVICE_HEADERS: ['DeviceID', 'Emel', 'NamaPeranti', 'Platform', 'Pelayar', 'IPTerakhir', 'DiciptaPada', 'DilihatTerakhir', 'TamatPada', 'Aktif', 'VersiSesi', 'TokenHash', 'SebabBatal', 'ClientInstanceID', 'JenisPeranti', 'ModelPeranti', 'Skrin', 'Viewport', 'PixelRatio', 'TouchPoints', 'CPU', 'RAMGB', 'Rangkaian', 'IPv4Awam', 'IPv6Awam', 'UserAgent', 'ZonMasa', 'Bahasa'],"
if old not in text: raise SystemExit('trusted headers anchor not found')
text = text.replace(old,new,1)
p.write_text(text)

# --- Auth normalization + richer historical login log ---
p = Path('apps-script/10_Auth.gs')
text = p.read_text()
old = r'''function normalizeClientInfo_(info) {
  info = info && typeof info === 'object' ? info : {};
  const ip = normalizeIp_(info.ip);
  return {
    ip,
    userAgent: String(info.userAgent || '').trim().slice(0, 500),
    platform: String(info.platform || '').trim().slice(0, 120),
    timezone: String(info.timezone || '').trim().slice(0, 100),
    language: String(info.language || '').trim().slice(0, 60)
  };
}'''
new = r'''function normalizeClientInfo_(info) {
  info = info && typeof info === 'object' ? info : {};
  const publicIpv4 = normalizeIp_(info.publicIpv4);
  const publicIpv6 = normalizeIp_(info.publicIpv6);
  const suppliedIp = normalizeIp_(info.ip);
  const ip = publicIpv4 || suppliedIp || publicIpv6;
  const num = (value, min, max) => {
    const n = Number(value);
    return Number.isFinite(n) && n >= min && n <= max ? n : '';
  };
  return {
    ip,
    publicIpv4,
    publicIpv6,
    ipSource:String(info.ipSource || '').trim().slice(0, 60),
    clientInstanceId:String(info.clientInstanceId || '').trim().slice(0, 120),
    userAgent: String(info.userAgent || '').trim().slice(0, 500),
    platform: String(info.platform || '').trim().slice(0, 120),
    vendor: String(info.vendor || '').trim().slice(0, 120),
    timezone: String(info.timezone || '').trim().slice(0, 100),
    browserTimezone: String(info.browserTimezone || '').trim().slice(0, 100),
    language: String(info.language || '').trim().slice(0, 60),
    deviceType:String(info.deviceType || '').trim().slice(0, 80),
    deviceModel:String(info.deviceModel || '').trim().slice(0, 160),
    architecture:String(info.architecture || '').trim().slice(0, 80),
    platformVersion:String(info.platformVersion || '').trim().slice(0, 100),
    browserBrands:String(info.browserBrands || '').trim().slice(0, 300),
    screen:String(info.screen || '').trim().slice(0, 60),
    viewport:String(info.viewport || '').trim().slice(0, 60),
    pixelRatio:num(info.pixelRatio,0.1,20),
    touchPoints:num(info.touchPoints,0,100),
    hardwareConcurrency:num(info.hardwareConcurrency,0,256),
    deviceMemoryGb:num(info.deviceMemoryGb,0,1024),
    colorDepth:num(info.colorDepth,0,128),
    displayMode:String(info.displayMode || '').trim().slice(0, 60),
    networkType:String(info.networkType || '').trim().slice(0, 60),
    networkDownlinkMbps:num(info.networkDownlinkMbps,0,100000),
    networkRttMs:num(info.networkRttMs,0,600000),
    saveData:!!info.saveData
  };
}'''
if old not in text: raise SystemExit('normalizeClientInfo anchor not found')
text = text.replace(old,new,1)
old = r'''    const device = [
      ci.platform ? `Platform=${ci.platform}` : '',
      ci.timezone ? `TZ=${ci.timezone}` : '',
      ci.language ? `Lang=${ci.language}` : '',
      ci.userAgent || ''
    ].filter(Boolean).join(' | ');'''
new = r'''    const network = [
      ci.networkType || '',
      ci.networkDownlinkMbps !== '' ? `${ci.networkDownlinkMbps}Mbps` : '',
      ci.networkRttMs !== '' ? `RTT ${ci.networkRttMs}ms` : '',
      ci.saveData ? 'SaveData' : ''
    ].filter(Boolean).join(' ');
    const device = [
      ci.deviceType ? `Type=${ci.deviceType}` : '',
      ci.deviceModel ? `Model=${ci.deviceModel}` : '',
      ci.platform ? `Platform=${ci.platform}` : '',
      ci.screen ? `Screen=${ci.screen}` : '',
      ci.viewport ? `Viewport=${ci.viewport}` : '',
      ci.touchPoints !== '' ? `Touch=${ci.touchPoints}` : '',
      ci.hardwareConcurrency !== '' ? `CPU=${ci.hardwareConcurrency}` : '',
      ci.deviceMemoryGb !== '' ? `RAM=${ci.deviceMemoryGb}GB` : '',
      network ? `Network=${network}` : '',
      ci.clientInstanceId ? `Client=${ci.clientInstanceId}` : '',
      ci.timezone ? `TZ=${ci.timezone}` : '',
      ci.language ? `Lang=${ci.language}` : '',
      ci.userAgent || ''
    ].filter(Boolean).join(' | ');'''
if old not in text: raise SystemExit('login device block anchor not found')
text = text.replace(old,new,1)
text = text.replace("String(detail || '')\n    ]);", "`${String(detail || '')}${tracking && ci.publicIpv6 ? `; IPv6=${ci.publicIpv6}` : ''}`\n    ]);", 1)
p.write_text(text)

# --- Trusted device schema/parsing/storage + telemetry sync endpoint ---
p = Path('apps-script/11_Sessions.gs')
text = p.read_text()
old = r'''    tokenHash:String(v[11] || '').trim(),
    revokeReason:String(v[12] || '').trim()
  };'''
new = r'''    tokenHash:String(v[11] || '').trim(),
    revokeReason:String(v[12] || '').trim(),
    clientInstanceId:String(v[13] || '').trim(),
    deviceType:String(v[14] || '').trim(),
    model:String(v[15] || '').trim(),
    screen:String(v[16] || '').trim(),
    viewport:String(v[17] || '').trim(),
    pixelRatio:v[18] === '' ? '' : Number(v[18]),
    touchPoints:v[19] === '' ? '' : Number(v[19]),
    cpu:v[20] === '' ? '' : Number(v[20]),
    ramGb:v[21] === '' ? '' : Number(v[21]),
    network:String(v[22] || '').trim(),
    publicIpv4:String(v[23] || '').trim(),
    publicIpv6:String(v[24] || '').trim(),
    userAgent:String(v[25] || '').trim(),
    timezone:String(v[26] || '').trim(),
    language:String(v[27] || '').trim()
  };'''
if old not in text: raise SystemExit('trusted parser anchor not found')
text = text.replace(old,new,1)
anchor = "function newTrustedDeviceSecret_() {"
helpers = r'''function trustedDeviceNetworkLabel_(ci) {
  return [
    ci.networkType || '',
    ci.networkDownlinkMbps !== '' ? `${ci.networkDownlinkMbps}Mbps` : '',
    ci.networkRttMs !== '' ? `RTT ${ci.networkRttMs}ms` : '',
    ci.saveData ? 'SaveData' : '',
    ci.displayMode || ''
  ].filter(Boolean).join(' ').slice(0, 220);
}

function trustedDeviceTelemetryValues_(ci) {
  return [
    ci.clientInstanceId || '', ci.deviceType || '', ci.deviceModel || '',
    ci.screen || '', ci.viewport || '', ci.pixelRatio === '' ? '' : ci.pixelRatio,
    ci.touchPoints === '' ? '' : ci.touchPoints,
    ci.hardwareConcurrency === '' ? '' : ci.hardwareConcurrency,
    ci.deviceMemoryGb === '' ? '' : ci.deviceMemoryGb,
    trustedDeviceNetworkLabel_(ci), ci.publicIpv4 || '', ci.publicIpv6 || '',
    ci.userAgent || '', ci.timezone || '', ci.language || ''
  ];
}

'''
if anchor not in text: raise SystemExit('trusted helper anchor not found')
text = text.replace(anchor, helpers+anchor,1)
old = r'''  sh.appendRow([
    deviceId, user.email, deviceNameFromClientInfo_(ci), platformNameFromClientInfo_(ci), browserNameFromUa_(ci.userAgent),
    ci.ip || '', now, now, exp, true, Math.max(1, Number(user.sessionVersion || 1)),
    hashTrustedDeviceSecret_(deviceId, secret), ''
  ]);'''
new = r'''  sh.appendRow([
    deviceId, user.email, deviceNameFromClientInfo_(ci), platformNameFromClientInfo_(ci), browserNameFromUa_(ci.userAgent),
    ci.ip || '', now, now, exp, true, Math.max(1, Number(user.sessionVersion || 1)),
    hashTrustedDeviceSecret_(deviceId, secret), '', ...trustedDeviceTelemetryValues_(ci)
  ]);'''
if old not in text: raise SystemExit('trusted append anchor not found')
text = text.replace(old,new,1)
# Replace whole touch function for consistent extended metadata writes.
pattern = re.compile(r"function touchTrustedDevice_\(rec, clientInfo, extendExpiry\) \{.*?\n\}\n\nfunction cleanupTrustedDevices_", re.S)
new_touch = r'''function touchTrustedDevice_(rec, clientInfo, extendExpiry) {
  const ci = normalizeClientInfo_(clientInfo);
  const now = new Date();
  const nextPlatform = platformNameFromClientInfo_(ci);
  const nextBrowser = browserNameFromUa_(ci.userAgent);
  const nextName = `${nextPlatform} · ${nextBrowser}`;
  const nextIp = ci.ip || rec.lastIp || '';
  const telemetry = trustedDeviceTelemetryValues_(ci);
  const lastSeenMs = dateMillis_(rec.lastSeenAt);
  const recent = lastSeenMs > 0 && (now.getTime() - lastSeenMs) < EK_TRUSTED_TOUCH_MIN_INTERVAL_MS_;
  const sameFingerprint = nextName === String(rec.deviceName || '') &&
    nextPlatform === String(rec.platform || '') &&
    nextBrowser === String(rec.browser || '') &&
    nextIp === String(rec.lastIp || '') &&
    String(ci.clientInstanceId || '') === String(rec.clientInstanceId || '') &&
    String(ci.deviceType || '') === String(rec.deviceType || '') &&
    String(ci.deviceModel || '') === String(rec.model || '') &&
    String(ci.screen || '') === String(rec.screen || '') &&
    String(ci.publicIpv4 || '') === String(rec.publicIpv4 || '') &&
    String(ci.publicIpv6 || '') === String(rec.publicIpv6 || '');

  if (extendExpiry && recent && sameFingerprint) return rec;

  const previousExpiryMs = dateMillis_(rec.expiresAt);
  const sh = ensureTrustedDevicesSheet_();
  const exp = extendExpiry ? new Date(Date.now() + EK.SESSION.REMEMBER_DAYS * 24 * 60 * 60 * 1000) : rec.expiresAt;
  sh.getRange(rec.row, 3, 1, 7).setValues([[
    nextName, nextPlatform, nextBrowser, nextIp,
    rec.createdAt || now, now, exp
  ]]);
  sh.getRange(rec.row, 14, 1, telemetry.length).setValues([telemetry]);
  rec.deviceName = nextName;
  rec.platform = nextPlatform;
  rec.browser = nextBrowser;
  rec.lastIp = nextIp;
  rec.lastSeenAt = now;
  rec.expiresAt = exp;
  rec.clientInstanceId = ci.clientInstanceId || '';
  rec.deviceType = ci.deviceType || '';
  rec.model = ci.deviceModel || '';
  rec.screen = ci.screen || '';
  rec.viewport = ci.viewport || '';
  rec.pixelRatio = ci.pixelRatio;
  rec.touchPoints = ci.touchPoints;
  rec.cpu = ci.hardwareConcurrency;
  rec.ramGb = ci.deviceMemoryGb;
  rec.network = trustedDeviceNetworkLabel_(ci);
  rec.publicIpv4 = ci.publicIpv4 || '';
  rec.publicIpv6 = ci.publicIpv6 || '';
  rec.userAgent = ci.userAgent || '';
  rec.timezone = ci.timezone || '';
  rec.language = ci.language || '';
  if (extendExpiry && previousExpiryMs && previousExpiryMs - now.getTime() < 5 * 60 * 1000) {
    invalidateTrustedDevicesCache_();
  }
  return rec;
}

function cleanupTrustedDevices_'''
text2,n = pattern.subn(new_touch,text,count=1)
if n != 1: raise SystemExit(f'touch replacement count={n}')
text = text2
old = r'''function publicTrustedDevice_(d) {
  return {
    deviceId:d.deviceId,
    deviceName:d.deviceName || 'Peranti',
    platform:d.platform || '',
    browser:d.browser || '',
    lastIp:d.lastIp || '',
    createdAt:d.createdAt ? formatDateTime_(d.createdAt) : '',
    lastSeenAt:d.lastSeenAt ? formatDateTime_(d.lastSeenAt) : '',
    expiresAt:d.expiresAt ? formatDateTime_(d.expiresAt) : '',
    active:!!d.active,
    revokeReason:d.revokeReason || ''
  };
}'''
new = r'''function publicTrustedDevice_(d) {
  return {
    deviceId:d.deviceId,
    deviceName:d.deviceName || 'Peranti',
    platform:d.platform || '', browser:d.browser || '', lastIp:d.lastIp || '',
    clientInstanceId:d.clientInstanceId || '', deviceType:d.deviceType || '', model:d.model || '',
    screen:d.screen || '', viewport:d.viewport || '', pixelRatio:d.pixelRatio === '' ? '' : d.pixelRatio,
    touchPoints:d.touchPoints === '' ? '' : d.touchPoints, cpu:d.cpu === '' ? '' : d.cpu,
    ramGb:d.ramGb === '' ? '' : d.ramGb, network:d.network || '',
    publicIpv4:d.publicIpv4 || '', publicIpv6:d.publicIpv6 || '',
    timezone:d.timezone || '', language:d.language || '',
    createdAt:d.createdAt ? formatDateTime_(d.createdAt) : '',
    lastSeenAt:d.lastSeenAt ? formatDateTime_(d.lastSeenAt) : '',
    expiresAt:d.expiresAt ? formatDateTime_(d.expiresAt) : '',
    active:!!d.active,
    revokeReason:d.revokeReason || ''
  };
}'''
if old not in text: raise SystemExit('public trusted anchor not found')
text = text.replace(old,new,1)
# Add authenticated background telemetry sync before logout.
anchor = "function logoutApp(token) {"
sync_fn = r'''function syncClientTelemetry(token, deviceCredential, clientInfo) {
  const session = verifySessionToken_(token);
  const user = requireSessionUser_(token);
  const ci = normalizeClientInfo_(clientInfo);
  let rec = null;
  if (session.d && deviceCredential) {
    rec = verifyTrustedDeviceCredential_(deviceCredential, user.email, session.d);
  } else if (session.d) {
    rec = findTrustedDeviceById_(session.d);
    if (!rec || rec.email !== user.email || !rec.active) rec = null;
  } else if (deviceCredential) {
    try { rec = verifyTrustedDeviceCredential_(deviceCredential, user.email); } catch (e) {}
  }
  if (!rec) return {ok:true,synced:false};
  touchTrustedDevice_(rec, ci, true);
  return {ok:true,synced:true,device:publicTrustedDevice_(rec)};
}

'''
if anchor not in text: raise SystemExit('logout anchor not found')
text = text.replace(anchor,sync_fn+anchor,1)
p.write_text(text)

# --- Setup self-heals extended headers and sizes ---
p = Path('apps-script/90_Setup.gs')
text = p.read_text()
text = text.replace("  sh.setColumnWidth(13, 260);\n  try { sh.hideColumns(12, 1); } catch (e) {}", "  sh.setColumnWidth(13, 260);\n  sh.setColumnWidth(14, 240); sh.setColumnWidths(15, 2, 150); sh.setColumnWidths(17, 2, 130);\n  sh.setColumnWidths(19, 4, 100); sh.setColumnWidth(23, 260); sh.setColumnWidths(24, 2, 190);\n  sh.setColumnWidth(26, 520); sh.setColumnWidths(27, 2, 160);\n  try { sh.hideColumns(12, 1); } catch (e) {}",1)
old = r'''  if (!sh) {
    setupTrustedDevicesSheet_(ss);
    sh = ss.getSheetByName(EK.SHEETS.TRUSTED_DEVICES);
  }
  EK_RUNTIME_SHEETS_[EK.SHEETS.TRUSTED_DEVICES] = sh;'''
new = r'''  if (!sh) {
    setupTrustedDevicesSheet_(ss);
    sh = ss.getSheetByName(EK.SHEETS.TRUSTED_DEVICES);
  } else {
    // Self-heal appended telemetry headers for an existing production sheet.
    ensureHeaders_(sh, EK.TRUSTED_DEVICE_HEADERS);
    styleHeader_(sh, EK.TRUSTED_DEVICE_HEADERS.length);
  }
  EK_RUNTIME_SHEETS_[EK.SHEETS.TRUSTED_DEVICES] = sh;'''
if old not in text: raise SystemExit('ensure trusted sheet anchor not found')
text = text.replace(old,new,1)
p.write_text(text)

# --- Bridge allowlist ---
p = Path('apps-script/Bridges.gs')
text = p.read_text()
text = text.replace("    'submitAbsenceRequest'", "    'submitAbsenceRequest',\n    'syncClientTelemetry'",1)
text = text.replace("    case 'submitAbsenceRequest': return submitAbsenceRequest.apply(null, args);", "    case 'submitAbsenceRequest': return submitAbsenceRequest.apply(null, args);\n    case 'syncClientTelemetry': return syncClientTelemetry.apply(null, args);",1)
p.write_text(text)

print('CLIENT_NETWORK_TELEMETRY_PATCH_OK')
