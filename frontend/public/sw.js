// Web Push service worker for CancelFill.
self.addEventListener('push', (event) => {
  let data = { title: 'CancelFill', body: '', url: '/' };
  try {
    data = { ...data, ...event.data.json() };
  } catch {
    /* non-JSON payload: keep defaults */
  }
  event.waitUntil(
    self.registration.showNotification(data.title, { body: data.body, data: { url: data.url } }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((wins) => {
      for (const w of wins) {
        if ('focus' in w) {
          w.navigate(url);
          return w.focus();
        }
      }
      return self.clients.openWindow(url);
    }),
  );
});
