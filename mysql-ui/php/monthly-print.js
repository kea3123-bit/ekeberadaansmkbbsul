/* eKeberadaan monthly report: native printable HTML. No Google Docs/GAS.
 * The browser's Print > Save as PDF creates PDF locally on desktop/iPhone.
 * All report text is escaped; the admin-only JSON comes from PHP/MySQL.
 */
(function(){
'use strict';
const PALETTE={aqua:'#C9F5F5',blue:'#91C6F4',amber:'#FFD09B',red:'#FF2A20',green:'#2D9D68'};
const CSS=[
  '#ek-report-viewer{position:fixed;inset:0;z-index:999999;background:#e8eef5;color:#1d2a3e;overflow:auto;font-family:Arial,Helvetica,sans-serif;font-size:11px;}',
  '#ek-report-viewer *{box-sizing:border-box;}',
  '.ek-report-toolbar{position:sticky;top:0;z-index:5;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 18px;background:#0d3976;color:white;box-shadow:0 2px 8px #0003;}',
  '.ek-report-toolbar button{padding:10px 16px;border:1px solid #d4e7ff;border-radius:7px;background:#fff;color:#103b77;font-weight:bold;cursor:pointer;}',
  '.ek-report-toolbar .ek-primary{background:#ffe45e;color:#152c56;border-color:#ffe45e;}',
  '.ek-report-toolbar-actions{display:flex;flex-wrap:wrap;gap:8px;}',
  '.ek-report-content{max-width:1150px;margin:20px auto 40px;}',
  '.ek-report-page{background:#fff;margin:0 0 18px;padding:17px;box-shadow:0 2px 14px #0002;page-break-after:always;break-after:page;}',
  '.ek-report-page:last-child{page-break-after:auto;break-after:auto;}',
  '.ek-report-title{background:#C9F5F5;padding:9px 12px;border-bottom:2px solid #2D9D68;text-align:center;font-size:15px;font-weight:800;text-transform:uppercase;letter-spacing:.3px;}',
  '.ek-report-sub{font-size:10px;text-align:center;padding:6px 0 10px;color:#334155;}',
  '.ek-report-table{border-collapse:collapse;width:100%;table-layout:fixed;font-size:9px;}',
  '.ek-report-table th,.ek-report-table td{border:1px solid #2D9D68;padding:4px 5px;text-align:center;vertical-align:middle;overflow-wrap:anywhere;white-space:pre-wrap;}',
  '.ek-report-table th{background:#91C6F4;color:#183452;font-weight:800;}',
  '.ek-report-table td.ek-left,.ek-report-table th.ek-left{text-align:left;}',
  '.ek-report-table tr:nth-child(even) td:not(.ek-red):not(.ek-amber){background:#f5faff;}',
  '.ek-report-table .ek-red{background:#FF2A20!important;color:#fff;font-weight:bold;}',
  '.ek-report-table .ek-amber{background:#FFD09B!important;color:#473522;}',
  '.ek-report-table .ek-aqua{background:#C9F5F5!important;font-weight:bold;}',
  '.ek-report-section-label{font-size:11px;font-weight:bold;background:#C9F5F5;padding:5px 9px;margin:6px 0 3px;border-left:3px solid #2D9D68;}',
  '.ek-report-person{margin:8px 0 14px;break-inside:avoid;page-break-inside:avoid;}',
  '.ek-report-person h3{font-size:10px;margin:0;background:#C9F5F5;padding:6px 8px;}',
  '.ek-report-week{margin-top:3px;}',
  '.ek-report-week td{height:22px;font-size:8px;}',
  '.ek-report-individual{font-size:7px;}',
  '.ek-report-individual th,.ek-report-individual td{padding:3px 2px;font-size:7px;}',
  '.ek-report-individual th:nth-child(8),.ek-report-individual th:nth-child(16){width:13%;}',
  '.ek-report-foot{font-size:9px;color:#475569;margin-top:9px;display:flex;gap:18px;justify-content:center;}',
  '.ek-report-key{display:inline-block;width:11px;height:11px;border:1px solid #999;vertical-align:middle;margin-right:4px;}',
  '@media(max-width:720px){.ek-report-toolbar{display:block;}.ek-report-toolbar-actions{margin-top:8px;}.ek-report-content{width:1100px;margin:10px 0;}.ek-report-page{box-shadow:none;}}',
  '@media print{',
    '@page{size:A4 landscape;margin:8mm;}',
    'html,body{background:#fff!important;margin:0!important;padding:0!important;overflow:visible!important;}',
    'body>*:not(#ek-report-viewer){display:none!important;}',
    '#ek-report-viewer{position:static!important;inset:auto!important;z-index:auto!important;overflow:visible!important;background:#fff!important;width:auto!important;height:auto!important;font-size:8px;}',
    '#ek-report-viewer .ek-report-toolbar{display:none!important;}',
    '#ek-report-viewer .ek-report-content{margin:0!important;max-width:none!important;width:100%!important;}',
    '#ek-report-viewer .ek-report-page{padding:0!important;margin:0!important;box-shadow:none!important;break-after:page;page-break-after:always;}',
    '#ek-report-viewer .ek-report-page:last-child{break-after:auto;page-break-after:auto;}',
    '#ek-report-viewer .ek-report-table{font-size:7px;}',
    '#ek-report-viewer .ek-report-person{break-inside:avoid;page-break-inside:avoid;}',
    '#ek-report-viewer *{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;}',
  '}'
].join('\n');
function h(v){
  return String(v===null||v===undefined?'':v)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function isColored(value){
  const text=String(value||'').toUpperCase();
  if(/LEWAT|BALIK AWAL/.test(text))return 'ek-red';
  if(/HUJUNG MINGGU|CUTI UMUM|TIDAK HADIR|BELUM HADIR|CUTI SAKIT/.test(text))return 'ek-amber';
  return '';
}
function table(headers,rows,kind){
  const titles=(headers||[]).map((x,i)=>'<th class="'+(i===1?'ek-left':'')+'">'+h(x)+'</th>').join('');
  const body=(rows||[]).map((r,ri)=>{
    const cells=(headers||[]).map((_,j)=>{
      const v=Array.isArray(r)?r[j]:'';
      let color=isColored(v);
      if(kind==='RINGKASAN'&&((j===5||j===7)&&Number(v)>0))color='ek-red';
      if(kind==='RINGKASAN'&&((j===9||j===10)&&Number(v)>0||j===headers.length-1))color='ek-amber';
      return '<td class="'+[j===1?'ek-left':'',color].filter(Boolean).join(' ')+'">'+h(v)+'</td>';
    }).join('');
    return '<tr>'+cells+'</tr>';
  }).join('');
  return '<table class="ek-report-table"><thead><tr>'+titles+'</tr></thead><tbody>'+body+'</tbody></table>';
}
function title(name,period,school){
  return '<div class="ek-report-title">'+h(school)+' — '+h(name)+'</div>'+
    '<div class="ek-report-sub">Tempoh: '+h(period)+'</div>';
}
function legend(){
  return '<div class="ek-report-foot"><span><i class="ek-report-key" style="background:#FF2A20"></i>Lewat / Balik Awal</span>'+
    '<span><i class="ek-report-key" style="background:#FFD09B"></i>Cuti / Tidak Hadir / Hujung Minggu</span>'+
    '<span><i class="ek-report-key" style="background:#91C6F4"></i>Kepala jadual</span></div>';
}
function page(content){
  return '<section class="ek-report-page">'+content+'</section>';
}
function dayInfo(key){
  const d=new Date(String(key)+'T12:00:00Z');
  return {
    label:String(key).slice(8,10)+'/'+String(key).slice(5,7),
    day:isNaN(d.valueOf())?'':['Ahd','Isn','Sel','Rab','Kha','Jum','Sab'][d.getUTCDay()]
  };
}
function monthlyPeople(sections){
  const individual=(sections.find(s=>s.name==='INDIVIDU')||{rows:[]}).rows||[];
  const byEmail=new Map();
  (sections||[]).filter(s=>/^PERAKAM /.test(s.name||'')).forEach(section=>{
    const days=(section.headers||[]).slice(2);
    (section.rows||[]).forEach(row=>{
      const email=String(row[1]||'').trim().toLowerCase();
      if(!email)return;
      if(!byEmail.has(email))byEmail.set(email,{email,name:row[0]||'',category:'',days:[]});
      const p=byEmail.get(email);
      days.forEach((date,i)=>{
        const raw=String(row[i+2]||'');
        const chunks=raw.split('|');
        const time=chunks[0].split(';');
        const first=time[0].split('/'),second=String(time[1]||'').split('/');
        const noTime=/^(BELUM HADIR|TIDAK HADIR|HUJUNG MINGGU|CUTI UMUM|TH|--)$/i.test(chunks[0]);
        const status=noTime?(chunks[0]==='TH'?'TIDAK HADIR':chunks[0]):(chunks[1]||'HADIR');
        const di=dayInfo(date);
        p.days.push({date,day:di.day,label:di.label,
          masuk:noTime?'':(first[0]==='--'?'':first[0]||''),
          balik:noTime?'':(first[1]==='--'?'':first[1]||''),
          masuk2:noTime?'':(second[0]==='--'?'':second[0]||''),
          balik2:noTime?'':(second[1]==='--'?'':second[1]||''),
          status,note:chunks.slice(1).join('|')||''});
      });
    });
  });
  const people=individual.length?individual.map((row,i)=>{
    const email=String(row[1]||'').trim().toLowerCase();
    const found=byEmail.get(email)||{days:[]};
    return {bil:i+1,email,name:row[0]||found.name||'',category:row[2]||'',
      summary:row,days:found.days.sort((a,b)=>a.date.localeCompare(b.date))};
  }):[...byEmail.values()].map((p,i)=>({...p,bil:i+1,summary:[]}));
  return people;
}
function simplePage(section,period,school){
  return page(title(section.name==='RINGKASAN'?'Ringkasan Kehadiran':
    section.name==='LEWAT BALIK AWAL'?'Lewat / Balik Awal':section.name,period,school)+
    table(section.headers,section.rows,section.name)+legend());
}
function cardPerson(person){
  const weeks=[];
  for(let i=0;i<person.days.length;i+=7){
    const dates=person.days.slice(i,i+7);
    const hds=dates.map(d=>d.label+' '+d.day);
    const values=dates.map(d=>{
      if(/TIDAK HADIR|HUJUNG MINGGU|CUTI UMUM|BELUM HADIR/.test(d.status))
        return d.status+(d.note?' — '+d.note:'');
      return (d.masuk||'--')+'/'+(d.balik||'--')+
        (d.masuk2||d.balik2?'; '+(d.masuk2||'--')+'/'+(d.balik2||'--'):'')+
        (d.status==='HADIR'?'':' — '+d.status);
    });
    weeks.push('<div class="ek-report-week">'+table(hds,[values],'PERAKAM')+'</div>');
  }
  return '<div class="ek-report-person"><h3>Bil. '+h(person.bil)+
    ' — '+h(person.name)+' / '+h(person.category)+'</h3>'+weeks.join('')+'</div>';
}
function perakamPages(people,period,school){
  let html='';
  for(let i=0;i<people.length;i+=2){
    html+=page(title('Laporan Perakam Waktu',period,school)+
      people.slice(i,i+2).map(cardPerson).join('')+legend());
  }
  return html;
}
function individualPage(person,period,school){
  const half=16,head=['Tarikh','Hari','Masuk','Balik','Masuk 2','Balik 2','Status','Catatan'];
  const left=person.days.slice(0,half),right=person.days.slice(half);
  const data=[];
  const unpack=d=>d?[d.label,d.day,d.masuk,d.balik,d.masuk2,d.balik2,d.status,d.note]:Array(8).fill('');
  for(let i=0;i<half;i++)data.push(unpack(left[i]).concat(unpack(right[i])));
  const count=person.summary||[];
  return page(title('Laporan Individu',period,school)+
    '<div class="ek-report-section-label">Bil. '+h(person.bil)+' — '+h(person.name)+
    ' | '+h(person.category)+'</div>'+
    '<p style="font-size:9px;margin:7px 0">Hadir: '+h(count[3]||0)+
    ' &nbsp; Lewat: '+h(count[4]||0)+' &nbsp; Balik awal: '+h(count[5]||0)+
    ' &nbsp; Tidak hadir: '+h(count[6]||0)+'</p>'+
    '<div class="ek-report-individual">'+table(head.concat(head),data,'INDIVIDU')+'</div>'+legend());
}
function buildMonthlyHtmlReport(report){
  if(!report||report.kind!=='MONTHLY_HTML'||!Array.isArray(report.sections))
    throw new Error('Data laporan HTML tidak sah. Sila kemas kini backend PHP.');
  const period=String(report.fromDate||'')+' hingga '+String(report.toDate||'');
  const school=report.schoolName||'eKeberadaan';
  const sections=report.sections;
  const summary=sections.find(s=>s.name==='RINGKASAN');
  const late=sections.find(s=>s.name==='LEWAT BALIK AWAL');
  const people=monthlyPeople(sections);
  if(!summary||!late||!people.length)
    throw new Error('Data laporan bulanan tidak lengkap. Sila semak rekod staf dalam MySQL.');
  return [simplePage(summary,period,school),
    simplePage(late,period,school),
    perakamPages(people,period,school),
    people.map(p=>individualPage(p,period,school)).join('')].join('');
}
function closeMonthlyHtmlReport(){
  const element=document.getElementById('ek-report-viewer');
  if(element)element.remove();
  const style=document.getElementById('ek-report-style');
  if(style)style.remove();
}
function showMonthlyReportPreview(report){
  closeMonthlyHtmlReport();
  const markup=buildMonthlyHtmlReport(report);
  const style=document.createElement('style');
  style.id='ek-report-style';style.textContent=CSS;
  document.head.appendChild(style);
  const root=document.createElement('div');
  root.id='ek-report-viewer';
  root.setAttribute('role','dialog');
  root.setAttribute('aria-label','Laporan bulanan boleh cetak');
  root.innerHTML='<div class="ek-report-toolbar">'+
    '<div><b>Laporan eKeberadaan</b><div style="font-size:11px;opacity:.85">HTML terus daripada MySQL · tanpa Google Docs</div></div>'+
    '<div class="ek-report-toolbar-actions">'+
    '<button type="button" class="ek-primary" id="ek-report-print">Cetak / Simpan PDF</button>'+
    '<button type="button" id="ek-report-download">Muat turun HTML</button>'+
    '<button type="button" id="ek-report-close">Tutup</button></div></div>'+
    '<main class="ek-report-content" id="ek-report-print-body">'+markup+'</main>';
  document.body.appendChild(root);
  root.querySelector('#ek-report-close').addEventListener('click',closeMonthlyHtmlReport);
  root.querySelector('#ek-report-print').addEventListener('click',()=>window.print());
  root.querySelector('#ek-report-download').addEventListener('click',()=>{
    const html='<!doctype html><html lang="ms"><head><meta charset="utf-8">'+
      '<meta name="viewport" content="width=device-width, initial-scale=1">'+
      '<title>Laporan eKeberadaan</title><style>'+CSS+'</style></head><body>'+
      '<div id="ek-report-viewer"><main class="ek-report-content">'+markup+'</main></div>'+
      '</body></html>';
    const url=URL.createObjectURL(new Blob([html],{type:'text/html;charset=utf-8'}));
    const link=document.createElement('a');
    link.href=url;
    link.download='Laporan_eKeberadaan_'+String(report.fromDate||'')+'_'+String(report.toDate||'')+'.html';
    document.body.appendChild(link);link.click();link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),15000);
  });
}
window.showMonthlyReportPreview=showMonthlyReportPreview;
window.closeMonthlyHtmlReport=closeMonthlyHtmlReport;
window.buildMonthlyHtmlReport=buildMonthlyHtmlReport;
})();
