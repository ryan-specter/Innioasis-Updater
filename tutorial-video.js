/**
 * Language variants for tutorial videos.
 *
 * A tutorial iframe can opt into a Spanish walkthrough with data-es-video and
 * data-es-start. Spanish readers get that embed; everyone else keeps the
 * English video already in the src attribute.
 *
 * The surrounding section can provide a default caption ([data-video-caption])
 * and a Spanish caption ([data-es-video-caption][hidden]).
 */
(function () {
    "use strict";

    function prefersSpanish() {
        var languages = (navigator.languages && navigator.languages.length)
            ? navigator.languages
            : [navigator.language || "en"];
        return String(languages[0] || "").toLowerCase().indexOf("es") === 0;
    }

    function buildSrc(id, start) {
        var src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(id) + "?rel=0";
        if (start) src += "&start=" + encodeURIComponent(start);
        src += "&hl=es&cc_lang_pref=es";
        return src;
    }

    function swap(frame) {
        var id = frame.getAttribute("data-es-video");
        if (!id) return;

        var src = buildSrc(id, frame.getAttribute("data-es-start"));
        /* Keep the base URL in sync so the embed language pass reuses it. */
        frame.setAttribute("data-embed-src", src);
        frame.setAttribute("src", src);

        var title = frame.getAttribute("data-es-title");
        if (title) frame.setAttribute("title", title);

        var section = frame.closest("section");
        if (!section) return;
        section.querySelectorAll("[data-video-caption]").forEach(function (caption) {
            caption.hidden = true;
        });
        section.querySelectorAll("[data-es-video-caption]").forEach(function (caption) {
            caption.hidden = false;
        });
    }

    function init() {
        if (!prefersSpanish()) return;
        document.querySelectorAll("iframe[data-es-video]").forEach(swap);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
