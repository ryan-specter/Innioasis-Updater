/*!
 * Site i18n — locale copies and region editions
 * ---------------------------------------------------------------
 * The site ships in English. Every other language is a pre-translated
 * catalog in i18n/catalogs/<locale>.json, produced by
 * scripts/i18n/translate.py. This file picks the visitor's locale, loads
 * that catalog and swaps the page's text, attributes, title and meta
 * description in place. Nothing is fetched until the locale is known to
 * differ from English, so an English visit costs one small request for
 * the picker list.
 *
 * A "copy" of the site lives at /<locale>/<page>.html. Those copies are
 * pre-rendered by scripts/i18n/prerender.py, so search engines see the
 * translated text in the HTML rather than after script execution. On a
 * copy, this runtime detects the path prefix, keeps the same page when
 * the language changes, and leaves the text alone because it is already
 * translated.
 *
 * Region editions are separate from language: a region decides what the
 * page may offer. Elements marked data-availability="updater" only render
 * where the updater app is usable, data-region-only="cn" only in the China
 * edition, and region copy overrides replace a source string after
 * translation. The rules live in i18n/regions.json.
 *
 * RULE: new user-facing copy belongs in the HTML (or a catalog), not in a
 * JavaScript string with no translation entry. The shell strings harvested
 * by scripts/i18n/harvest_ui_strings.py cover the ones that must stay in JS.
 * ---------------------------------------------------------------
 */
(function (global) {
    "use strict";

    var DEFAULT_LOCALE = "en";
    var STORAGE_LOCALE = "innioasis-locale";
    var STORAGE_REGION = "innioasis-region";
    var STORAGE_COUNTRY = "innioasis-country";

    var SKIP_TAGS = {
        SCRIPT: 1, STYLE: 1, PRE: 1, CODE: 1, KBD: 1, SAMP: 1, TEXTAREA: 1
    };

    var ATTRIBUTES = ["title", "alt", "placeholder", "aria-label", "aria-description"];
    var META_NAMES = {
        "description": 1,
        "keywords": 1,
        "og:title": 1,
        "og:description": 1,
        "og:site_name": 1,
        "twitter:title": 1,
        "twitter:description": 1
    };

    var state = {
        locale: DEFAULT_LOCALE,
        dir: "ltr",
        strings: null,
        locales: [],
        regions: null,
        region: "intl",
        availability: {},
        regionCopy: {},
        applied: 0,
        panel: null
    };

    var observer = null;
    var applying = false;
    var baseUrl = "/";

    /* ---------------------------------------------------------------- */
    /* Utilities                                                        */
    /* ---------------------------------------------------------------- */

    function scriptBase() {
        var script = document.currentScript;
        if (!script) {
            var scripts = document.querySelectorAll('script[src*="site-locale.js"]');
            script = scripts.length ? scripts[scripts.length - 1] : null;
        }
        if (!script || !script.src) return "/";
        return script.src.replace(/[^/]*$/, "");
    }

    function readStorage(key) {
        try { return global.localStorage.getItem(key); } catch (_) { return null; }
    }

    function writeStorage(key, value) {
        try { global.localStorage.setItem(key, value); } catch (_) {}
    }

    function normalise(text) {
        return String(text == null ? "" : text).replace(/\s+/g, " ").trim();
    }

    function fetchJson(path, timeoutMs) {
        var controller = typeof AbortController === "function" ? new AbortController() : null;
        var timer = null;
        if (controller && timeoutMs) {
            timer = setTimeout(function () { controller.abort(); }, timeoutMs);
        }
        return fetch(baseUrl + path, {
            cache: "no-cache",
            signal: controller ? controller.signal : undefined
        }).then(function (response) {
            if (timer) clearTimeout(timer);
            if (!response.ok) throw new Error("HTTP " + response.status + " for " + path);
            return response.json();
        }).catch(function (error) {
            if (timer) clearTimeout(timer);
            throw error;
        });
    }

    function normalizeTag(value) {
        return String(value || "").toLowerCase().replace(/_/g, "-");
    }

    /* ---------------------------------------------------------------- */
    /* Locale resolution                                                */
    /* ---------------------------------------------------------------- */

    function localeIndex() {
        var map = {};
        state.locales.forEach(function (entry) { map[entry.code.toLowerCase()] = entry; });
        return map;
    }

    function pathLocale() {
        var segments = global.location.pathname.split("/").filter(Boolean);
        if (!segments.length) return "";
        var candidate = normalizeTag(segments[0]);
        var map = localeIndex();
        return map[candidate] ? map[candidate].code : "";
    }

    function param(name) {
        try {
            return new URLSearchParams(global.location.search).get(name) || "";
        } catch (_) {
            return "";
        }
    }

    function browserLocales() {
        var list = (navigator.languages && navigator.languages.length)
            ? navigator.languages
            : [navigator.language || ""];
        return list.map(normalizeTag).filter(Boolean);
    }

    function matchBrowserLocale(map) {
        var candidates = browserLocales();
        for (var i = 0; i < candidates.length; i += 1) {
            var tag = candidates[i];
            if (map[tag]) return map[tag].code;
            var language = tag.split("-")[0];
            if (language === "zh") {
                /* Simplified unless the region says otherwise. */
                if (/-(tw|hk|mo)$/.test(tag)) {
                    if (map["zh-tw"]) return "zh-TW";
                    if (map["zh-hant"]) return map["zh-hant"].code;
                }
                if (map["zh-cn"]) return "zh-CN";
                continue;
            }
            if (map[language]) return map[language].code;
            /* en-GB and friends exist as variants; fall back to their base. */
            for (var code in map) {
                if (!Object.prototype.hasOwnProperty.call(map, code)) continue;
                if (map[code].base === language) return map[code].code;
            }
        }
        return "";
    }

    function regionDefaultLocale() {
        var region = state.regions && state.regions.regions[state.region];
        if (!region) return "";
        var country = readStorage(STORAGE_COUNTRY) || "";
        var mapped = country && region.autoLocales ? region.autoLocales[country] : "";
        if (mapped) return mapped;
        return (region.locales && region.locales[0]) || "";
    }

    function resolveLocale() {
        var map = localeIndex();
        var requested = normalizeTag(param("lang"));
        if (requested) {
            if (map[requested]) return map[requested].code;
            /* The picker list can be missing on a partial deploy; an explicit
               ?lang= is still the visitor's instruction, so honour it and let
               the catalog fetch decide whether the language exists. */
            if (/^[a-z]{2,3}(-[a-z0-9]{2,4})?$/.test(requested)) return requested;
        }
        var fromPath = pathLocale();
        if (fromPath) return fromPath;
        var stored = normalizeTag(readStorage(STORAGE_LOCALE));
        if (stored && map[stored]) return stored;
        var fromRegion = normalizeTag(regionDefaultLocale());
        if (fromRegion && map[fromRegion]) return fromRegion;
        return matchBrowserLocale(map) || DEFAULT_LOCALE;
    }

    /* ---------------------------------------------------------------- */
    /* Region resolution                                                */
    /* ---------------------------------------------------------------- */

    function resolveRegion() {
        var regions = state.regions && state.regions.regions ? state.regions.regions : {};
        var requested = normalizeTag(param("region"));
        if (requested && regions[requested]) return requested;
        var stored = normalizeTag(readStorage(STORAGE_REGION));
        if (stored && regions[stored]) return stored;
        var country = readStorage(STORAGE_COUNTRY);
        var mapped = country && state.regions && state.regions.countryRegions
            ? state.regions.countryRegions[country]
            : "";
        if (mapped && regions[mapped]) return mapped;
        return (state.regions && state.regions.default) || "intl";
    }

    /* Cloudflare's /cdn-cgi/trace is the only reliable, same-origin way to
       learn the visitor's country without a third party. It exists only
       behind Cloudflare, and a failed lookup changes nothing. */
    function confirmCountry() {
        if (readStorage(STORAGE_COUNTRY)) return Promise.resolve();
        if (param("region")) return Promise.resolve();
        return fetch(baseUrl + "cdn-cgi/trace", { cache: "no-store" })
            .then(function (response) { return response.ok ? response.text() : ""; })
            .then(function (text) {
                var match = /(?:^|\n)loc=([A-Z]{2})(?:\n|$)/.exec(text || "");
                if (!match) return;
                writeStorage(STORAGE_COUNTRY, match[1]);
            })
            .catch(function () {});
    }

    /* ---------------------------------------------------------------- */
    /* Translation                                                      */
    /* ---------------------------------------------------------------- */

    function regionValue(source) {
        var entry = state.regionCopy[source];
        if (!entry) return "";
        return entry[state.locale] || entry[state.locale.split("-")[0]] || entry.en || "";
    }

    function translateValue(value) {
        var text = String(value == null ? "" : value);
        var parts = /^(\s*)([\s\S]*?)(\s*)$/.exec(text);
        if (!parts) return value;
        var core = normalise(parts[2]);
        if (!core) return value;

        var regional = regionValue(core);
        if (regional) return parts[1] + regional + parts[3];

        if (!state.strings) return value;
        var translated = state.strings[core];
        if (translated === undefined) return value;
        return parts[1] + translated + parts[3];
    }

    function shouldSkip(element) {
        if (!element) return false;
        if (SKIP_TAGS[element.tagName]) return true;
        if (element.hasAttribute && element.hasAttribute("data-i18n-skip")) return true;
        if (element.getAttribute && element.getAttribute("translate") === "no") return true;
        return false;
    }

    function translateAttributes(element) {
        if (!element.getAttribute) return;
        for (var i = 0; i < ATTRIBUTES.length; i += 1) {
            var name = ATTRIBUTES[i];
            if (!element.hasAttribute(name)) continue;
            var value = element.getAttribute(name);
            var next = translateValue(value);
            if (next !== value) element.setAttribute(name, next);
        }
    }

    function translateTree(root) {
        if (!root) return;
        if (root.nodeType === 3) {
            var next = translateValue(root.nodeValue);
            if (next !== root.nodeValue) {
                root.nodeValue = next;
                state.applied += 1;
            }
            return;
        }
        if (root.nodeType !== 1 && root.nodeType !== 9 && root.nodeType !== 11) return;
        if (root.nodeType === 1 && shouldSkip(root)) return;

        if (root.nodeType === 1) translateAttributes(root);

        for (var node = root.firstChild; node; node = node.nextSibling) {
            if (node.nodeType === 3) {
                var value = translateValue(node.nodeValue);
                if (value !== node.nodeValue) {
                    node.nodeValue = value;
                    state.applied += 1;
                }
            } else if (node.nodeType === 1) {
                translateTree(node);
            }
        }
    }

    function translateHead() {
        if (!state.strings && !Object.keys(state.regionCopy).length) return;
        var title = document.title;
        var nextTitle = translateValue(title);
        if (nextTitle !== title) document.title = nextTitle;

        var metas = document.querySelectorAll(
            'meta[name="description"], meta[name="keywords"], meta[property^="og:"], meta[name^="twitter:"]'
        );
        Array.prototype.forEach.call(metas, function (meta) {
            var key = (meta.getAttribute("name") || meta.getAttribute("property") || "").toLowerCase();
            if (!META_NAMES[key]) return;
            var content = meta.getAttribute("content") || "";
            var next = translateValue(content);
            if (next !== content) meta.setAttribute("content", next);
        });
    }

    function applyLanguage() {
        var root = document.documentElement;
        if (!root) return;
        root.setAttribute("lang", state.locale);
        root.setAttribute("dir", state.dir);
        root.setAttribute("data-locale", state.locale);

        if (state.locale === DEFAULT_LOCALE && !Object.keys(state.regionCopy).length) {
            translateHead();
            return;
        }
        if (!document.body) return;
        applying = true;
        try {
            translateTree(document.body);
        } finally {
            applying = false;
        }
        translateHead();
    }

    function watch() {
        if (observer || typeof MutationObserver !== "function" || !document.body) return;
        observer = new MutationObserver(function (records) {
            if (applying) return;
            if (!state.strings && !Object.keys(state.regionCopy).length) return;
            applying = true;
            try {
                for (var i = 0; i < records.length; i += 1) {
                    var record = records[i];
                    if (record.type === "childList") {
                        for (var j = 0; j < record.addedNodes.length; j += 1) {
                            var added = record.addedNodes[j];
                            if (added.nodeType === 3) translateTree(added);
                            else if (added.nodeType === 1 && !added.hasAttribute("data-locale-panel")) {
                                translateTree(added);
                            }
                        }
                    } else if (record.type === "characterData" && record.target) {
                        var value = translateValue(record.target.nodeValue);
                        if (value !== record.target.nodeValue) record.target.nodeValue = value;
                    }
                }
            } finally {
                applying = false;
            }
        });
        observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    }

    /* ---------------------------------------------------------------- */
    /* Region gating                                                    */
    /* ---------------------------------------------------------------- */

    function listed(value) {
        return String(value || "").split(",").map(function (part) {
            return part.trim().toLowerCase();
        }).filter(Boolean);
    }

    function regionAllows(element) {
        var only = element.getAttribute("data-region-only");
        if (only && listed(only).indexOf(state.region) < 0) return false;
        var hide = element.getAttribute("data-region-hide");
        if (hide && listed(hide).indexOf(state.region) >= 0) return false;
        var need = element.getAttribute("data-availability");
        if (need && !state.availability[normalise(need).toLowerCase()]) return false;
        var deny = element.getAttribute("data-availability-hide");
        if (deny && state.availability[normalise(deny).toLowerCase()]) return false;
        return true;
    }

    function applyRegions() {
        var nodes = document.querySelectorAll(
            "[data-region-only], [data-region-hide], [data-availability], [data-availability-hide]"
        );
        Array.prototype.forEach.call(nodes, function (element) {
            if (regionAllows(element)) {
                element.removeAttribute("hidden");
                element.removeAttribute("data-region-hidden");
                if (element.getAttribute("data-region-was-display") !== null) {
                    element.style.display = element.getAttribute("data-region-was-display");
                    element.removeAttribute("data-region-was-display");
                }
            } else {
                element.setAttribute("data-region-hidden", "1");
                element.setAttribute("hidden", "");
                if (element.style && element.style.display && element.style.display !== "none") {
                    element.setAttribute("data-region-was-display", element.style.display);
                    element.style.display = "none";
                }
            }
        });
        document.documentElement.setAttribute("data-region", state.region);
    }

    /* ---------------------------------------------------------------- */
    /* Picker                                                           */
    /* ---------------------------------------------------------------- */

    var STRINGS = {
        language: "Language",
        region: "Edition",
        search: "Search languages",
        close: "Close",
        allLanguages: "All languages",
        editionNote: "The edition changes what this site offers, not just the language.",
        english: "English (original)"
    };

    function t(key) {
        if (!state.strings) return STRINGS[key];
        return state.strings[STRINGS[key]] || STRINGS[key];
    }

    function buildPanel() {
        if (state.panel) return state.panel;

        var panel = document.createElement("div");
        panel.className = "site-locale-panel";
        panel.setAttribute("data-locale-panel", "1");
        panel.setAttribute("role", "dialog");
        panel.setAttribute("aria-modal", "true");
        panel.setAttribute("aria-label", t("language"));
        panel.hidden = true;

        var header = document.createElement("div");
        header.className = "site-locale-panel-head";
        header.innerHTML =
            '<strong class="site-locale-panel-title"></strong>' +
            '<button type="button" class="site-locale-close" aria-label="' + escapeHtml(t("close")) + '">×</button>';
        panel.appendChild(header);

        var search = document.createElement("input");
        search.type = "search";
        search.className = "site-locale-search";
        search.placeholder = t("search");
        search.setAttribute("aria-label", t("search"));
        panel.appendChild(search);

        var list = document.createElement("div");
        list.className = "site-locale-list";
        list.setAttribute("role", "listbox");
        panel.appendChild(list);

        var editions = document.createElement("div");
        editions.className = "site-locale-editions";
        panel.appendChild(editions);

        document.body.appendChild(panel);
        state.panel = panel;

        header.querySelector(".site-locale-close").addEventListener("click", closePanel);
        search.addEventListener("input", function () {
            renderList(list, search.value);
        });
        panel.addEventListener("click", function (event) {
            if (event.target === panel) closePanel();
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && !panel.hidden) closePanel();
        });

        renderEditions(editions);
        renderList(list, "");
        return panel;
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, function (character) {
            return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character];
        });
    }

    function renderList(container, query) {
        var needle = normalise(query).toLowerCase();
        container.innerHTML = "";

        var entries = state.locales.filter(function (entry) {
            if (!needle) return true;
            return (entry.code + " " + entry.name + " " + entry.native).toLowerCase().indexOf(needle) >= 0;
        });

        if (!entries.some(function (entry) { return entry.code === DEFAULT_LOCALE; })) {
            entries.unshift({ code: DEFAULT_LOCALE, name: "English", native: "English", dir: "ltr" });
        }

        entries.forEach(function (entry) {
            var button = document.createElement("button");
            button.type = "button";
            button.className = "site-locale-item";
            button.setAttribute("role", "option");
            button.setAttribute("data-code", entry.code);
            if (entry.code === state.locale) {
                button.classList.add("is-current");
                button.setAttribute("aria-selected", "true");
            }
            var native = document.createElement("span");
            native.className = "site-locale-native";
            native.setAttribute("lang", entry.code);
            native.setAttribute("dir", entry.dir || "ltr");
            native.textContent = entry.native || entry.name;
            var english = document.createElement("span");
            english.className = "site-locale-english";
            english.textContent = entry.name;
            button.appendChild(native);
            button.appendChild(english);
            button.addEventListener("click", function () { setLocale(entry.code); });
            container.appendChild(button);
        });
    }

    function renderEditions(container) {
        var regions = state.regions && state.regions.regions ? state.regions.regions : {};
        var codes = Object.keys(regions);
        if (codes.length < 2) {
            container.hidden = true;
            return;
        }
        container.innerHTML = "";
        var label = document.createElement("div");
        label.className = "site-locale-editions-label";
        label.textContent = t("region");
        container.appendChild(label);

        var row = document.createElement("div");
        row.className = "site-locale-editions-row";
        codes.forEach(function (code) {
            var button = document.createElement("button");
            button.type = "button";
            button.className = "site-locale-edition";
            button.textContent = regions[code].label || code;
            if (code === state.region) button.classList.add("is-current");
            button.addEventListener("click", function () { setRegion(code); });
            row.appendChild(button);
        });
        container.appendChild(row);

        var note = document.createElement("p");
        note.className = "site-locale-note";
        note.textContent = t("editionNote");
        container.appendChild(note);
    }

    function openPanel() {
        var panel = buildPanel();
        panel.hidden = false;
        document.documentElement.classList.add("site-locale-open");
        var search = panel.querySelector(".site-locale-search");
        if (search) {
            search.value = "";
            renderList(panel.querySelector(".site-locale-list"), "");
            search.focus();
        }
    }

    function closePanel() {
        if (!state.panel) return;
        state.panel.hidden = true;
        document.documentElement.classList.remove("site-locale-open");
    }

    function togglePanel() {
        var panel = buildPanel();
        if (panel.hidden) openPanel();
        else closePanel();
    }

    function labelFor(code) {
        for (var i = 0; i < state.locales.length; i += 1) {
            if (state.locales[i].code === code) return state.locales[i].native || state.locales[i].name;
        }
        return "English";
    }

    function mountToggle() {
        if (document.querySelector(".site-locale-toggle")) return;
        var tools = document.querySelector("#nav-root .nav-tools") || document.querySelector(".nav-tools");
        var button = document.createElement("button");
        button.type = "button";
        button.className = "site-locale-toggle";
        button.setAttribute("aria-haspopup", "dialog");
        button.title = t("language");
        button.innerHTML =
            '<span class="site-locale-globe" aria-hidden="true">' +
            '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8">' +
            '<circle cx="12" cy="12" r="9"></circle><path d="M3 12h18M12 3c2.6 3 2.6 15 0 18M12 3c-2.6 3-2.6 15 0 18"></path>' +
            "</svg></span>" +
            '<span class="site-locale-toggle-label"></span>';
        button.querySelector(".site-locale-toggle-label").textContent = labelFor(state.locale);

        if (tools) {
            tools.insertBefore(button, tools.firstChild);
        } else {
            button.classList.add("site-locale-toggle--floating");
            document.body.appendChild(button);
        }
        button.addEventListener("click", togglePanel);
    }

    /* ---------------------------------------------------------------- */
    /* Switching                                                         */
    /* ---------------------------------------------------------------- */

    function navigate(params) {
        var url = new URL(global.location.href);
        Object.keys(params).forEach(function (key) {
            url.searchParams.set(key, params[key]);
        });
        global.location.href = url.pathname + url.search + url.hash;
    }

    function setLocale(code) {
        if (!code || code === state.locale) {
            closePanel();
            return;
        }
        writeStorage(STORAGE_LOCALE, code);

        var segments = global.location.pathname.split("/");
        var first = segments[1] ? normalizeTag(segments[1]) : "";
        var map = localeIndex();
        var onCopy = !!map[first];

        if (onCopy) {
            /* Keep the visitor on the same page, in the new copy. */
            if (code === DEFAULT_LOCALE) segments.splice(1, 1);
            else segments[1] = code;
            var path = segments.join("/") || "/";
            global.location.href = path + (global.location.search || "");
            return;
        }
        navigate({ lang: code, region: state.region });
    }

    function setRegion(code) {
        if (!code) return;
        writeStorage(STORAGE_REGION, code);
        navigate({ region: code, lang: state.locale });
    }

    /* ---------------------------------------------------------------- */
    /* Boot                                                             */
    /* ---------------------------------------------------------------- */

    function loadCatalog(code) {
        var map = localeIndex();
        var entry = map[normalizeTag(code)] || {};
        var base = entry.base || code;
        return fetchJson("i18n/catalogs/" + base + ".json", 6000)
            .then(function (catalog) {
                state.dir = catalog.dir || entry.dir || "ltr";
                return catalog.strings || {};
            })
            .catch(function () {
                if (base !== code && base.indexOf("-") > 0) {
                    var language = base.split("-")[0];
                    return fetchJson("i18n/catalogs/" + language + ".json", 6000)
                        .then(function (catalog) {
                            state.dir = catalog.dir || entry.dir || "ltr";
                            return catalog.strings || {};
                        })
                        .catch(function () { return null; });
                }
                return null;
            });
    }

    function injectStylesheet() {
        if (document.getElementById("site-locale-styles")) return;
        var link = document.createElement("link");
        link.id = "site-locale-styles";
        link.rel = "stylesheet";
        link.href = baseUrl + "site-locale.css";
        document.head.appendChild(link);
    }

    function start() {
        baseUrl = scriptBase();
        injectStylesheet();

        Promise.all([
            fetchJson("i18n/site-locales.json", 6000).catch(function () { return { locales: [] }; }),
            fetchJson("i18n/regions.json", 6000).catch(function () { return null; })
        ]).then(function (results) {
            state.locales = (results[0] && results[0].locales) || [];
            state.regions = results[1];
            return confirmCountry();
        }).then(function () {
            state.region = resolveRegion();
            state.locale = resolveLocale();
            var map = localeIndex();
            var entry = map[normalizeTag(state.locale)] || {};
            state.dir = entry.dir || "ltr";

            /* The China edition is a Chinese-language edition. A stored or
               auto-detected edition must not survive an explicit choice of
               another language, or the page ends up Chinese in German
               clothing. An explicit ?region= stays respected. */
            if (!param("region") && state.region === "cn" && !/^zh(-|$)/.test(state.locale)) {
                state.region = (state.regions && state.regions.default) || "intl";
            }
            var resolvedRegion = state.regions && state.regions.regions
                ? state.regions.regions[state.region]
                : null;
            state.availability = (resolvedRegion && resolvedRegion.availability) || {};
            state.regionCopy = (resolvedRegion && resolvedRegion.copy) || {};

            applyRegions();
            applyLanguage();

            var needsCatalog = baseOfLocale(state.locale) !== DEFAULT_LOCALE;
            if (!needsCatalog) return null;
            return loadCatalog(state.locale);
        }).then(function (catalog) {
            if (catalog) {
                state.strings = catalog;
                applyLanguage();
            }
            watch();
            if (document.body) mountToggle();
            else document.addEventListener("DOMContentLoaded", mountToggle);
            document.documentElement.setAttribute("data-locale-ready", "1");
        }).catch(function () {
            /* A failed boot must leave an English page, never a blank one. */
            document.documentElement.setAttribute("data-locale-ready", "1");
        });
    }

    function baseOfLocale(code) {
        var map = localeIndex();
        var entry = map[normalizeTag(code)];
        if (!entry) return normalizeTag(code).split("-")[0];
        return normalizeTag(entry.base || entry.code);
    }

    global.InnioasisLocale = {
        get locale() { return state.locale; },
        get direction() { return state.dir; },
        get region() { return state.region; },
        availability: function (feature) {
            return !!state.availability[String(feature || "").toLowerCase()];
        },
        set: setLocale,
        setRegion: setRegion,
        open: openPanel,
        close: closePanel
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () { void start(); });
    } else {
        void start();
    }
})(typeof window !== "undefined" ? window : globalThis);
