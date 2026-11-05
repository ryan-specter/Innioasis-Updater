/**
 * Ads experiment, ad-supported side.
 *
 * site-init.js decides which side of the experiment a browser is on and loads
 * this file only for the ad-supported group (roughly 30% of visitors). It
 * mounts one labelled ad slot in the page flow, lets the visitor ask why they
 * are seeing it or switch back to donation appeals, and asks a short feedback
 * question once, after a couple of page views.
 *
 * Nothing here identifies a visitor. The slot holds a real ad only when a
 * provider below is configured; until then it reserves the same space with the
 * site's own promotion, so placement and page layout can be judged first.
 */
(function (global, document) {
    "use strict";

    var CONFIG = {
        /* "house"       - the site's own promotion, no third-party requests.
           "adsense"     - needs adsenseClient and adsenseSlot below.
           "ethicalads"  - needs ethicaladsPublisher below. Contextual text
                           ads, no cookies, no cross-site tracking, which is
                           the closest match to what the site promises. */
        provider: "house",
        adsenseClient: "",              /* e.g. "ca-pub-0000000000000000" */
        adsenseSlot: "",                /* e.g. "1234567890" */
        ethicaladsPublisher: "",        /* e.g. "innioasis-app" */

        /* Same-origin endpoint that stores or forwards feedback. The Worker in
           ads-feedback-worker.js serves it; see wrangler.ads-feedback.toml.
           Leave empty to keep feedback in this browser only. */
        feedbackEndpoint: "/ad-feedback",

        /* Ask after this many page views, so the question follows experience
           rather than the first impression of one page. */
        feedbackAfterViews: 2
    };

    var HTML = document.documentElement;
    var VIEWS_KEY = "innioasis-ads-views";
    var FEEDBACK_KEY = "innioasis-ad-feedback";
    var PROMPT_KEY = "innioasis-ads-feedback-asked";
    var SCORES = ["fine", "slight", "intrusive", "donations"];
    var SCORE_LABELS = {
        fine: "Fine, keep them",
        slight: "A little annoying",
        intrusive: "Too intrusive",
        donations: "I'd prefer donations"
    };
    var mounted = [];

    /* ---------------------------------------------------------------- state */

    function readNumber(key) {
        try {
            var value = parseInt(global.localStorage.getItem(key), 10);
            return isFinite(value) ? value : 0;
        } catch (_) {}
        return 0;
    }

    function writeValue(key, value) {
        try { global.localStorage.setItem(key, String(value)); } catch (_) {}
    }

    function readValue(key) {
        try { return global.localStorage.getItem(key); } catch (_) {}
        return null;
    }

    function allowsStorage() {
        return !global.INNIOASIS_PRIVACY || global.INNIOASIS_PRIVACY.allows("feedback");
    }

    function countPageView() {
        var views = readNumber(VIEWS_KEY) + 1;
        writeValue(VIEWS_KEY, views);
        return views;
    }

    function isNetworkProvider() {
        var provider = String(CONFIG.provider || "house").toLowerCase();
        if (provider === "adsense") return !!(CONFIG.adsenseClient && CONFIG.adsenseSlot);
        if (provider === "ethicalads") return !!CONFIG.ethicaladsPublisher;
        return false;
    }

    /* ---------------------------------------------------------------- styles */

    function ensureStyles() {
        if (document.getElementById("y1-ads-experiment-style")) return;
        var style = document.createElement("style");
        style.id = "y1-ads-experiment-style";
        style.textContent =
            ".ads-unit { margin: 1.6rem auto; max-width: 960px; padding: 10px 14px 8px; border: 1px solid var(--lumen-line, rgba(255,255,255,.12)); border-radius: 14px; background: var(--lumen-panel-soft, rgba(255,255,255,.04)); box-sizing: border-box; }" +
            ".ads-unit-label { margin: 0 0 8px; font-size: .66rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: var(--lumen-muted, #94a3b8); }" +
            ".ads-unit-slot { min-height: 96px; display: flex; align-items: center; justify-content: center; overflow: hidden; }" +
            ".ads-unit-slot ins, .ads-unit-slot iframe { max-width: 100%; }" +
            ".ads-unit-foot { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 14px; margin: 8px 0 0; font-size: .74rem; line-height: 1.5; color: var(--lumen-muted, #94a3b8); }" +
            ".ads-unit-foot > span { flex: 1 1 220px; }" +
            ".ads-unit-link, .ads-feedback-link { padding: 0; border: 0; background: none; font: inherit; color: var(--lumen-accent, #6366f1); text-decoration: underline; cursor: pointer; }" +
            ".ads-unit-link:hover, .ads-feedback-link:hover { color: var(--lumen-text, #f8fafc); }" +
            ":root[data-lumen-theme=\"light\"] .ads-unit-link:hover, :root[data-lumen-theme=\"light\"] .ads-feedback-link:hover { color: #0f172a; }" +
            ".ads-house { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 16px; width: 100%; padding: 4px 2px; }" +
            ".ads-house-copy { flex: 1 1 260px; min-width: 0; }" +
            ".ads-house-copy strong { display: block; font-size: .98rem; line-height: 1.3; color: var(--lumen-text, #f8fafc); }" +
            ":root[data-lumen-theme=\"light\"] .ads-house-copy strong { color: #0f172a; }" +
            ".ads-house-copy span { display: block; margin-top: 2px; font-size: .82rem; line-height: 1.45; color: var(--lumen-muted, #94a3b8); }" +
            ".ads-house-cta { display: inline-flex; align-items: center; padding: 7px 14px; border-radius: 999px; border: 1px solid var(--lumen-line-strong, rgba(255,255,255,.2)); background: var(--lumen-accent-wash, rgba(99,102,241,.16)); color: var(--lumen-text, #f8fafc); font-size: .82rem; font-weight: 700; text-decoration: none; white-space: nowrap; }" +
            ".ads-house-cta:hover { background: var(--lumen-accent, #6366f1); color: #fff; }" +
            ".ads-feedback { position: fixed; left: 16px; bottom: calc(112px + env(safe-area-inset-bottom, 0px)); z-index: 10004; width: 344px; max-width: calc(100vw - 32px); box-sizing: border-box; padding: 14px; border: 1px solid var(--lumen-line-strong, rgba(255,255,255,.18)); border-radius: 14px; background: var(--lumen-panel, #12141c); box-shadow: 0 16px 48px rgba(0,0,0,.5); color: var(--lumen-text, #f8fafc); font-family: inherit; }" +
            ":root[data-lumen-theme=\"light\"] .ads-feedback { background: #fff; color: #0f172a; border-color: rgba(0,0,0,.12); box-shadow: 0 16px 40px rgba(0,0,0,.18); }" +
            ".ads-feedback-close { position: absolute; top: 6px; right: 6px; width: 26px; height: 26px; padding: 0; border: 0; border-radius: 50%; background: none; color: var(--lumen-muted, #94a3b8); font-size: 1.1rem; line-height: 1; cursor: pointer; }" +
            ".ads-feedback-close:hover { background: var(--lumen-accent-wash, rgba(99,102,241,.16)); color: var(--lumen-text, #fff); }" +
            ".ads-feedback-kicker { margin: 0 0 4px; font-size: .66rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: var(--lumen-muted, #94a3b8); }" +
            ".ads-feedback h2 { margin: 0 22px 10px 0; font-size: .95rem; line-height: 1.35; }" +
            ".ads-feedback-options { display: flex; flex-wrap: wrap; gap: 6px; }" +
            ".ads-feedback-options button { flex: 1 1 46%; padding: 7px 9px; border-radius: 9px; border: 1px solid var(--lumen-line, rgba(255,255,255,.16)); background: transparent; color: inherit; font: inherit; font-size: .8rem; line-height: 1.3; text-align: left; cursor: pointer; }" +
            ".ads-feedback-options button:hover { border-color: var(--lumen-accent, #6366f1); }" +
            ".ads-feedback-options button[aria-pressed=\"true\"] { border-color: var(--lumen-accent, #6366f1); background: var(--lumen-accent-wash, rgba(99,102,241,.18)); font-weight: 700; }" +
            ".ads-feedback-comment { display: block; margin-top: 9px; }" +
            ".ads-feedback-comment span { display: block; font-size: .74rem; color: var(--lumen-muted, #94a3b8); margin-bottom: 3px; }" +
            ".ads-feedback-comment textarea { width: 100%; box-sizing: border-box; padding: 6px 8px; border-radius: 8px; border: 1px solid var(--lumen-line, rgba(255,255,255,.16)); background: var(--lumen-panel-soft, rgba(255,255,255,.04)); color: inherit; font: inherit; font-size: .82rem; resize: vertical; }" +
            ".ads-feedback-actions { display: flex; align-items: center; gap: 10px; margin-top: 10px; }" +
            ".ads-feedback-send { padding: 7px 14px; border: 0; border-radius: 999px; background: var(--lumen-accent, #6366f1); color: #fff; font: inherit; font-size: .82rem; font-weight: 700; cursor: pointer; }" +
            ".ads-feedback-send:disabled { opacity: .5; cursor: default; }" +
            ".ads-feedback-later { padding: 0; border: 0; background: none; color: var(--lumen-muted, #94a3b8); font: inherit; font-size: .78rem; text-decoration: underline; cursor: pointer; }" +
            ".ads-feedback-status { margin: 8px 0 0; font-size: .76rem; line-height: 1.4; color: var(--lumen-muted, #94a3b8); }" +
            ".ads-why { width: 420px; max-width: calc(100vw - 32px); padding: 16px; border: 1px solid var(--lumen-line-strong, rgba(255,255,255,.18)); border-radius: 14px; background: var(--lumen-panel, #12141c); color: var(--lumen-text, #f8fafc); font-family: inherit; }" +
            ".ads-why::backdrop { background: rgba(0,0,0,.55); }" +
            ":root[data-lumen-theme=\"light\"] .ads-why { background: #fff; color: #0f172a; }" +
            ".ads-why h2 { margin: 0 0 8px; font-size: 1rem; }" +
            ".ads-why p { margin: 0 0 9px; font-size: .85rem; line-height: 1.5; color: var(--lumen-muted, #94a3b8); }" +
            ":root[data-lumen-theme=\"light\"] .ads-why p { color: #475569; }" +
            ".ads-why-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 12px; }" +
            ".ads-why-close { padding: 7px 14px; border: 1px solid var(--lumen-line-strong, rgba(255,255,255,.2)); border-radius: 999px; background: transparent; color: inherit; font: inherit; font-size: .82rem; cursor: pointer; }" +
            "@media (max-width: 640px) { .ads-feedback { left: 12px; right: 12px; width: auto; max-width: none; } }" +
            "@media (prefers-reduced-motion: reduce) { .ads-unit, .ads-feedback { transition: none; } }";
        (document.head || HTML).appendChild(style);
    }

    /* ------------------------------------------------------------ ad slot */

    var HOUSE_PROMOS = [
        {
            title: "Rockbox on your Innioasis player",
            copy: "Install Rockbox on a Y1 or Y2 with the Updater: pick the model, pick the release, connect when asked.",
            href: "/guides/rockbox-y1.html",
            cta: "Read the steps"
        },
        {
            title: "Every stock firmware release, archived",
            copy: "Original software and restore files for Y1, Y2, G1, G3, G5, Q8, R1, PR1 and D1, checked before they go up.",
            href: "/firmware.html",
            cta: "Browse firmware"
        },
        {
            title: "Themes for Y1 and Y2",
            copy: "The community themes gallery: browse covers, install one, and take a screenshot back to the forum.",
            href: "https://themes.innioasis.app/",
            cta: "Open the gallery"
        },
        {
            title: "Bring a player back to original software",
            copy: "Coming back from Rockbox or another custom system uses the same Updater flow, with no extra downloads.",
            href: "/guides/restore-original-y1.html",
            cta: "Restore guide"
        }
    ];

    function renderHouse(slot) {
        var promo = HOUSE_PROMOS[Math.floor(Math.random() * HOUSE_PROMOS.length)] || HOUSE_PROMOS[0];
        var wrap = document.createElement("div");
        wrap.className = "ads-house";
        var copy = document.createElement("div");
        copy.className = "ads-house-copy";
        var title = document.createElement("strong");
        title.textContent = promo.title;
        var text = document.createElement("span");
        text.textContent = promo.copy;
        copy.appendChild(title);
        copy.appendChild(text);
        var cta = document.createElement("a");
        cta.className = "ads-house-cta";
        cta.href = promo.href;
        cta.textContent = promo.cta;
        wrap.appendChild(copy);
        wrap.appendChild(cta);
        slot.appendChild(wrap);
    }

    function loadScript(src, attrs) {
        var existing = document.querySelector('script[src="' + src + '"]');
        if (existing) return existing;
        var script = document.createElement("script");
        Object.keys(attrs || {}).forEach(function (name) {
            script.setAttribute(name, attrs[name]);
        });
        script.src = src;
        script.async = true;
        (document.head || HTML).appendChild(script);
        return script;
    }

    function renderAdsense(slot) {
        loadScript("https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=" + encodeURIComponent(CONFIG.adsenseClient), {
            crossorigin: "anonymous"
        });
        var ins = document.createElement("ins");
        ins.className = "adsbygoogle";
        ins.style.display = "block";
        ins.style.width = "100%";
        ins.setAttribute("data-ad-client", CONFIG.adsenseClient);
        ins.setAttribute("data-ad-slot", CONFIG.adsenseSlot);
        ins.setAttribute("data-ad-format", "auto");
        ins.setAttribute("data-full-width-responsive", "true");
        slot.appendChild(ins);
        try {
            (global.adsbygoogle = global.adsbygoogle || []).push({});
        } catch (_) {}
    }

    function renderEthicalAds(slot) {
        var holder = document.createElement("div");
        holder.setAttribute("data-ea-publisher", CONFIG.ethicaladsPublisher);
        holder.setAttribute("data-ea-type", "text");
        if (HTML.getAttribute("data-lumen-theme") === "light") holder.setAttribute("data-ea-theme", "light");
        slot.appendChild(holder);
        loadScript("https://media.ethicalads.io/media/client/ethicalads.min.js");
    }

    function renderProvider(slot) {
        var provider = String(CONFIG.provider || "house").toLowerCase();
        if (provider === "adsense" && CONFIG.adsenseClient && CONFIG.adsenseSlot) {
            renderAdsense(slot);
            return;
        }
        if (provider === "ethicalads" && CONFIG.ethicaladsPublisher) {
            renderEthicalAds(slot);
            return;
        }
        renderHouse(slot);
    }

    function buildUnit() {
        var unit = document.createElement("aside");
        unit.className = "ads-unit";
        unit.setAttribute("data-ads-unit", "");
        unit.setAttribute("aria-label", isNetworkProvider() ? "Advertisement" : "Ad space");

        var label = document.createElement("p");
        label.className = "ads-unit-label";
        label.textContent = isNetworkProvider() ? "Advertisement" : "Ad space (preview)";

        var slot = document.createElement("div");
        slot.className = "ads-unit-slot";
        renderProvider(slot);

        var foot = document.createElement("p");
        foot.className = "ads-unit-foot";
        foot.innerHTML =
            "<span>Ads replace donation appeals for a share of visitors.</span>" +
            '<button type="button" class="ads-unit-link" data-ads-why>Why am I seeing this?</button>' +
            '<button type="button" class="ads-unit-link" data-ads-hide>Hide ads</button>';

        unit.appendChild(label);
        unit.appendChild(slot);
        unit.appendChild(foot);
        return unit;
    }

    function firstSection(root) {
        var kids = root.children || [];
        for (var i = 0; i < kids.length; i += 1) {
            if (/^(SECTION|ARTICLE)$/.test(kids[i].tagName)) return kids[i];
        }
        return null;
    }

    function mountUnits() {
        var root = document.querySelector("main#main") || document.querySelector("main");
        if (!root) return;
        var anchor = firstSection(root);
        var unit = buildUnit();
        if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(unit, anchor.nextSibling);
        else root.insertBefore(unit, root.firstChild || null);
        mounted.push(unit);
    }

    /* ---------------------------------------------------------- why / hide */

    function openWhy() {
        var existing = document.getElementById("ads-why-dialog");
        if (existing) {
            try { existing.showModal(); } catch (_) { existing.setAttribute("open", ""); }
            return;
        }
        var dialog = document.createElement("dialog");
        dialog.id = "ads-why-dialog";
        dialog.className = "ads-why";
        dialog.setAttribute("aria-labelledby", "ads-why-title");
        dialog.innerHTML =
            '<h2 id="ads-why-title">Why am I seeing ads?</h2>' +
            "<p>Innioasis.app is testing whether ads can pay for the site instead of donation appeals. About 30% of visitors are in this test; the rest still see the donation appeals.</p>" +
            "<p>This browser keeps its test group, so you keep the same experience on your next visit. You can leave the test whenever you like: <strong>Hide ads</strong> switches you back to the donation version for this browser.</p>" +
            '<div class="ads-why-actions">' +
            '<button type="button" class="ads-unit-link" data-ads-privacy>Privacy details</button>' +
            '<button type="button" class="ads-why-close" data-ads-why-close>Close</button>' +
            "</div>";
        (document.body || HTML).appendChild(dialog);
        dialog.addEventListener("click", function (event) {
            var target = event.target;
            if (!target || !target.closest) return;
            if (target.closest("[data-ads-why-close]")) {
                try { dialog.close(); } catch (_) { dialog.removeAttribute("open"); }
            }
            if (target.closest("[data-ads-privacy]")) {
                try { dialog.close(); } catch (_) {}
                var openPrivacy = document.querySelector("[data-privacy-open]");
                if (openPrivacy) openPrivacy.click();
            }
        });
        try { dialog.showModal(); } catch (_) { dialog.setAttribute("open", ""); }
    }

    function clearUnits() {
        mounted.forEach(function (unit) {
            if (unit && unit.parentNode) unit.parentNode.removeChild(unit);
        });
        mounted = [];
        var feedback = document.getElementById("ads-feedback-panel");
        if (feedback && feedback.parentNode) feedback.parentNode.removeChild(feedback);
        var why = document.getElementById("ads-why-dialog");
        if (why && why.parentNode) why.parentNode.removeChild(why);
    }

    function reportOptOut() {
        var payload = {
            type: "ads-experiment",
            score: "optout",
            comment: "",
            page: global.location.pathname,
            views: readNumber(VIEWS_KEY),
            at: new Date().toISOString()
        };
        post(payload);
    }

    function hideAds() {
        reportOptOut();
        clearUnits();
        if (global.INNIOASIS_EXPERIMENT && global.INNIOASIS_EXPERIMENT.set) {
            global.INNIOASIS_EXPERIMENT.set("donations");
        }
    }

    /* ------------------------------------------------------------ feedback */

    function alreadyAsked() {
        if (readValue(PROMPT_KEY) === "1") return true;
        try { return global.sessionStorage.getItem(PROMPT_KEY) === "1"; } catch (_) {}
        return false;
    }

    function markAsked() {
        writeValue(PROMPT_KEY, "1");
        try { global.sessionStorage.setItem(PROMPT_KEY, "1"); } catch (_) {}
    }

    function post(payload) {
        if (!CONFIG.feedbackEndpoint) return Promise.resolve(false);
        if (typeof global.fetch !== "function") return Promise.resolve(false);
        return global.fetch(CONFIG.feedbackEndpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            credentials: "omit",
            keepalive: true
        }).then(function (response) {
            return !!response && response.ok;
        }).catch(function () {
            return false;
        });
    }

    function buildFeedback() {
        if (document.getElementById("ads-feedback-panel")) return;
        var card = document.createElement("section");
        card.id = "ads-feedback-panel";
        card.className = "ads-feedback";
        card.setAttribute("role", "dialog");
        card.setAttribute("aria-labelledby", "ads-feedback-title");
        card.innerHTML =
            '<button type="button" class="ads-feedback-close" data-ads-feedback-close aria-label="Close feedback question">&times;</button>' +
            '<p class="ads-feedback-kicker">One quick question</p>' +
            '<h2 id="ads-feedback-title">Ads instead of donation appeals - how is it going?</h2>' +
            '<div class="ads-feedback-options" role="group" aria-label="How the ads feel">' +
            SCORES.map(function (score) {
                return '<button type="button" data-ads-score="' + score + '" aria-pressed="false">' + SCORE_LABELS[score] + "</button>";
            }).join("") +
            "</div>" +
            '<label class="ads-feedback-comment"><span>Anything else? (optional)</span>' +
            '<textarea data-ads-comment rows="2" maxlength="600" aria-label="Anything else about the ads"></textarea></label>' +
            '<div class="ads-feedback-actions">' +
            '<button type="button" class="ads-feedback-send" data-ads-send disabled>Send</button>' +
            '<button type="button" class="ads-feedback-later" data-ads-later>Not now</button>' +
            "</div>" +
            '<p class="ads-feedback-status" data-ads-status role="status" aria-live="polite"></p>';

        var selected = null;
        var send = card.querySelector("[data-ads-send]");
        var status = card.querySelector("[data-ads-status]");

        card.addEventListener("click", function (event) {
            var target = event.target;
            if (!target || !target.closest) return;
            var scoreButton = target.closest("[data-ads-score]");
            if (scoreButton) {
                selected = scoreButton.getAttribute("data-ads-score");
                card.querySelectorAll("[data-ads-score]").forEach(function (button) {
                    button.setAttribute("aria-pressed", button === scoreButton ? "true" : "false");
                });
                send.disabled = false;
                return;
            }
            if (target.closest("[data-ads-feedback-close]") || target.closest("[data-ads-later]")) {
                markAsked();
                card.remove();
                return;
            }
            if (target.closest("[data-ads-send]") && selected) {
                submit(selected, card, status, send);
            }
        });

        document.body.appendChild(card);
    }

    function submit(score, card, status, send) {
        var commentEl = card.querySelector("[data-ads-comment]");
        var comment = commentEl ? String(commentEl.value || "").slice(0, 600) : "";
        var payload = {
            type: "ads-experiment",
            score: score,
            comment: comment,
            page: global.location.pathname,
            views: readNumber(VIEWS_KEY),
            at: new Date().toISOString()
        };
        var stored = { score: score, comment: comment, at: payload.at, views: payload.views };
        markAsked();
        send.disabled = true;
        status.textContent = "Sending...";
        if (allowsStorage()) {
            try { global.localStorage.setItem(FEEDBACK_KEY, JSON.stringify(stored)); } catch (_) {}
        }
        post(payload).then(function (ok) {
            status.textContent = ok
                ? "Thanks - that reached the maintainer."
                : "Thanks - it is saved in this browser. (" + (comment ? "Your note is kept for you." : "") + ")";
            global.setTimeout(function () { card.remove(); }, ok ? 2200 : 4200);
        });
    }

    function maybeAsk(views) {
        if (alreadyAsked()) return;
        if (views < CONFIG.feedbackAfterViews) return;
        buildFeedback();
    }

    /* ------------------------------------------------------------------ init */

    function init() {
        if (!global.INNIOASIS_EXPERIMENT || !global.INNIOASIS_EXPERIMENT.isAds()) return;
        ensureStyles();
        var views = countPageView();
        mountUnits();
        document.addEventListener("click", function (event) {
            var target = event.target;
            if (!target || !target.closest) return;
            if (target.closest("[data-ads-hide]")) {
                event.preventDefault();
                hideAds();
                return;
            }
            if (target.closest("[data-ads-why]")) {
                event.preventDefault();
                openWhy();
            }
        });
        maybeAsk(views);
        global.addEventListener("innioasis-privacy-change", function () {
            /* Withdrawing feedback permission keeps the question on screen but
               stops the answer being remembered locally. */
            var card = document.getElementById("ads-feedback-panel");
            if (card) card.setAttribute("data-ads-storage", allowsStorage() ? "on" : "off");
        });
    }

    global.INNIOASIS_ADS = { config: CONFIG, hide: hideAds };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})(typeof window !== "undefined" ? window : globalThis, document);
