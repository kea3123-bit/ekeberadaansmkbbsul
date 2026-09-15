const CACHE='eke-static-608d87fc3a5e';
const ASSETS=["./","./index.html","./manifest.webmanifest","./assets/logo.8a416c3282a0.png","./vendor/bootstrap/bootstrap.min.css","./vendor/bootstrap/bootstrap.bundle.min.js","./assets/app.47475ec00564.css","./assets/mobile.3b1920d1212a.css","./assets/config.4f6130d435f9.js","./assets/gas-shim.1f295770fbe0.js","./assets/runtime.768618465b1f.js","./assets/core.88206f1376e2.js","./assets/attendance.d79cac55f147.js","./assets/absence.b30d6d107262.js","./assets/admin.1ace1af4ee96.js","./assets/exports.98f10f271201.js"];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('eke-static-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{
  const r=e.request;
  if(r.method!=='GET')return;
  const u=new URL(r.url);
  if(u.origin!==self.location.origin)return;
  if(r.mode==='navigate'){e.respondWith(fetch(r).then(res=>{const cp=res.clone();caches.open(CACHE).then(c=>c.put('./index.html',cp));return res;}).catch(()=>caches.match('./index.html')));return;}
  e.respondWith(caches.match(r).then(hit=>hit||fetch(r)));
});
