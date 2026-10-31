/* Time-limited verified DELIMa email PIN recovery. MySQL API only. */
async function openPinRecovery(){
  if(!state.pinRecoveryAvailable)return showLoginError('Tempoh reset PIN kendiri tidak tersedia.');
  const email=String(state.selectedAccount?.email ||
    document.getElementById('delimaEmail')?.value ||
    readLastAccount()?.email || '').trim().toLowerCase();
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
    return showLoginError('Masukkan emel DELIMa yang berdaftar dahulu.');
  hideLoginError();
  state.recoveryEmail=email;
  const btn=(typeof event!=='undefined' && event?.currentTarget?.tagName==='BUTTON')?event.currentTarget:null;
  if(btn)setButtonBusy(btn,true,'Menghantar kod…');
  try{
    const result=await runServer('requestPinRecovery',email);
    text('recoveryEmailLabel',email);
    ['recoveryCode','recoveryPin','recoveryPinConfirm'].forEach(id=>{
      const el=document.getElementById(id);if(el)el.value='';
    });
    showLoginStep('recovery');
    toast(result?.message||'Semak emel DELIMa untuk kod pengesahan.',5200);
    setTimeout(()=>document.getElementById('recoveryCode')?.focus(),100);
  }catch(e){
    showLoginError(e.message||'Permintaan kod gagal.');
  }finally{
    if(btn)setButtonBusy(btn,false,'');
  }
}
async function resendPinRecovery(){
  if(!state.recoveryEmail)return showLoginStep('email');
  hideLoginError();
  try{
    const result=await runServer('requestPinRecovery',state.recoveryEmail);
    toast(result?.message||'Semak emel DELIMa. Permintaan berulang dihadkan.',4800);
  }catch(e){showLoginError(e.message||'Permintaan gagal.');}
}
async function submitPinRecovery(){
  const code=String(document.getElementById('recoveryCode')?.value||'').replace(/\D/g,'');
  const pin=String(document.getElementById('recoveryPin')?.value||'').replace(/\D/g,'');
  const confirm=String(document.getElementById('recoveryPinConfirm')?.value||'').replace(/\D/g,'');
  if(!state.recoveryEmail)return showLoginError('Sila mulakan semula permintaan reset PIN.');
  if(code.length!==6)return showLoginError('Masukkan kod pengesahan 6 digit.');
  if(pin.length!==6 || confirm!==pin)return showLoginError('PIN baharu mesti 6 digit dan kedua-duanya sepadan.');
  hideLoginError();
  const btn=document.getElementById('recoveryConfirmBtn');
  setButtonBusy(btn,true,'Mengesahkan emel…');
  try{
    const result=await runServer('completePinRecovery',state.recoveryEmail,code,pin,confirm);
    applySessionResult(result);
    state.recoveryEmail='';
    rememberLastAccount(result.boot?.user);
    ['recoveryCode','recoveryPin','recoveryPinConfirm'].forEach(id=>{
      const el=document.getElementById(id);if(el)el.value='';
    });
    enterApp();
    toast('PIN baharu disimpan. Sesi peranti aktif sehingga 30 hari.',4500);
  }catch(e){showLoginError(e.message||'Kod tidak sah atau telah tamat.');}
  finally{setButtonBusy(btn,false,'');}
}
