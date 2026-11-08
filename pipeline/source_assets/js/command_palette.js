(function () {
    "use strict";

    const RECENT_KEY = "rigs.commandPalette.recent";
    const RECENT_LIMIT = 5;
    const HINT_KEY = "rigs.commandPalette.hintDismissed";
    const QUICK_KEYS = 9;
    const EVENT_ID = /^n?0*(\d+)$/i;

    function readRecent() {
        try {
            return JSON.parse(localStorage.getItem(RECENT_KEY)) || [];
        } catch (e) {
            return [];
        }
    }

    function remember(url) {
        try {
            const recent = [url].concat(readRecent().filter((item) => item !== url)).slice(0, RECENT_LIMIT);
            localStorage.setItem(RECENT_KEY, JSON.stringify(recent));
        } catch (e) {
            /* Recents are a convenience; private windows may refuse storage */
        }
    }

    function hintDismissed() {
        try {
            return localStorage.getItem(HINT_KEY) === "1";
        } catch (e) {
            return true;
        }
    }

    function dismissHint() {
        try {
            localStorage.setItem(HINT_KEY, "1");
        } catch (e) {
            /* Without storage the hint simply comes back next time */
        }
        document.querySelectorAll(".command-palette-hint").forEach((hint) => hint.remove());
    }

    function showHint(shortcut) {
        const badge = document.querySelector("#searchForm .command-palette-shortcut");
        if (hintDismissed() || !badge || badge.offsetParent === null) return;

        const hint = document.createElement("div");
        hint.className = "command-palette-hint";
        hint.setAttribute("role", "status");
        const text = document.createElement("span");
        text.append("Try the command picker with ");
        const key = document.createElement("kbd");
        key.textContent = shortcut;
        text.appendChild(key);
        const close = document.createElement("button");
        close.type = "button";
        close.className = "btn-close btn-close-white";
        close.setAttribute("aria-label", "Dismiss");
        close.addEventListener("click", dismissHint);
        hint.append(text, close);
        badge.closest(".navbar-search-actions").appendChild(hint);
        requestAnimationFrame(() => hint.classList.add("show"));
    }

    function words(text) {
        return text.toLowerCase().split(/[^a-z0-9&']+/).filter(Boolean);
    }

    function isSubsequence(needle, haystack) {
        let i = 0;
        for (const char of haystack) {
            if (char === needle[i]) i++;
            if (i === needle.length) return true;
        }
        return false;
    }

    function score(command, query) {
        const title = command.title.toLowerCase();
        const titleWords = words(title);
        const otherWords = words(command.section + " " + command.keywords);
        let total = 0;
        for (const token of query.toLowerCase().split(/\s+/).filter(Boolean)) {
            if (title.startsWith(token)) total += 100;
            else if (titleWords.some((word) => word.startsWith(token))) total += 80;
            else if (title.includes(token)) total += 60;
            else if (otherWords.some((word) => word.startsWith(token))) total += 40;
            else if (token.length > 1 && isSubsequence(token, title.replace(/\s+/g, ""))) total += 20;
            else return 0;
        }
        return total;
    }

    function init() {
        const modalElement = document.getElementById("command-palette");
        const data = document.getElementById("command-palette-data");
        if (!modalElement || !data || typeof bootstrap === "undefined") return;

        const commands = JSON.parse(data.textContent);
        const input = document.getElementById("command-palette-input");
        const list = document.getElementById("command-palette-list");
        const postForm = document.getElementById("command-palette-post");
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        const shortcut = modalElement.dataset.shortcut;
        const altLabel = modalElement.dataset.alt === "⌥" ? "⌥" : "Alt ";
        let visible = [];
        let active = 0;

        showHint(shortcut);
        document.querySelectorAll("[data-command-palette-open]").forEach((button) => {
            button.addEventListener("click", () => modal.show());
        });

        function dynamicCommands(query) {
            const extra = [];
            const eventMatch = query.trim().match(EVENT_ID);
            if (eventMatch) {
                const id = eventMatch[1];
                extra.push({
                    title: `Open event N${id.padStart(5, "0")}`,
                    section: "Go to",
                    url: modalElement.dataset.eventUrl.replace("/0/", `/${id}/`),
                    icon: "fa-calendar-day",
                    method: "get",
                });
            }
            if (query.trim()) {
                extra.push({
                    title: `Search for “${query.trim()}”`,
                    section: "Go to",
                    url: `${modalElement.dataset.searchUrl}?q=${encodeURIComponent(query.trim())}`,
                    icon: "fa-search",
                    method: "get",
                    transient: true,
                });
            }
            return extra;
        }

        function filtered(query) {
            if (!query.trim()) {
                const recentUrls = readRecent();
                const recent = recentUrls
                    .map((url) => commands.find((command) => command.url === url))
                    .filter(Boolean)
                    .map((command) => Object.assign({}, command, { section: "Recent" }));
                return recent.concat(commands);
            }
            const recentUrls = readRecent();
            const ranked = commands
                .map((command) => ({ command, score: score(command, query) + (recentUrls.includes(command.url) ? 5 : 0) }))
                .filter((entry) => entry.score > 0)
                .sort((a, b) => b.score - a.score)
                .map((entry) => entry.command);
            const extra = dynamicCommands(query);
            const eventJump = extra.filter((command) => !command.transient);
            const searchFor = extra.filter((command) => command.transient);
            return eventJump.concat(ranked, searchFor);
        }

        function render() {
            const query = input.value;
            visible = filtered(query);
            active = Math.min(active, Math.max(visible.length - 1, 0));
            list.replaceChildren();
            let section = null;
            visible.forEach((command, index) => {
                if (!query.trim() && command.section !== section) {
                    section = command.section;
                    const header = document.createElement("li");
                    header.className = "list-group-item command-palette-section";
                    header.setAttribute("role", "presentation");
                    header.textContent = section;
                    list.appendChild(header);
                }
                const item = document.createElement("li");
                item.className = "list-group-item list-group-item-action command-palette-item";
                item.id = `command-palette-option-${index}`;
                item.setAttribute("role", "option");
                item.dataset.index = index;
                const icon = document.createElement("span");
                icon.className = `fas ${command.icon} fa-fw text-body-secondary`;
                icon.setAttribute("aria-hidden", "true");
                const title = document.createElement("span");
                title.className = "flex-grow-1";
                title.textContent = command.title;
                item.append(icon, title);
                if (query.trim() && command.section) {
                    const hint = document.createElement("small");
                    hint.className = "text-body-secondary";
                    hint.textContent = command.section;
                    item.appendChild(hint);
                }
                if (index < QUICK_KEYS) {
                    const quick = document.createElement("kbd");
                    quick.className = "command-palette-quick-key";
                    quick.textContent = `${altLabel}${index + 1}`;
                    quick.setAttribute("aria-hidden", "true");
                    item.appendChild(quick);
                    item.setAttribute("aria-keyshortcuts", `Alt+${index + 1}`);
                }
                list.appendChild(item);
            });
            if (!visible.length) {
                const empty = document.createElement("li");
                empty.className = "list-group-item text-body-secondary";
                empty.textContent = "Nothing matches";
                list.appendChild(empty);
            }
            highlight();
        }

        function highlight() {
            list.querySelectorAll(".command-palette-item").forEach((item) => {
                const isActive = Number(item.dataset.index) === active;
                item.classList.toggle("active", isActive);
                item.setAttribute("aria-selected", isActive ? "true" : "false");
                if (isActive) {
                    input.setAttribute("aria-activedescendant", item.id);
                    item.scrollIntoView({ block: "nearest" });
                }
            });
        }

        function run(command, newTab) {
            if (!command) return;
            if (!command.transient) remember(command.url);
            if (command.method === "post") {
                postForm.action = command.url;
                postForm.submit();
            } else if (newTab) {
                window.open(command.url, "_blank", "noopener");
            } else {
                window.location.href = command.url;
            }
        }

        input.addEventListener("input", () => {
            active = 0;
            render();
        });

        input.addEventListener("keydown", (event) => {
            const quick = event.altKey && !event.ctrlKey && !event.metaKey && event.code.match(/^(?:Digit|Numpad)([1-9])$/);
            if (quick) {
                event.preventDefault();
                const index = Number(quick[1]) - 1;
                if (index < visible.length) run(visible[index], event.shiftKey);
                return;
            }
            if (event.key === "ArrowDown") {
                event.preventDefault();
                active = visible.length ? (active + 1) % visible.length : 0;
                highlight();
            } else if (event.key === "ArrowUp") {
                event.preventDefault();
                active = visible.length ? (active - 1 + visible.length) % visible.length : 0;
                highlight();
            } else if (event.key === "Enter") {
                event.preventDefault();
                run(visible[active], event.metaKey || event.ctrlKey);
            }
        });

        list.addEventListener("mousemove", (event) => {
            const item = event.target.closest(".command-palette-item");
            if (item && Number(item.dataset.index) !== active) {
                active = Number(item.dataset.index);
                highlight();
            }
        });

        list.addEventListener("click", (event) => {
            const item = event.target.closest(".command-palette-item");
            if (item) run(visible[Number(item.dataset.index)], event.metaKey || event.ctrlKey);
        });

        modalElement.addEventListener("shown.bs.modal", () => {
            input.focus();
            dismissHint();
        });
        modalElement.addEventListener("show.bs.modal", () => {
            input.value = "";
            active = 0;
            render();
        });

        document.addEventListener("keydown", (event) => {
            if ((event.metaKey || event.ctrlKey) && !event.altKey && event.key.toLowerCase() === "k") {
                if (document.querySelector(".modal.show:not(#command-palette)")) return;
                event.preventDefault();
                if (modalElement.classList.contains("show")) modal.hide();
                else modal.show();
            }
        });
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
})();
