// eKeberadaan PHP/MySQL PWA: install support, not offline attendance.
// Never cache login responses, MySQL API requests or personal data.
const PWA_CACHE='eke-pwa-shell-v1';
const ASSETS=['./offline.html','./manifest.webmanifest','./icon-192.png',
  './icon-512.png','./apple-touch-icon.png'];
self.addEventListener('install',event=>{
  event.waitUntil(caches.open(PWA_CACHE)
    .then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
  event.waitUntil((async()=>{
    const keys=await caches.keys();
    await Promise.all(keys.filter(key=>
      (key.startsWith('eke-static-')||key.startsWith('eke-pwa-'))&&key!==PWA_CACHE
    ).map(key=>caches.delete(key)));
    await self.clients.claim();
  })());
});
self.addEventListener('fetch',event=>{
  const request=event.request;
  if(request.method!=='GET'||request.mode!=='navigate')return;
  if(new URL(request.url).origin!==self.location.origin)return;
  // Fetch the current app shell on every navigation so updates win.
  // Offline we display a notice rather than pretending punch succeeded.
  event.respondWith(fetch(request).catch(async()=>{
    const cache=await caches.open(PWA_CACHE);
    return await cache.match('./offline.html')||Response.error();
  }));
});
