// The Kanban: drag a rig between the status columns, or onto the cancel/invoice drop zones that appear while
// dragging. Each card's menu does the same, for touch screens and keyboards.
(function () {
    "use strict";

    const options = document.getElementById("kanban-options");
    if (options) {
        options.addEventListener("change", () => options.submit());
    }

    const board = document.getElementById("kanban");
    if (!board) {
        return;
    }
    const csrf = board.querySelector("[name=csrfmiddlewaretoken]").value;
    const cancelled = board.dataset.cancelledStatus;
    const canChange = board.dataset.canChange === "1";
    const statusColumns = ["provisional", "confirmed", "booked"];
    const statusNames = {};
    board.querySelectorAll("[data-kanban-action=status]").forEach((button) => {
        statusNames[button.dataset.status] = button.textContent.replace("Move to", "").trim();
    });
    let dragged = null;

    function url(kind, pk) {
        return board.dataset[`${kind}Url`].replace("/0/", `/${pk}/`);
    }

    function post(kind, card, data) {
        card.classList.add("kanban-card-busy");
        return fetch(url(kind, card.dataset.event), {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
            body: new URLSearchParams(data || {}),
        })
            .then((response) =>
                response
                    .json()
                    .catch(() => ({ error: `Something went wrong (${response.status})` }))
                    .then((json) => {
                        if (!response.ok) {
                            throw new Error(json.error || `Something went wrong (${response.status})`);
                        }
                        return json;
                    })
            )
            .catch((error) => {
                toast(`${card.dataset.displayId}: ${error.message}`, "danger");
                throw error;
            })
            .finally(() => card.classList.remove("kanban-card-busy"));
    }

    function cell(lane, column) {
        return board.querySelector(`.kanban-cell[data-lane="${lane}"][data-column="${column}"]`);
    }

    function laneOf(card) {
        return card.closest(".kanban-cell").dataset.lane;
    }

    function columnOf(card) {
        return card.closest(".kanban-cell").dataset.column;
    }

    // Keep each column in date order
    function place(card, target) {
        const after = Array.from(target.querySelectorAll(".kanban-card")).find(
            (other) => other !== card && other.dataset.sort > card.dataset.sort
        );
        target.insertBefore(card, after || null);
        card.classList.add("kanban-card-moved");
        card.addEventListener("animationend", () => card.classList.remove("kanban-card-moved"), { once: true });
    }

    function recount() {
        board.querySelectorAll("[data-column-count]").forEach((badge) => {
            badge.textContent = board.querySelectorAll(
                `.kanban-cell[data-column="${badge.dataset.columnCount}"] .kanban-card`
            ).length;
        });
        board.querySelectorAll("[data-lane-count]").forEach((badge) => {
            badge.textContent = board.querySelectorAll(
                `.kanban-cell[data-lane="${badge.dataset.laneCount}"] .kanban-card`
            ).length;
        });
    }

    // Icons for what still needs chasing on a card, as the server works them out
    function renderFlags(card, flags) {
        const holder = card.querySelector(".kanban-card-flags");
        holder.querySelectorAll("[data-bs-toggle=tooltip]").forEach((el) => {
            const tooltip = bootstrap.Tooltip.getInstance(el);
            if (tooltip) {
                tooltip.dispose();
            }
        });
        holder.replaceChildren(
            ...flags.map((flag) => {
                const clickable = canChange && flag.action;
                const tip = clickable ? `${flag.tip} ${flag.action_tip}` : flag.tip;
                const element = document.createElement(clickable ? "button" : "span");
                element.className = `kanban-flag text-warning${clickable ? " btn btn-link p-0" : ""}`;
                element.dataset.flag = flag.key;
                element.dataset.bsToggle = "tooltip";
                element.title = tip;
                element.setAttribute("aria-label", tip);
                if (clickable) {
                    element.type = "button";
                    element.dataset.kanbanAction = flag.action;
                } else {
                    element.tabIndex = 0;
                    element.setAttribute("role", "img");
                }
                const icon = document.createElement("span");
                icon.className = `fas ${flag.icon}`;
                element.append(icon);
                new bootstrap.Tooltip(element);
                return element;
            })
        );
        card.classList.toggle("kanban-card-flagged", flags.length > 0);
    }

    function updateMenu(card) {
        card.querySelectorAll("[data-kanban-status-option]").forEach((option) => {
            option.hidden =
                option.dataset.kanbanStatusOption === card.dataset.status || !statusColumns.includes(columnOf(card));
        });
    }

    function toast(message, colour, action) {
        const element = document.createElement("div");
        element.className = `toast align-items-center text-bg-${colour} border-0`;
        element.setAttribute("role", colour === "danger" ? "alert" : "status");
        element.setAttribute("aria-live", colour === "danger" ? "assertive" : "polite");
        element.setAttribute("aria-atomic", "true");
        element.innerHTML =
            '<div class="d-flex"><div class="toast-body"></div>' +
            '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" ' +
            'aria-label="Close"></button></div>';
        element.querySelector(".toast-body").textContent = message;
        if (action) {
            const link = document.createElement(action.href ? "a" : "button");
            link.className = "btn btn-light btn-sm ms-2";
            link.textContent = action.label;
            if (action.href) {
                link.href = action.href;
            } else {
                link.type = "button";
                link.addEventListener("click", () => {
                    bootstrap.Toast.getInstance(element).hide();
                    action.onClick();
                });
            }
            element.querySelector(".toast-body").append(link);
        }
        document.getElementById("kanban-toasts").append(element);
        element.addEventListener("hidden.bs.toast", () => element.remove());
        new bootstrap.Toast(element, { autohide: !action || !action.sticky, delay: action ? 15000 : 6000 }).show();
    }

    function setStatus(card, status, target) {
        return post("status", card, { status: status }).then((data) => {
            card.dataset.status = data.status;
            renderFlags(card, data.flags);
            place(card, target || cell(laneOf(card), data.column));
            updateMenu(card);
            recount();
            toast(`${data.display_id} moved to ${statusNames[data.status] || data.column}`, "success");
        });
    }

    function markResponse(card, sent) {
        return post("response", card, { sent: sent ? "1" : "0" }).then((data) => {
            renderFlags(card, data.flags);
            if (sent) {
                toast(`${data.display_id} marked as response sent`, "success", {
                    label: "Undo",
                    onClick: () => markResponse(card, false),
                });
            } else {
                toast(`${data.display_id} marked as response not sent`, "secondary");
            }
        });
    }

    function cancel(card) {
        const lane = laneOf(card);
        return post("status", card, { status: cancelled }).then((data) => {
            card.remove();
            recount();
            toast(`${data.display_id} cancelled`, "secondary", {
                label: "Undo",
                onClick: () =>
                    post("status", card, { status: data.previous_status }).then((restored) => {
                        card.dataset.status = restored.status;
                        renderFlags(card, restored.flags);
                        place(card, cell(lane, restored.column));
                        updateMenu(card);
                        recount();
                        toast(`${restored.display_id} restored`, "success");
                    }),
            });
        });
    }

    function invoice(card) {
        return post("invoice", card).then((data) => {
            const target = cell(laneOf(card), data.column);
            card.setAttribute("data-invoiced", "");
            if (!statusColumns.includes(data.column)) {
                // Finished: it moves on to the finance columns and can't be moved by hand any more
                card.removeAttribute("draggable");
                const menu = card.querySelector(".kanban-card-menu");
                if (menu) {
                    menu.remove();
                }
            } else {
                // Invoiced ahead of the event: it keeps its place, but can't be cancelled or invoiced again
                card.querySelectorAll("[data-kanban-action=invoice], [data-kanban-action=cancel]").forEach((button) =>
                    button.closest("li").remove()
                );
            }
            const badge = document.createElement("a");
            badge.href = data.invoice.url;
            badge.className = "badge text-bg-info text-decoration-none";
            badge.textContent = `Invoiced ${data.invoice.display_id}`;
            if (!data.invoice.closed) {
                badge.textContent += ` \u00b7 \u00a3${data.invoice.balance} due`;
            }
            const badges = card.querySelector(".kanban-card-badges");
            badges.querySelectorAll(".text-bg-light").forEach((price) => price.remove());
            badges.append(badge);
            place(card, target);
            recount();
            const message = data.created
                ? `Invoice ${data.invoice.display_id} created for ${data.display_id}`
                : `${data.display_id} already has invoice ${data.invoice.display_id}`;
            toast(message, data.created ? "success" : "warning", {
                label: "View invoice",
                href: data.invoice.url,
                sticky: true,
            });
        });
    }

    // Where the dragged card may go: another status column in its own lane, or a drop zone
    function accepts(target) {
        if (!dragged) {
            return false;
        }
        if (target.dataset.dropzone) {
            return !dragged.hasAttribute("data-invoiced");
        }
        return (
            dragged.querySelector("[data-kanban-action=status]") !== null &&
            statusColumns.includes(columnOf(dragged)) &&
            statusColumns.includes(target.dataset.column) &&
            target.dataset.lane === laneOf(dragged) &&
            target.dataset.column !== columnOf(dragged)
        );
    }

    const targets = () => document.querySelectorAll(".kanban-cell, [data-dropzone]");

    board.addEventListener("dragstart", (e) => {
        const card = e.target.closest && e.target.closest(".kanban-card[draggable]");
        if (!card) {
            return;
        }
        dragged = card;
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", card.dataset.displayId);
        // Let the browser take its drag image before the card is restyled
        requestAnimationFrame(() => {
            card.classList.add("kanban-card-dragging");
            document.body.classList.add("kanban-dragging");
            targets().forEach((target) => target.classList.toggle("kanban-target", accepts(target)));
        });
    });

    board.addEventListener("dragend", () => {
        if (dragged) {
            dragged.classList.remove("kanban-card-dragging");
        }
        dragged = null;
        document.body.classList.remove("kanban-dragging");
        targets().forEach((target) => target.classList.remove("kanban-target", "kanban-over"));
    });

    targets().forEach((target) => {
        target.addEventListener("dragover", (e) => {
            if (accepts(target)) {
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";
                target.classList.add("kanban-over");
            }
        });
        target.addEventListener("dragleave", (e) => {
            if (!target.contains(e.relatedTarget)) {
                target.classList.remove("kanban-over");
            }
        });
        target.addEventListener("drop", (e) => {
            if (!accepts(target)) {
                return;
            }
            e.preventDefault();
            const card = dragged;
            if (target.dataset.dropzone === "cancel") {
                cancel(card);
            } else if (target.dataset.dropzone === "invoice") {
                invoice(card);
            } else {
                const status = statusColumns.indexOf(target.dataset.column);
                setStatus(card, status, target);
            }
        });
    });

    board.addEventListener("click", (e) => {
        const button = e.target.closest("[data-kanban-action]");
        if (!button) {
            return;
        }
        const card = button.closest(".kanban-card");
        const action = button.dataset.kanbanAction;
        if (action === "status") {
            setStatus(card, button.dataset.status);
        } else if (action === "response") {
            markResponse(card, true);
        } else if (action === "cancel") {
            cancel(card);
        } else if (action === "invoice") {
            invoice(card);
        }
    });

    board.querySelectorAll(".kanban-card").forEach(updateMenu);
    recount();
})();
