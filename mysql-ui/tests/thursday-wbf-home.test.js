'use strict';
const fs=require('node:fs');
const assert=require('node:assert/strict');
const js=fs.readFileSync('mysql-ui/Scripts.html','utf8');
const html=fs.readFileSync('mysql-ui/Index.html','utf8');
new Function(js);
for(const id of ['homeWbfTag','homeWbfDetail','s1OutRef'])assert(html.includes('id="'+id+'"'),'Missing home schedule element '+id);
for(const text of ['wbf.wbfActive','wbf.wbfPending','wbf.wbfOutWindow','wbf.wbfApplied','WBF aktif','if(res.schedule)state.boot.schedule=res.schedule'])
  assert(js.includes(text),'Missing WBF display or punch state sync: '+text);
const render=js.slice(js.indexOf('  function renderBoot(){'),js.indexOf('  function navigate(',js.indexOf('  function renderBoot(){')));
assert(render.includes("text('s1OutRef',wbf.wbfPending?"),'WBF display is still hardcoded');
assert(render.includes('homeWbfTag'),'WBF badge must be visible on eligible Thursdays');
const punch=js.slice(js.indexOf('  async function startPunch('),js.indexOf('  function currentPosition()',js.indexOf('  async function startPunch(')));
assert(punch.includes('if(res.schedule)state.boot.schedule=res.schedule'),'Fresh WBF schedule must be shown immediately after punch');
assert(punch.indexOf('if(res.schedule)state.boot.schedule=res.schedule')<punch.indexOf('renderBoot()'),'Schedule must be applied before rendering');
console.log('THURSDAY_WBF_HOME_UI_AND_PUNCH_UPDATE_OK');
