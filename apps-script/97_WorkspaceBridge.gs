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
/**
 * Exact palette sampled from the supplied 96-page Google Sheets PDF.
 * Styles apply ONLY to Google Workspace output; MySQL is the source.
 */
function workspaceReportColors_(){
  return {aqua:'#C9F5F5',blue:'#91C6F4',amber:'#FFD09B',
    red:'#FF2A20',green:'#2D9D68',white:'#FFFFFF',
    ink:'#183452',pale:'#F7FBFF'};
}
function workspaceReportCellColor_(value,kind,head){
  const c=workspaceReportColors_();
  if(head)return c.blue;
  const txt=String(value||'').toUpperCase();
  if(/LEWAT|BALIK AWAL/.test(txt))return c.red;
  if(/HUJUNG MINGGU|CUTI UMUM|TIDAK HADIR|BELUM HADIR|CUTI SAKIT/.test(txt))return c.amber;
  return kind==='RINGKASAN'&&txt==='CATATAN'?c.amber:c.white;
}
function workspaceDocReportHeading_(body,text,subtitle){
  const c=workspaceReportColors_();
  const p=body.appendParagraph(String(text));
  if(p.setHeading)p.setHeading(DocumentApp.ParagraphHeading.HEADING2);
  if(p.editAsText){
    const t=p.editAsText();
    if(t.setForegroundColor)t.setForegroundColor(c.ink);
    if(t.setBold)t.setBold(true);
    if(t.setFontSize)t.setFontSize(12);
    if(t.setBackgroundColor)t.setBackgroundColor(c.aqua);
  }
  if(subtitle){
    const sub=body.appendParagraph(String(subtitle).slice(0,220));
    if(sub.editAsText&&sub.editAsText().setFontSize)sub.editAsText().setFontSize(8);
  }
}
function workspaceDocStyleTable_(table,headers,rows,kind){
  if(!table||typeof table.getRow!=='function')return; // mocked in CI
  const c=workspaceReportColors_();
  if(table.setBorderColor)table.setBorderColor(c.green);
  if(table.setBorderWidth)table.setBorderWidth(0.5);
  const n=rows.length+1,cols=headers.length;
  for(let i=0;i<n;i++){
    const row=table.getRow(i);if(!row)continue;
    for(let j=0;j<cols;j++){
      const cell=row.getCell(j);if(!cell)continue;
      const value=i===0?headers[j]:(rows[i-1]||[])[j];
      let color=workspaceReportCellColor_(value,kind,i===0);
      if(i>0&&kind==='RINGKASAN'&&j===cols-1)color=c.amber;
      if(/^PERAKAM/.test(kind) && i>0 && i%2===0)color=c.blue;
      // For perakam, highlighted column stays amber for a Saturday/holiday.
      if(i>0&&/^PERAKAM/.test(kind)&&j>=2&&
         /HUJUNG MINGGU|CUTI UMUM/.test(String(value||'')))color=c.amber;
      if(cell.setBackgroundColor)cell.setBackgroundColor(color);
      if(cell.editAsText){
        const t=cell.editAsText();
        if(t.setFontSize)t.setFontSize(cols>=11?6:8);
        if(i===0&&t.setBold)t.setBold(true);
        if(t.setForegroundColor)t.setForegroundColor(c.ink);
      }
    }
  }
}
function workspaceReportIndividualRows_(sections){
  const map={},order=[];
  sections.filter(s=>/^PERAKAM /.test(s.name)).forEach(section=>{
    section.rows.forEach(row=>{
      const email=String(row[1]||'').trim().toLowerCase();
      if(!email)return;
      if(!map[email]){map[email]={name:row[0],email:email,days:{}};order.push(email);}
      section.headers.slice(2).forEach((date,j)=>{
        const raw=String(row[j+2]||'');
        const chunks=raw.split('|');
        const time=chunks[0].split(';');
        const s1=time[0].split('/'),s2=(time[1]||'').split('/');
        const noTime=/^(BELUM HADIR|TIDAK HADIR|HUJUNG MINGGU|CUTI UMUM|TH|--)$/i.test(chunks[0]);
        const status=noTime?chunks[0]:(chunks[1]||'HADIR');
        const dt=new Date(String(date)+'T00:00:00Z');
        const day=isNaN(dt.valueOf())?'':(['Ahd','Isn','Sel','Rab','Kha','Jum','Sab'][dt.getUTCDay()]);
        map[email].days[date]=[date.slice(8,10)+'/'+date.slice(5,7),day,
          noTime?'':(s1[0]==='--'?'':s1[0]||''),
          noTime?'':(s1[1]==='--'?'':s1[1]||''),
          noTime?'':(s2[0]==='--'?'':s2[0]||''),
          noTime?'':(s2[1]==='--'?'':s2[1]||''),
          status, noTime?(chunks.slice(1).join('|')||(/HUJUNG MINGGU|CUTI UMUM/.test(status)?status:'')):''];
      });
    });
  });
  const stats=sections.find(s=>s.name==='INDIVIDU');
  const staff=stats?stats.rows.map(r=>{
    const email=String(r[1]||'').trim().toLowerCase();
    const m=map[email]||{days:{}};
    return {name:r[0],email:email,category:r[2],summary:r,days:m.days};
  }):order.map(email=>map[email]);
  return staff.map((x,i)=>({
    bil:i+1,name:x.name||'',category:x.category||'',email:x.email||'',
    summary:x.summary||[],days:Object.keys(x.days||{}).sort().map(date=>x.days[date])
  }));
}
function workspaceReportIndividualTable_(person){
  const h=['Tarikh','Hari','Masuk','Keluar','Masuk 2','Keluar 2','Status','Catatan'];
  const items=person.days||[];
  // Pair first 16 dates with the remaining 15, matching the sample PDF.
  const top=items.slice(0,16),bottom=items.slice(16,32);
  const cols=h.concat(h);
  const rows=Array.from({length:Math.max(top.length,bottom.length)},(_,i)=>
    (top[i]||Array(8).fill('')).concat(bottom[i]||Array(8).fill('')));
  return {headers:cols,rows:rows};
}

function workspacePdfPerakamCard_(person){
  const all=person.days||[];
  const rows=[];
  for(let start=0;start<all.length;start+=7){
    const dates=all.slice(start,start+7);
    const heads=dates.map(d=>d[0]+'\n'+d[1]);
    const values=dates.map(d=>{
      const status=String(d[6]||'');
      if(/HUJUNG MINGGU|CUTI UMUM|TIDAK HADIR|BELUM HADIR/.test(status))return status;
      const session1=(d[2]||'--')+'/'+(d[3]||'--');
      const session2=d[4]||d[5]?' ; '+(d[4]||'--')+'/'+(d[5]||'--'):'';
      return session1+session2+(status==='HADIR'?'':'\n'+status);
    });
    while(heads.length<7)heads.push('');
    while(values.length<7)values.push('');
    rows.push(heads,values);
  }
  if(!rows.length)rows.push(Array(7).fill(''),Array(7).fill(''));
  return {headers:rows[0],rows:rows.slice(1)};
}

function workspaceExportPdf_(data){
  const sections=workspaceReportSections_(data);
  const title=workspaceSanitizeName_(data.title);
  const monthly=sections.some(s=>s.name==='RINGKASAN')&&sections.some(s=>s.name==='INDIVIDU');
  const individuals=monthly?workspaceReportIndividualRows_(sections):[];
  if(individuals.length>150)
    throw new Error('Laporan melebihi 150 staf. Gunakan eksport Google Sheets.');
  const doc=DocumentApp.create(title+' [sementara]');
  try {
    const body=doc.getBody();
    if(body.setMarginTop)body.setMarginTop(28);
    if(body.setMarginBottom)body.setMarginBottom(27);
    if(body.setMarginLeft)body.setMarginLeft(25);
    if(body.setMarginRight)body.setMarginRight(25);
    let page=0,perakamRendered=false;
    sections.forEach((section,index)=>{
      if(monthly&&/^PERAKAM /.test(section.name)){
        if(perakamRendered)return;
        perakamRendered=true;
        for(let i=0;i<individuals.length;i+=4){
          if(page++)body.appendPageBreak();
          workspaceDocReportHeading_(body,'Laporan Perakam Waktu',
            'SMK Bandar Baru Sungai Lalang  |  '+String(data.subtitle||'').split(' · ')[0]);
          individuals.slice(i,i+4).forEach(person=>{
            const detail=workspacePdfPerakamCard_(person);
            const who=body.appendParagraph('Bil: '+person.bil+'   Nama: '+person.name+
                '   Kategori: '+person.category);
            if(who.editAsText&&who.editAsText().setFontSize)who.editAsText().setFontSize(7);
            const t=body.appendTable([detail.headers].concat(detail.rows));
            workspaceDocStyleTable_(t,detail.headers,detail.rows,'PERAKAM WAKTU');
          });
        }
        return;
      }
      if(section.name==='INDIVIDU'&&monthly){
        individuals.forEach((person,i)=>{
          if(page++)body.appendPageBreak();
          workspaceDocReportHeading_(body,'Laporan Individu',
             'Bil: '+person.bil+'  |  Nama: '+person.name+'  |  '+person.category+
             '  |  Tempoh: '+String(data.subtitle||'').split(' · ')[0]);
          const detail=workspaceReportIndividualTable_(person);
          const table=body.appendTable([detail.headers].concat(detail.rows));
          workspaceDocStyleTable_(table,detail.headers,detail.rows,'INDIVIDU');
          const note=body.appendParagraph('Petunjuk: Merah = Lewat / Balik Awal   •   Jingga = Tidak Hadir / Cuti / Hujung Minggu');
          if(note.editAsText&&note.editAsText().setFontSize)note.editAsText().setFontSize(7);
        });
        return;
      }
      if(page++)body.appendPageBreak();
      let heading=section.name;
      if(section.name==='RINGKASAN')heading='SMK Bandar Baru Sungai Lalang — Ringkasan Kehadiran';
      if(section.name==='LEWAT BALIK AWAL')heading='SMK Bandar Baru Sungai Lalang — Laporan Lewat / Balik Awal';
      if(/^PERAKAM /.test(section.name))heading='Laporan Perakam Waktu — '+section.name;
      workspaceDocReportHeading_(body,heading,String(data.subtitle||'').split(' · ')[0]);
      // Never silently truncate monthly report rows.
      const table=body.appendTable([section.headers].concat(section.rows));
      workspaceDocStyleTable_(table,section.headers,section.rows,section.name);
    });
    doc.saveAndClose();
    const file=DriveApp.getFileById(doc.getId());
    const pdfBytes=file.getAs(MimeType.PDF).getBytes();
    if(pdfBytes.length>2500000)
      throw new Error('PDF melebihi 2.5 MB. Gunakan eksport Google Sheets atau pilih tempoh lebih pendek.');
    return {ok:true,mimeType:'application/pdf',fileName:title+'.pdf',base64:Utilities.base64Encode(pdfBytes)};
  }finally{
    try{DriveApp.getFileById(doc.getId()).setTrashed(true);}catch(e){}
  }
}
function workspaceExportSheet_(data){
  const sections=workspaceReportSections_(data);
  const colors=workspaceReportColors_();
  const monthly=sections.some(s=>s.name==='RINGKASAN')&&sections.some(s=>s.name==='INDIVIDU');
  const all=sections.slice();
  if(monthly){
    const individual=workspaceReportIndividualRows_(sections);
    const detail=[];
    individual.forEach(person=>{
      (person.days||[]).forEach(d=>detail.push([
        String(person.bil),person.name,person.category
      ].concat(d)));
    });
    if(detail.length)
      all.push({name:'INDIVIDU HARIAN',
        headers:['Bil.','Nama','Kategori','Tarikh','Hari','Masuk','Keluar','Masuk 2','Keluar 2','Status','Catatan'],
        rows:detail});
  }
  const title=workspaceSanitizeName_(data.title);
  const ss=SpreadsheetApp.create(title);
  const names=[];
  const safe=value=>/^[=+\-@]/.test(value)?"'"+value:value;
  all.forEach((section,index)=>{
    const sh=index===0?ss.getSheets()[0]:ss.insertSheet();
    const name=section.name.slice(0,31);
    sh.setName(name);names.push(name);
    const header=section.headers,cols=header.length;
    const titleRow=[name].concat(Array(cols-1).fill(''));
    const values=[titleRow,header].concat(section.rows).map(r=>r.map(safe));
    for(let at=0;at<values.length;at+=250){
      const chunk=values.slice(at,at+250);
      const range=sh.getRange(at+1,1,chunk.length,cols);
      range.setValues(chunk);
      if(range.setBackgrounds){
        const backgrounds=chunk.map((row,k)=>row.map((val,j)=>{
          const i=at+k;
          if(i===0)return colors.aqua;
          if(i===1)return colors.blue;
          if(name==='RINGKASAN'&&j===cols-1)return colors.amber;
          return workspaceReportCellColor_(val,name,false);
        }));
        range.setBackgrounds(backgrounds);
      }
      if(range.setBorder)
        range.setBorder(true,true,true,true,true,true,colors.green,
            SpreadsheetApp.BorderStyle?SpreadsheetApp.BorderStyle.SOLID:null);
    }
    const titleRange=sh.getRange(1,1,1,cols);
    if(titleRange.setBackground)titleRange.setBackground(colors.aqua);
    if(titleRange.setFontWeight)titleRange.setFontWeight('bold');
    const headerRange=sh.getRange(2,1,1,cols);
    headerRange.setFontWeight('bold').setBackground(colors.blue);
    if(headerRange.setFontColor)headerRange.setFontColor(colors.ink);
    sh.setFrozenRows(2);
    sh.autoResizeColumns(1,Math.min(cols,12));
    if(sh.getRange&&values.length>2){
      const dataRange=sh.getRange(3,1,values.length-2,cols);
      if(dataRange.setWrap)dataRange.setWrap(true);
      if(dataRange.setFontSize)dataRange.setFontSize(cols>11?9:10);
    }
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
