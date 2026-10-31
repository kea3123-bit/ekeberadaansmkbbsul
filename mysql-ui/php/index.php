<?php
declare(strict_types=1);
$root = dirname(__DIR__);
$index = file_get_contents($root.'/Index.html');
if ($index === false) { http_response_code(500); exit('Index.html missing'); }
$styles = file_get_contents($root.'/Styles.html');
$logo = file_get_contents($root.'/Logo.html');
$scripts = file_get_contents($root.'/Scripts.html');
$pinUi = file_get_contents(__DIR__.'/pin-ui.js');
$pinRecoveryUi = file_get_contents(__DIR__.'/pin-recovery-ui.js');
$monthlyPrintUi = file_get_contents(__DIR__.'/monthly-print.js');
if ($styles === false || $logo === false || $scripts === false || $pinUi === false || $pinRecoveryUi === false || $monthlyPrintUi === false) { http_response_code(500); exit('App assets missing'); }
// The refactor/performance-v2 frontend uses runServerRaw(), while older
// frontend revisions used runServer(). Adapt either version without modifying
// the canonical source scripts from the upstream branch.
$rpcOld = "function runServerRaw(fn, ...args){\n    return new Promise((resolve,reject)=>{\n      google.script.run\n        .withSuccessHandler(resolve)\n        .withFailureHandler(err=>reject(new Error(err && err.message ? err.message : String(err))))[fn](...args);\n    });\n  }";
$rpcOldLegacy = "function runServer(fn, ...args){\n    return new Promise((resolve,reject)=>{\n      google.script.run\n        .withSuccessHandler(resolve)\n        .withFailureHandler(err=>reject(new Error(err && err.message ? err.message : String(err))))[fn](...args);\n    });\n  }";
$rpcNew = <<<'JS'
async function runServerRaw(fn, ...args){
    const payload=JSON.stringify({fn,args});
    // CORS-simple text/plain does not need an OPTIONS preflight. Keep the
    // exact JSON payload and explicit session-token checks in PHP/MySQL.
    const options={
      method:'POST',
      headers:{'Content-Type':'text/plain;charset=UTF-8'},
      credentials:'same-origin',
      cache:'no-store',
      body:payload
    };
    let response;
    try {
      response=await fetch('api.php',options);
      if(response.status===415){
        // Graceful compatibility while an older cPanel api.php is upgraded.
        // The old server rejects before dispatching, so retry is safe.
        try{
          response=await fetch('api.php',{
            ...options,headers:{'Content-Type':'application/json'}
          });
        }catch(_legacyError){
          throw new Error('API cPanel belum dikemas kini untuk sambungan tanpa preflight. Gantikan api.php dan php/api.php daripada branch terkini.');
        }
      }
    }catch(e){
      if(e instanceof Error && e.message.includes('belum dikemas kini'))throw e;
      throw new Error('Tidak dapat menghubungi API MySQL di hosting. Semak sambungan internet, HTTPS dan tetapan CORS cPanel.');
    }
    const obj=await response.json().catch(()=>({
      ok:false,
      error:'HTTP '+response.status+': respons server bukan JSON. Semak cPanel PHP error_log.'
    }));
    if(!response.ok||!obj.ok)throw new Error(obj.error||'Permintaan MySQL gagal (HTTP '+response.status+').');
    return obj.result;
  }

JS;
// The renderer serves two targets:
// - cPanel PHP site: same-origin relative API endpoint
// - GitHub Actions static build: explicit HTTPS API on existing cPanel hosting.
// The endpoint is PUBLIC configuration, not a database credential.
$apiUrl = getenv('EKE_PUBLIC_API_URL') ?: 'api.php';
if ($apiUrl !== 'api.php' &&
    $apiUrl !== 'https://ppdkmy.edu.my/ekeberadaansmkbbsul/api.php') {
    http_response_code(500);
    exit('Invalid EKE_PUBLIC_API_URL');
}
$rpcNew = str_replace("fetch('api.php',", 'fetch(' . json_encode($apiUrl, JSON_UNESCAPED_SLASHES) . ',', $rpcNew);
// All API credentials are explicit session tokens in JSON, never cookies.
$rpcNew = str_replace("credentials:'same-origin'", "credentials:'omit'", $rpcNew);
if (strpos($scripts,$rpcOld)!==false) {
    $scripts = str_replace($rpcOld,$rpcNew,$scripts);
} elseif (strpos($scripts,$rpcOldLegacy)!==false) {
    $scripts = str_replace($rpcOldLegacy,str_replace('runServerRaw(', 'runServer(', $rpcNew),$scripts);
} else {
    http_response_code(500);
    exit('Scripts.html RPC signature not recognized: check upstream frontend version.');
}
// Force a temporary admin-issued PIN to be changed; legacy Sheets PINs do not
// need resetting unless their source record already required it.
$hooks=[
  "    setTimeout(()=>syncClientTelemetry().catch(()=>{}),0);",
  "    setTimeout(()=>getClientNetworkInfo(false).catch(()=>{}),0);"
];
$hookFound=false;
foreach($hooks as $hook) {
    if(strpos($scripts,$hook)!==false) {
        $scripts = str_replace($hook,$hook."\n    if (state.boot?.user?.mustChangePassword) setTimeout(()=>openChangePin(true),250);",$scripts);
        $hookFound=true;
        break;
    }
}
if (!$hookFound) {http_response_code(500);exit('Frontend first-login hook mismatch');}
$scripts .= "\n".$pinUi."\n".$pinRecoveryUi."\n".$monthlyPrintUi;
$index = str_replace('<button class="btn ghost small" onclick="logout()">Keluar</button>',
  '<button class="btn ghost small" type="button" onclick="openChangePin()">Tukar PIN</button><button class="btn ghost small" onclick="logout()">Keluar</button>', $index);
$index = str_replace("<?!= include('Styles'); ?>",$styles,$index);
$index = str_replace("<?!= include('Logo'); ?>",$logo,$index);
$index = str_replace("<?!= include('Scripts'); ?>",$scripts,$index);
header('Content-Type: text/html; charset=UTF-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
echo $index;
