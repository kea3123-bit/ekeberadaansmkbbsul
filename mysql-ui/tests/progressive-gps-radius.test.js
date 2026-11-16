'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const s=fs.readFileSync('mysql-ui/Scripts.html','utf8');
new Function(s);
const begin=s.indexOf('  function progressivePunchRadius(');
const end=s.indexOf('  function liveLocationAgeMs(',begin);
assert(begin>=0&&end>begin,'Missing progressive client preview');
const fn=new Function(s.slice(begin,end)+'return progressivePunchRadius;')();
for(const [distance,expectedRadius,expectedAllowed] of [
 [90,90,true],[91,100,true],[100,100,true],[100.1,110,true],
 [114,120,true],[139.99,140,true],[140,140,true],[140.01,140,false]
]){
 const x=fn(distance,90);
 assert.equal(x.usedRadiusM,expectedRadius,'Wrong preview stage for '+distance);
 assert.equal(x.allowed,expectedAllowed,'Wrong preview allow for '+distance);
}
assert.equal(fn(100,95).usedRadiusM,105,'Stage needs to start at actual admin radius');
assert.equal(fn(139,135).usedRadiusM,140,'Final stage capped at 140m');
assert.equal(fn(161,160).allowed,false,'Existing admin radius must not be silently reduced');
assert(s.includes('state.homeFallbackRadiusCircle=L.circle'),'Fallback ring absent on map');
assert(s.includes('progressiveRadiusUsed'),'Frontend must use server-authoritative allowance flag');
assert(s.includes('res.usedRadiusM'),'Frontend must show server-selected radius, not estimate');
assert(s.includes("refreshMyTimeReasonNotice(true)"),'Mandatory reason gate must remain');
assert(s.includes("runServer('punch',state.token,type,loc,clientInfo)"),'Normal punch API must remain');
assert(s.includes('const thresholdsM=[80,100,120,140]'),
 'Do not confuse the separate GPS accuracy staged-acquisition policy');
console.log('PROGRESSIVE_GPS_RADIUS_OWN_ADMIN_MAP_PREVIEW_OK');
