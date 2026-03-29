const CACHE_NAME = "shenas-v1";
const PRECACHE = ["/", "/static/images/shenas.png", "/static/manifest.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE)),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name)),
      ),
    ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API calls: network-only (never cache)
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  // Static assets: cache-first
  if (
    url.pathname.startsWith("/static/") ||
    url.pathname.startsWith("/vendor/") ||
    url.pathname.startsWith("/ui/") ||
    url.pathname.startsWith("/components/")
  ) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
            }
            return response;
          }),
      ),
    );
    return;
  }

  // SPA routes: serve cached shell, fall back to network
  if (request.mode === "navigate") {
    event.respondWith(
      caches.match("/").then((cached) => cached || fetch(request)),
    );
  }
});
