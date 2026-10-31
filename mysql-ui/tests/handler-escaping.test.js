'use strict';
const fs=require('fs');
const assert=require('node:assert/strict');
const src=fs.readFileSync('mysql-ui/Scripts.html','utf8');
// Dangerous anti-pattern: JSON.stringify directly interpolated into quoted
// HTML onclick handlers. Apostrophes truncate the attribute.
assert.equal((src.match(/\$\{JSON\.stringify\(/g)||[]).length,0,
  'Unsafe JSON.stringify() markup interpolation has returned');
const encoded=(src.match(/\$\{attr\(JSON\.stringify\(/g)||[]).length;
assert.ok(encoded>=20,'Expected all dynamic onclick arguments to be encoded');
function escapeHtml(value){
  return String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
}
const input='O\'Connor"><img src=x onerror=alert(1)>';
const escaped=escapeHtml(JSON.stringify(input));
assert.ok(!escaped.includes("'")&&!escaped.includes('<')&&!escaped.includes('>'));
assert.ok(escaped.includes('&#039;')&&escaped.includes('&lt;'));
assert.ok(src.includes('href="'+String.fromCharCode(39)+'+attr(url)'), 'Report links must encode the URL');
console.log('PASS frontend: dynamic action arguments HTML-escaped, apostrophe/XSS regression guarded');
