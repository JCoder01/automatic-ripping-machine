const darkSwitch = document.getElementById("darkSwitch");
const darkSwitchSun = document.getElementById("darkSwitchSun");
const darkSwitchMoon = document.getElementById("darkSwitchMoon");

function isDark() {
    return localStorage.getItem("darkSwitch") === "dark";
}

function applyTheme() {
    const dark = isDark();
    if (dark) {
        document.documentElement.setAttribute("data-bs-theme", "dark");
    } else {
        document.documentElement.removeAttribute("data-bs-theme");
    }
    if (darkSwitchSun && darkSwitchMoon) {
        darkSwitchSun.style.display = dark ? "none" : "";
        darkSwitchMoon.style.display = dark ? "" : "none";
    }
}

window.addEventListener("DOMContentLoaded", () => {
    if (!darkSwitch) return;

    applyTheme();

    darkSwitch.addEventListener("click", () => {
        if (isDark()) {
            localStorage.removeItem("darkSwitch");
        } else {
            localStorage.setItem("darkSwitch", "dark");
        }
        applyTheme();
    });
});
