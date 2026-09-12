// ---------- Tidak Hadir / Keberadaan ----------
  async function loadAbsenceData(force=false){
    if(state.absence&&!force){renderAbsence();return;}
    try{state.absence=await runServer('getAbsenceData',state.token);renderAbsence();}
    catch(e){handleServerError(e);}
  }

  function updateAbsenceModeUi(){
    const mode=document.getElementById('absenceMode')?.value||'TIDAK_HADIR',d=state.absence||{};
    const typeSel=document.getElementById('absenceType');
    const requiredAbsenceTypes=[
      'CUTI REHAT KHAS','CUTI REHAT','CUTI SAKIT (AWAM)','CUTI SAKIT (SWASTA)',
      'CUTI TANPA REKOD KELOMPOK','KURSUS','BENGKEL','TAKLIMAT','MESYUARAT','SEMINAR',
      'AKTIVITI KOKURIKULUM','AKTIVITI SUKAN/PERMAINAN','URUSAN PEPERIKSAAN','LAIN-LAIN'
    ];
    const requiredPresenceTypes=[
      'PROGRAM DALAMAN SEKOLAH - KEBERADAAN',
      'URUSAN PERIBADI (MASUK LEWAT) - KEBERADAAN',
      'MESYUARAT DALAM SEKOLAH - KEBERADAAN',
      'BENGKEL/KURSUS/SEMINAR (PPD)',
      'BENGKEL/KURSUS/SEMINAR (JPN)',
      'BENGKEL/KURSUS/SEMINAR (KPM)',
      'MESYUARAT/TAKLIMAT (PPD)',
      'MESYUARAT/TAKLIMAT (JPN)',
      'MESYUARAT/TAKLIMAT (KPM)',
      'URUSAN PEPERIKSAAN','LAIN-LAIN - KEBERADAAN'
    ];
    const serverTypes=mode==='KEBERADAAN'?(d.presenceTypes||[]):(d.types||[]);
    const requiredTypes=mode==='KEBERADAAN'?requiredPresenceTypes:requiredAbsenceTypes;
    const seen=new Set(),types=[];
    [...serverTypes,...requiredTypes].forEach(value=>{const x=String(value||'').trim().toUpperCase();if(x&&!seen.has(x)){seen.add(x);types.push(x);}});
    if(typeSel)typeSel.innerHTML='<option value="">Pilih jenis</option>'+types.map(x=>`<option>${esc(x)}</option>`).join('');
    ['absenceStartTimeWrap','absenceEndTimeWrap'].forEach(id=>document.getElementById(id)?.classList.toggle('hidden',mode!=='KEBERADAAN'));
    const st=document.getElementById('absenceStartTime'),et=document.getElementById('absenceEndTime');if(st)st.required=mode==='KEBERADAAN';if(et)et.required=mode==='KEBERADAAN';
  }

  function renderAbsence(){
    const d=state.absence;if(!d)return;
    const s=document.getElementById('absenceStartDate'),e=document.getElementById('absenceEndDate'),systemStart=d.systemStartDate||getSystemStartDateClient();if(s){s.min=systemStart;if(!s.value||s.value<systemStart)s.value=d.today<systemStart?systemStart:d.today;}if(e){e.min=systemStart;if(!e.value||e.value<systemStart)e.value=d.today<systemStart?systemStart:d.today;}
    updateAbsenceModeUi();
    const own=d.own||[];
    document.getElementById('absenceOwnRows').innerHTML=own.length?own.map(r=>`<tr><td>${esc(r.submittedAt||'—')}</td><td><b>${esc(r.mode==='KEBERADAAN'?'Keberadaan':'Tidak Hadir')}</b></td><td>${esc(r.type)}</td><td>${esc(formatDateRange(r.startDate,r.endDate))}</td><td>${r.mode==='KEBERADAAN'?esc(`${r.startTime||'—'} – ${r.endTime||'—'}`):'—'}</td><td><span class="request-status ${absenceStatusClass(r.status)}">${esc(r.status)}</span></td><td>${esc(r.comment||'—')}</td><td>${r.status==='MENUNGGU'?`<button class="action-link warn-link" onclick='cancelAbsence(${JSON.stringify(r.id)})'>Batalkan</button>`:'—'}</td></tr>`).join(''):'<tr><td colspan="8" class="empty-cell">Belum ada permohonan.</td></tr>';
  }

  async function submitAbsence(ev){
    ev.preventDefault();const p=Object.fromEntries(new FormData(ev.target).entries());
    try{const r=await runServer('submitAbsenceRequest',state.token,p);toast(r.message,5000);ev.target.reset();state.absence=null;state.absencePublic=null;document.getElementById('absenceMode').value='TIDAK_HADIR';await loadAbsenceData(true);}
    catch(e){handleServerError(e);}
  }
  async function cancelAbsence(id){if(!confirm('Batalkan permohonan ini?'))return;try{await runServer('cancelMyAbsenceRequest',state.token,id);toast('Permohonan dibatalkan.');state.absence=null;state.absencePublic=null;await loadAbsenceData(true);}catch(e){handleServerError(e);}}
  function formatDateRange(a,b){return a===b?a:`${a} → ${b}`;}
  function absenceStatusClass(s){return s==='DILULUSKAN'?'approved':s==='DITOLAK'?'rejected':s==='DIBATALKAN'?'cancelled':s==='TIDAK MOHON'?'unexplained':'pending';}

  function addClientDays(key,n){const d=new Date(key+'T12:00:00');d.setDate(d.getDate()+n);return localDateKey(d);}
  function localDateKey(d){const y=d.getFullYear(),m=String(d.getMonth()+1).padStart(2,'0'),day=String(d.getDate()).padStart(2,'0');return `${y}-${m}-${day}`;}
  function presetRange(kind){const today=state.boot?.today||localDateKey(new Date()),systemStart=getSystemStartDateClient(),d=new Date(today+'T12:00:00'),single=key=>{const safe=key<systemStart?systemStart:key;return[safe,safe];};if(kind==='yesterday')return single(addClientDays(today,-1));if(kind==='tomorrow')return single(addClientDays(today,1));if(kind==='today')return single(today);if(kind==='month'){const start=`${today.slice(0,7)}-01`;return[start<systemStart?systemStart:start,today];}const start=addClientDays(today,-d.getDay());return[start<systemStart?systemStart:start,today];}

  function compareText(a,b){return String(a??'').localeCompare(String(b??''),'ms',{numeric:true,sensitivity:'base'});}
  function sortRecords(list,mode){
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
  }


  // ---------- Senarai Tidak Hadir / Keberadaan (semua pengguna) ----------
  function ensureAbsencePublicDates(){
    const f=document.getElementById('absencePublicFrom'),t=document.getElementById('absencePublicTo'),systemStart=getSystemStartDateClient();
    if(f){f.min=systemStart;if(!f.value||f.value<systemStart)f.value=presetRange('today')[0];}
    if(t){t.min=systemStart;if(!t.value||t.value<systemStart)t.value=state.boot?.today||localDateKey(new Date());}
  }
  async function loadAbsencePublic(force=false){
    ensureAbsencePublicDates();
    const from=document.getElementById('absencePublicFrom')?.value,to=document.getElementById('absencePublicTo')?.value,key=`${from}|${to}`;
    if(state.absencePublic&&!force&&state.absencePublic._key===key){applyAbsencePublicFilters();return;}
    try{state.absencePublic=await runServer('getPublicAbsencePresenceData',state.token,from,to);state.absencePublic._key=key;applyAbsencePublicFilters();}
    catch(e){handleServerError(e);}
  }
  function setAbsencePublicPreset(kind){const [f,t]=presetRange(kind);document.getElementById('absencePublicFrom').value=f;document.getElementById('absencePublicTo').value=t;loadAbsencePublic(true);}
  function currentAbsencePublicFilters(){return {fromDate:document.getElementById('absencePublicFrom')?.value||'',toDate:document.getElementById('absencePublicTo')?.value||'',search:String(document.getElementById('absencePublicSearch')?.value||'').trim(),mode:document.getElementById('absencePublicMode')?.value||'',status:document.getElementById('absencePublicStatus')?.value||'',category:document.getElementById('absencePublicCategory')?.value||'',sort:getTableSort('absencePublic')};}
  function filteredAbsencePublicRows(){
    const data=state.absencePublic?.rows||[],f=currentAbsencePublicFilters(),q=norm(f.search);
    return sortRecords(data.filter(r=>{const hay=norm([r.name,r.jobTitle,r.category,r.mode,r.type,r.note,r.startDate,r.endDate,r.startTime,r.endTime,r.status].join(' '));return(!q||hay.includes(q))&&(!f.mode||r.mode===f.mode)&&(!f.status||r.status===f.status)&&(!f.category||r.category===f.category);}),f.sort);
  }
  function applyAbsencePublicFilters(){
    const data=state.absencePublic?.rows||[],list=filteredAbsencePublicRows();
    text('absencePublicCount',`${list.length} / ${data.length} rekod`);updateTableSortIndicators('absencePublic');
    const summary=document.getElementById('absencePublicSummary');
    if(summary){const th=list.filter(r=>r.mode==='TIDAK_HADIR').length,kb=list.filter(r=>r.mode==='KEBERADAAN').length,nm=list.filter(r=>r.status==='TIDAK MOHON').length;summary.innerHTML=[['Jumlah',list.length],['Tidak Hadir',th],['Keberadaan',kb],['Tiada Penjelasan',nm]].map(x=>`<div class="summary-card"><span>${esc(x[0])}</span><strong>${x[1]}</strong></div>`).join('');}
    const body=document.getElementById('absencePublicRows');if(!body)return;
    body.innerHTML=list.length?list.map(r=>`<tr><td><b>${esc(r.name||'—')}</b><small class="table-sub">${esc(r.jobTitle||'—')} · ${esc(r.category||'—')}</small></td><td><b>${esc(r.mode==='KEBERADAAN'?'Keberadaan':'Tidak Hadir')}</b></td><td>${esc(r.type||'—')}${String(r.note||'').trim()?`<small class="table-sub">${esc(r.note)}</small>`:''}</td><td>${esc(formatDateRange(r.startDate,r.endDate))}${r.mode==='KEBERADAAN'?`<small class="table-sub">${esc(r.startTime||'—')} – ${esc(r.endTime||'—')}</small>`:''}</td><td><span class="request-status ${absenceStatusClass(r.status)}">${esc(r.status)}</span></td></tr>`).join(''):'<tr><td colspan="5" class="empty-cell">Tiada rekod sepadan untuk tempoh dan tapisan dipilih.</td></tr>';
  }
  async function generatePublicAbsencePresencePdfClient(){
    try{const filters=currentAbsencePublicFilters();const r=await runServer('generatePublicAbsencePresencePdf',state.token,filters);downloadPdfResult(r);toast('Laporan PDF Senarai Tidak Hadir / Keberadaan dijana.');}
    catch(e){handleServerError(e);}
  }

  function ensureAbsenceManageDates(){const f=document.getElementById('absenceManageFrom'),t=document.getElementById('absenceManageTo'),today=presetRange('today')[0];if(f&&!f.value)f.value=today;if(t&&!t.value)t.value=today;}
  async function loadAbsenceManagement(force=false){
    ensureAbsenceManageDates();const from=document.getElementById('absenceManageFrom')?.value,to=document.getElementById('absenceManageTo')?.value;
    const key=`${from}|${to}`;if(state.absenceManagement&&!force&&state.absenceManagement._key===key){applyAbsenceManageFilters();return;}
    try{state.absenceManagement=await runServer('getAbsenceManagementData',state.token,from,to);state.absenceManagement._key=key;applyAbsenceManageFilters();}
    catch(e){handleServerError(e);}
  }
  function setAbsenceManagePreset(kind){const [f,t]=presetRange(kind);document.getElementById('absenceManageFrom').value=f;document.getElementById('absenceManageTo').value=t;loadAbsenceManagement(true);}
  function applyAbsenceManageFilters(){const data=state.absenceManagement?.requests||[],q=norm(document.getElementById('absenceManageSearch')?.value),st=document.getElementById('absenceManageStatus')?.value||'',cat=document.getElementById('absenceManageCategory')?.value||'',mode=document.getElementById('absenceManageMode')?.value||'',sort=getTableSort('absenceManage');const list=sortRecords(data.filter(r=>{const hay=norm([r.id,r.submittedAt,r.name,r.jobTitle,r.email,r.category,r.mode,r.type,r.startDate,r.endDate,r.startTime,r.endTime,r.note,r.status,r.reviewerJobTitle,r.reviewedAt,r.comment].join(' '));return(!q||hay.includes(q))&&(!st||r.status===st)&&(!cat||r.category===cat)&&(!mode||r.mode===mode);}),sort);text('absenceManageCount',`${list.length} / ${data.length} rekod`);const body=document.getElementById('absenceManageRows');if(!body)return;body.innerHTML=list.length?list.map(r=>`<tr><td><b>${esc(r.name)}</b><small class="table-sub">${esc(r.jobTitle||'—')} · ${esc(r.email)} · ${esc(r.category)}</small></td><td><b>${esc(r.mode==='KEBERADAAN'?'Keberadaan':'Tidak Hadir')}</b></td><td><b>${esc(r.type)}</b></td><td>${esc(formatDateRange(r.startDate,r.endDate))}${r.mode==='KEBERADAAN'?`<small class="table-sub">${esc(r.startTime||'—')} – ${esc(r.endTime||'—')}</small>`:''}<small class="table-sub">${r.synthetic?'Dikesan:':'Hantar:'} ${esc(r.submittedAt)}</small></td><td>${esc(r.note||'—')}</td><td><span class="request-status ${absenceStatusClass(r.status)}">${esc(r.status)}</span></td><td>${r.status==='MENUNGGU'?`<div class="row-actions"><button class="action-link approve-link" onclick='openReviewAbsence(${JSON.stringify(r.id)},"DILULUSKAN")'>Lulus</button><button class="action-link warn-link" onclick='openReviewAbsence(${JSON.stringify(r.id)},"DITOLAK")'>Tolak</button></div>`:r.synthetic?'<span class="muted">Tiada permohonan</span>':`<span class="review-role-tag">${esc(r.reviewerJobTitle||'Pengurusan')}</span><small class="table-sub">Catatan: ${esc(r.comment||'—')}</small><small class="table-sub">${esc(r.reviewedAt||'—')}</small>`}</td></tr>`).join(''):'<tr><td colspan="7" class="empty-cell">Tiada rekod sepadan.</td></tr>';
  }

  function openReviewAbsence(id,decision){
    const r=state.absenceManagement?.requests?.find(x=>x.id===id);if(!r)return;const approve=decision==='DILULUSKAN';
    showModal(`<div class="review-request"><div class="first-login-badge">PERMOHONAN KEPADA PENGETUA</div><h3>${approve?'Luluskan':'Tolak'} Permohonan</h3><p><b>${esc(r.name)}</b><br><span class="muted">${esc(r.jobTitle||'')} · ${esc(r.email)} · ${esc(r.category)}</span></p><div class="review-summary"><div><span>Mod</span><b>${esc(r.mode==='KEBERADAAN'?'Keberadaan':'Tidak Hadir')}</b></div><div><span>Jenis</span><b>${esc(r.type)}</b></div><div><span>Tempoh</span><b>${esc(formatDateRange(r.startDate,r.endDate))}</b></div><div><span>Masa</span><b>${r.mode==='KEBERADAAN'?esc(`${r.startTime} – ${r.endTime}`):'—'}</b></div><div class="span-2"><span>Catatan</span><b>${esc(r.note||'—')}</b></div></div><form onsubmit='reviewAbsence(event,${JSON.stringify(id)},${JSON.stringify(decision)})'><label>Ulasan Pengetua / Pengurusan<textarea name="comment" rows="3" placeholder="Ulasan keputusan (opsyenal)"></textarea></label><p><button class="btn ${approve?'primary':'dark'}" type="submit">${approve?'Luluskan Permohonan':'Tolak Permohonan'}</button></p></form></div>`);
  }
  async function reviewAbsence(ev,id,decision){ev.preventDefault();const comment=new FormData(ev.target).get('comment')||'';try{const r=await runServer('reviewAbsenceRequest',state.token,id,decision,comment);closeModal();toast(r.conflicts?.length?`Keputusan disimpan. ${r.conflicts.length} tarikh mempunyai rekod waktu sedia ada dan tidak ditindih.`:'Keputusan permohonan disimpan.',5000);state.absenceManagement=null;state.absence=null;state.absencePublic=null;await loadAbsenceManagement(true);}catch(e){handleServerError(e);}}
  async function generateAbsencePresencePdfClient(){try{const filters={fromDate:document.getElementById('absenceManageFrom').value,toDate:document.getElementById('absenceManageTo').value,mode:document.getElementById('absenceManageMode').value,status:document.getElementById('absenceManageStatus').value,category:document.getElementById('absenceManageCategory').value};const r=await runServer('generateAbsencePresencePdf',state.token,filters);downloadPdfResult(r);toast('Laporan PDF dijana.');}catch(e){handleServerError(e);}}


  // ---------- Semakan Lewat / Balik Awal ----------
  function ensureTimeReviewDates(){const f=document.getElementById('timeReviewFrom'),t=document.getElementById('timeReviewTo'),today=presetRange('today')[0];if(f&&!f.value)f.value=today;if(t&&!t.value)t.value=today;}
  async function loadTimeReview(force=false){
    if(!state.boot?.user?.isAdmin)return;ensureTimeReviewDates();const from=document.getElementById('timeReviewFrom').value,to=document.getElementById('timeReviewTo').value,key=`${from}|${to}`;
    if(state.timeReview&&!force&&state.timeReview._key===key){applyTimeReviewFilters();return;}
    try{state.timeReview=await runServer('getTimeReviewData',state.token,from,to);state.timeReview._key=key;applyTimeReviewFilters();}catch(e){handleServerError(e);}
  }
  function setTimeReviewPreset(kind){const [f,t]=presetRange(kind);document.getElementById('timeReviewFrom').value=f;document.getElementById('timeReviewTo').value=t;loadTimeReview(true);}
  function applyTimeReviewFilters(){const data=state.timeReview?.rows||[],q=norm(document.getElementById('timeReviewSearch')?.value),type=document.getElementById('timeReviewType')?.value||'',st=document.getElementById('timeReviewStatus')?.value||'',sort=getTableSort('timeReview');const list=sortRecords(data.filter(r=>{const hay=norm([r.name,r.jobTitle,r.email,r.category,r.date,r.type,r.session,r.recordTime,r.referenceTime,r.reviewStatus,r.reviewerJobTitle,r.comment].join(' '));return(!q||hay.includes(q))&&(!type||r.type===type)&&(!st||r.reviewStatus===st);}),sort);text('timeReviewCount',`${list.length} / ${data.length} rekod`);const body=document.getElementById('timeReviewRows');if(!body)return;body.innerHTML=list.length?list.map(r=>`<tr><td><b>${esc(r.name)}</b><small class="table-sub">${esc(r.jobTitle||'—')} · ${esc(r.email)}</small></td><td>${esc(r.date)}</td><td><span class="badge ${r.type==='LEWAT'?'lewat':'awal'}">${esc(r.type)}</span></td><td>${esc(r.session)}</td><td><b>${esc(r.recordTime)}</b></td><td>${esc(r.referenceTime||'—')}</td><td><span class="request-status ${r.reviewStatus==='DIAMBIL MAKLUM'?'approved':r.reviewStatus==='DITOLAK'?'rejected':'pending'}">${esc(r.reviewStatus)}</span></td><td>${r.reviewStatus==='BELUM DIAMBIL MAKLUM'?`<div class="row-actions"><button class="action-link approve-link" onclick='openTimeReview(${JSON.stringify(r.id)},"DIAMBIL MAKLUM")'>Diambil Maklum</button><button class="action-link warn-link" onclick='openTimeReview(${JSON.stringify(r.id)},"DITOLAK")'>Ditolak</button></div>`:`<span class="review-role-tag">${esc(r.reviewerJobTitle||'Pentadbir Sistem')}</span><small class="table-sub">Catatan: ${esc(r.comment||'—')}</small><small class="table-sub">${esc(r.reviewedAt||'—')}</small>`}</td></tr>`).join(''):'<tr><td colspan="8" class="empty-cell">Tiada rekod sepadan.</td></tr>';
  }
  function openTimeReview(id,decision){const r=state.timeReview?.rows?.find(x=>x.id===id);if(!r)return;showModal(`<h3>${esc(decision==='DIAMBIL MAKLUM'?'Diambil Maklum':'Tolak')} Rekod Waktu</h3><p><b>${esc(r.name)}</b><br><span class="muted">${esc(r.jobTitle||'')} · ${esc(r.email)}</span></p><div class="review-summary"><div><span>Jenis</span><b>${esc(r.type)}</b></div><div><span>Sesi</span><b>${esc(r.session)}</b></div><div><span>Waktu</span><b>${esc(r.recordTime)}</b></div><div><span>Rujukan</span><b>${esc(r.referenceTime||'—')}</b></div></div><form onsubmit='submitTimeReview(event,${JSON.stringify(id)},${JSON.stringify(decision)})'><label>Ulasan<textarea name="comment" rows="3" placeholder="Catatan (opsyenal)"></textarea></label><p><button class="btn ${decision==='DIAMBIL MAKLUM'?'primary':'dark'}" type="submit">Simpan Keputusan</button></p></form>`);}
  async function submitTimeReview(ev,id,decision){ev.preventDefault();const comment=new FormData(ev.target).get('comment')||'';try{const r=await runServer('reviewTimeException',state.token,id,decision,comment);closeModal();toast(`${r.status}.`,4500);state.timeReview=null;state.myCardLoaded=false;state.adminCardData=null;await loadTimeReview(true);}catch(e){handleServerError(e);}}
  async function generateTimeReviewPdfClient(){try{const filters={fromDate:document.getElementById('timeReviewFrom').value,toDate:document.getElementById('timeReviewTo').value,type:document.getElementById('timeReviewType').value,status:document.getElementById('timeReviewStatus').value};const r=await runServer('generateTimeReviewPdf',state.token,filters);downloadPdfResult(r);toast('Laporan PDF dijana.');}catch(e){handleServerError(e);}}
