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
})();
