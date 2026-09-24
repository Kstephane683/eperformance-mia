/* Coquille : la maquette validee, hors-ligne. */
const C='mia-v4';
const S=['/app/','/app/index.html','/app/manifest.webmanifest','/app/icones/mia-192.png','/app/icones/mia-512.png','/app/icones/apple-touch-icon.png','/app/polices/dm-sans-400.woff2','/app/polices/dm-sans-500.woff2','/app/polices/dm-sans-600.woff2','/app/polices/dm-sans-700.woff2','/app/polices/cormorant-garamond-600.woff2'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(S)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==C).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{if(e.request.method!=='GET'||new URL(e.request.url).origin!==location.origin)return;e.respondWith(caches.match(e.request).then(c=>c||fetch(e.request)))});
