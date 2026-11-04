/**
 * Shared site shell: body classes and bottom dock.
 */
(function (global) {
    "use strict";

    function resolveEffectiveTheme(theme) {
        if (theme === "auto" || theme === "light" || !theme) return "dark";
        return (theme === "high-contrast" || theme === "2077") ? theme : "dark";
    }

    function applyStoredTheme() {
        var allowed = ["auto", "dark", "high-contrast", "2077"];
        var stored = null;
        try { stored = global.localStorage.getItem("lumen-theme"); } catch (_) {}
        var theme = allowed.indexOf(stored) >= 0 ? stored : "auto";
        if (document.documentElement) document.documentElement.setAttribute("data-lumen-theme", resolveEffectiveTheme(theme));
        return theme;
    }

    applyStoredTheme();

    /* Privacy consent. The site sets no cookies and does no fingerprinting.
       The only local storage is the visitor's own theme choice (always
       remembered — it is the look they picked) plus, only when allowed,
       their answers to the "was this useful?" prompts and their
       nightly-builds preference. The consent record itself is kept so the
       banner does not nag on every visit. */
    var CONSENT_KEY = "innioasis-consent";

    function readConsent() {
        try {
            var raw = global.localStorage.getItem(CONSENT_KEY);
            if (!raw) return null;
            var data = JSON.parse(raw);
            /* A record is only valid when both booleans are present, so a
               partial or corrupt value never counts as consent. */
            if (data && typeof data === "object" &&
                typeof data.feedback === "boolean" &&
                typeof data.nightly === "boolean") {
                return { feedback: data.feedback, nightly: data.nightly };
            }
        } catch (_) {}
        return null;
    }

    function writeConsent(prefs) {
        var next = { feedback: prefs.feedback !== false, nightly: prefs.nightly !== false };
        try { global.localStorage.setItem(CONSENT_KEY, JSON.stringify(next)); } catch (_) {}
        if (!next.feedback) {
            try {
                var doomed = [];
                for (var i = 0; i < global.localStorage.length; i += 1) {
                    var key = global.localStorage.key(i);
                    if (key && key.indexOf("innioasis-feedback-") === 0) doomed.push(key);
                }
                doomed.forEach(function (key) { global.localStorage.removeItem(key); });
            } catch (_) {}
        }
        if (!next.nightly) {
            try { global.localStorage.removeItem("innioasis-show-nightly"); } catch (_) {}
        }
        return next;
    }

    global.INNIOASIS_PRIVACY = {
        read: readConsent,
        save: writeConsent,
        hasDecided: function () { return readConsent() !== null; },
        /* Whether the site may remember a given preference. Theme is always
           allowed; optional preferences only after explicit consent. */
        allows: function (feature) {
            if (feature === "theme") return true;
            var prefs = readConsent();
            return !!prefs && prefs[feature] === true;
        }
    };

    function executeInlineScripts(container) {
        if (!container) return;
        container.querySelectorAll("script").forEach(function (oldScript) {
            var newScript = document.createElement("script");
            Array.from(oldScript.attributes).forEach(function (attr) {
                newScript.setAttribute(attr.name, attr.value);
            });
            newScript.textContent = oldScript.textContent;
            oldScript.parentNode.replaceChild(newScript, oldScript);
        });
    }

    function toolbarCandidates() {
        return [
            "support_toolbar.html",
            "../support_toolbar.html",
            "../../support_toolbar.html",
            "../../../support_toolbar.html",
            "https://innioasis.app/support_toolbar.html",
            "https://themes.innioasis.app/support_toolbar.html",
        ];
    }

    function addThemeFallback() {
        if (document.getElementById("nav-root") || document.getElementById("lumen-theme-fallback")) return;
        var control = document.createElement("label");
        control.id = "lumen-theme-fallback";
        control.className = "lumen-theme-control lumen-theme-control--fallback";
        control.innerHTML = '<span>Theme</span><select aria-label="Choose site colour theme"><option value="auto">Auto</option><option value="dark">Dark</option><option value="high-contrast">High contrast</option><option value="2077">2077</option></select>';
        var select = control.querySelector("select");
        var stored = "auto";
        try { stored = global.localStorage.getItem("lumen-theme") || "auto"; } catch (_) {}
        select.value = ["auto", "dark", "high-contrast", "2077"].indexOf(stored) >= 0 ? stored : "auto";
        select.addEventListener("change", function () {
            document.documentElement.setAttribute("data-lumen-theme", resolveEffectiveTheme(select.value));
            try { global.localStorage.setItem("lumen-theme", select.value); } catch (_) {}
        });
        document.body.appendChild(control);
    }

    function notifyDockReady() {
        try {
            global.dispatchEvent(new CustomEvent("y1-dock-slot-ready"));
        } catch (_) {}
    }

    function removeDuplicateSupportToolbars(slot) {
        var toolbars = Array.from(document.querySelectorAll("#support-toolbar-container"));
        var mounted = slot ? slot.querySelector("#support-toolbar-container") : null;
        toolbars.forEach(function (toolbar) {
            if (!mounted) {
                mounted = toolbar;
                return;
            }
            if (toolbar !== mounted) toolbar.remove();
        });
    }

    async function loadSupportToolbar() {
        var slot = document.getElementById("support-toolbar-slot");
        if (!slot || slot.dataset.shellLoaded === "1" || slot.dataset.shellLoading === "1") return;
        slot.dataset.shellLoading = "1";
        removeDuplicateSupportToolbars(slot);
        try {
            for (var i = 0; i < toolbarCandidates().length; i++) {
                try {
                    var res = await fetch(toolbarCandidates()[i], { cache: "no-cache" });
                    if (!res.ok) continue;
                    slot.innerHTML = await res.text();
                    executeInlineScripts(slot);
                    removeDuplicateSupportToolbars(slot);
                    slot.dataset.shellLoaded = "1";
                    notifyDockReady();
                    return;
                } catch (_) {}
            }
        } finally {
            delete slot.dataset.shellLoading;
        }
    }

    async function init() {
        if (document.documentElement) {
            document.documentElement.classList.add("site-themes-html");
        }
        if (document.body) {
            document.body.classList.add("site-themes-app");
        }
        await loadSupportToolbar();
        if (document.body) {
            document.body.classList.add("site-dock-mode");
            addThemeFallback();
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            void init();
        });
    } else {
        void init();
    }

    global.y1LoadSupportToolbar = loadSupportToolbar;
})(typeof window !== "undefined" ? window : globalThis);
