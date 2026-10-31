'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const source=fs.readFileSync('mysql-ui/php/monthly-print.js','utf8');
const ctx={window:{}};
vm.runInNewContext(source,ctx,{filename:'monthly-print.js'});
assert.equal(typeof ctx.window.buildMonthlyHtmlReport,'function');
assert.equal(typeof ctx.window.showMonthlyReportPreview,'function');
assert.ok(!source.includes('Google Docs API'),'PDF viewer should not require Docs');
const bad='Ali <img src=x onerror=alert(1)> & \'Latif';
const month={
  ok:true,kind:'MONTHLY_HTML',schoolName:'SMK Bandar Baru Sungai Lalang',
  fromDate:'2026-10-01',toDate:'2026-10-31',
  sections:[
    {name:'RINGKASAN',headers:['Bil.','Nama','Lewat Bil.','Balik Awal Bil.','Tidak Hadir','Catatan'],
      rows:[[1,bad,1,1,0,''],[2,'Staf B',0,0,1,'']]},
    {name:'LEWAT BALIK AWAL',headers:['Tarikh','Nama','Lewat','Balik awal'],
      rows:[['2026-10-01',bad,'LEWAT','BALIK AWAL']]},
    {name:'PERAKAM 01-07',headers:['Nama','Emel','2026-10-01','2026-10-02'],
      rows:[[bad,'a@example.test','07:55/15:30|LEWAT / BALIK AWAL','HUJUNG MINGGU'],
            ['Staf B','b@example.test','TIDAK HADIR|Cuti sakit','07:30/16:30']]},
    {name:'INDIVIDU',headers:['Nama','Emel','Kategori','Hari hadir','Lewat','Balik awal','Tidak hadir','Belum hadir'],
      rows:[[bad,'a@example.test','AKP',1,1,1,0,0],['Staf B','b@example.test','PPP',1,0,0,1,0]]}
  ]
};
const output=ctx.window.buildMonthlyHtmlReport(month);
assert.ok(output.includes('Ringkasan Kehadiran'));
assert.ok(output.includes('Laporan Perakam Waktu'));
assert.ok(output.includes('Laporan Individu'));
assert.ok(output.includes('HUJUNG MINGGU'));
assert.ok(output.includes('Cuti sakit'));
assert.ok(output.includes('ek-red')&&output.includes('ek-amber'));
assert.ok(output.includes('&lt;img src=x onerror=alert(1)&gt;'),'unsafe DB content must be escaped');
assert.ok(!output.includes('<img src=x onerror=alert(1)>'),'HTML injection present');
assert.equal((output.match(/ek-report-page/g)||[]).length,5,
  'Expected summary, exceptions, one perakam group and two individual pages');
assert.throws(()=>ctx.window.buildMonthlyHtmlReport({kind:'MONTHLY_HTML',sections:[]}),/tidak lengkap/);
const frontend=fs.readFileSync('mysql-ui/Scripts.html','utf8');
assert.ok(frontend.includes("runServer('generateAttendancePresenceReportHtml',state.token,period)"));
assert.ok(!frontend.includes("runServer('generateAttendancePresenceReportPdf',state.token,p)"));
const endpoint=fs.readFileSync('php/api.php','utf8');
assert.ok(endpoint.includes("case 'generateAttendancePresenceReportHtml':"));
assert.ok(endpoint.includes("require_user($a[0]??'',true)"));
assert.ok(!endpoint.slice(endpoint.indexOf("case 'generateAttendancePresenceReportHtml':"),
  endpoint.indexOf("case 'generatePublicAbsencePresencePdf':")).includes('workspace_report('));
const view=fs.readFileSync('mysql-ui/Index.html','utf8');
assert.ok(view.includes('Cetak / Simpan PDF (HTML)'));
console.log('PASS: admin-only HTML print report, 5 pages, status colors, XSS escaping and no Google Docs');
