// JyotiGPT offline service worker — caches the app shell for offline use.

const VERSION = "v1";
const SHELL_CACHE = `jyoti-shell-${VERSION}`;
const STATIC_CACHE = `jyoti-static-${VERSION}`;

const PRECACHE_URLS = [
  "/",
  "/manifest.json",
  "/favicon.png",
  "/web-app-manifest-192x192.png",
  "/web-app-manifest-512x512.png",
];

// Install — precache the app shell.
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting()),
  );
});

// Activate — clean stale caches.
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((name) => name !== SHELL_CACHE && name !== STATIC_CACHE)
          .map((name) => caches.delete(name)),
      ),
    ).then(() => self.clients.claim()),
  );
});

// Fetch — offline-first for navigations and static assets; pass-through for
// API calls and non-same-origin requests.
self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Skip non-GET and API calls.
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  // Pass through cross-origin requests.
  if (url.origin !== self.location.origin) return;

  // Pass through /api/ requests (always need the network).
  if (url.pathname.startsWith("/api/")) return;

  // Navigation requests — network-first, fall back to cached shell.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(request, clone));
          return response;
        })
        .catch(() => caches.match("/")),
    );
    return;
  }

  // Other same-origin GET — cache-first, update in background.
  event.respondWith(
    caches.match(request).then((cached) => {
      const fetching = fetch(request).then((response) => {
        const clone = response.clone();
        caches.open(STATIC_CACHE).then((cache) => cache.put(request, clone));
        return response;
      }).catch(() => cached);
      return cached ?? fetching;
    }),
  );
});
