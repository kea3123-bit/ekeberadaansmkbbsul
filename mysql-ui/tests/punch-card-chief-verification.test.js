'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const js=fs.readFileSync('mysql-ui/Scripts.html','utf8');
const css=fs.readFileSync('mysql-ui/Styles.html','utf8');
const markup=fs.readFileSync('mysql-ui/Index.html','utf8');
new Function(js); // full JavaScript syntax
const start=js.indexOf('  function cardRowsHtml(');
const end=js.indexOf('  function compactCardReason(',start);
assert(start>0&&end>start,'TT Ketua renderer functions missing');
const esc=v=>String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;')
  .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const {cardRowsHtml,cardChiefMark}=new Function('esc','cardStatement',
  js.slice(start,end)+'return {cardRowsHtml,cardChiefMark};')(esc,()=> 'LEWAT · DIAMBIL MAKLUM');
const approval={label:'MAKLUM',kind:'TIME_REVIEW',entries:[{
 type:'LEWAT Sesi 1',reviewerName:'Pengarah Sekolah',reviewerJobTitle:'Pengetua',reviewedAt:'2026-11-15'}]};
const data={daysInMonth:30,records:[
 {day:10,status:'LEWAT',inTime:'07:48',outTime:'14:31',reviewItems:[{type:'LEWAT',session:1}],chiefVerification:approval},
 {day:11,status:'LEWAT',inTime:'08:10',reviewItems:[{type:'LEWAT',session:1}],chiefVerification:null},
 {day:12,status:'TIDAK HADIR',reason:'LAIN-LAIN',chiefVerification:{label:'LULUS',kind:'TIDAK_HADIR',entries:[{
  type:'TIDAK_HADIR · LAIN-LAIN',reviewerName:'Pengarah Sekolah',reviewerJobTitle:'Pengetua',reviewedAt:'2026-11-12'}]}},
 {day:13,status:'TIDAK HADIR',reason:'TIADA PENJELASAN',chiefVerification:null}
]};
const display=cardRowsHtml(data,1);
const print=cardRowsHtml(data,1,true);
for(const html of [display,print]){
  assert(html.includes('pc-chief-mark'),'Verified decision must be rendered');
  assert(html.includes('<small>MAKLUM</small>'),'Late incident should be marked acknowledged');
  assert(html.includes('<small>LULUS</small>'),'Approved absence should be marked LULUS');
  assert(html.includes('Pengetua'),'Reviewer's real title should appear in the tooltip');
  assert(html.includes('2026-11-15'),'Decision date should appear in tooltip');
  assert(html.includes('colspan="5" class="pc-absence-full"'),'Absent rows must reserve own TT Ketua cell');
  assert(html.includes('<td class="pc-sign"></td>'),'Unreviewed incidents must keep TT Ketua blank');
  assert(!html.includes('colspan="6" class="pc-absence-full"'),'No merged absence row can hide TT Ketua');
}
assert(cardChiefMark({chiefVerification:{label:'MAKLUM',entries:[]}})==='','No forged mark with missing decision data');
assert(cardChiefMark({chiefVerification:{label:'DITOLAK',entries:[{}]}})==='','Rejected case is not a positive mark');
const dangerous={chiefVerification:{label:'LULUS',entries:[{reviewerName:'<script>alert(1)</script>'}]}};
assert(!cardChiefMark(dangerous).includes('<script>'),'Tooltip user data must be HTML escaped');
assert(markup.includes('id="myCardRows"')&&markup.includes('id="adminCardRows"'),'Both card instances must remain');
assert(js.includes('renderMyPunchCard(){')&&js.includes('cardRowsHtml(d,state.myCardHalf)'),'Own card uses shared renderer');
assert(js.includes('function renderAdminCard(){')&&js.includes('cardRowsHtml(d,state.adminCardHalf)'),'Admin card uses shared renderer');
assert(js.includes('rows.innerHTML=cardRowsHtml(data,half,true)'),'Print spread uses shared renderer');
assert(css.includes('.pc-chief-mark')&&css.includes('@media print'),'Decision marker must remain printable');
console.log('PUNCH_CARD_TT_KETUA_OWN_ADMIN_PRINT_OK');
