(function () {
    const MIN_IOS = [16, 4];

    function platform() {
        const ua = navigator.userAgent;
        const ios = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
        const standalone = navigator.standalone === true || (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches);
        const match = ua.match(/OS (\d+)[_.](\d+)/);
        const version = ios && match ? [Number(match[1]), Number(match[2])] : null;
        return {ios, standalone, version};
    }

    function supported() {
        return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
    }

    function keyBytes(base64) {
        const padded = (base64 + "=".repeat((4 - base64.length % 4) % 4)).replace(/-/g, "+").replace(/_/g, "/");
        return Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
    }

    function sameKey(buffer, base64) {
        if (!buffer) return false;
        const have = new Uint8Array(buffer);
        const want = keyBytes(base64);
        return have.length === want.length && have.every((byte, index) => byte === want[index]);
    }

    function post(cfg, url, body) {
        return fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/json", "X-CSRFToken": cfg.csrf},
            body: JSON.stringify(body || {}),
            credentials: "same-origin",
        });
    }

    async function register(cfg) {
        await navigator.serviceWorker.register(cfg.sw, {scope: "/"});
        return navigator.serviceWorker.ready;
    }

    async function subscribeAndRecord(cfg, registration) {
        const created = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: keyBytes(cfg.key),
        });
        const response = await post(cfg, cfg.subscribe, created.toJSON());
        if (!response.ok) throw new Error("The server didn't accept this device");
        return created;
    }

    async function sync(cfg, registration, subscription) {
        let known = false;
        if (sameKey(subscription.options && subscription.options.applicationServerKey, cfg.key)) {
            const response = await post(cfg, cfg.check, {endpoint: subscription.endpoint});
            known = response.ok && (await response.json()).known;
        }
        if (known) return subscription;
        await subscription.unsubscribe();
        return subscribeAndRecord(cfg, registration);
    }

    async function status(cfg) {
        const where = platform();
        if (where.ios && !where.standalone) {
            const old = where.version && (where.version[0] < MIN_IOS[0] || (where.version[0] === MIN_IOS[0] && where.version[1] < MIN_IOS[1]));
            return {state: old ? "ios-old" : "ios-install"};
        }
        if (!window.isSecureContext) return {state: "insecure"};
        if (!supported()) return {state: where.ios ? "ios-old" : "unsupported"};
        if (Notification.permission === "denied") return {state: "denied", ios: where.ios};
        const registration = await register(cfg);
        let subscription = await registration.pushManager.getSubscription();
        if (!subscription || Notification.permission !== "granted") return {state: "off", registration};
        try {
            subscription = await sync(cfg, registration, subscription);
        } catch (error) {
            console.warn("Couldn't check this device's subscription", error);
        }
        return {state: "on", registration, subscription};
    }

    async function enable(cfg) {
        if ((await Notification.requestPermission()) !== "granted") return status(cfg);
        const registration = await register(cfg);
        const existing = await registration.pushManager.getSubscription();
        if (existing) await existing.unsubscribe();
        await subscribeAndRecord(cfg, registration);
        return status(cfg);
    }

    async function disable(cfg) {
        const registration = await register(cfg);
        const subscription = await registration.pushManager.getSubscription();
        if (subscription) {
            await post(cfg, cfg.unsubscribe, {endpoint: subscription.endpoint});
            await subscription.unsubscribe();
        }
        return status(cfg);
    }

    async function test(cfg) {
        const response = await post(cfg, cfg.test);
        return (await response.json()).sent;
    }

    function guidance(result) {
        switch (result.state) {
            case "ios-install":
                return {
                    message: "To get notifications on your iPhone or iPad, RIGS first needs adding to your Home Screen.",
                    steps: [
                        "Open RIGS in Safari.",
                        "Tap the Share button, then choose Add to Home Screen.",
                        "Open RIGS from your new Home Screen icon and turn on notifications from there.",
                    ],
                };
            case "ios-old":
                return {
                    message: "Notifications on iPhone and iPad need iOS 16.4 or newer. Update iOS, then add RIGS to your Home Screen.",
                    steps: [],
                };
            case "insecure":
                return {message: "Notifications only work on a secure (https) connection.", steps: []};
            case "unsupported":
                return {
                    message: "This browser can't show RIGS notifications. Try a recent version of Chrome, Edge, Firefox or Safari.",
                    steps: [],
                };
            case "denied":
                return {
                    message: "Notifications are blocked for RIGS on this device.",
                    steps: result.ios
                        ? ["Open the Settings app, then Notifications, then RIGS.", "Turn on Allow Notifications, then come back here."]
                        : [
                              "Click the padlock or settings icon at the left of the address bar.",
                              "Set Notifications to Allow.",
                              "Reload this page and turn notifications on.",
                          ],
                };
            case "off":
                return {
                    message: "Get told straight away when a rig you're MIC on changes, when it's nearly time to meet, and more.",
                    steps: [],
                    canEnable: true,
                };
            default:
                return {message: "Notifications are on for this device.", steps: []};
        }
    }

    function storage(userId) {
        const key = "rigs-push-box-dismissed:" + userId;
        const cookie = "rigs_push_box_" + userId + "=1";
        return {
            dismissed() {
                try {
                    if (window.localStorage.getItem(key)) return true;
                } catch (error) {}
                return document.cookie.split("; ").includes(cookie);
            },
            dismiss() {
                try {
                    window.localStorage.setItem(key, "1");
                    return;
                } catch (error) {}
                document.cookie = cookie + "; max-age=31536000; path=/; SameSite=Lax";
            },
        };
    }

    async function box(root) {
        const cfg = {
            key: root.dataset.key,
            csrf: root.dataset.csrf,
            sw: root.dataset.sw,
            subscribe: root.dataset.subscribe,
            unsubscribe: root.dataset.unsubscribe,
            check: root.dataset.check,
            test: root.dataset.test,
        };
        const saved = storage(root.dataset.user);
        const message = root.querySelector("[data-push-message]");
        const steps = root.querySelector("[data-push-steps]");
        const enableButton = root.querySelector("[data-push-enable]");
        const dismissButton = root.querySelector("[data-push-dismiss]");

        function render(result, problem) {
            if (result.state === "on" || saved.dismissed()) {
                root.hidden = true;
                return;
            }
            const text = guidance(result);
            message.textContent = problem || text.message;
            steps.replaceChildren(...text.steps.map((step) => Object.assign(document.createElement("li"), {textContent: step})));
            steps.hidden = !text.steps.length;
            enableButton.hidden = !text.canEnable;
            root.hidden = false;
        }

        dismissButton.addEventListener("click", () => {
            saved.dismiss();
            root.hidden = true;
        });
        enableButton.addEventListener("click", async () => {
            enableButton.disabled = true;
            try {
                render(await enable(cfg));
            } catch (error) {
                render({state: "off"}, "Something went wrong turning notifications on: " + error.message);
            }
            enableButton.disabled = false;
        });

        try {
            render(await status(cfg));
        } catch (error) {
            console.warn("Couldn't work out notification status", error);
        }
    }

    window.RigsPush = {status, enable, disable, test, guidance, box, platform};
})();
