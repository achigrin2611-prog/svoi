const CACHE_NAME = 'svoi-v2';
const urlsToCache = ['/', '/static/style.css', '/static/script.js', '/static/icon-192.png'];

self.addEventListener('install', (event) => {
    event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(urlsToCache)));
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((response) => response || fetch(event.request))
    );
});

self.addEventListener('push', (event) => {
    let data = { title: 'Свои', body: 'Новое сообщение', url: '/' };
    if (event.data) {
        try { data = event.data.json(); } catch(e) {}
    }
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/static/icon-192.png',
            data: { url: data.url }
        })
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    event.waitUntil(clients.openWindow(event.notification.data.url || '/'));
});