from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    s = p.read_text(encoding='utf-8')
    if old not in s:
        raise SystemExit(f'anchor not found: {path}: {old[:100]!r}')
    s2 = s.replace(old, new, 1)
    p.write_text(s2, encoding='utf-8')

# 1) Cache TTLs: write paths already invalidate these caches, so longer TTLs
# remove thundering-herd reads without delaying admin changes.
replace_once(
    'apps-script/00_Core.gs',
    "  USERS_TTL_SEC: 10,\n  SETTINGS_TTL_SEC: 30,\n  TRUSTED_DEVICES_TTL_SEC: 15",
    "  USERS_TTL_SEC: 300,\n  SETTINGS_TTL_SEC: 300,\n  TRUSTED_DEVICES_TTL_SEC: 60"
)

# 2) Trusted-device metadata is informational, not auth state. Persist it at
# most hourly for a stable device/IP instead of creating Sheets write churn on
# session renewals. Security mutations still use invalidateTrustedDevicesCache_.
replace_once(
    'apps-script/11_Sessions.gs',
    "const EK_TRUSTED_TOUCH_MIN_INTERVAL_MS_ = 5 * 60 * 1000;",
    "const EK_TRUSTED_TOUCH_MIN_INTERVAL_MS_ = 60 * 60 * 1000;"
)
replace_once(
    'apps-script/11_Sessions.gs',
    "  const sh = ensureTrustedDevicesSheet_();\n  const exp = extendExpiry ? new Date(Date.now() + EK.SESSION.REMEMBER_DAYS * 24 * 60 * 60 * 1000) : rec.expiresAt;",
    "  const previousExpiryMs = dateMillis_(rec.expiresAt);\n  const sh = ensureTrustedDevicesSheet_();\n  const exp = extendExpiry ? new Date(Date.now() + EK.SESSION.REMEMBER_DAYS * 24 * 60 * 60 * 1000) : rec.expiresAt;"
)
replace_once(
    'apps-script/11_Sessions.gs',
    "  rec.lastSeenAt = now;\n  rec.expiresAt = exp;\n  invalidateTrustedDevicesCache_();\n  return rec;",
    "  rec.lastSeenAt = now;\n  rec.expiresAt = exp;\n  // Do not invalidate the shared trusted-device cache for a normal metadata\n  // touch. A stale lastSeen/IP for <=60s does not change authentication. Only\n  // force invalidation when the previous credential was close to expiry, so a\n  // concurrent execution cannot reject a credential we have just extended.\n  if (extendExpiry && previousExpiryMs && previousExpiryMs - now.getTime() < 5 * 60 * 1000) {\n    invalidateTrustedDevicesCache_();\n  }\n  return rec;"
)

# 3) Cross-execution cache for TIDAK_HADIR. Approval/submission/cancel write
# paths call invalidateAbsenceRows_, which now removes this cache too.
replace_once(
    'apps-script/61_Absence.gs',
    "function readAbsenceRows_() {\n  if(Array.isArray(EK_RUNTIME_ABSENCE_ROWS_))return EK_RUNTIME_ABSENCE_ROWS_;\n  const sh=getSheetOrThrow_(EK.SHEETS.ABSENCE); if(sh.getLastRow()<2)return(EK_RUNTIME_ABSENCE_ROWS_=[]);\n  const vals=sh.getRange(2,1,sh.getLastRow()-1,EK.ABSENCE_HEADERS.length).getValues();\n  EK_RUNTIME_ABSENCE_ROWS_=vals.map((v,i)=>({row:i+2,id:String(v[0]||''),submittedAt:v[1]||'',submittedMs:dateValueMs_(v[1]),email:normalizeEmail_(v[2]),name:String(v[3]||''),category:String(v[4]||''),type:String(v[5]||''),startDate:dateCellToKey_(v[6]),endDate:dateCellToKey_(v[7]),note:String(v[8]||''),status:String(v[9]||'MENUNGGU'),reviewedBy:String(v[10]||''),reviewedAt:v[11]||'',comment:String(v[12]||''),updatedAt:v[13]||'',mode:String(v[14]||'TIDAK_HADIR').toUpperCase()==='KEBERADAAN'?'KEBERADAAN':'TIDAK_HADIR',startTime:normalizeOptionalTime_(v[15]),endTime:normalizeOptionalTime_(v[16]),jobTitle:String(v[17]||'')})).filter(r=>r.id);\n  return EK_RUNTIME_ABSENCE_ROWS_;\n}\nfunction invalidateAbsenceRows_(){EK_RUNTIME_ABSENCE_ROWS_=null;}",
    "const EK_ABSENCE_CACHE_KEY_ = 'EK_PERF_ABSENCE_ROWS_V1';\nconst EK_ABSENCE_CACHE_TTL_SEC_ = 60;\nfunction readAbsenceRows_() {\n  if(Array.isArray(EK_RUNTIME_ABSENCE_ROWS_))return EK_RUNTIME_ABSENCE_ROWS_;\n  const cached=cacheGetJson_(EK_ABSENCE_CACHE_KEY_);\n  if(Array.isArray(cached)){EK_RUNTIME_ABSENCE_ROWS_=cached;return cached;}\n  const sh=getSheetOrThrow_(EK.SHEETS.ABSENCE); if(sh.getLastRow()<2)return(EK_RUNTIME_ABSENCE_ROWS_=[]);\n  const vals=sh.getRange(2,1,sh.getLastRow()-1,EK.ABSENCE_HEADERS.length).getValues();\n  EK_RUNTIME_ABSENCE_ROWS_=vals.map((v,i)=>({row:i+2,id:String(v[0]||''),submittedAt:v[1]||'',submittedMs:dateValueMs_(v[1]),email:normalizeEmail_(v[2]),name:String(v[3]||''),category:String(v[4]||''),type:String(v[5]||''),startDate:dateCellToKey_(v[6]),endDate:dateCellToKey_(v[7]),note:String(v[8]||''),status:String(v[9]||'MENUNGGU'),reviewedBy:String(v[10]||''),reviewedAt:v[11]||'',comment:String(v[12]||''),updatedAt:v[13]||'',mode:String(v[14]||'TIDAK_HADIR').toUpperCase()==='KEBERADAAN'?'KEBERADAAN':'TIDAK_HADIR',startTime:normalizeOptionalTime_(v[15]),endTime:normalizeOptionalTime_(v[16]),jobTitle:String(v[17]||'')})).filter(r=>r.id);\n  cachePutJson_(EK_ABSENCE_CACHE_KEY_,EK_RUNTIME_ABSENCE_ROWS_,EK_ABSENCE_CACHE_TTL_SEC_);\n  return EK_RUNTIME_ABSENCE_ROWS_;\n}\nfunction invalidateAbsenceRows_(){EK_RUNTIME_ABSENCE_ROWS_=null;try{getScriptCache_().remove(EK_ABSENCE_CACHE_KEY_);}catch(e){}}"
)

# 4) Cross-execution cache for SEMAkan_WAKTU, with the same explicit write
# invalidation contract.
replace_once(
    'apps-script/60_TimeReview.gs',
    "function readTimeReviewRows_(){\n  if(Array.isArray(EK_RUNTIME_TIME_REVIEW_ROWS_))return EK_RUNTIME_TIME_REVIEW_ROWS_;\n  const sh=getTimeReviewSheet_();if(sh.getLastRow()<2)return(EK_RUNTIME_TIME_REVIEW_ROWS_=[]);\n  EK_RUNTIME_TIME_REVIEW_ROWS_=sh.getRange(2,1,sh.getLastRow()-1,EK.TIME_REVIEW_HEADERS.length).getValues().map((v,i)=>({\n    row:i+2,id:String(v[0]||''),createdAt:v[1]||'',date:dateCellToKey_(v[2]),email:normalizeEmail_(v[3]),name:String(v[4]||''),jobTitle:String(v[5]||''),category:String(v[6]||''),type:String(v[7]||''),session:Number(v[8]||1),recordTime:displayMalaysiaTime_(v[9]),referenceTime:displayMalaysiaTime_(v[10]),reviewStatus:String(v[11]||'BELUM DIAMBIL MAKLUM'),reviewedBy:String(v[12]||''),reviewerName:String(v[13]||''),reviewedAt:v[14]||'',comment:String(v[15]||'')\n  })).filter(r=>r.id);return EK_RUNTIME_TIME_REVIEW_ROWS_;\n}\nfunction invalidateTimeReviewRows_(){EK_RUNTIME_TIME_REVIEW_ROWS_=null;}",
    "const EK_TIME_REVIEW_CACHE_KEY_='EK_PERF_TIME_REVIEW_ROWS_V1';\nconst EK_TIME_REVIEW_CACHE_TTL_SEC_=60;\nfunction readTimeReviewRows_(){\n  if(Array.isArray(EK_RUNTIME_TIME_REVIEW_ROWS_))return EK_RUNTIME_TIME_REVIEW_ROWS_;\n  const cached=cacheGetJson_(EK_TIME_REVIEW_CACHE_KEY_);\n  if(Array.isArray(cached)){EK_RUNTIME_TIME_REVIEW_ROWS_=cached;return cached;}\n  const sh=getTimeReviewSheet_();if(sh.getLastRow()<2)return(EK_RUNTIME_TIME_REVIEW_ROWS_=[]);\n  EK_RUNTIME_TIME_REVIEW_ROWS_=sh.getRange(2,1,sh.getLastRow()-1,EK.TIME_REVIEW_HEADERS.length).getValues().map((v,i)=>({\n    row:i+2,id:String(v[0]||''),createdAt:v[1]||'',date:dateCellToKey_(v[2]),email:normalizeEmail_(v[3]),name:String(v[4]||''),jobTitle:String(v[5]||''),category:String(v[6]||''),type:String(v[7]||''),session:Number(v[8]||1),recordTime:displayMalaysiaTime_(v[9]),referenceTime:displayMalaysiaTime_(v[10]),reviewStatus:String(v[11]||'BELUM DIAMBIL MAKLUM'),reviewedBy:String(v[12]||''),reviewerName:String(v[13]||''),reviewedAt:v[14]||'',comment:String(v[15]||'')\n  })).filter(r=>r.id);cachePutJson_(EK_TIME_REVIEW_CACHE_KEY_,EK_RUNTIME_TIME_REVIEW_ROWS_,EK_TIME_REVIEW_CACHE_TTL_SEC_);return EK_RUNTIME_TIME_REVIEW_ROWS_;\n}\nfunction invalidateTimeReviewRows_(){EK_RUNTIME_TIME_REVIEW_ROWS_=null;try{getScriptCache_().remove(EK_TIME_REVIEW_CACHE_KEY_);}catch(e){}}"
)

# Allow the serialized punch path in Phase 2 to skip a full review-sheet scan
# when it knows the exact attendance slot was newly written.
replace_once(
    'apps-script/60_TimeReview.gs',
    "  const id = timeReviewId_(user,data.date,data.type,data.session);\n  const existing = readTimeReviewRows_().find(r=>r.id===id);\n  if (existing) return Object.assign({}, existing, {isNew:false});",
    "  const id = timeReviewId_(user,data.date,data.type,data.session);\n  if(!data.assumeNew){\n    const existing = readTimeReviewRows_().find(r=>r.id===id);\n    if (existing) return Object.assign({}, existing, {isNew:false});\n  }"
)

# 5) Session secret: avoid PropertiesService on every signed-session verify.
replace_once(
    'apps-script/10_Auth.gs',
    "function getSessionSecret_() {\n  const props = PropertiesService.getScriptProperties();\n  let secret = props.getProperty(EK.SESSION.SECRET_KEY);\n  if (!secret) {\n    secret = `${Utilities.getUuid()}-${Utilities.getUuid()}-${Date.now()}`;\n    props.setProperty(EK.SESSION.SECRET_KEY, secret);\n  }\n  return secret;\n}",
    "const EK_SESSION_SECRET_CACHE_KEY_='EK_PERF_SESSION_SECRET_V1';\nlet EK_RUNTIME_SESSION_SECRET_='';\nfunction getSessionSecret_() {\n  if(EK_RUNTIME_SESSION_SECRET_)return EK_RUNTIME_SESSION_SECRET_;\n  try{const cached=getScriptCache_().get(EK_SESSION_SECRET_CACHE_KEY_);if(cached){EK_RUNTIME_SESSION_SECRET_=cached;return cached;}}catch(e){}\n  const props = PropertiesService.getScriptProperties();\n  let secret = props.getProperty(EK.SESSION.SECRET_KEY);\n  if (!secret) {\n    secret = `${Utilities.getUuid()}-${Utilities.getUuid()}-${Date.now()}`;\n    props.setProperty(EK.SESSION.SECRET_KEY, secret);\n  }\n  EK_RUNTIME_SESSION_SECRET_=secret;\n  try{getScriptCache_().put(EK_SESSION_SECRET_CACHE_KEY_,secret,21600);}catch(e){}\n  return secret;\n}"
)

# 6) Pages origin allow-list: another ScriptProperties read removed from every RPC.
replace_once(
    'apps-script/Bridges.gs',
    "function getPagesWebOrigins_() {\n  var props = PropertiesService.getScriptProperties();\n  var multi = String(props.getProperty('EK_PAGES_ORIGINS') || '').trim();\n  var legacy = String(props.getProperty('EK_PAGES_ORIGIN') || '').trim();\n  var raw = multi || legacy || 'https://farshoffs.github.io,https://kea3123-bit.github.io';\n  var seen = {};\n  return raw.split(/[\\s,;]+/).map(function(value) {\n    return String(value || '').trim().replace(/\\/$/, '');\n  }).filter(function(value) {\n    if (!/^https:\\/\\/[A-Za-z0-9.-]+(?::\\d+)?$/.test(value)) return false;\n    if (seen[value]) return false;\n    seen[value] = true;\n    return true;\n  });\n}",
    "var EK_RUNTIME_PAGES_ORIGINS_=null;\nvar EK_PAGES_ORIGINS_CACHE_KEY_='EK_PERF_PAGES_ORIGINS_V1';\nfunction getPagesWebOrigins_() {\n  if(Array.isArray(EK_RUNTIME_PAGES_ORIGINS_))return EK_RUNTIME_PAGES_ORIGINS_.slice();\n  try{var cached=getScriptCache_().get(EK_PAGES_ORIGINS_CACHE_KEY_);if(cached){var parsed=JSON.parse(cached);if(Array.isArray(parsed)){EK_RUNTIME_PAGES_ORIGINS_=parsed;return parsed.slice();}}}catch(e){}\n  var props = PropertiesService.getScriptProperties();\n  var multi = String(props.getProperty('EK_PAGES_ORIGINS') || '').trim();\n  var legacy = String(props.getProperty('EK_PAGES_ORIGIN') || '').trim();\n  var raw = multi || legacy || 'https://farshoffs.github.io,https://kea3123-bit.github.io';\n  var seen = {};\n  var origins=raw.split(/[\\s,;]+/).map(function(value) {\n    return String(value || '').trim().replace(/\\/$/, '');\n  }).filter(function(value) {\n    if (!/^https:\\/\\/[A-Za-z0-9.-]+(?::\\d+)?$/.test(value)) return false;\n    if (seen[value]) return false;\n    seen[value] = true;\n    return true;\n  });\n  EK_RUNTIME_PAGES_ORIGINS_=origins;\n  try{getScriptCache_().put(EK_PAGES_ORIGINS_CACHE_KEY_,JSON.stringify(origins),300);}catch(e){}\n  return origins.slice();\n}"
)

# 7) gh-pages orphan checkout was preserving untracked node_modules. Clean all
# untracked/ignored files before copying _site back into the orphan branch.
replace_once(
    '.github/workflows/github-pages.yml',
    "          git checkout --orphan gh-pages\n          git rm -rf .\n          cp -a /tmp/eke-gh-pages/. .",
    "          git checkout --orphan gh-pages\n          git rm -rf . || true\n          git clean -fdx\n          cp -a /tmp/eke-gh-pages/. ."
)

# Keep local/source worktrees clean too.
Path('.gitignore').write_text('node_modules/\n_site/\n.DS_Store\n',encoding='utf-8')

# Persist the audit rationale in-repo.
audit = Path('docs/PERFORMANCE_AUDIT_100_USERS.md')
audit.write_text('''# Launch performance audit — 100 daily users\n\n## Scope\n\nAudit target: 100 active daily users with a morning punch burst, GitHub Pages frontend, Apps Script backend and Google Sheets persistence.\n\n## Key findings\n\n1. Static frontend size is bounded and content-hashed; growth over days is primarily backend data-access growth, not browser bundle growth.\n2. The punch path currently holds one ScriptLock while reading daily attendance, absence data, writing attendance/audit and creating review rows. That serializes a burst.\n3. A new attendance row invalidates the global attendance index, causing later requests to rebuild an A:B index over historical attendance. This cost grows with time.\n4. TIDAK_HADIR and SEMAKAN_WAKTU were only memoized per execution, so concurrent executions repeatedly reread full sheets.\n5. Session renewal can rewrite trusted-device metadata frequently and invalidate a cache shared by all users.\n6. Session-secret and Pages-origin properties were reread on every RPC.\n7. gh-pages orphan publication could preserve untracked node_modules after npm install, bloating the deployment branch.\n\n## Phase 1 applied\n\n- User/settings CacheService TTL: 300 seconds.\n- Trusted-device read cache: 60 seconds; stable-device metadata touch capped to once per hour.\n- Shared 60-second caches for absence and time-review rows with explicit invalidation on writes.\n- Runtime/CacheService session-secret and Pages-origin caching.\n- Time-review writer supports an assumeNew fast path for the serialized punch flow.\n- gh-pages publication cleans untracked/ignored files before copying _site.\n\n## Phase 2 target\n\n- Maintain attendance index/day map incrementally on append instead of invalidating/rebuilding.\n- Use a compact IP/hour cache instead of scanning every today's row per punch.\n- Keep the ScriptLock only around the minimal attendance read/write critical section.\n- Move audit/review/email work after the lock.\n- Record lock wait/hold telemetry for launch verification.\n\n## Launch verification\n\nBefore and after deploying the modular Apps Script backend, run `diagnosePerformanceBackend()` from the Apps Script editor and retain its output. Perform a controlled burst test before launch. Backend source changes are not live until the existing Apps Script Web App is published as a new version.\n''',encoding='utf-8')
