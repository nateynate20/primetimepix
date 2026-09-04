{% load static %}// PrimeTimePix service worker.
// Bump CACHE_VERSION to force clients to drop old caches on the next visit.
const CACHE_VERSION = 'ptp-cache-v1';
const OFFLINE_URL = '{% url "pwa_offline" %}';

// Small app shell precached on install so the offline page and core icons are
// always available, even on a first failed navigation.
const PRECACHE_URLS = [
  OFFLINE_URL,
  '{% static "images/logo-mark.png" %}',
  '{% static "images/logo-light.png" %}',
  '{% static "images/icon-192.png" %}',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;

  // Only deal with same-origin GETs; never touch POSTs or cross-origin (CDNs).
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Navigations: network-first so pages stay fresh; fall back to the cached
  // offline page when the network is unavailable.
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  // Static assets: cache-first for instant repeat loads, with a runtime cache.
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(req).then((cached) => cached || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE_VERSION).then((cache) => cache.put(req, copy));
        return res;
      }).catch(() => cached))
    );
    return;
  }
});

// ── Web push ────────────────────────────────────────────────────────────────
// Handlers are harmless without an active subscription, so they ship with
// PWA-lite and light up once web push is enabled.
self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { body: event.data ? event.data.text() : '' };
  }
  const title = data.title || 'PrimeTimePix';
  const options = {
    body: data.body || '',
    icon: data.icon || '{% static "images/icon-192.png" %}',
    badge: '{% static "images/icon-192.png" %}',
    tag: data.tag,
    renotify: Boolean(data.tag),
    data: { url: data.url || '/dashboard/' },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || '/dashboard/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const client of list) {
        if (client.url.indexOf(target) !== -1 && 'focus' in client) return client.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow(target);
    })
  );
});
