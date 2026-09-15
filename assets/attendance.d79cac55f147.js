// ---------- Punch on Home ----------
  function punchGpsPolicy(){
    const s=state.boot?.settings||{};
    const radiusM=Math.max(1,Number(s.radiusM)||200);
    const thresholdsM=[80,100,120,140];
    return {
      radiusM,
      configuredMaxAccuracyM:Math.max(140,Number(s.maxGpsAccuracyM)||140),
      thresholdsM,
      stageMs:2000,
      timeoutMs:8000
    };
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
      let best=null,watchId=null,settled=false,stageIndex=0;
      const timers=[];
      const threshold=()=>policy.thresholdsM[stageIndex];
      const clearAll=()=>{
        timers.forEach(t=>clearTimeout(t));
        if(watchId!==null)try{navigator.geolocation.clearWatch(watchId);}catch(e){}
      };
      const finish=(err,pos)=>{
        if(settled)return;
        settled=true; clearAll();
        err?reject(err):resolve(pos);
      };
      const describe=(prefix,pos)=>{
        const acc=pos?.coords?Math.round(Number(pos.coords.accuracy)||0):0;
        const distance=pos?.coords?Math.round(punchGpsDistance(pos)):NaN;
        return `${prefix} · sasaran ±${threshold()}m${acc?` · bacaan ±${acc}m`:''}${Number.isFinite(distance)?` · anggaran ${distance}m / ${Math.round(policy.radiusM)}m`:''}`;
      };
      const tryAccept=pos=>{
        if(!pos?.coords)return false;
        const accuracy=Number(pos.coords.accuracy);
        if(!Number.isFinite(accuracy)||accuracy<0)return false;
        if(accuracy<=threshold()){
          gps('busy',describe('Lokasi diterima',pos));
          finish(null,pos);
          return true;
        }
        return false;
      };
      const advanceStage=()=>{
        if(settled)return;
        if(stageIndex>=policy.thresholdsM.length-1)return;
        const previous=threshold();
        stageIndex++;
        gps('busy',describe(`Belum capai ±${previous}m. Melonggarkan ketepatan`,best));
        if(best)tryAccept(best);
      };

      gps('busy','Mengesan lokasi… sasaran GPS ±80m');
      for(let i=1;i<policy.thresholdsM.length;i++){
        timers.push(setTimeout(advanceStage,policy.stageMs*i));
      }
      timers.push(setTimeout(()=>{
        if(settled)return;
        if(best&&tryAccept(best))return;
        if(!best)return finish(new Error('Lokasi GPS belum dapat dikesan selepas 8 saat. Aktifkan Location/GPS dan cuba semula.'));
        const accuracy=Math.round(Number(best.coords.accuracy)||0),distance=Math.round(punchGpsDistance(best));
        finish(new Error(`Ketepatan GPS masih ±${accuracy}m selepas cuba bertahap 80m → 100m → 120m → 140m. Had akhir ialah ±140m.${Number.isFinite(distance)?` Anggaran lokasi semasa ${distance}m dari pusat.`:''}`));
      },policy.timeoutMs));

      watchId=navigator.geolocation.watchPosition(pos=>{
        const accuracy=Number(pos?.coords?.accuracy);
        if(!Number.isFinite(accuracy)||accuracy<0)return;
        if(!best||accuracy<Number(best.coords.accuracy))best=pos;
        if(tryAccept(pos))return;
        const chosen=best||pos;
        gps('busy',describe('Mengesan lokasi',chosen));
      },err=>{
        if(err?.code===1)return finish(new Error('Akses lokasi ditolak. Benarkan Location untuk laman ini.'));
        if(!best&&err?.code===2)gps('busy',`GPS belum mendapat lokasi · sasaran ±${threshold()}m · mencuba lagi…`);
      },{enableHighAccuracy:true,timeout:policy.timeoutMs+1000,maximumAge:0});
    });
  }

  async function startPunch(type){
    const test=String(state.boot?.settings?.systemMode||'REAL')==='TEST';
    const gpsPolicy=punchGpsPolicy();
    setPunchBusy(true); gps('busy',test?'MOD TEST — merakam waktu dan IP…':'Mengesan lokasi… sasaran GPS ±80m');
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
  function gps(cls,msg){const d=document.getElementById('gpsDot');if(d)d.className='gps-dot '+cls;text('locationText',msg);}
  function setPunchBusy(b){const step=state.boot?.attendance?.nextRecord||{type:'IN',session:1,complete:false},i=document.getElementById('btnIn'),o=document.getElementById('btnOut');if(i)i.disabled=b||step.complete||step.type!=='IN';if(o)o.disabled=b||step.complete||step.type!=='OUT';}


  // ---------- Own Kad Perakam Waktu ----------
  async function loadMyCard(force=false){
    const monthInput=document.getElementById('myCardMonth');if(!monthInput.value)monthInput.value=(state.boot?.today||'').slice(0,7);const monthKey=monthInput.value;
    if(!force&&state.myCardLoaded&&state.myCardData?.month===monthKey){renderMyPunchCard();return;}
    const loading=document.getElementById('pcLoading');loading.classList.remove('hidden');
    try{state.myCardData=await runServer('getMyPunchCardMonth',state.token,monthKey);state.myCardLoaded=true;renderMyPunchCard();}
    catch(e){document.getElementById('myCardRows').innerHTML=`<tr><td colspan="7" class="pc-error">${esc(e.message)}</td></tr>`;handleServerError(e,false);}
    finally{loading.classList.add('hidden');}
  }

  function renderMyPunchCard(){const d=state.myCardData;if(!d)return;text('pcCardNumber',d.cardNumber||'1');text('pcName',d.user?.name||'—');text('pcDepartment',d.department||d.schoolName||'—');text('pcMonthLabel',formatMonthMalay(d.month));document.getElementById('myCardRows').innerHTML=cardRowsHtml(d,state.myCardHalf);document.getElementById('cardHalf1Btn').classList.toggle('active',state.myCardHalf===1);document.getElementById('cardHalf2Btn').classList.toggle('active',state.myCardHalf===2);}
  function setMyCardHalf(half){state.myCardHalf=half===2?2:1;renderMyPunchCard();}
  function clearPunchCardPrintPages(){document.getElementById('punchCardPrintPages')?.remove();}
  function buildPunchCardPrintPages(){
    const d=state.myCardData,source=document.getElementById('physicalPunchCard');
    if(!d||!source)return null;
    clearPunchCardPrintPages();
    const host=document.createElement('div');host.id='punchCardPrintPages';host.className='punch-card-print-pages';
    [1,2].forEach(half=>{
      const page=document.createElement('section');page.className='punch-card-print-page';page.dataset.half=String(half);
      const card=source.cloneNode(true);card.classList.add('physical-card-print');card.removeAttribute('id');
      const rows=card.querySelector('#myCardRows');if(rows){rows.innerHTML=cardRowsHtml(d,half);rows.removeAttribute('id');}
      const loading=card.querySelector('#pcLoading');if(loading)loading.remove();
      card.querySelectorAll('[id]').forEach(el=>el.removeAttribute('id'));
      page.appendChild(card);host.appendChild(page);
    });
    document.body.appendChild(host);return host;
  }
  function printMyPunchCard(){
    if(!state.myCardData)return toast('Kad Perakam Waktu belum dimuatkan.');
    if(!buildPunchCardPrintPages())return toast('Kad Perakam Waktu tidak dapat disediakan untuk cetakan.');
    window.addEventListener('afterprint',clearPunchCardPrintPages,{once:true});
    requestAnimationFrame(()=>requestAnimationFrame(()=>window.print()));
  }

  function cardRowsHtml(d,half){
    const start=half===1?1:16,end=half===1?Math.min(15,d.daysInMonth):d.daysInMonth,byDay=new Map((d.records||[]).map(r=>[Number(r.day),r]));let html='';
    if(start>end)return '<tr><td colspan="7" class="pc-empty">Tiada tarikh untuk bahagian ini.</td></tr>';
    for(let day=start;day<=end;day++){
      const r=byDay.get(day)||{},status=String(r.status||'').trim().toUpperCase();
      const cls=status==='TIDAK HADIR'?'pc-row-absent':status==='WEEKEND'?'pc-row-weekend':(status.includes('LEWAT')||status.includes('BALIK AWAL'))?'pc-row-lewat':status==='HADIR'?'pc-row-hadir':'';
      if(status==='WEEKEND'){const label=String(r.reason||'').trim().toUpperCase()||'CUTI';html+=`<tr class="${cls}"><td class="pc-day">${day}</td><td colspan="6" class="pc-weekend-full"><span>${esc(label)}</span></td></tr>`;continue;}
      if(status==='TIDAK HADIR'){const reason=String(r.reason||'').trim(),detail=reason&&reason.toUpperCase()!=='TIDAK HADIR'?reason:'TIADA PENJELASAN';html+=`<tr class="${cls}"><td class="pc-day">${day}</td><td colspan="6" class="pc-absence-full"><span class="pc-absence-label">TIDAK HADIR</span><span class="pc-absence-reason">${esc(detail)}</span></td></tr>`;continue;}
      const reviews=r.reviewItems||[], flagged=(type,session)=>reviews.some(x=>String(x.type||'').toUpperCase()===type&&Number(x.session||1)===session), tc=(v,bad)=>`<td class="${bad?'pc-time-alert':''}">${esc(shortTime(v))}</td>`;
      html+=`<tr class="${cls}"><td class="pc-day">${day}</td>${tc(r.inTime,flagged('LEWAT',1))}${tc(r.outTime,flagged('BALIK AWAL',1))}${tc(r.inTime2,flagged('LEWAT',2))}${tc(r.outTime2,flagged('BALIK AWAL',2))}<td class="pc-statement">${esc(cardStatement(r))}</td><td class="pc-sign"></td></tr>`;
    }return html;
  }
  function shortTime(v){return v?String(v).slice(0,5):'';}
  function cardStatement(r){
    if(!r)return '';
    const status=String(r.status||''), parts=[];
    if(status.includes('LEWAT'))parts.push('LEWAT');
    if(status.includes('BALIK AWAL'))parts.push('BALIK AWAL');
    if(parts.length){
      parts.push(r.reviewState||'BELUM DIAMBIL MAKLUM');
      // Untuk pengguna Keberadaan yang punch lewat, kekalkan catatan
      // Keberadaan pada Kad Perakam sebagai konteks yang telah dimaklumkan.
      if(r.reason&&String(r.reason).toUpperCase().includes('KEBERADAAN'))parts.push(r.reason);
    } else if(r.reason)parts.push(r.reason);
    return parts.join(' · ');
  }
  function formatMonthMalay(monthKey){if(!/^\d{4}-\d{2}$/.test(monthKey||''))return monthKey||'—';const[y,m]=monthKey.split('-').map(Number);const months=['JANUARI','FEBRUARI','MAC','APRIL','MEI','JUN','JULAI','OGOS','SEPTEMBER','OKTOBER','NOVEMBER','DISEMBER'];return `${months[m-1]} ${y}`;}
