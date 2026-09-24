/**
 * Shared glue for the ARM UI shell: replaces htmx's native confirm() dialog
 * with the app's styled Bootstrap modal, and turns "showToast" events
 * (dispatched by the server via the HX-Trigger response header - see
 * feed_json() in arm/ui/jobs/jobs.py) into Bootstrap toasts.
 */
(function () {
    "use strict";

    // ---------- Confirm modal (replaces htmx's native confirm()) ----------
    const confirmModalEl = document.getElementById("confirmModal");
    if (confirmModalEl) {
        const confirmModal = new bootstrap.Modal(confirmModalEl);
        const titleEl = document.getElementById("confirmModalTitle");
        const bodyEl = document.getElementById("confirmModalBody");
        const yesBtn = document.getElementById("confirmModalYes");

        document.body.addEventListener("htmx:confirm", function (evt) {
            // Only intercept requests that opted in via hx-confirm="..."
            if (!evt.detail.question) {
                return;
            }
            evt.preventDefault();

            titleEl.textContent = evt.detail.elt.dataset.confirmTitle || "Please Confirm";
            bodyEl.textContent = evt.detail.question;

            function onYes() {
                cleanup();
                evt.detail.issueRequest(true);
            }
            function cleanup() {
                yesBtn.removeEventListener("click", onYes);
                confirmModalEl.removeEventListener("hidden.bs.modal", cleanup);
            }

            yesBtn.addEventListener("click", onYes);
            confirmModalEl.addEventListener("hidden.bs.modal", cleanup);
            confirmModal.show();
        });
    }

    // ---------- Toasts ----------
    const toastHolder = document.getElementById("toastHolder");

    function pingReadNotify(notifyId) {
        htmx.ajax("GET", "/json?mode=read_notification&notify_id=" + notifyId, {swap: "none"});
    }

    function addToast(note) {
        const existing = document.getElementById("toast" + note.id);
        if (existing) {
            return;
        }
        const toastEl = document.createElement("div");
        toastEl.id = "toast" + note.id;
        toastEl.className = "toast";
        toastEl.setAttribute("role", "alert");
        toastEl.setAttribute("aria-live", "assertive");
        toastEl.setAttribute("aria-atomic", "true");
        toastEl.innerHTML = `<div class="toast-header">
                <strong class="me-auto">${note.title}</strong>
                <small class="text-muted">just now</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">${note.message}</div>`;
        toastHolder.appendChild(toastEl);
        const toast = new bootstrap.Toast(toastEl, {delay: 6500});
        toastEl.addEventListener("hidden.bs.toast", function () {
            pingReadNotify(note.id);
            toastEl.remove();
        });
        toast.show();
    }

    if (toastHolder) {
        document.body.addEventListener("showToast", function (evt) {
            (evt.detail.notes || evt.detail || []).forEach(addToast);
        });
    }

    // ---------- Notifications panel ----------
    const notificationBellBtn = document.getElementById("notificationBellBtn");
    const notificationPanel = document.getElementById("notificationPanel");
    if (notificationBellBtn && notificationPanel) {
        const closeBtn = document.getElementById("notificationPanelClose");
        const clearAllBtn = document.getElementById("notificationClearAll");
        const panelBody = document.getElementById("notificationPanelBody");

        function onDocClick(evt) {
            if (!notificationPanel.contains(evt.target) && !notificationBellBtn.contains(evt.target)) {
                closePanel();
            }
        }
        function onKeydown(evt) {
            if (evt.key === "Escape") {
                closePanel();
            }
        }
        function openPanel() {
            notificationPanel.classList.add("show");
            htmx.ajax("GET", "/notificationview", {target: panelBody, swap: "innerHTML"});
            // Capture phase + next tick, so the click that opened the panel
            // doesn't immediately bubble into onDocClick and close it again.
            setTimeout(() => document.addEventListener("click", onDocClick, true), 0);
            document.addEventListener("keydown", onKeydown);
        }
        function closePanel() {
            notificationPanel.classList.remove("show");
            document.removeEventListener("click", onDocClick, true);
            document.removeEventListener("keydown", onKeydown);
        }

        notificationBellBtn.addEventListener("click", function (evt) {
            evt.preventDefault();
            if (notificationPanel.classList.contains("show")) {
                closePanel();
            } else {
                openPanel();
            }
        });
        if (closeBtn) {
            closeBtn.addEventListener("click", closePanel);
        }
        if (clearAllBtn) {
            clearAllBtn.addEventListener("click", function () {
                htmx.ajax("GET", "/notificationclose", {target: panelBody, swap: "innerHTML"});
            });
        }

        document.body.addEventListener("notificationsCleared", function () {
            const badge = document.getElementById("notificationBadge");
            if (badge) {
                badge.remove();
            }
        });
    }

    // ---------- Popovers (settings page's "more info" hints) ----------
    // BS5 popovers need explicit init, unlike BS4's implicit jQuery plugin
    // scan. Nothing on this page currently swaps in new popover triggers via
    // htmx, so a single pass at load is enough.
    document.querySelectorAll('[data-bs-toggle="popover"]').forEach(function (el) {
        new bootstrap.Popover(el);
    });

    // ---------- Tooltips (top bar icon buttons) ----------
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
        new bootstrap.Tooltip(el);
    });
})();
