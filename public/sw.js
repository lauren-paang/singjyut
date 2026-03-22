// ── Service Worker ──────────────────────────────────────────────────────────
// Caches static assets for PWA shell. API calls always go to network.

const CACHE_NAME = 'singjyut-v3';
const STATIC_ASSETS = [
    '/',
    '/public/index.html',
    '/public/style.css',
    '/public/app.js',
    '/public/tts.js',
    '/public/youtube-player.js',
    '/public/karaoke.js',
    '/public/manifest.json',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // API calls: always network, never cache
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(fetch(event.request));
        return;
    }

    // Static assets: network-first, fall back to cache
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});
