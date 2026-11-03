/**
 * macOS tutorial variants.
 *
 * A tutorial iframe can opt in with data-mac-video and data-mac-start.
 * The surrounding section can provide a default caption ([data-video-caption])
 * and a macOS caption ([data-mac-video-caption][hidden]).
 */
(function () {
    "use strict";

    function isMac() {
        return /Macintosh/.test(navigator.userAgent);
    }

    function buildSrc(id, start) {
        var src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(id) + "?rel=0";
        if (start) src += "&start=" + encodeURIComponent(start);
        return src;
    }

    function swap(frame) {
        var id = frame.getAttribute("data-mac-video");
        if (!id) return;

        frame.setAttribute("src", buildSrc(id, frame.getAttribute("data-mac-start")));

        var macTitle = frame.getAttribute("data-mac-title");
        if (macTitle) frame.setAttribute("title", macTitle);

        var section = frame.closest("section");
        if (!section) return;
        section.querySelectorAll("[data-video-caption]").forEach(function (caption) {
            caption.hidden = true;
        });
        section.querySelectorAll("[data-mac-video-caption]").forEach(function (caption) {
            caption.hidden = false;
        });
    }

    function init() {
        if (!isMac()) return;
        document.querySelectorAll("iframe[data-mac-video]").forEach(swap);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
