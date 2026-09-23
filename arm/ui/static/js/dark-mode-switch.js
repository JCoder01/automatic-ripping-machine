const darkSwitch = document.getElementById("darkSwitch");

function initTheme() {
    const isDark = localStorage.getItem("darkSwitch") === "dark";
    darkSwitch.checked = isDark;
    if (isDark) {
        document.documentElement.setAttribute("data-bs-theme", "dark");
    } else {
        document.documentElement.removeAttribute("data-bs-theme");
    }
}

function resetTheme() {
    if (darkSwitch.checked) {
        document.documentElement.setAttribute("data-bs-theme", "dark");
        localStorage.setItem("darkSwitch", "dark");
    } else {
        document.documentElement.removeAttribute("data-bs-theme");
        localStorage.removeItem("darkSwitch");
    }
}

window.addEventListener("DOMContentLoaded", () => {
    if (!darkSwitch) return;

    // Apply theme on page load
    initTheme();

    // Listen for switch toggle
    darkSwitch.addEventListener("change", () => {
        resetTheme();
    });
});
