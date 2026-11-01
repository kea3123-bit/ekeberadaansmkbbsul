'use strict';
const fs = require('node:fs');
const assert = require('node:assert/strict');
const cp = require('node:child_process');
const php = fs.readFileSync('php/api.php','utf8');
const js = fs.readFileSync('mysql-ui/Scripts.html','utf8');
const labels = ['BENGKEL/KURSUS/SEMINAR','MESYUARAT/TAKLIMAT'];
const listInPhp = (fn) => {
  const rx=new RegExp('function '+fn+'\\(\\): array \\{([\\s\\S]*?)\\n\\}');
  const m=php.match(rx);assert(m,'Missing backend '+fn);
  const output=cp.execFileSync('php',['-r','function '+fn+'(): array {'+m[1]+'\n} echo json_encode('+fn+'());'],{encoding:'utf8'});
  return JSON.parse(output);
};
const absence=listInPhp('absence_types');
const presence=listInPhp('presence_types');
for(const list of [absence,presence]){
  for(const label of labels){
    const sek=label+' (SEK)',ppd=label+' (PPD)';
    assert.equal(list.filter(x=>x===sek).length,1,'Missing/duplicate SEK '+sek);
    assert(list.includes(ppd),'Existing PPD type must remain available: '+label);
    assert(list.indexOf(sek)<list.indexOf(ppd),'SEK must appear before PPD: '+label);
    for(const suffix of ['JPN','KPM'])assert(list.includes(label+' ('+suffix+')'),'Existing '+suffix+' type must remain: '+label);
  }
}
const m=js.match(/const requiredExternalOfficialTypes=\[([\s\S]*?)\];/);
assert(m,'Frontend fallback official types missing');
const fallback=[...m[1].matchAll(/'([^']+)'/g)].map(x=>x[1]);
for(const label of labels) {
  assert(fallback.includes(label+' (SEK)'),'Frontend fallback missing '+label);
  assert(fallback.indexOf(label+' (SEK)')<fallback.indexOf(label+' (PPD)'),'Frontend fallback ordering wrong');
}
assert(js.includes('const sourceTypes=Array.isArray(serverTypes)&&serverTypes.length?serverTypes:fallbackTypes'),'Server-provided MySQL validation lists must remain authoritative');
assert(js.includes("if(!normalizedAllowed.includes(selectedType))"),'Client-side validation must preserve approved types');
console.log('SEK_ABSENCE_AND_PRESENCE_BACKEND_FRONTEND_OPTIONS_OK');
