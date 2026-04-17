// Mordomo Virtual SW - Versao que SEMPRE busca conteudo novo (network-first)
const CACHE_NAME = 'mordomo-v' + Date.now();

self.addEventListener('install', (event) => {
  // Sobe imediato sem esperar
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    // Limpa TODOS os caches antigos
    const keys = await caches.keys();
    await Promise.all(keys.map(k => caches.delete(k)));
    // Assume controle imediato
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Nao intercepta API nem POST — sempre direto a rede
  if (url.pathname.startsWith('/api/') || event.request.method !== 'GET') {
    return;
  }

  // Network-first: sempre tenta rede, cache so como fallback offline
  event.respondWith((async () => {
    try {
      const fresh = await fetch(event.request);
      return fresh;
    } catch (_) {
      const cached = await caches.match(event.request);
      if (cached) return cached;
      throw _;
    }
  })());
});

// Permite a pagina forcar atualizacao
self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting();
});
