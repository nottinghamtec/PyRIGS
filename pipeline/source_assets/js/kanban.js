// The Kanban: drag a rig between the status columns, or onto the cancel/invoice drop zones that appear while
// dragging. Each card's menu does the same, for touch screens and keyboards.
(function () {
    "use strict";

    const horizon = document.getElementById("horizon");
    if (horizon) {
        horizon.addEventListener("change", () => horizon.form.submit());
    }

    const board = document.getElementById("kanban");
    if (!board) {
        return;
    }
    const csrf = board.querySelector("[name=csrfmiddlewaretoken]").value;
    const cancelled = board.dataset.cancelledStatus;
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
            place(card, target || cell(laneOf(card), data.column));
            updateMenu(card);
            recount();
            toast(`${data.display_id} moved to ${statusNames[data.status] || data.column}`, "success");
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
            card.removeAttribute("draggable");
            const menu = card.querySelector(".kanban-card-menu");
            if (menu) {
                menu.remove();
            }
            if (data.invoice.void || !target) {
                card.remove();
            } else {
                const badge = document.createElement("a");
                badge.href = data.invoice.url;
                badge.className = "badge text-bg-info text-decoration-none";
                badge.textContent = `Invoice ${data.invoice.display_id}`;
                card.querySelector(".kanban-card-badges").append(badge);
                place(card, target);
            }
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
            return true;
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
        } else if (action === "cancel") {
            cancel(card);
        } else if (action === "invoice") {
            invoice(card);
        }
    });

    board.querySelectorAll(".kanban-card").forEach(updateMenu);
    recount();
})();
