/* Temporary self-service PIN reset: 31 Oct - 7 Nov 2026, no email code. */
function openPinRecovery(){
  if(!state.pinRecoveryAvailable)
    return showLoginError('Tempoh reset PIN sementara tidak tersedia.');
  const email=String(state.selectedAccount?.email ||
    document.getElementById('delimaEmail')?.value ||
    readLastAccount()?.email || '').trim().toLowerCase();
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
    return showLoginError('Masukkan emel DELIMa yang berdaftar dahulu.');
  hideLoginError();
  state.recoveryEmail=email;
  text('recoveryEmailLabel',email);
  ['recoveryPin','recoveryPinConfirm'].forEach(id=>{
    const el=document.getElementById(id);if(el)el.value='';
  });
  showLoginStep('recovery');
  setTimeout(()=>document.getElementById('recoveryPin')?.focus(),80);
}
async function submitPinRecovery(){
  if(!state.pinRecoveryAvailable)
    return showLoginError('Tempoh reset PIN sementara telah tamat.');
  const email=state.recoveryEmail;
  const pin=String(document.getElementById('recoveryPin')?.value||'').replace(/\D/g,'');
  const confirm=String(document.getElementById('recoveryPinConfirm')?.value||'').replace(/\D/g,'');
  if(!email)return showLoginError('Mulakan semula daripada halaman login.');
  if(pin.length!==6||confirm!==pin)
    return showLoginError('Masukkan PIN baharu 6 digit yang sama pada kedua-dua ruangan.');
  hideLoginError();
  const btn=document.getElementById('recoveryConfirmBtn');
  setButtonBusy(btn,true,'Menyimpan PIN…');
  try{
    const result=await runServer('completePinRecovery',email,pin,confirm);
    applySessionResult(result);
    state.recoveryEmail='';
    ['recoveryPin','recoveryPinConfirm'].forEach(id=>{
      const el=document.getElementById(id);if(el)el.value='';
    });
    enterApp();
    toast('PIN baharu berjaya disimpan. Sesi aktif sehingga 30 hari.',4500);
  }catch(e){showLoginError(e.message||'Gagal menyimpan PIN baharu.');}
  finally{setButtonBusy(btn,false,'');}
}
