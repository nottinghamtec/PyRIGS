self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
    let data = {};
    try {
        data = event.data ? event.data.json() : {};
    } catch (error) {
        data = {body: event.data ? event.data.text() : ""};
    }
    event.waitUntil(
        self.registration.showNotification(data.title || "RIGS", {
            body: data.body || "",
            tag: data.tag,
            icon: "{% load static %}{% static 'imgs/pyrigs-avatar.png' %}",
            data: {url: data.url || "/notifications/"},
        })
    );
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    const target = new URL(event.notification.data.url, self.location.origin).href;
    event.waitUntil(
        self.clients.matchAll({type: "window", includeUncontrolled: true}).then((windows) => {
            for (const client of windows) {
                if ("focus" in client && "navigate" in client) {
                    return client.focus().then(() => client.navigate(target));
                }
            }
            return self.clients.openWindow(target);
        })
    );
});
