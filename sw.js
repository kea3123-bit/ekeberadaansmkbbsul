const CACHE='eke-static-bb078eb47771';
const ASSETS=["./","./index.html","./manifest.webmanifest","./assets/logo.8a416c3282a0.png","./vendor/bootstrap/bootstrap.min.css","./vendor/bootstrap/bootstrap.bundle.min.js","./assets/app.75a7dd64b8f8.css","./assets/mobile.3b1920d1212a.css","./assets/config.d93bfcd5dee0.js","./assets/gas-shim.ea99fc45c6f8.js","./assets/runtime.768618465b1f.js","./assets/core.ad39a92a5c8a.js","./assets/attendance.0ce5ad02bc58.js","./assets/absence.c0cb3679e2b1.js","./assets/admin.954d85a0e373.js","./assets/exports.3323b70d6dc0.js"];
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
