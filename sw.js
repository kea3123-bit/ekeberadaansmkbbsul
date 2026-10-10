const CACHE='eke-static-bab31d025d27';
const ASSETS=["./","./index.html","./manifest.webmanifest","./assets/logo.8a416c3282a0.png","./vendor/bootstrap/bootstrap.min.css","./vendor/bootstrap/bootstrap.bundle.min.js","./assets/app.54956bdcc0a5.css","./assets/mobile.3b1920d1212a.css","./assets/config.c9a53c4ab8ab.js","./assets/gas-shim.8a36f9e99c8e.js","./assets/runtime.768618465b1f.js","./assets/core.166987ce2f7c.js","./assets/attendance.1311b59c58e7.js","./assets/absence.e6d37e890149.js","./assets/admin.59e7b3b4c2ec.js","./assets/exports.2402a6c36028.js"];
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
