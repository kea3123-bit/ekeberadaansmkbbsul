from pathlib import Path
import re

# ---------- Index.html ----------
p = Path('Index.html')
s = p.read_text()

# Remove all visible sort form controls.
for sort_id in ['absencePublicSort','absenceManageSort','timeReviewSort','reportSort','userSort']:
    pattern = rf'<label>Susun<select id="{sort_id}"[^>]*>.*?</select></label>'
    s2, n = re.subn(pattern, '', s, count=1, flags=re.S)
    assert n == 1, f'Could not remove {sort_id}'
    s = s2

headers = {
'<thead><tr><th>Pegawai</th><th>Mod</th><th>Jenis</th><th>Tempoh / Masa</th><th>Status</th></tr></thead>':
'''<thead><tr><th class="sortable-th"><button type="button" class="table-sort-btn" onclick="toggleTableSort('absencePublic','name')">Pegawai <span id="sort-absencePublic-name" class="sort-indicator">↕</span></button></th><th>Mod</th><th>Jenis</th><th class="sortable-th"><button type="button" class="table-sort-btn" onclick="toggleTableSort('absencePublic','date')">Tempoh / Masa <span id="sort-absencePublic-date" class="sort-indicator">↕</span></button></th><th class="sortable-th"><button type="button" class="table-sort-btn" onclick="toggleTableSort('absencePublic','status')">Status <span id="sort-absencePublic-status" class="sort-indicator">↕</span></button></th></tr></thead>''',
'<thead><tr><th>Pegawai</th><th>Mod</th><th>Jenis</th><th>Tempoh / Masa</th><th>Catatan</th><th>Status</th><th>Tindakan / Pelulus</th></tr></thead>':
'''<thead><tr><th class="sortable-th"><button type="button" class="table-sort-btn" onclick="toggleTableSort('absenceManage','name')">Pegawai <span id="sort-absenceManage-name" class="sort-indicator">↕</span></button></th><th>Mod</th><th>Jenis</th><th class="sortable-th"><button type="button" class="table-sort-btn" onclick="toggleTableSort('absenceManage','date')">Tempoh / Masa <span id="sort-absenceManage-date" class="sort-indicator">↕</span></button></th><th>Catatan</th><th class="sortable-th"><button type="button" class="table-sort-btn" onclick="toggleTableSort('absenceManage','status')">Status <span id="sort-absenceManage-status" class="sort-indicator">↕</span></button></th><th>Tindakan / Pelulus</th></tr></thead>''',
'<thead><tr><th>Pegawai</th><th>Tarikh</th><th>Jenis</th><th>Sesi</th><th>Waktu</th><th>Rujukan</th><th>Status</th><th>Tindakan / Pelulus</th></tr></thead>':
'''<thead><tr><th class="sortable-th"><button type="button" class="table-sort-btn" onclick="toggleTableSort('timeReview','name')">Pegawai <span id="sort-timeReview-name" class="sort-indicator">↕</span></button></th><th class="sortable-th"><button type="button" class="table-sort-btn" onclick="toggleTableSort('timeReview','date')">Tarikh <span id="sort-timeReview-date" class="sort-indicator">↕</span></button></th><th>Jenis</th><th>Sesi</th><th>Waktu</th><th>Rujukan</th><th class="sortable-th"><button type="button" class="table-sort-btn" onclick="toggleTableSort('timeReview','status')">Status <span id="sort-timeReview-status" class="sort-indicator">↕</span></button></th><th>Tindakan / Pelulus</th></tr></thead>''',
'<thead><tr><th>Nama</th><th>Jawatan / Kategori</th><th>Status</th><th>Masuk 1</th><th>Keluar 1</th><th>Masuk 2</th><th>Keluar 2</th><th>Sumber / Sebab</th><th>IP / Semakan</th><th>Tindakan</th></tr></thead>':
'''<thead><tr><th class="sortable-th"><button type="button" class="table-sort-btn" onclick="toggleTableSort('report','name')">Nama <span id="sort-report-name" class="sort-indicator">↕</span></button></th><th>Jawatan / Kategori</th><th class="sortable-th"><button type="button" class="table-sort-btn" onclick="toggleTableSort('report','status')">Status <span id="sort-report-status" class="sort-indicator">↕</span></button></th><th class="sortable-th"><button type="button" class="table-sort-btn" onclick="toggleTableSort('report','in')">Masuk 1 <span id="sort-report-in" class="sort-indicator">↕</span></button></th><th>Keluar 1</th><th>Masuk 2</th><th>Keluar 2</th><th>Sumber / Sebab</th><th>IP / Semakan</th><th>Tindakan</th></tr></thead>''',
'<thead><tr><th class="select-col"><input id="selectAllUsers" type="checkbox" onchange="toggleSelectAllUsers(this.checked)" title="Pilih semua yang sedang dipaparkan"></th><th>Aktif</th><th>Nama / Jawatan</th><th>Emel</th><th>Kategori</th><th>Pentadbir Sistem</th><th>PIN</th><th>Waktu Sesi / Catatan</th><th>Tindakan</th></tr></thead>':
'''<thead><tr><th class="select-col"><input id="selectAllUsers" type="checkbox" onchange="toggleSelectAllUsers(this.checked)" title="Pilih semua yang sedang dipaparkan"></th><th class="sortable-th"><button type="button" class="table-sort-btn" onclick="toggleTableSort('users','active')">Aktif <span id="sort-users-active" class="sort-indicator">↕</span></button></th><th class="sortable-th"><button type="button" class="table-sort-btn" onclick="toggleTableSort('users','name')">Nama / Jawatan <span id="sort-users-name" class="sort-indicator">↕</span></button></th><th>Emel</th><th class="sortable-th"><button type="button" class="table-sort-btn" onclick="toggleTableSort('users','category')">Kategori <span id="sort-users-category" class="sort-indicator">↕</span></button></th><th>Pentadbir Sistem</th><th>PIN</th><th>Waktu Sesi / Catatan</th><th>Tindakan</th></tr></thead>'''
}
for old, new in headers.items():
    assert old in s, 'Expected table header not found: ' + old[:80]
    s = s.replace(old, new, 1)
p.write_text(s)

# ---------- Scripts.html ----------
p = Path('Scripts.html')
s = p.read_text()
s = s.replace("selectedUserEmails:new Set(), filteredUsers:[], filteredReport:[],", "selectedUserEmails:new Set(), filteredUsers:[], filteredReport:[], tableSorts:{},", 1)

old_sort = "function sortRecords(list,mode){const rows=(list||[]).slice(),m=String(mode||''),cmp=(a,b)=>compareText(a,b),dateOf=r=>String(r.startDate||r.date||r.submittedAt||''),statusOf=r=>String(r.reviewStatus||r.status||r.category||''),timeOf=r=>String(r.inTime||'99:99');if(m==='date_desc')return rows.sort((a,b)=>cmp(dateOf(b),dateOf(a))||cmp(a.name,b.name));if(m==='date_asc')return rows.sort((a,b)=>cmp(dateOf(a),dateOf(b))||cmp(a.name,b.name));if(m==='name_desc')return rows.sort((a,b)=>cmp(b.name,a.name));if(m==='status_asc')return rows.sort((a,b)=>cmp(statusOf(a),statusOf(b))||cmp(a.name,b.name));if(m==='category_asc')return rows.sort((a,b)=>cmp(a.category,b.category)||cmp(a.name,b.name));if(m==='active_first')return rows.sort((a,b)=>(Number(!!b.active)-Number(!!a.active))||cmp(a.name,b.name));if(m==='in_asc')return rows.sort((a,b)=>cmp(timeOf(a),timeOf(b))||cmp(a.name,b.name));if(m==='in_desc')return rows.sort((a,b)=>cmp(timeOf(b),timeOf(a))||cmp(a.name,b.name));return rows.sort((a,b)=>cmp(a.name,b.name));}"
assert old_sort in s, 'sortRecords source not found'
new_sort = r'''function sortRecords(list,mode){
    const rows=(list||[]).slice(),m=String(mode||''),cmp=(a,b)=>compareText(a,b),dateOf=r=>String(r.startDate||r.date||r.submittedAt||''),statusOf=r=>String(r.reviewStatus||r.status||r.category||''),timeOf=r=>String(r.inTime||'99:99');
    if(m==='date_desc')return rows.sort((a,b)=>cmp(dateOf(b),dateOf(a))||cmp(a.name,b.name));
    if(m==='date_asc')return rows.sort((a,b)=>cmp(dateOf(a),dateOf(b))||cmp(a.name,b.name));
    if(m==='name_desc')return rows.sort((a,b)=>cmp(b.name,a.name));
    if(m==='status_asc')return rows.sort((a,b)=>cmp(statusOf(a),statusOf(b))||cmp(a.name,b.name));
    if(m==='status_desc')return rows.sort((a,b)=>cmp(statusOf(b),statusOf(a))||cmp(a.name,b.name));
    if(m==='category_asc')return rows.sort((a,b)=>cmp(a.category,b.category)||cmp(a.name,b.name));
    if(m==='category_desc')return rows.sort((a,b)=>cmp(b.category,a.category)||cmp(a.name,b.name));
    if(m==='active_first')return rows.sort((a,b)=>(Number(!!b.active)-Number(!!a.active))||cmp(a.name,b.name));
    if(m==='inactive_first')return rows.sort((a,b)=>(Number(!!a.active)-Number(!!b.active))||cmp(a.name,b.name));
    if(m==='in_asc')return rows.sort((a,b)=>cmp(timeOf(a),timeOf(b))||cmp(a.name,b.name));
    if(m==='in_desc')return rows.sort((a,b)=>cmp(timeOf(b),timeOf(a))||cmp(a.name,b.name));
    return rows.sort((a,b)=>cmp(a.name,b.name));
  }

  const TABLE_SORT_CONFIG={
    absencePublic:{default:'date_desc',name:['name_asc','name_desc'],date:['date_desc','date_asc'],status:['status_asc','status_desc']},
    absenceManage:{default:'date_desc',name:['name_asc','name_desc'],date:['date_desc','date_asc'],status:['status_asc','status_desc']},
    timeReview:{default:'date_desc',name:['name_asc','name_desc'],date:['date_desc','date_asc'],status:['status_asc','status_desc']},
    report:{default:'name_asc',name:['name_asc','name_desc'],status:['status_asc','status_desc'],in:['in_asc','in_desc']},
    users:{default:'name_asc',active:['active_first','inactive_first'],name:['name_asc','name_desc'],category:['category_asc','category_desc']}
  };
  function getTableSort(scope){const cfg=TABLE_SORT_CONFIG[scope];return state.tableSorts?.[scope]||cfg?.default||'name_asc';}
  function updateTableSortIndicators(scope){
    const cfg=TABLE_SORT_CONFIG[scope];if(!cfg)return;const current=getTableSort(scope);
    Object.entries(cfg).forEach(([key,pair])=>{if(key==='default'||!Array.isArray(pair))return;const el=document.getElementById(`sort-${scope}-${key}`);if(!el)return;const active=pair.includes(current);el.textContent=active?(current===pair[0]?'↑':'↓'):'↕';const th=el.closest('th');if(th)th.setAttribute('aria-sort',active?(current===pair[0]?'ascending':'descending'):'none');});
  }
  function toggleTableSort(scope,key){
    const cfg=TABLE_SORT_CONFIG[scope],pair=cfg?.[key];if(!Array.isArray(pair))return;
    const current=getTableSort(scope);state.tableSorts=state.tableSorts||{};state.tableSorts[scope]=current===pair[0]?pair[1]:pair[0];
    updateTableSortIndicators(scope);
    const apply={absencePublic:applyAbsencePublicFilters,absenceManage:applyAbsenceManageFilters,timeReview:applyTimeReviewFilters,report:applyReportFilters,users:applyUserFilters}[scope];if(typeof apply==='function')apply();
  }'''
s = s.replace(old_sort, new_sort, 1)

repls = {
"document.getElementById('absencePublicSort')?.value||'date_desc'":"getTableSort('absencePublic')",
"document.getElementById('absenceManageSort')?.value||'date_desc'":"getTableSort('absenceManage')",
"document.getElementById('timeReviewSort')?.value||'date_desc'":"getTableSort('timeReview')",
"document.getElementById('reportSort')?.value||'name_asc'":"getTableSort('report')",
"document.getElementById('userSort')?.value||'name_asc'":"getTableSort('users')",
}
for old,new in repls.items():
    assert old in s, 'Missing sort reader '+old
    s=s.replace(old,new,1)

# Keep header arrows synced on every render/filter pass.
for old,new in [
("text('absencePublicCount',`${list.length} / ${data.length} rekod`);", "text('absencePublicCount',`${list.length} / ${data.length} rekod`);updateTableSortIndicators('absencePublic');"),
("state.filteredReport=list;text('reportFilterCount',`${list.length} / ${data.length} rekod`);", "state.filteredReport=list;text('reportFilterCount',`${list.length} / ${data.length} rekod`);updateTableSortIndicators('report');"),
("state.filteredUsers=list;text('userFilterCount',`${list.length} / ${data.length} pengguna`);", "state.filteredUsers=list;text('userFilterCount',`${list.length} / ${data.length} pengguna`);updateTableSortIndicators('users');")
]:
    assert old in s, 'Missing indicator anchor '+old
    s=s.replace(old,new,1)
p.write_text(s)

# ---------- web/config.js overrides ----------
p=Path('web/config.js')
s=p.read_text()
old = "const list = data.filter(r => {\n      const hay = norm([r.id,r.submittedAt,r.name,r.jobTitle,r.email,r.category,r.mode,r.type,r.startDate,r.endDate,r.startTime,r.endTime,r.note,r.status,r.reviewedBy,r.reviewerName,r.reviewerJobTitle,r.reviewedAt,r.comment].join(' '));\n      return (!q || hay.includes(q)) && (!st || r.status === st) && (!cat || r.category === cat) && (!mode || r.mode === mode);\n    });"
new = "const list = sortRecords(data.filter(r => {\n      const hay = norm([r.id,r.submittedAt,r.name,r.jobTitle,r.email,r.category,r.mode,r.type,r.startDate,r.endDate,r.startTime,r.endTime,r.note,r.status,r.reviewedBy,r.reviewerName,r.reviewerJobTitle,r.reviewedAt,r.comment].join(' '));\n      return (!q || hay.includes(q)) && (!st || r.status === st) && (!cat || r.category === cat) && (!mode || r.mode === mode);\n    }), getTableSort('absenceManage'));"
assert old in s, 'config absence list block not found'
s=s.replace(old,new,1)
old = "const list = data.filter(r => {\n      const hay = norm([r.name,r.jobTitle,r.email,r.category,r.date,r.type,r.session,r.recordTime,r.referenceTime,r.reviewStatus,r.reviewerName,r.reviewerJobTitle,r.comment].join(' '));\n      return (!q || hay.includes(q)) && (!type || r.type === type) && (!st || r.reviewStatus === st);\n    });"
new = "const list = sortRecords(data.filter(r => {\n      const hay = norm([r.name,r.jobTitle,r.email,r.category,r.date,r.type,r.session,r.recordTime,r.referenceTime,r.reviewStatus,r.reviewerName,r.reviewerJobTitle,r.comment].join(' '));\n      return (!q || hay.includes(q)) && (!type || r.type === type) && (!st || r.reviewStatus === st);\n    }), getTableSort('timeReview'));"
assert old in s, 'config time list block not found'
s=s.replace(old,new,1)
s=s.replace("text('absenceManageCount', `${list.length} / ${data.length} rekod`);", "text('absenceManageCount', `${list.length} / ${data.length} rekod`);\n    updateTableSortIndicators('absenceManage');",1)
s=s.replace("text('timeReviewCount', `${list.length} / ${data.length} rekod`);", "text('timeReviewCount', `${list.length} / ${data.length} rekod`);\n    updateTableSortIndicators('timeReview');",1)
p.write_text(s)

# ---------- Styles.html ----------
p=Path('Styles.html')
s=p.read_text()
css = r'''
  /* Table-header sorting: sorting belongs to the data columns, not the filter form. */
  th.sortable-th{padding:0!important}
  .table-sort-btn{width:100%;min-width:max-content;border:0;background:transparent;color:inherit;font:inherit;font-weight:inherit;text-transform:inherit;letter-spacing:inherit;text-align:left;display:flex;align-items:center;justify-content:space-between;gap:7px;padding:11px 12px;cursor:pointer}
  .table-sort-btn:hover,.table-sort-btn:focus-visible{background:rgba(7,83,185,.07);outline:none}
  .sort-indicator{display:inline-flex;align-items:center;justify-content:center;min-width:16px;font-size:14px;font-weight:900;line-height:1;color:var(--blue)}
  th[aria-sort="ascending"] .table-sort-btn,th[aria-sort="descending"] .table-sort-btn{color:var(--blue2)}
  @media(max-width:760px){.table-sort-btn{padding:11px 10px;gap:5px}.sort-indicator{font-size:13px}}
'''
assert '</style>' in s
s=s.rsplit('</style>',1)[0]+css+'</style>'+s.rsplit('</style>',1)[1]
p.write_text(s)

# Validation anchors.
for path in ['Index.html','Scripts.html','web/config.js','Styles.html']:
    assert Path(path).exists()
assert 'id="reportSort"' not in Path('Index.html').read_text()
assert "toggleTableSort('users','category')" in Path('Index.html').read_text()
assert "getTableSort('timeReview')" in Path('web/config.js').read_text()
