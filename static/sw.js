const CACHE_NAME = 'svoi-v1';
const urlsToCache = [
    '/',
    '/static/style.css',
    '/static/script.js',
    '/static/icon-192.png',
    '/static/icon-512.png'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(urlsToCache))
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});
// ============ PWA: РЕГИСТРАЦИЯ SERVICE WORKER ============
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then((reg) => console.log('✅ Service Worker зарегистрирован:', reg.scope))
            .catch((err) => console.error('❌ SW ошибка:', err));
    });
}