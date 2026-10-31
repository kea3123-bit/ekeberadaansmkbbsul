/**
 * eKeberadaan hybrid MySQL + Google Workspace bridge.
 *
 * Adds a narrow signed endpoint to the existing Apps Script deployment.
 * It never reads/writes PENGGUNA, KEHADIRAN, TETAPAN or other Google Sheets DB
 * tables: MySQL is the ONLY authoritative database for the PHP application.
 *
 * Install: in original Apps Script project's Script Properties create
 * EK_WORKSPACE_BRIDGE_SECRET = a NEW independent 64-hex-character random secret.
 * Add this file and install the one-line doPost hook in Bridges.gs. Deploy NEW
 * version of the existing /exec deployment (same published URL).
 */
function workspaceBridgePost_(e) {
  function json(value) {
    return ContentService.createTextOutput(JSON.stringify(value))
      .setMimeType(ContentService.MimeType.JSON);
  }
  try {
    const p=(e&&e.parameter)||{};
    if (String(p.workspace||'')!=='1') throw new Error('Workspace request not selected.');
    const payload=String(p.payload||'');
    const signature=String(p.signature||'');
    if(!payload||payload.length>175000||!/^[a-zA-Z0-9_-]{43}$/.test(signature))
      throw new Error('Workspace request invalid.');
    const secret=String(PropertiesService.getScriptProperties().getProperty('EK_WORKSPACE_BRIDGE_SECRET')||'').trim();
    if(!/^[0-9a-f]{64,128}$/i.test(secret))throw new Error('EK_WORKSPACE_BRIDGE_SECRET belum ditetapkan.');
    const bytes=Utilities.computeHmacSha256Signature(payload,secret,Utilities.Charset.UTF_8);
    const expected=Utilities.base64EncodeWebSafe(bytes).replace(/=+$/,'');
    let diff=expected.length^signature.length;
    for(let i=0;i<Math.max(expected.length,signature.length);i++)
      diff|=((expected.charCodeAt(i)||0)^(signature.charCodeAt(i)||0));
    if(diff!==0)throw new Error('Workspace signature rejected.');
    const req=JSON.parse(payload);
    if(req.v!==1||!Number.isInteger(req.issuedAt)||Math.abs(Math.floor(Date.now()/1000)-req.issuedAt)>180)
      throw new Error('Workspace request expired.');
    const nonce=String(req.nonce||'');
    if(!/^[a-f0-9]{32}$/.test(nonce))throw new Error('Workspace request nonce invalid.');
    const cache=CacheService.getScriptCache(),key='EK_WS_NONCE_'+nonce;
    if(cache.get(key))throw new Error('Workspace request already used.');
    cache.put(key,'1',240);
    const data=req.data||{};
    let result;
    switch(String(req.action||'')){
      case 'photo': result=workspacePhoto_(data);break;
      case 'findPhoto':result=workspaceFindPhoto_(data);break;
      case 'syncPhotos':result=workspaceSyncPhotos_(data);break;
      case 'exportPdf':result=workspaceExportPdf_(data);break;
      case 'exportSheet':result=workspaceExportSheet_(data);break;
      case 'sendEmail':result=workspaceSendEmail_(data);break;
      case 'ping':result={ready:true,version:'workspace-bridge-v1',timezone:'Asia/Kuala_Lumpur'};break;
      default:throw new Error('Workspace operation not allowed.');
    }
    return json({ok:true,result:result});
  }catch(err){
    // Never echo the shared secret, signed payload, stack or file data.
    return json({ok:false,error:String(err&&err.message||'Workspace error').slice(0,180)});
  }
}

function workspacePhoto_(data) {
  const id=String(data.fileId||'').trim();
  if(!/^[A-Za-z0-9_-]{12,120}$/.test(id))throw new Error('Photo file ID invalid.');
  const file=DriveApp.getFileById(id);
  const mime=String(file.getMimeType()||'');
  if(!/^image\/(?:png|jpeg|webp|gif)$/.test(mime))throw new Error('Drive photo type unsupported.');
  if(file.getSize()>2500000)throw new Error('Gambar Google Drive melebihi 2.5 MB. Sila kecilkan saiz eoperasi.png.');
  const encoded=Utilities.base64Encode(file.getBlob().getBytes());
  return {ok:true,dataUrl:'data:'+mime+';base64,'+encoded};
}

/**
 * Find only the current authenticated user's eoperasi.png by the trusted
 * name/category and root folder supplied by PHP/MySQL over signed HMAC RPC.
 * Does not search arbitrary user-submitted Drive IDs or read Sheets data.
 */
function workspaceFindPhoto_(data){
  const rootId=String(data.rootFolderId||'').trim();
  const name=String(data.name||'').trim();
  const category=String(data.category||'').trim();
  if(!/^[A-Za-z0-9_-]{12,120}$/.test(rootId))throw new Error('ID folder induk Google Drive tidak sah.');
  if(!name||name.length>200)throw new Error('Nama pegawai tidak sah.');
  const categories={Pengurusan:'01 - Pengurusan',Pentadbir:'01 - Pengurusan',
    PPP:'02 - Guru',AKP:'03 - Anggota Kumpulan Pelaksana',
    Praktikum:'04 - Praktikum',MySTEP:'05 - MySTEP'};
  const categoryFolder=categories[category];
  if(!categoryFolder)return {ok:true,fileId:'',message:'Kategori pengguna tidak mempunyai folder gambar profil: '+category};
  const root=DriveApp.getFolderById(rootId);
  const categoriesFound=root.getFoldersByName(categoryFolder);
  if(!categoriesFound.hasNext())return {ok:true,fileId:'',message:'Folder kategori '+categoryFolder+' tidak dijumpai dalam Google Drive.'};
  const parent=categoriesFound.next();
  const norm=value=>String(value||'').trim().toLowerCase().replace(/\s+/g,' ');
  let staffFolder=null;
  const dirs=parent.getFolders();
  while(dirs.hasNext()){
    const entry=dirs.next();
    if(norm(entry.getName())===norm(name)){staffFolder=entry;break;}
  }
  if(!staffFolder)return {ok:true,fileId:'',message:'Folder bernama '+name+' tidak dijumpai dalam '+categoryFolder+'.'};
  const files=staffFolder.getFiles();
  while(files.hasNext()){
    const entry=files.next();
    if(String(entry.getName()||'').trim().toLowerCase()==='eoperasi.png'){
      return {ok:true,fileId:entry.getId()};
    }
  }
  return {ok:true,fileId:'',message:'eoperasi.png tidak dijumpai dalam folder '+name+'.'};
}

function workspaceSyncPhotos_(data){
  const rootId=String(data.rootFolderId||'').trim();
  if(!/^[A-Za-z0-9_-]{12,120}$/.test(rootId))throw new Error('Profile root folder missing.');
  const users=Array.isArray(data.users)?data.users:[];
  if(users.length>250)throw new Error('Too many users for one photo sync.');
  const root=DriveApp.getFolderById(rootId);
  const categories={Pengurusan:'01 - Pengurusan',Pentadbir:'01 - Pengurusan',
    PPP:'02 - Guru',AKP:'03 - Anggota Kumpulan Pelaksana',
    Praktikum:'04 - Praktikum',MySTEP:'05 - MySTEP'};
  const roots={};
  const uniqueNames=[...new Set(Object.values(categories))];
  uniqueNames.forEach(n=>{
    const it=root.getFoldersByName(n);
    if(it.hasNext()) roots[n]=it.next();
  });
  const normalize=n=>String(n||'').trim().toLowerCase().replace(/\s+/g,' ');
  const folders={};
  Object.entries(categories).forEach(([cat,n])=>{
    if(!roots[n])return;
    if(!folders[n]){
      const names={};const it=roots[n].getFolders();
      while(it.hasNext()){const f=it.next();names[normalize(f.getName())]=f;}
      folders[n]=names;
    }
  });
  let matched=0;
  const unmatched=[],updates=[];
  users.forEach(u=>{
    const email=String(u.email||'').toLowerCase(),name=String(u.name||'');
    const category=String(u.category||'');
    if(!email||!name||!categories[category])return;
    const f=folders[categories[category]]?.[normalize(name)];
    if(!f){unmatched.push(name+' ('+category+')');return;}
    const fs=f.getFiles();let hit=null;
    while(fs.hasNext()){
      const file=fs.next();
      if(String(file.getName()).toLowerCase()==='eoperasi.png'){hit=file;break;}
    }
    if(!hit){unmatched.push(name+' — eoperasi.png tiada');return;}
    updates.push({email:email,fileId:hit.getId()});matched++;
  });
  return {ok:true,matched:matched,unmatched:unmatched.slice(0,250),updates:updates};
}
function workspaceSanitizeName_(name){
  return String(name||'Laporan eKeberadaan').replace(/[<>:"/\\|?*\x00-\x1f]/g,' ').slice(0,90);
}
function workspaceTableData_(data){
  const headers=Array.isArray(data.headers)?data.headers:[];
  const rows=Array.isArray(data.rows)?data.rows:[];
  if(!headers.length||headers.length>20||rows.length>250)
    throw new Error('Workspace report exceeds 250 rows or 20 columns.');
  const clean=v=>String(v===null||v===undefined?'':v).slice(0,250);
  return {
    headers:headers.map(clean),
    rows:rows.map(row=>{
      if(!Array.isArray(row))return headers.map(()=>'');
      return headers.map((_,i)=>clean(row[i]));
    })
  };
}
function workspaceReportSections_(data){
  if(!Array.isArray(data.sections)||!data.sections.length)
    return [{name:'LAPORAN',...workspaceTableData_(data)}];
  if(data.sections.length>12)throw new Error('Laporan melebihi 12 bahagian.');
  const safe=v=>String(v===null||v===undefined?'':v).slice(0,250);
  let count=0;
  return data.sections.map((s,i)=>{
    const headers=Array.isArray(s.headers)?s.headers:[];
    const rows=Array.isArray(s.rows)?s.rows:[];
    if(!headers.length||headers.length>20 || rows.length>3500)
      throw new Error('Format jadual laporan tidak sah.');
    count+=rows.length;
    if(count>5000)throw new Error('Terlalu banyak baris laporan; pilih tempoh lebih pendek.');
    return {name:workspaceSanitizeName_(s.name||'LAPORAN '+(i+1)).slice(0,31),
      headers:headers.map(safe),
      rows:rows.map(r=>headers.map((_,j)=>safe(Array.isArray(r)?r[j]:'')))};
  });
}
function workspaceExportPdf_(data){
  const sections=workspaceReportSections_(data);
  const total=sections.reduce((n,s)=>n+s.rows.length,0);
  if(total>1600)throw new Error('Terlalu banyak baris untuk PDF. Gunakan eksport Google Sheets atau pilih tempoh lebih pendek.');
  const title=workspaceSanitizeName_(data.title);
  const doc=DocumentApp.create(title+' [sementara]');
  try{
    const body=doc.getBody();
    body.appendParagraph(title).setHeading(DocumentApp.ParagraphHeading.HEADING1);
    body.appendParagraph(String(data.subtitle||'').slice(0,250));
    sections.forEach((section,index)=>{
      if(index)body.appendPageBreak();
      body.appendParagraph(section.name).setHeading(DocumentApp.ParagraphHeading.HEADING2);
      if(section.name==='INDIVIDU' && sections.length>1){
        // Each staff member receives a dedicated PDF page.
        section.rows.forEach((row,i)=>{
          if(i)body.appendPageBreak();
          body.appendParagraph(String(row[0]||'Pegawai')).setHeading(DocumentApp.ParagraphHeading.HEADING2);
          const detail=section.headers.map((header,j)=>[header,row[j]||'']);
          body.appendTable(detail);
        });
      }else{
        // No silent 180-row slice: everything present in this section is printed.
        body.appendTable([section.headers].concat(section.rows));
      }
    });
    doc.saveAndClose();
    const file=DriveApp.getFileById(doc.getId());
    const pdfBytes=file.getAs(MimeType.PDF).getBytes();
    if(pdfBytes.length>2500000)throw new Error('PDF melebihi 2.5 MB. Pilih tempoh lebih pendek atau eksport ke Google Sheets.');
    return {ok:true,mimeType:'application/pdf',fileName:title+'.pdf',base64:Utilities.base64Encode(pdfBytes)};
  }finally{
    try{DriveApp.getFileById(doc.getId()).setTrashed(true);}catch(e){}
  }
}
function workspaceExportSheet_(data){
  const sections=workspaceReportSections_(data);
  const title=workspaceSanitizeName_(data.title);
  const ss=SpreadsheetApp.create(title);
  const names=[];
  // Escape formula-style imported cells and use batched setValues.
  const safe=value=>/^[=+\-@]/.test(value)?"'"+value:value;
  sections.forEach((section,index)=>{
    const sh=index===0?ss.getSheets()[0]:ss.insertSheet();
    const name=section.name.slice(0,31);
    sh.setName(name);names.push(name);
    const header=section.headers;
    const rows=[header].concat(section.rows).map(r=>r.map(safe));
    for(let at=0;at<rows.length;at+=250){
      const chunk=rows.slice(at,at+250);
      sh.getRange(at+1,1,chunk.length,header.length).setValues(chunk);
    }
    sh.getRange(1,1,1,header.length).setFontWeight('bold').setBackground('#dce8ff');
    sh.setFrozenRows(1);sh.autoResizeColumns(1,Math.min(header.length,12));
  });
  return {ok:true,url:ss.getUrl(),sheetName:names[0],sheetNames:names};
}

/**
 * Isolated MailApp adapter. Input is signed by PHP's HMAC bridge and comes
 * only from its server-side MySQL outbox worker, never from a browser.
 * Does not read or write the historical Google Sheets database.
 */
function workspaceSendEmail_(data){
  const recipient=String(data.to||'').trim().toLowerCase();
  const subject=String(data.subject||'').trim();
  const body=String(data.body||'');
  const deliveryKey=String(data.deliveryKey||'').trim();
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recipient)||recipient.length>254)
    throw new Error('Workspace recipient invalid.');
  if(!subject||subject.length>180||/[\r\n]/.test(subject))
    throw new Error('Workspace email subject invalid.');
  if(!body||body.length>12000)throw new Error('Workspace email body invalid.');
  if(!/^[a-f0-9]{64}$/.test(deliveryKey))
    throw new Error('Workspace email delivery key invalid.');
  const key='EK_MAIL_SENT_'+deliveryKey;
  const cache=CacheService.getScriptCache();
  const lock=LockService.getScriptLock();
  lock.waitLock(15000);
  try{
    if(cache.get(key))return {sent:true,duplicate:true};
    MailApp.sendEmail({to:recipient,subject:subject,body:body,name:'eKeberadaan'});
    // Within six hours repeated worker retries will not duplicate an email.
    cache.put(key,'1',21600);
    return {sent:true,duplicate:false};
  }finally{
    lock.releaseLock();
  }
}

/**
 * Run ONCE manually from the Apps Script editor after confirmed MySQL cutover.
 * Remove ONLY legacy jobs that still read/write the old Sheets database.
 * This does not remove the signed Workspace Web App or MailApp adapter.
 */
function disableLegacySheetTriggersAfterMySqlCutover() {
  const legacy=[
    'sendPunchReminderTrigger',
    'sendYesterdayAttendanceReportTrigger',
    'checkExpiredPresenceWithoutPunchTrigger'
  ];
  let removed=0;
  ScriptApp.getProjectTriggers().forEach(function(trigger) {
    if(legacy.indexOf(trigger.getHandlerFunction())!==-1) {
      ScriptApp.deleteTrigger(trigger);
      removed++;
    }
  });
  return {removed:removed,workspaceBridgeUnchanged:true};
}
