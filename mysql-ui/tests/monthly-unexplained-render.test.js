'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const js=fs.readFileSync('mysql-ui/php/monthly-print.js','utf8');
const ctx={window:{},console};
vm.createContext(ctx);vm.runInContext(js,ctx);
const report={
 kind:'MONTHLY_HTML',fromDate:'2026-10-01',toDate:'2026-10-01',schoolName:'Sekolah Ujian',
 sections:[
  {name:'RINGKASAN',headers:['Bil.','Nama','Kategori','Hari Kerja','Hadir','Lewat Bil.','Lewat Min.','Balik Awal Bil.','Balik Awal Min.','Tidak Hadir','Keberadaan','Catatan'],
   rows:[[1,'PEGAWAI A','AKP',1,1,1,40,1,30,0,1,'']]},
  {name:'LEWAT BALIK AWAL',
   headers:['Tarikh','Nama','Emel','Lewat','Balik awal','Masuk','Balik','Masuk 2','Balik 2','Penjelasan Lewat','Penjelasan Balik Awal'],
   rows:[
     ['2026-10-01','PEGAWAI A','a@example.test','LEWAT','','08:10','16:30','','','TIADA PENJELASAN',''],
     ['2026-10-01','PEGAWAI B','b@example.test','LEWAT','BALIK AWAL','08:10','14:30','','',
      'Keberadaan: MESYUARAT (07:30–08:30)','TIADA PENJELASAN']
   ]},
  {name:'PERAKAM 01-01',headers:['Nama','Emel','2026-10-01'],
   rows:[['PEGAWAI A','a@example.test','08:10/16:30|LEWAT'],
         ['PEGAWAI B','b@example.test','08:10/14:30|LEWAT / BALIK AWAL']]},
  {name:'INDIVIDU',headers:['Nama','Emel','Kategori','Hadir','Lewat','Balik awal','Tidak hadir','Belum hadir'],
   rows:[['PEGAWAI A','a@example.test','AKP',1,1,0,0,0],['PEGAWAI B','b@example.test','PPP',1,1,1,0,0]]}
 ]};
const html=ctx.window.buildMonthlyHtmlReport(report);
assert(html.includes('Penjelasan Lewat')&&html.includes('Penjelasan Balik Awal'));
assert(html.includes('ek-time-exceptions'));
assert(html.includes('<td class="ek-red">LEWAT</td>'),'Unexplained late should be red');
assert(html.includes('<td class="ek-explained">LEWAT</td>'),'Explained late must not be red');
assert(html.includes('<td class="ek-red">BALIK AWAL</td>'),'Unexplained early must be red');
assert(html.includes('<td class="ek-explained">Keberadaan:'),'Explained request should have softer highlight');
assert(html.includes('<td class="ek-red">TIADA PENJELASAN</td>'),'Missing request must be visible');
assert(html.includes('<td class="ek-red">LEWAT</td>'));
assert(!html.includes('<script>alert(1)</script>'),'Dangerous markup visible');
console.log('MONTHLY_UNEXPLAINED_HIGHLIGHTS_RENDER_TEST_OK');
