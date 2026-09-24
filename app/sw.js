/* Service worker de l'app Mia — coquille hors-ligne v1.
   Pré-cache la coquille ; l'API reste réseau (jamais cachée : les
   conversations sont des données personnelles). Le cache hors-ligne
   CHIFFRÉ des conversations récentes (conception §5) arrive en v1.1. */
const CACHE = 'mia-app-v1';
const COQUILLE = [
  '/app/', '/app/index.html', '/app/manifest.webmanifest',
  '/app/vendor/preact.module.js', '/app/vendor/hooks.module.js', '/app/vendor/htm.module.js',
  '/app/icones/mia-192.png', '/app/icones/mia-512.png'
];
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(COQUILLE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/api/')) return; // jamais de cache API
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then(c => c || fetch(e.request).then(r => {
      if (r.ok && url.origin === location.origin) {
        const copie = r.clone();
        caches.open(CACHE).then(c2 => c2.put(e.request, copie));
      }
      return r;
    }).catch(() => caches.match('/app/index.html')))
  );
});
