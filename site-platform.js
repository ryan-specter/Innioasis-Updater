/* OS-aware install links.
 *
 * Static install pages carry every platform. This script only improves the
 * visit for a desktop reader: it highlights the matching Windows, macOS or
 * Linux guide, moves that choice to the front, and rewrites links that opt in
 * with data-install-guide. Phones and tablets are deliberately left alone, and
 * with JavaScript disabled every link still works.
 */
(function (global) {
    "use strict";

    var OS = {
        windows: { key: "windows", label: "Windows", slug: "windows", anchor: "windows" },
        macos: { key: "macos", label: "macOS", slug: "mac", anchor: "macos" },
        linux: { key: "linux", label: "Linux", slug: "linux", anchor: "linux" }
    };

    var COPY = {
        windows: {
            heading: "Install Updater CE on your Windows PC",
            lead: "Windows needs the MediaTek USB driver before Updater CE can see a powered-off player.",
            steps: [
                "Download <code>installer.exe</code> from the official GitHub release and run it.",
                "Run <code>DriverInstall.exe</code>, then restart the PC so the MediaTek driver is active.",
                "Use a data cable and a USB port on the PC itself. When Updater CE asks, power the player off and connect it."
            ],
            note: "If SmartScreen blocks the download, choose <strong>More info</strong> then <strong>Run anyway</strong> for the official file."
        },
        macos: {
            heading: "Install Updater CE on your Mac",
            lead: "No separate USB driver is needed. macOS blocks the first launch until you approve the app.",
            steps: [
                "Download <code>Innioasis.Updater.for.Mac.dmg</code>, open it, and drag the app into Applications.",
                "Right-click the app and choose Open, or approve it in System Settings &rarr; Privacy &amp; Security with Open Anyway.",
                "Connect the player directly to the Mac, not through an unpowered hub, and plug it in only when Updater CE asks."
            ],
            note: "SP Flash Tool is not available on macOS; Updater CE uses the MTKClient route."
        },
        linux: {
            heading: "Install Updater CE on Linux",
            lead: "The AppImage is for Intel/AMD x86_64 Linux. USB access needs a udev rule.",
            steps: [
                "Download <code>UpdaterCE.AppImage</code> and run <code>chmod +x UpdaterCE.AppImage</code>.",
                "If it does not start, install <code>libfuse2</code> (or <code>libfuse2t64</code> on Ubuntu 24.04). Do not run it as root.",
                "Add the MediaTek udev rule for vendor ID <code>0e8d</code>, reload udev, and connect the player only at the prompt."
            ],
            note: "Add your user to <code>plugdev</code> if the player is still permission-denied."
        }
    };

    function detectPlatform() {
        var ua = navigator.userAgent || "";
        if (/android|iphone|ipad|ipod|iemobile|windows phone|mobile|tablet|kindle|silk|cros|chrome os|chromeos|fuchsia/i.test(ua)) return null;
        if (navigator.maxTouchPoints > 1 && global.matchMedia && !global.matchMedia("(pointer: fine)").matches) return null;
        var name = ((navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || "") + " " + ua;
        name = name.toLowerCase();
        if (name.indexOf("win") !== -1) return "windows";
        if (name.indexOf("mac") !== -1) return "macos";
        if (name.indexOf("linux") !== -1 || name.indexOf("x11") !== -1) return "linux";
        return null;
    }

    var platform = detectPlatform();
    var script = document.currentScript || document.querySelector('script[src*="site-platform.js"]');
    var root = "";
    try {
        root = script && script.src ? new URL(".", script.src).href : "";
    } catch (error) {
        root = "";
    }
    if (!root) {
        var src = (script && script.getAttribute("src")) || "";
        root = src.replace(/site-platform\.js.*$/, "");
    }

    if (platform) document.documentElement.setAttribute("data-os", platform);
    global.INNIOASIS_PLATFORM = platform ? {
        key: platform,
        label: OS[platform].label,
        slug: OS[platform].slug,
        anchor: OS[platform].anchor
    } : null;

    function each(selector, callback) {
        Array.prototype.forEach.call(document.querySelectorAll(selector), callback);
    }

    function setupStrips() {
        each("[data-os-install-strip]", function (strip) {
            if (strip.getAttribute("data-os-ready") === platform) return;
            var link = strip.querySelector('[data-os-guide="' + platform + '"]');
            var actions = strip.querySelector(".lumen-actions");
            if (link && actions && actions.firstElementChild !== link) {
                actions.insertBefore(link, actions.firstElementChild);
            }
            if (link) {
                link.classList.add("lumen-button--primary");
                link.setAttribute("data-detected", "true");
            }
            var note = strip.querySelector("[data-os-strip-note]");
            if (note) note.textContent = "We detected " + OS[platform].label + ", so its guide is first.";
            strip.setAttribute("data-os-ready", platform);
        });
    }

    function setupPickers() {
        each("[data-os-picker]", function (picker) {
            if (picker.getAttribute("data-os-ready") === platform) return;
            var link = picker.querySelector('[data-os-choice="' + platform + '"]');
            if (link) {
                link.setAttribute("data-detected", "true");
                var first = picker.querySelector(".install-os-choice");
                if (first && first !== link) picker.insertBefore(link, first);
            }
            var detected = picker.querySelector("[data-os-detected]");
            if (detected) {
                detected.hidden = false;
                detected.textContent = "Detected " + OS[platform].label;
            }
            picker.setAttribute("data-os-ready", platform);
        });
    }

    function rewriteGuides() {
        if (!root) return;
        each("a[data-install-guide]", function (link) {
            var slug = link.getAttribute("data-install-guide");
            if (!slug || !/^[a-z0-9-]+$/.test(slug)) return;
            var next = root + "install/" + slug + "-" + OS[platform].slug + ".html";
            if (link.href !== next) link.href = next;
            link.setAttribute("data-install-os", platform);
        });
    }

    function injectGuideCopy() {
        if (!/(^|\/)(guide|firmware-guide)\.html$/.test(location.pathname)) return;
        var main = document.getElementById("main");
        if (!main || main.querySelector("[data-os-guide-copy]")) return;
        var header = main.querySelector("header");
        if (!header) return;
        var copy = COPY[platform];
        var section = document.createElement("section");
        section.className = "lumen-guide-section install-section install-os-copy";
        section.setAttribute("data-os-guide-copy", platform);
        section.innerHTML =
            '<p class="lumen-kicker">Your computer · ' + OS[platform].label + '</p>' +
            '<h2>' + copy.heading + '</h2>' +
            '<p class="lead">' + copy.lead + '</p>' +
            '<ol class="lumen-steps">' + copy.steps.map(function (step) { return "<li>" + step + "</li>"; }).join("") + '</ol>' +
            '<p class="lumen-meta">' + copy.note + '</p>' +
            '<div class="lumen-actions">' +
            '<a class="lumen-button lumen-button--primary" href="' + root + 'install/' + OS[platform].slug + '.html">All ' + OS[platform].label + ' install guides</a>' +
            '<a class="lumen-button" href="' + root + 'install/index.html">Every platform</a>' +
            '<a class="lumen-button" href="' + root + 'drivers.html#' + OS[platform].anchor + '">Setup notes</a>' +
            '</div>';
        header.parentNode.insertBefore(section, header.nextSibling);
    }

    function observe() {
        if (!global.MutationObserver) return;
        var pending = null;
        function refresh() {
            setupStrips();
            setupPickers();
            rewriteGuides();
        }
        var observer = new MutationObserver(function () {
            if (pending) return;
            pending = global.setTimeout(function () {
                pending = null;
                refresh();
            }, 40);
        });
        observer.observe(document.body, { childList: true, subtree: true });
        /* Deferred scripts and the catalog can paint their links after this
           script starts. Two timed passes cover that without relying on
           requestAnimationFrame, which browsers pause in background tabs. */
        global.setTimeout(refresh, 300);
        global.setTimeout(refresh, 1200);
    }

    function init() {
        if (!platform) return;
        document.body.classList.add("platform-" + platform);
        setupStrips();
        setupPickers();
        rewriteGuides();
        injectGuideCopy();
        observe();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})(window);
