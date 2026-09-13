from pathlib import Path


def replace_once(src, old, new, label):
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 match, got {count}')
    return src.replace(old, new, 1)

scripts_path = Path('Scripts.html')
scripts = scripts_path.read_text(encoding='utf-8')
old = """  async function startPunch(type){
    const test=String(state.boot?.settings?.systemMode||'REAL')==='TEST';
    setPunchBusy(true); gps('busy',test?'MOD TEST — merakam waktu dan IP…':'Mendapatkan lokasi GPS dan IP awam…');
    try{
      const ipPromise=getClientNetworkInfo(false); let loc=null;
      if(!test){const pos=await currentPosition();loc={lat:pos.coords.latitude,lng:pos.coords.longitude,accuracy:pos.coords.accuracy};gps('ok',`GPS ±${Math.round(loc.accuracy)}m · menyemak radius dan IP…`);}
      const clientInfo=await ipPromise, res=await runServer('punch',state.token,type,loc,clientInfo);
      if(res&&res.attendance){state.boot.attendance=res.attendance;renderBoot();}else await refreshBoot();
      const ipText=res.ip?` · IP ${res.ip}`:' · IP tidak dikesan';
      gps('ok',test?`Rekod MOD TEST diterima${ipText}.`:`Rekod waktu diterima · jarak ${res.distanceM}m${ipText}.`);
      toast(res.ipWarning||res.message,res.ipWarning?6000:4500); state.myCardLoaded=false; state.myCardData=null;
      if(res.timeException) state.timeReview=null;
    }catch(e){gps('',e.message);handleServerError(e,false);}finally{setPunchBusy(false);}
  }

  function currentPosition(){return new Promise((resolve,reject)=>{if(!navigator.geolocation)return reject(new Error('Pelayar ini tidak menyokong geolocation.'));navigator.geolocation.getCurrentPosition(resolve,err=>{const msg={1:'Akses lokasi ditolak. Benarkan Location untuk laman ini.',2:'Lokasi tidak dapat dikesan.',3:'Masa mendapatkan lokasi tamat.'}[err.code]||err.message;reject(new Error(msg));},{enableHighAccuracy:true,timeout:18000,maximumAge:0});});}
"""
new = """  function punchGpsPolicy(){
    const s=state.boot?.settings||{};
    const radiusM=Math.max(1,Number(s.radiusM)||200);
    const configuredMaxAccuracyM=Math.max(1,Number(s.maxGpsAccuracyM)||120);
    const targetAccuracyM=Math.min(configuredMaxAccuracyM,Math.max(25,Math.min(40,radiusM*0.5)));
    const usableAccuracyM=Math.min(configuredMaxAccuracyM,Math.max(45,Math.min(65,radiusM*0.8)));
    return {radiusM,configuredMaxAccuracyM,targetAccuracyM,usableAccuracyM,timeoutMs:8000};
  }

  function clientHaversineMeters(lat1,lon1,lat2,lon2){
    const rad=x=>x*Math.PI/180,R=6371000,dLat=rad(lat2-lat1),dLon=rad(lon2-lon1);
    const a=Math.sin(dLat/2)**2+Math.cos(rad(lat1))*Math.cos(rad(lat2))*Math.sin(dLon/2)**2;
    return R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a));
  }

  function punchGpsDistance(pos){
    const s=state.boot?.settings||{},lat=Number(s.schoolLat),lng=Number(s.schoolLng);
    if(!pos?.coords||!Number.isFinite(lat)||!Number.isFinite(lng))return NaN;
    return clientHaversineMeters(Number(pos.coords.latitude),Number(pos.coords.longitude),lat,lng);
  }

  function bestPunchPosition(){
    const policy=punchGpsPolicy();
    return new Promise((resolve,reject)=>{
      if(!navigator.geolocation)return reject(new Error('Pelayar ini tidak menyokong geolocation.'));
      let best=null,watchId=null,settled=false;
      const finish=(err,pos)=>{
        if(settled)return;settled=true;
        if(watchId!==null)try{navigator.geolocation.clearWatch(watchId);}catch(_e){}
        clearTimeout(timer);
        err?reject(err):resolve(pos);
      };
      const timer=setTimeout(()=>{
        if(!best)return finish(new Error('Lokasi GPS belum dapat dikesan. Cuba aktifkan Location/GPS dan cuba semula.'));
        const accuracy=Math.round(Number(best.coords.accuracy)||0),distance=Math.round(punchGpsDistance(best));
        if(accuracy>policy.usableAccuracyM){
          return finish(new Error(`Ketepatan GPS masih ±${accuracy}m selepas beberapa bacaan. Untuk radius ${Math.round(policy.radiusM)}m, tunggu GPS lebih stabil dan cuba semula.${Number.isFinite(distance)?` Anggaran lokasi semasa ${distance}m dari pusat.`:''}`));
        }
        finish(null,best);
      },policy.timeoutMs);
      watchId=navigator.geolocation.watchPosition(pos=>{
        const accuracy=Number(pos?.coords?.accuracy);
        if(!Number.isFinite(accuracy)||accuracy<0)return;
        if(!best||accuracy<Number(best.coords.accuracy))best=pos;
        const chosen=best||pos,bestAccuracy=Math.round(Number(chosen.coords.accuracy)||0),distance=Math.round(punchGpsDistance(chosen));
        gps('busy',`Menstabilkan GPS… ±${bestAccuracy}m${Number.isFinite(distance)?` · anggaran ${distance}m / ${Math.round(policy.radiusM)}m`:''}`);
        if(bestAccuracy<=policy.targetAccuracyM)finish(null,chosen);
      },err=>{
        if(err?.code===1)return finish(new Error('Akses lokasi ditolak. Benarkan Location untuk laman ini.'));
        if(!best&&err?.code===2)gps('busy','GPS belum mendapat lokasi. Mencuba lagi…');
      },{enableHighAccuracy:true,timeout:policy.timeoutMs,maximumAge:0});
    });
  }

  async function startPunch(type){
    const test=String(state.boot?.settings?.systemMode||'REAL')==='TEST';
    const gpsPolicy=punchGpsPolicy();
    setPunchBusy(true); gps('busy',test?'MOD TEST — merakam waktu dan IP…':'Mencari bacaan GPS terbaik…');
    try{
      const ipPromise=getClientNetworkInfo(false); let loc=null;
      if(!test){
        const pos=await bestPunchPosition();
        loc={lat:pos.coords.latitude,lng:pos.coords.longitude,accuracy:pos.coords.accuracy};
        const estimated=Math.round(punchGpsDistance(pos));
        gps('ok',`GPS ±${Math.round(loc.accuracy)}m${Number.isFinite(estimated)?` · anggaran ${estimated}m / ${Math.round(gpsPolicy.radiusM)}m`:''} · menyemak server…`);
      }
      const clientInfo=await ipPromise, res=await runServer('punch',state.token,type,loc,clientInfo);
      if(res&&res.attendance){state.boot.attendance=res.attendance;renderBoot();}else await refreshBoot();
      const ipText=res.ip?` · IP ${res.ip}`:' · IP tidak dikesan';
      gps('ok',test?`Rekod MOD TEST diterima${ipText}.`:`Rekod waktu diterima · GPS ±${Number(res.accuracyM)||Math.round(loc?.accuracy||0)}m · jarak ${res.distanceM}m / ${Number(res.radiusM)||Math.round(gpsPolicy.radiusM)}m${ipText}.`);
      toast(res.ipWarning||res.message,res.ipWarning?6000:4500); state.myCardLoaded=false; state.myCardData=null;
      if(res.timeException) state.timeReview=null;
    }catch(e){gps('',e.message);handleServerError(e,false);}finally{setPunchBusy(false);}
  }

  function currentPosition(){return new Promise((resolve,reject)=>{if(!navigator.geolocation)return reject(new Error('Pelayar ini tidak menyokong geolocation.'));navigator.geolocation.getCurrentPosition(resolve,err=>{const msg={1:'Akses lokasi ditolak. Benarkan Location untuk laman ini.',2:'Lokasi tidak dapat dikesan.',3:'Masa mendapatkan lokasi tamat.'}[err.code]||err.message;reject(new Error(msg));},{enableHighAccuracy:true,timeout:18000,maximumAge:0});});}
"""
scripts = replace_once(scripts, old, new, 'Scripts GPS flow')

old = "  function fillSettings(s){const f=document.getElementById('settingsForm');if(!f)return;Object.keys(s).forEach(k=>{if(f.elements[k])f.elements[k].value=s[k]??'';});updateModeSettingHint();if(state.locationMap)setTimeout(syncMapFromInputs,30);}\n"
new = """  function fillSettings(s){const f=document.getElementById('settingsForm');if(!f)return;Object.keys(s).forEach(k=>{if(f.elements[k])f.elements[k].value=s[k]??'';});updateModeSettingHint();updateGpsSettingWarning();if(state.locationMap)setTimeout(syncMapFromInputs,30);}
  function updateGpsSettingWarning(){
    const radius=Number(document.getElementById('settingRadius')?.value||0),accuracy=Number(document.getElementById('settingGpsAccuracy')?.value||0),hint=document.getElementById('gpsSettingWarning');
    if(!hint)return;
    const risky=radius>0&&accuracy>radius;
    hint.classList.toggle('hidden',!risky);
    if(risky)hint.textContent=`⚠ Had ketepatan GPS ${Math.round(accuracy)}m lebih besar daripada radius ${Math.round(radius)}m. Semasa punch, app akan menunggu bacaan yang lebih tepat supaya staf dalam radius tidak tersalah ditolak.`;
  }
"""
scripts = replace_once(scripts, old, new, 'Settings warning function')
old = "  function syncMapRadius(){if(!state.locationMap)return;const radius=Math.max(1,parseFloat(document.getElementById('settingRadius')?.value)||200);state.locationCircle?.setRadius(radius);const ll=state.locationMarker?.getLatLng();if(ll)syncMapReadout(ll.lat,ll.lng,radius);}\n"
new = "  function syncMapRadius(){updateGpsSettingWarning();if(!state.locationMap)return;const radius=Math.max(1,parseFloat(document.getElementById('settingRadius')?.value)||200);state.locationCircle?.setRadius(radius);const ll=state.locationMarker?.getLatLng();if(ll)syncMapReadout(ll.lat,ll.lng,radius);}\n"
scripts = replace_once(scripts, old, new, 'Radius warning hook')
scripts_path.write_text(scripts, encoding='utf-8')

index_path = Path('Index.html')
index = index_path.read_text(encoding='utf-8')
old = """                <label>Radius (meter)<input id=\"settingRadius\" name=\"radiusM\" type=\"number\" min=\"1\" max=\"5000\" required oninput=\"syncMapRadius()\"></label>
                <label>Had ketepatan GPS (m)<input name=\"maxGpsAccuracyM\" type=\"number\" min=\"1\" max=\"2000\" required></label>
                <div class=\"span-2 map-setting-block\">
"""
new = """                <label>Radius (meter)<input id=\"settingRadius\" name=\"radiusM\" type=\"number\" min=\"1\" max=\"5000\" required oninput=\"syncMapRadius()\"></label>
                <label>Had ketepatan GPS (m)<input id=\"settingGpsAccuracy\" name=\"maxGpsAccuracyM\" type=\"number\" min=\"1\" max=\"2000\" required oninput=\"updateGpsSettingWarning()\"></label>
                <div id=\"gpsSettingWarning\" class=\"span-2 setting-hint test-hint hidden\"></div>
                <div class=\"span-2 map-setting-block\">
"""
index = replace_once(index, old, new, 'Index GPS warning')
index_path.write_text(index, encoding='utf-8')

user_api_path = Path('apps-script/20_UserApi.gs')
user_api = user_api_path.read_text(encoding='utf-8')
user_api = replace_once(user_api, "    distanceM:loc.distanceM,\n    ip:recordIp || '',\n", "    distanceM:loc.distanceM,\n    accuracyM:loc.accuracyM,\n    radiusM:Number(settings.RADIUS_M),\n    ip:recordIp || '',\n", 'Punch response diagnostics')
user_api = replace_once(user_api, "  audit_(action,user.email,`${exceptionType || 'TEPAT MASA'}; mod=${isTestMode ? 'TEST' : 'REAL'}; jarak ${loc.distanceM}m; IP=${recordIp || '-'}; ${ipCheck.note || 'IP tiada isu'}; writeMs=${writeMs}; slotWaitMs=${slot.slotWaitMs}; slotsCreated=${slot.createdSlots}`,user.email);\n", "  audit_(action,user.email,`${exceptionType || 'TEPAT MASA'}; mod=${isTestMode ? 'TEST' : 'REAL'}; jarak=${loc.distanceM}m; akurasi=±${loc.accuracyM}m; radius=${settings.RADIUS_M}m; IP=${recordIp || '-'}; ${ipCheck.note || 'IP tiada isu'}; writeMs=${writeMs}; slotWaitMs=${slot.slotWaitMs}; slotsCreated=${slot.createdSlots}`,user.email);\n", 'Punch audit diagnostics')
user_api_path.write_text(user_api, encoding='utf-8')

settings_path = Path('apps-script/42_Settings.gs')
settings = settings_path.read_text(encoding='utf-8')
old = """  if (distance > radius) {
    throw new Error(`Anda berada kira-kira ${distance}m dari lokasi yang ditetapkan. Rekod waktu hanya dibenarkan dalam radius ${radius}m.`);
  }
"""
new = """  if (distance > radius) {
    if (distance - accuracy <= radius) {
      throw new Error(`Bacaan GPS belum cukup stabil untuk menentukan kedudukan dengan yakin (jarak bacaan ${distance}m, ketepatan ±${Math.round(accuracy)}m, radius ${radius}m). Tunggu beberapa saat dan cuba semula.`);
    }
    throw new Error(`Anda berada kira-kira ${distance}m dari lokasi yang ditetapkan (GPS ±${Math.round(accuracy)}m). Rekod waktu hanya dibenarkan dalam radius ${radius}m.`);
  }
"""
settings = replace_once(settings, old, new, 'Server uncertain boundary')
settings_path.write_text(settings, encoding='utf-8')
