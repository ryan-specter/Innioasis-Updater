(function () {
    "use strict";

    function escapeHtml(value) {
        return String(value == null ? "" : value).replace(/[&<>'"]/g, function (char) {
            return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char];
        });
    }

    function zipAssets(release) {
        if (!release || !Array.isArray(release.assets)) return [];
        return release.assets.filter(function (asset) {
            return asset.name && asset.name.toLowerCase().endsWith(".zip");
        });
    }

    /* The canonical firmware packages, labelled by which model each one
       installs. Y1 Type A devices shipped with software 2.0.0 or later;
       Y1 Type B devices shipped with an earlier version. Y2 devices use
       rom_y2.zip. Release details offer these for manual download. */
    var MODEL_ZIPS = [
        { name: "rom.zip", label: "Y1 · Type A", type: "A", title: "For Y1 players that shipped with software 2.0.0 or later" },
        { name: "rom_type_a.zip", label: "Y1 · Type A", type: "A", title: "For Y1 players that shipped with software 2.0.0 or later" },
        { name: "rom_y1_type_a.zip", label: "Y1 · Type A", type: "A", title: "For Y1 players that shipped with software 2.0.0 or later" },
        { name: "rom_type_b.zip", label: "Y1 · Type B", type: "B", title: "For Y1 players that shipped with an earlier software version" },
        { name: "rom_y1_type_b.zip", label: "Y1 · Type B", type: "B", title: "For Y1 players that shipped with an earlier software version" },
        { name: "rom_240p.zip", label: "Y1 · Type A · 240p", type: "A", title: "240p build for Y1 players that shipped with software 2.0.0 or later" },
        { name: "rom_240p_type_b.zip", label: "Y1 · Type B · 240p", type: "B", title: "240p build for Y1 players that shipped with an earlier software version" },
        { name: "rom_360p.zip", label: "Y1 · Type A · 360p", type: "A", title: "360p build for Y1 players that shipped with software 2.0.0 or later" },
        { name: "rom_360p_type_b.zip", label: "Y1 · Type B · 360p", type: "B", title: "360p build for Y1 players that shipped with an earlier software version" },
        { name: "rom_y2.zip", label: "Y2", type: "", title: "For Y2 players" }
    ];

    /* The hardware type a package belongs to. Y1 shipped in two revisions:
       Type A (software 2.0.0 or later) and Type B (earlier). The ROMs are not
       interchangeable, so anything offered to a player has to match the type
       of that player. "" means the package carries no type of its own, which
       covers Y2 packages, Linux installers and plain update bundles. */
    function zipType(name) {
        var n = String(name || "").toLowerCase();
        if (/type[_-]?b/.test(n)) return "B";
        if (/type[_-]?a/.test(n)) return "A";
        if (/^rom(?:[_-](?:240p|360p))?\.zip$/.test(n)) return "A";
        return "";
    }

    /* The packages a release may ship for an item, narrowed to the selected
       hardware type. Y1 releases can use rom.zip (Type A), rom_type_b.zip
       (Type B), or the 240p/360p split of either; Rockbox-style Y1 releases
       ship only the resolution split. Y2 releases use rom_y2.zip and have no
       type, mirroring how the Updater app treats any rom*.zip as a Y1
       package. Passing no type keeps every variant, which is what the
       homepage table and older callers expect. */
    function packageNamesFor(item, type) {
        var name = (item.packageName || "").toLowerCase();
        var wanted = String(type || "").toUpperCase();
        var names = name ? [name] : [];
        if (name === "rom.zip") {
            var typeA = ["rom.zip", "rom_type_a.zip", "rom_y1_type_a.zip", "rom_240p.zip", "rom_360p.zip"];
            var typeB = ["rom_type_b.zip", "rom_y1_type_b.zip", "rom_240p_type_b.zip", "rom_360p_type_b.zip"];
            if (wanted === "A") names = typeA.slice();
            else if (wanted === "B") names = typeB.slice();
            else names = typeA.concat(typeB);
        }
        if (item.repo && item.repo.toLowerCase().indexOf("y2linux") !== -1) {
            names.push("first-install.zip", "y2linux");
        }
        return names;
    }

    /* Releases that actually carry an item's model package. Shared repos
       hold releases for both models, so model matching happens per item. */
    function matchingReleases(releaseList, item, type) {
        if (!Array.isArray(releaseList) || !releaseList.length) return [];
        var names = packageNamesFor(item, type);
        var wanted = String(type || "").toUpperCase();
        var isDedicatedRepo = item.repo && item.repo.toLowerCase() !== "y1-community/y1-stock-rom";
        return releaseList.filter(function (release) {
            var zips = zipAssets(release);
            if (!zips.length) return false;
            /* A player must never be offered a release whose packages only fit
               the other hardware revision: that ROM will not boot. Only
               type-tagged packages are judged this way, so Y2 and Linux
               installer releases keep the package-name rules below. */
            if (wanted) {
                var typed = zips.filter(function (asset) { return zipType(asset.name) !== ""; });
                if (typed.length && !typed.some(function (asset) { return zipType(asset.name) === wanted; })) return false;
            }
            if (isDedicatedRepo) return true;
            return zips.some(function (asset) {
                var an = (asset.name || "").toLowerCase();
                return names.some(function (n) { return an === n || an.indexOf(n) !== -1; });
            });
        });
    }

    /* A nightly build is a GitHub pre-release, or a release whose tag or
       name says so. Rockbox Y1 and Y2 ship nightly builds, so a project
       can have nightlies without any stable release. A release tagged
       "stable" is always treated as stable, matching the Updater app. */
    function isNightly(release) {
        if (!release) return false;
        var tag = (release.tag_name || "").toLowerCase();
        if (tag.indexOf("stable") !== -1) return false;
        var label = (tag + " " + (release.name || "")).toLowerCase();
        return !!release.prerelease || label.indexOf("nightly") !== -1;
    }

    /* Clean display version for a release, mirroring the Updater app's
       parse_version_designations: a YYYYMMDD-HHMM timestamp in the tag
       wins, then a v-prefixed dotted number anywhere in the tag, then a
       trailing dotted number, then the tag itself with hex commit suffixes
       removed. "launcher-v0.9" becomes "0.9"; a tag like "Solar 20260630-0550"
       is kept as its timestamp. */
    function displayVersion(tag) {
        var name = String(tag == null ? "" : tag);
        var clean = name.replace(/-[a-f0-9]{16,}!?$/, "").replace(/[-!]+$/, "");
        var extracted = null;
        var timestamp = clean.match(/(\d{8})-(\d{4})\b/);
        if (timestamp) extracted = timestamp[1] + "-" + timestamp[2];
        if (!extracted) {
            var versionPattern = clean.match(/\bv([\d.]+)\b/i);
            if (versionPattern) extracted = versionPattern[1];
        }
        if (!extracted && clean.indexOf("-") !== -1) {
            var lastPart = clean.split("-").pop();
            if (/^v/i.test(lastPart)) lastPart = lastPart.slice(1);
            if (/^[\d.]+$/.test(lastPart)) extracted = lastPart;
        }
        return extracted || clean;
    }

    /* Sortable key for a release so newer builds come first, mirroring the
       Updater app's _release_sort_key: a tag-embedded YYYYMMDD-HHMM
       timestamp sorts highest, then the semantic version tuple, then the
       GitHub published date as the tiebreaker, then the tag name. Releases
       with no usable version sort below the versioned ones. */
    function releaseSortKey(release) {
        var tag = (release && release.tag_name) || "";
        var version = displayVersion(tag);
        var tagTimestamp = 0;
        var timestampMatch = version.match(/^(\d{8})-(\d{4})$/);
        if (timestampMatch) {
            var digits = timestampMatch[1];
            var time = timestampMatch[2];
            tagTimestamp = Date.UTC(Number(digits.slice(0, 4)), Number(digits.slice(4, 6)) - 1, Number(digits.slice(6, 8)), Number(time.slice(0, 2)), Number(time.slice(2, 4)));
        }
        var semver = null;
        if (!tagTimestamp && /^\d+(\.\d+)*$/.test(version)) {
            semver = version.split(".").map(function (part) { return Number(part); });
        }
        var published = 0;
        if (release && release.published_at) {
            var parsed = Date.parse(release.published_at);
            if (!isNaN(parsed)) published = parsed;
        }
        return [tagTimestamp || semver ? 1 : 0, tagTimestamp, semver || [], published, tag.toLowerCase()];
    }

    /* Compare two releaseSortKey arrays, newest first. Elements 0-2 are
       numeric or numeric arrays, element 3 is the published date, and the
       tag name breaks any remaining tie. */
    function compareReleaseKeys(a, b) {
        for (var i = 0; i < 4; i += 1) {
            var left = a[i];
            var right = b[i];
            if (Array.isArray(left) && Array.isArray(right)) {
                var length = Math.max(left.length, right.length);
                for (var part = 0; part < length; part += 1) {
                    var leftPart = part < left.length ? left[part] : 0;
                    var rightPart = part < right.length ? right[part] : 0;
                    if (leftPart !== rightPart) return leftPart - rightPart;
                }
            } else if (left !== right) {
                return left - right;
            }
        }
        return a[4].localeCompare(b[4]);
    }

    /* GitHub access tokens from config.ini. Entries may be stored with or
       without the github_pat_ prefix; a missing prefix is re-added so the
       token is accepted by the API. The public release directory uses a
       random token per request to ride out rate limits and falls back to
       an unauthenticated request when every token has been tried. */
    var githubTokens = [];

    function loadGithubTokens() {
        return fetch("config.ini", { cache: "no-store" })
            .then(function (response) { return response.ok ? response.text() : ""; })
            .then(function (text) {
                githubTokens = (text || "").split(/\r?\n/)
                    .map(function (line) { return line.trim(); })
                    .filter(function (line) { return /^(key_\d+|token)\s*=/.test(line); })
                    .map(function (line) { return line.split("=").slice(1).join("=").trim(); })
                    .filter(function (value) { return value.length > 10; })
                    .map(function (value) {
                        return /^(github_pat_|ghp_|gho_|ghu_)/.test(value) ? value : "github_pat_" + value;
                    });
                /* Share the pool with the docs reader so a page never loads
                   config.ini twice. */
                window.INNIOASIS_GITHUB_TOKENS = githubTokens;
                return githubTokens;
            })
            .catch(function () { githubTokens = []; return githubTokens; });
    }

    /* Call GitHub API with token rotation, pruning invalid tokens on 401,
       retrying on rate limits (403/429), and falling back to unauthenticated. */
    function fetchGithubApi(url) {
        var tried = [];
        function attempt() {
            var token = null;
            if (githubTokens.length > 0) {
                var available = githubTokens.filter(function (t) { return tried.indexOf(t) === -1; });
                if (available.length > 0) {
                    var idx = Math.floor(Math.random() * available.length);
                    token = available[idx];
                    tried.push(token);
                }
            }
            var headers = { Accept: "application/vnd.github+json" };
            if (token) headers.Authorization = "Bearer " + token;

            return fetch(url, { headers: headers })
                .then(function (response) {
                    if (response.ok) return response;
                    if (response.status === 401 && token) {
                        var pIndex = githubTokens.indexOf(token);
                        if (pIndex !== -1) githubTokens.splice(pIndex, 1);
                        return attempt();
                    }
                    if ((response.status === 403 || response.status === 429) && token) {
                        return attempt();
                    }
                    return response;
                })
                .catch(function (err) {
                    if (token) return attempt();
                    throw err;
                });
        }
        return attempt();
    }

    /* One page of releases for a repo using token rotation and fallback. */
    function fetchReleasesPage(repo, page) {
        var url = "https://api.github.com/repos/" + repo + "/releases?per_page=100&page=" + page;
        return fetchGithubApi(url);
    }

    function fetchAllReleases(repo, page, collected) {
        if (page > 100) return Promise.resolve({ releases: collected, complete: false });
        return fetchReleasesPage(repo, page)
            .then(function (response) {
                if (!response.ok) return collected.length ? { releases: collected, complete: false } : null;
                return response.json().then(function (releaseList) {
                    if (!Array.isArray(releaseList)) return collected.length ? { releases: collected, complete: false } : null;
                    var all = collected.concat(releaseList);
                    var link = response.headers.get("Link") || "";
                    var hasNext = /<[^>]+>;\s*rel=["']next["']/.test(link);
                    return (hasNext || releaseList.length === 100) ? fetchAllReleases(repo, page + 1, all) : { releases: all, complete: true };
                });
            });
    }

    /* The visitor's language. YouTube picks a matching dubbed or
       multi-language audio track when the creator has published one, and
       plays the original audio when there is none. */
    function preferredLanguage() {
        var raw = (navigator.languages && navigator.languages[0]) || navigator.language || "en";
        var short = String(raw).toLowerCase().split("-")[0];
        return short || "en";
    }

    function withPlayerLanguage(src, lang) {
        if (!src || src.indexOf("youtube") === -1) return src;
        var url;
        try {
            url = new URL(src, window.location.href);
        } catch (error) {
            return src;
        }
        url.searchParams.set("hl", lang);
        url.searchParams.set("cc_lang_pref", lang);
        return url.toString();
    }

    /* Player language for every embed; the Spanish walkthrough stays the
       final slide of the carousel. */
    function applyEmbedLanguage() {
        var lang = preferredLanguage();
        document.querySelectorAll("iframe[src*='youtube']").forEach(function (frame) {
            var base = frame.getAttribute("data-embed-src") || frame.getAttribute("src");
            if (!base) return;
            frame.setAttribute("data-embed-src", base);
            frame.setAttribute("src", withPlayerLanguage(base, lang));
        });
    }

    function initCarousel(root) {
        /* The Cristian Plaza walkthrough is Spanish: only Spanish readers see
           it, and it is never part of an English reader's slide order. */
        if (preferredLanguage() !== "es") {
            root.querySelectorAll("[data-video-lang='es']").forEach(function (slide) {
                if (slide.parentNode) slide.parentNode.removeChild(slide);
            });
        }
        var slides = Array.from(root.querySelectorAll(".lumen-carousel-slide"));
        var stage = root.querySelector(".lumen-carousel-stage");
        var previous = root.querySelector("[data-carousel-previous]");
        var next = root.querySelector("[data-carousel-next]");
        var creditLink = root.querySelector("[data-carousel-credit-link]");
        var current = 0;
        if (!slides.length) return;

        function shuffle(items) {
            for (var i = items.length - 1; i > 0; i -= 1) {
                var j = Math.floor(Math.random() * (i + 1));
                var item = items[i];
                items[i] = items[j];
                items[j] = item;
            }
            return items;
        }

        function arrangeSlides() {
            if (!stage) return;
            var fixed = slides.filter(function (slide) { return slide.getAttribute("data-carousel-fixed") === "true"; })
                .sort(function (a, b) { return Number(a.getAttribute("data-carousel-order") || 99) - Number(b.getAttribute("data-carousel-order") || 99); });
            /* 50/50 opening pick: Frawgeey or Dammit Jeff leads on each visit. */
            if (fixed.length >= 2 && Math.random() < 0.5) {
                fixed = [fixed[1], fixed[0]];
            }
            var rotating = shuffle(slides.filter(function (slide) { return fixed.indexOf(slide) === -1; }));
            if (/Mac|iPhone|iPad/.test(navigator.userAgent)) {
                var macFirst = rotating.findIndex(function (slide) { return slide.getAttribute("data-video-key") === "veromarstars-rockbox-themes"; });
                if (macFirst > 0) rotating.unshift(rotating.splice(macFirst, 1)[0]);
            }
            slides = fixed.concat(rotating);
            /* A slide marked as last always closes the carousel: the Spanish
               walkthrough is the final pick for non-Spanish visitors. */
            var tail = slides.filter(function (slide) {
                return slide.getAttribute("data-carousel-last") === "true";
            });
            if (tail.length) {
                slides = slides.filter(function (slide) { return tail.indexOf(slide) === -1; }).concat(tail);
            }
            slides.forEach(function (slide, index) {
                slide.setAttribute("aria-label", "Video " + (index + 1) + " of " + slides.length);
                slide.setAttribute("aria-roledescription", "slide");
                stage.appendChild(slide);
            });
        }

        function setSlide(index) {
            current = (index + slides.length) % slides.length;
            slides.forEach(function (slide, i) {
                var active = i === current;
                slide.setAttribute("aria-hidden", active ? "false" : "true");
                slide.inert = !active;
                slide.querySelectorAll("iframe").forEach(function (iframe) {
                    var originalSrc = iframe.getAttribute("data-carousel-src") || iframe.getAttribute("src");
                    if (originalSrc) iframe.setAttribute("data-carousel-src", originalSrc);
                    if (active) {
                        if (originalSrc && iframe.getAttribute("src") === "about:blank") iframe.setAttribute("src", originalSrc);
                    } else if (iframe.getAttribute("src") !== "about:blank") {
                        iframe.setAttribute("src", "about:blank");
                    }
                });
                slide.querySelectorAll("a, button, details, iframe").forEach(function (control) {
                    control.tabIndex = active ? 0 : -1;
                });
            });
            var activeSlide = slides[current];
            if (creditLink) {
                var creditName = activeSlide.getAttribute("data-credit");
                var creditUrl = activeSlide.getAttribute("data-video-url");
                if (creditName) creditLink.textContent = creditName;
                if (creditUrl) creditLink.setAttribute("href", creditUrl);
            }
        }

        if (previous) previous.addEventListener("click", function () { setSlide(current - 1); });
        if (next) next.addEventListener("click", function () { setSlide(current + 1); });
        root.addEventListener("keydown", function (event) {
            if (event.key === "ArrowLeft") { event.preventDefault(); setSlide(current - 1); }
            if (event.key === "ArrowRight") { event.preventDefault(); setSlide(current + 1); }
        });
        arrangeSlides();
        setSlide(0);
    }

    var LUMEN_DONATE_METHODS = [
        { name: "Ko-fi", href: "https://ko-fi.com/teamslide" },
        { name: "PayPal", href: "https://paypal.me/ryanspecter282" },
        { name: "Patreon", href: "https://www.patreon.com/ryanspecter" }
    ];

    function showDialog(dialog) {
        try { dialog.showModal(); } catch (_) { dialog.setAttribute("open", ""); }
    }

    function closeDialog(dialog) {
        try { dialog.close(); } catch (_) { dialog.removeAttribute("open"); }
    }

    function openDonateDialog() {
        var donateTrigger = document.querySelector("[data-donate-open]");
        if (donateTrigger) {
            donateTrigger.click();
            return;
        }
        var donatePanel = document.getElementById("y1-donate-panel");
        if (donatePanel) {
            donatePanel.hidden = false;
            var backdrop = document.querySelector("[data-dock-backdrop]");
            if (backdrop) backdrop.hidden = false;
            return;
        }
        window.location.href = "support_devs.html#donations";
    }

    function initFeedback(root) {
        var key = "innioasis-feedback-" + (root.getAttribute("data-feedback") || location.pathname);
        var support = root.querySelector("[data-feedback-support]");
        root.querySelectorAll("button[data-feedback-value]").forEach(function (button) {
            button.addEventListener("click", function () {
                var value = button.getAttribute("data-feedback-value");
                /* Only persist the answer when the visitor has allowed it;
                   otherwise the choice lives for the rest of the visit only. */
                if (!window.INNIOASIS_PRIVACY || window.INNIOASIS_PRIVACY.allows("feedback")) {
                    try { localStorage.setItem(key, value); } catch (_) {}
                }
                root.querySelectorAll("button[data-feedback-value]").forEach(function (other) {
                    other.setAttribute("aria-pressed", other === button ? "true" : "false");
                });
                if (value === "yes") {
                    openDonateDialog();
                }
                if (support) support.hidden = value !== "no";
            });
        });
    }

    function detectPlatform() {
        var ua = navigator.userAgent || "";
        var platform = (navigator.userAgentData && navigator.userAgentData.platform) || ua;
        var p = (platform + " " + ua).toLowerCase();
        if (p.indexOf("win") !== -1) return "windows";
        if (p.indexOf("mac") !== -1 || p.indexOf("iphone") !== -1 || p.indexOf("ipad") !== -1 || p.indexOf("ipod") !== -1) return "macos";
        if (p.indexOf("linux") !== -1 || p.indexOf("x11") !== -1 || p.indexOf("android") !== -1) return "linux";
        return null;
    }

    function initPlatformReveal() {
        document.querySelectorAll("[data-platform-detect]").forEach(function (options) {
            var detected = detectPlatform();
            var cards = Array.prototype.slice.call(options.querySelectorAll("[data-platform]"));
            if (!detected || cards.length < 2) return;
            var chosen = cards.filter(function (card) { return card.getAttribute("data-platform") === detected; })[0];
            if (!chosen) return;
            /* Move the detected platform's card to the front and hide the rest,
               keeping them in the document so anchors like #macos still work. */
            options.insertBefore(chosen, options.firstChild);
            options.classList.add("lumen-download-options--single");
            cards.forEach(function (card) { if (card !== chosen) card.hidden = true; });
            var toggle = options.querySelector("[data-another-platform]");
            if (toggle) {
                toggle.hidden = false;
                toggle.addEventListener("click", function () {
                    cards.forEach(function (card) { card.hidden = false; });
                    options.classList.remove("lumen-download-options--single");
                    toggle.hidden = true;
                });
            }
        });
    }

    function copyTextFallback(text) {
        var area = document.createElement("textarea");
        area.value = text;
        area.setAttribute("readonly", "");
        area.style.position = "absolute";
        area.style.left = "-9999px";
        document.body.appendChild(area);
        area.select();
        try { document.execCommand("copy"); } catch (_) {}
        document.body.removeChild(area);
    }

    /* Download links with data-download-confirm swap their label for the
       confirm phrase once the browser starts the download (e.g. the Windows
       installer button reads "Download started"). The label is translated
       for the Night City theme when that theme is active. */
    function initDownloadConfirm() {
        document.querySelectorAll("[data-download-confirm]").forEach(function (link) {
            link.addEventListener("click", function () {
                var label = link.getAttribute("data-download-confirm");
                if (window.INNIOASIS_I18N && window.INNIOASIS_I18N.isActive && window.INNIOASIS_I18N.isActive()) {
                    label = window.INNIOASIS_I18N.translate(label);
                }
                link.textContent = label;
            });
        });
    }

    function openEdgeKeepModal() {
        var modal = document.getElementById("edge-keep-modal");
        if (!modal) return;
        modal.hidden = false;
        modal.setAttribute("aria-hidden", "false");
        var close = modal.querySelector("[data-edge-keep-close]");
        if (close) close.focus();
    }

    function closeEdgeKeepModal() {
        var modal = document.getElementById("edge-keep-modal");
        if (!modal) return;
        modal.hidden = true;
        modal.setAttribute("aria-hidden", "true");
    }

    function initEdgeKeepHelp() {
        var openers = document.querySelectorAll("[data-edge-keep-hint], .lumen-edge-help-text");
        openers.forEach(function (btn) {
            btn.addEventListener("click", function (event) {
                event.preventDefault();
                openEdgeKeepModal();
            });
        });
        var modal = document.getElementById("edge-keep-modal");
        if (modal) {
            modal.addEventListener("click", function (event) {
                if (event.target === modal) closeEdgeKeepModal();
            });
            modal.addEventListener("keydown", function (event) {
                if (event.key === "Escape" || event.key === "Esc") closeEdgeKeepModal();
            });
            var closeButton = modal.querySelector("[data-edge-keep-close]");
            if (closeButton) closeButton.addEventListener("click", closeEdgeKeepModal);
        }
    }


    function initCopyButtons() {
        document.querySelectorAll("[data-copy-target]").forEach(function (button) {
            button.addEventListener("click", function () {
                var target = document.getElementById(button.getAttribute("data-copy-target"));
                if (!target) return;
                var text = target.textContent;
                function confirm() {
                    var original = button.textContent;
                    button.textContent = "Copied!";
                    button.classList.add("is-copied");
                    setTimeout(function () {
                        button.textContent = original;
                        button.classList.remove("is-copied");
                    }, 1600);
                }
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(text).then(confirm, function () { copyTextFallback(text); confirm(); });
                } else {
                    copyTextFallback(text);
                    confirm();
                }
            });
        });
    }

    function detectSystemArchitecture() {
        var ua = navigator.userAgent || "";
        var platform = navigator.platform || "";
        var os = detectPlatform() || "unknown";

        var arch = "x86-64";
        if (/arm64|aarch64|armv8/i.test(ua) || /arm64|aarch64/i.test(platform)) {
            arch = "arm64";
        } else if (/riscv64|riscv/i.test(ua)) {
            arch = "riscv";
        }
        return { os: os, arch: arch };
    }

    async function getFullPlatform() {
        var p = detectSystemArchitecture();
        if (navigator.userAgentData && typeof navigator.userAgentData.getHighEntropyValues === "function") {
            try {
                var data = await navigator.userAgentData.getHighEntropyValues(["architecture"]);
                if (data && data.architecture) {
                    var a = data.architecture.toLowerCase();
                    if (a.includes("arm")) p.arch = "arm64";
                    else if (a.includes("x86")) p.arch = "x86-64";
                    else if (a.includes("riscv")) p.arch = "riscv";
                }
            } catch (_) {}
        }
        return p;
    }

    var portableIndexCache = {};

    function normalizePortableRepo(value) {
        var text = String(value || "").trim();
        text = text.replace(/^https?:\/\/(www\.)?github\.com\//i, "").replace(/\.git$/i, "").replace(/\/+$/, "");
        if (text.indexOf("/") === -1 || text.indexOf("/") !== text.lastIndexOf("/")) return "";
        var parts = text.split("/");
        return parts[0] && parts[1] ? text : "";
    }

    function parsePortableZips(value) {
        var raw = Array.isArray(value) ? value : String(value || "").split(/[\s,]+/);
        var seen = {};
        var repos = [];
        raw.forEach(function (entry) {
            var repo = normalizePortableRepo(entry);
            var key = repo.toLowerCase();
            if (repo && !seen[key]) {
                seen[key] = true;
                repos.push(repo);
            }
        });
        return repos;
    }

    function portablePlatformKey(platform) {
        if (!platform) return "";
        if (platform.os === "macos") return "macos";
        if (platform.os !== "windows" && platform.os !== "linux") return "";
        if (platform.arch && platform.arch !== "x86-64" && platform.arch !== "arm64") return "";
        return platform.os + (platform.arch === "arm64" ? "-arm64" : "");
    }

    function portableDownloadUrl(repo, tag, name) {
        return "https://github.com/" + repo + "/releases/download/" +
            encodeURIComponent(String(tag)) + "/" + encodeURIComponent(String(name));
    }

    function fetchPortableIndex(repo) {
        if (!portableIndexCache[repo]) {
            portableIndexCache[repo] = fetch("https://raw.githubusercontent.com/" + repo + "/main/index.json", { cache: "no-store" })
                .then(function (res) {
                    if (!res.ok) throw new Error("HTTP " + res.status);
                    return res.json();
                })
                .catch(function () { return null; });
        }
        return portableIndexCache[repo];
    }

    var portableAssetProbeCache = {};

    function githubReleaseAssetParts(url) {
        var match = /^https:\/\/github\.com\/([^/]+)\/([^/]+)\/releases\/download\/([^/]+)\/([^/?#]+)/i.exec(String(url || ""));
        if (!match) return null;
        try {
            return {
                repo: match[1] + "/" + match[2],
                tag: decodeURIComponent(match[3]),
                name: decodeURIComponent(match[4])
            };
        } catch (_) {
            return null;
        }
    }

    async function probePortableAsset(assetUrl, filename) {
        var proxy = downloadProxyUrl();
        var proxyHref = proxy ? downloadHref(assetUrl, filename) : "";
        if (proxyHref) {
            var cached = portableAssetProbeCache[proxyHref];
            if (cached !== undefined) return cached;
            try {
                var res = await fetch(proxyHref, { method: "HEAD", cache: "no-store" });
                if (res.ok) {
                    var proxied = { exists: true, proxied: true };
                    portableAssetProbeCache[proxyHref] = proxied;
                    return proxied;
                }
            } catch (_) {}
        }

        var parts = githubReleaseAssetParts(assetUrl);
        if (!parts) return null;
        try {
            var apiRes = await fetchGithubApi("https://api.github.com/repos/" + parts.repo + "/releases/tags/" + encodeURIComponent(parts.tag));
            if (apiRes.ok) {
                var release = await apiRes.json();
                var found = Array.isArray(release.assets) && release.assets.some(function (asset) {
                    return asset && String(asset.name) === parts.name;
                });
                if (found) {
                    var direct = { exists: true, proxied: false };
                    if (proxyHref) portableAssetProbeCache[proxyHref] = direct;
                    return direct;
                }
            }
        } catch (_) {}
        return null;
    }

    function findPortableAsset(index, tag, sourceAsset, platformKey) {
        if (!index || Number(index.schema) !== 1 || !Array.isArray(index.releases)) return null;
        var release = index.releases.find(function (candidate) {
            return candidate && String(candidate.tag || "") === String(tag);
        });
        if (!release || !Array.isArray(release.assets)) return null;
        var base = String(sourceAsset).replace(/\.zip$/i, "");
        var suffix = platformKey === "macos" ? "-macos.zip" :
            platformKey === "windows" ? "-windows.zip" :
            platformKey === "windows-arm64" ? "-windows-arm64.zip" :
            platformKey === "linux" ? "-linux.zip" :
            platformKey === "linux-arm64" ? "-linux-arm64.zip" : "";
        return release.assets.find(function (asset) {
            if (!asset || !asset.name || String(asset.platform || "") !== platformKey) return false;
            var declared = String(asset.source_asset || "");
            if (declared) return declared === String(sourceAsset);
            return Boolean(suffix) && String(asset.name || "") === base + suffix;
        }) || null;
    }

    async function resolvePortableZip(mirrors, releaseTag, sourceAsset) {
        var repos = parsePortableZips(mirrors);
        if (!repos.length || !releaseTag || !sourceAsset) return null;
        var platform = await getFullPlatform();
        var key = portablePlatformKey(platform);
        if (!key) return null;
        for (var i = 0; i < repos.length; i++) {
            var index = await fetchPortableIndex(repos[i]);
            var asset = findPortableAsset(index, releaseTag, sourceAsset, key);
            if (!asset) continue;
            var url = /^https:\/\/github\.com\//i.test(String(asset.url || ""))
                ? asset.url
                : portableDownloadUrl(repos[i], releaseTag, asset.name);
            var probe = await probePortableAsset(url, asset.name);
            if (!probe || !probe.exists) continue;
            return {
                url: url,
                name: asset.name,
                platform: key,
                repo: repos[i],
                proxied: Boolean(probe.proxied)
            };
        }
        return null;
    }

    var cachedUpdaterNeoAssets = null;
    async function fetchUpdaterNeoAssets() {
        if (cachedUpdaterNeoAssets !== null) return cachedUpdaterNeoAssets;
        var assets = [];
        var seenNames = {};

        function addAsset(a) {
            if (a && a.name && !seenNames[a.name]) {
                seenNames[a.name] = true;
                assets.push(a);
            }
        }

        // If running locally, check for local test assets first
        if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
            try {
                var localRes = await fetch("/api/local-portable-assets");
                if (localRes.ok) {
                    var localAssets = await localRes.json();
                    if (Array.isArray(localAssets)) {
                        localAssets.forEach(addAsset);
                    }
                }
            } catch (_) {}
        }

        // Query GitHub API for latest release
        var url = "https://api.github.com/repos/y1-community/updater-ce-neo/releases/latest";
        try {
            var res = await fetchGithubApi(url);
            if (res.ok) {
                var data = await res.json();
                if (Array.isArray(data.assets)) data.assets.forEach(addAsset);
            }
        } catch (_) {}

        // Also query recent releases to pick up platform assets uploaded across releases
        try {
            var allUrl = "https://api.github.com/repos/y1-community/updater-ce-neo/releases?per_page=10";
            var allRes = await fetchGithubApi(allUrl);
            if (allRes.ok) {
                var list = await allRes.json();
                if (Array.isArray(list)) {
                    list.forEach(function (rel) {
                        if (Array.isArray(rel.assets)) rel.assets.forEach(addAsset);
                    });
                }
            }
        } catch (_) {}

        cachedUpdaterNeoAssets = assets;
        return cachedUpdaterNeoAssets;
    }

    function findMatchingPortableAsset(assets, platform) {
        if (!assets || !assets.length) return null;
        var osPattern = platform.os;
        var arch = platform.arch;

        if (osPattern === "macos") {
            return assets.find(function (a) {
                var n = (a.name || "").toLowerCase();
                if (!n.endsWith(".zip")) return false;
                if (n.includes("mac") || n.includes("darwin") || n.includes("osx")) {
                    if (arch === "arm64" && (n.includes("arm64") || n.includes("aarch64") || n.includes("apple-silicon") || n.includes("m1"))) return true;
                    if (arch === "x86-64" && (n.includes("x86") || n.includes("intel"))) return true;
                    if (!n.includes("arm64") && !n.includes("aarch64") && !n.includes("x86") && !n.includes("intel")) return true;
                }
                return false;
            }) || null;
        }

        return assets.find(function (a) {
            var n = (a.name || "").toLowerCase();
            if (!n.endsWith(".zip")) return false;
            var norm = n.replace(/[-_.]/g, "");
            if (!norm.includes(osPattern)) return false;
            if (!norm.includes("updater") && !norm.includes("portable")) return false;

            if (arch === "arm64") {
                return norm.includes("arm64") || norm.includes("aarch64");
            } else if (arch === "riscv") {
                return norm.includes("riscv");
            } else {
                return !norm.includes("arm64") && !norm.includes("aarch64") && !norm.includes("riscv");
            }
        }) || null;
    }

    function saveAsFile(blob, filename) {
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(function () {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 1000);
    }

    function downloadProxyUrl() {
        var meta = document.querySelector('meta[name="innioasis-download-proxy"]');
        var value = meta ? (meta.getAttribute("content") || "").trim() : "";
        if (value) return value;
        if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") return "/download-proxy";
        return "";
    }

    function downloadHref(assetUrl, filename) {
        var proxy = downloadProxyUrl();
        if (!proxy) return assetUrl;
        return proxy + (proxy.indexOf("?") === -1 ? "?" : "&") +
            "url=" + encodeURIComponent(assetUrl) +
            "&filename=" + encodeURIComponent(filename || "firmware.zip");
    }

    async function streamDownload(url, onChunk) {
        var tryUrls = [];
        if (url.startsWith("/")) {
            tryUrls.push(url);
        } else {
            if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
                tryUrls.push("/download-proxy?url=" + encodeURIComponent(url));
            }
            tryUrls.push(url);
        }

        var lastError = null;
        for (var i = 0; i < tryUrls.length; i++) {
            try {
                var res = await fetch(tryUrls[i]);
                if (res.ok && res.body && typeof res.body.getReader === "function") {
                    var totalBytes = Number(res.headers.get("content-length")) || 0;
                    var reader = res.body.getReader();
                    var chunks = [];
                    var loaded = 0;
                    while (true) {
                        var chunk = await reader.read();
                        if (chunk.done) break;
                        chunks.push(chunk.value);
                        loaded += chunk.value.length;
                        onChunk(loaded, totalBytes);
                    }
                    return new Blob(chunks);
                }
            } catch (e) {
                lastError = e;
            }
        }
        throw lastError || new Error("Failed to download file");
    }

    var downloadInProgress = false;

    async function startSmartZipDownload(zipUrl, zipName, itemName, itemModel, releaseTag, portableZips) {
        if (downloadInProgress) return;
        downloadInProgress = true;

        var wrap = document.getElementById("lumen-download-progress-wrap");
        if (!wrap) {
            wrap = document.createElement("div");
            wrap.id = "lumen-download-progress-wrap";
            wrap.className = "lumen-download-progress-wrap";
            wrap.setAttribute("aria-live", "polite");
            wrap.innerHTML =
                '<div class="lumen-download-progress-box">' +
                '  <div class="lumen-download-progress-header">' +
                '    <span id="lumen-download-progress-label">Downloading…</span>' +
                '    <div class="lumen-download-progress-actions">' +
                '      <span id="lumen-download-progress-metrics">0%</span>' +
                '      <button type="button" id="lumen-download-progress-dismiss" class="lumen-download-progress-dismiss" hidden aria-label="Dismiss notification">' +
                '        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
                '          <polyline points="20 6 9 17 4 12"></polyline>' +
                '        </svg>' +
                '        <span>OK</span>' +
                '      </button>' +
                '    </div>' +
                '  </div>' +
                '  <div class="lumen-download-progress-bar-bg">' +
                '    <div id="lumen-download-progress-bar" class="lumen-download-progress-bar-fill" style="width: 0%"></div>' +
                '  </div>' +
                '</div>';
            var container = document.querySelector(".lumen-catalog-container") || document.querySelector("main") || document.body;
            container.prepend(wrap);
        }
        var label = document.getElementById("lumen-download-progress-label");
        var metrics = document.getElementById("lumen-download-progress-metrics");
        var bar = document.getElementById("lumen-download-progress-bar");
        var dismissBtn = document.getElementById("lumen-download-progress-dismiss");

        if (wrap) wrap.hidden = false;
        if (dismissBtn) dismissBtn.hidden = true;
        if (label) label.textContent = "Finding the best server location…";
        if (metrics) metrics.textContent = "";
        if (bar) bar.style.width = "1%";

        var startTime = Date.now();
        var totalBytesLoaded = 0;
        var lastMetricsUpdate = 0;

        var introDone = false;
        var introTimers = [];

        function clearIntroTimers() {
            introTimers.forEach(function (t) { clearTimeout(t); });
            introTimers = [];
        }

        var introPromise = new Promise(function (resolve) {
            var step = 1;
            function nextStep() {
                step += 1;
                if (step <= 10) {
                    if (bar) bar.style.width = step + "%";
                    if (label) {
                        if (step <= 5) label.textContent = "Finding the best server location…";
                        else label.textContent = "Building your zip…";
                    }
                    if (metrics) metrics.textContent = "";
                    var t = setTimeout(nextStep, 1000);
                    introTimers.push(t);
                } else {
                    introDone = true;
                    resolve();
                }
            }
            var t0 = setTimeout(nextStep, 1000);
            introTimers.push(t0);
        });

        var latestStreamPercent = 0;
        function updateProgress(percent) {
            latestStreamPercent = percent;
            if (!introDone) return;
            var now = Date.now();
            if (now - lastMetricsUpdate < 80 && percent < 100) return;
            lastMetricsUpdate = now;
            var elapsedSec = (now - startTime) / 1000;
            var speedMBs = elapsedSec > 0 ? (totalBytesLoaded / 1024 / 1024 / elapsedSec).toFixed(1) : "0.0";
            var overallPct = Math.min(98, Math.max(10, 10 + Math.round((percent / 100) * 88)));
            if (bar) bar.style.width = overallPct + "%";
            if (label) label.textContent = "Downloading…";
            if (metrics) metrics.textContent = overallPct + "% (" + speedMBs + " MB/s)";
        }

        introPromise.then(function () {
            if (latestStreamPercent > 0) {
                updateProgress(latestStreamPercent);
            }
        });

        var isPackagingDone = false;
        var finishTimers = [];

        function clearFinishTimers() {
            finishTimers.forEach(function (t) { clearTimeout(t); });
            finishTimers = [];
        }

        function startFinishingStage() {
            if (bar) bar.style.width = "99%";
            if (label) label.textContent = "Downloading (Finishing up)";
            if (metrics) metrics.textContent = "";

            var t1 = setTimeout(function () {
                if (isPackagingDone) return;
                if (bar) bar.style.width = "100%";
                var t2 = setTimeout(function () {
                    if (isPackagingDone) return;
                    if (label) label.textContent = "Saving to Downloads";
                }, 1000);
                finishTimers.push(t2);
            }, 10000);
            finishTimers.push(t1);
        }

        function markCompleted() {
            isPackagingDone = true;
            clearFinishTimers();
            clearIntroTimers();
            if (bar) bar.style.width = "100%";
            if (label) label.textContent = "Saved to downloads";
            if (metrics) metrics.textContent = "";
            if (dismissBtn) {
                dismissBtn.hidden = false;
                dismissBtn.onclick = function () {
                    if (wrap) wrap.hidden = true;
                    dismissBtn.hidden = true;
                    downloadInProgress = false;
                };
            }
        }

        try {
            var platform = await getFullPlatform();
            var portableZip = await resolvePortableZip(portableZips, releaseTag, zipName);
            if (portableZip) {
                clearIntroTimers();
                if (bar) bar.style.width = "100%";
                if (label) label.textContent = "Starting portable package download…";
                if (metrics) metrics.textContent = "";
                var portableLink = document.createElement("a");
                portableLink.href = portableZip.proxied ? downloadHref(portableZip.url, zipName) : portableZip.url;
                portableLink.download = zipName;
                portableLink.rel = "noopener";
                document.body.appendChild(portableLink);
                portableLink.click();
                setTimeout(function () {
                    if (portableLink.parentNode) portableLink.parentNode.removeChild(portableLink);
                    markCompleted();
                }, 1000);
                return;
            }
            var neoAssets = await fetchUpdaterNeoAssets();
            var matchingTool = findMatchingPortableAsset(neoAssets, platform);

            var romBlob = null;
            var toolBlob = null;

            if (matchingTool && window.JSZip) {
                var romLoaded = 0;
                var toolLoaded = 0;
                var romTotal = 0;
                var toolTotal = 0;

                romBlob = await streamDownload(zipUrl, function (loaded, total) {
                    romLoaded = loaded;
                    romTotal = total;
                    totalBytesLoaded = romLoaded + toolLoaded;
                    var pct = Math.round((romLoaded / (romTotal || romLoaded || 1)) * 49);
                    updateProgress(pct);
                });

                toolBlob = await streamDownload(matchingTool.browser_download_url, function (loaded, total) {
                    toolLoaded = loaded;
                    toolTotal = total;
                    totalBytesLoaded = romLoaded + toolLoaded;
                    var pct = 49 + Math.round((toolLoaded / (toolTotal || toolLoaded || 1)) * 49);
                    updateProgress(Math.min(98, pct));
                });
            } else {
                romBlob = await streamDownload(zipUrl, function (loaded, total) {
                    totalBytesLoaded = loaded;
                    var pct = total > 0 ? Math.round((loaded / total) * 98) : 49;
                    updateProgress(pct);
                });
            }

            await introPromise;
            startFinishingStage();

            if (matchingTool && window.JSZip && toolBlob) {
                if (platform.os === "windows" || platform.os === "linux") {
                    var toolZip = await window.JSZip.loadAsync(toolBlob);
                    var romZip = await window.JSZip.loadAsync(romBlob);

                    var spPrefix = "";
                    var spEntry = Object.keys(toolZip.files).find(function (f) {
                        return /(^|\/)SP_Flash_Tool\//i.test(f);
                    });
                    if (spEntry) {
                        var m = spEntry.match(/(.*?SP_Flash_Tool\/)/i);
                        if (m) spPrefix = m[1];
                    } else {
                        spPrefix = "SP_Flash_Tool/";
                    }

                    var scatterFileName = "";
                    var scatterPath = "";
                    Object.keys(romZip.files).forEach(function (f) {
                        if (!romZip.files[f].dir && /_scatter(\.txt)?$/i.test(f)) {
                            scatterPath = f;
                            scatterFileName = f.split("/").pop();
                        }
                    });
                    if (!scatterFileName) {
                        Object.keys(romZip.files).forEach(function (f) {
                            if (!romZip.files[f].dir && /scatter.*\.txt$/i.test(f)) {
                                scatterPath = f;
                                scatterFileName = f.split("/").pop();
                            }
                        });
                    }
                    if (!scatterFileName) scatterFileName = "*_Android_scatter.txt";

                    var romScatterDir = "";
                    if (scatterPath && scatterPath.indexOf("/") !== -1) {
                        romScatterDir = scatterPath.substring(0, scatterPath.lastIndexOf("/") + 1);
                    }

                    var romKeys = Object.keys(romZip.files);
                    for (var r = 0; r < romKeys.length; r++) {
                        var rKey = romKeys[r];
                        var rObj = romZip.files[rKey];
                        if (rObj.dir) continue;
                        if (/history\.ini$/i.test(rKey)) continue;

                        if (romScatterDir) {
                            if (!rKey.startsWith(romScatterDir)) continue;
                            var rel = rKey.substring(romScatterDir.length);
                            if (rel.indexOf("/") !== -1) continue; // no subfolders
                        } else {
                            if (rKey.indexOf("/") !== -1) continue; // no subfolders
                        }

                        var targetName = rKey.split("/").pop();
                        var rData = await rObj.async("uint8array");
                        toolZip.file(spPrefix + targetName, rData);
                    }

                    var customHistoryIni =
                        "[LastDAFilePath]\r\n" +
                        "lastDir=MTK_AllInOne_DA.bin\r\n\r\n" +
                        "[RecentOpenFile]\r\n" +
                        "lastDir=\r\n" +
                        "scatterHistory=" + scatterFileName + "\r\n" +
                        "authHistory=@Invalid()\r\n";
                    toolZip.file(spPrefix + "history.ini", customHistoryIni);

                    var finalBlob = await toolZip.generateAsync({ type: "blob" });
                    saveAsFile(finalBlob, zipName);
                } else if (platform.os === "macos") {
                    var macToolZip = await window.JSZip.loadAsync(toolBlob);
                    var macOutZip = new window.JSZip();

                    var macKeys = Object.keys(macToolZip.files);
                    var appBase = "";
                    for (var mk = 0; mk < macKeys.length; mk++) {
                        var k = macKeys[mk];
                        var idx = k.indexOf("Updater CE.app");
                        if (idx !== -1) {
                            appBase = k.substring(0, idx);
                            break;
                        }
                    }
                    if (!appBase) {
                        for (var mk = 0; mk < macKeys.length; mk++) {
                            var k = macKeys[mk];
                            var idx = k.indexOf(".app");
                            if (idx !== -1) {
                                var slashBefore = k.lastIndexOf("/", idx);
                                appBase = slashBefore !== -1 ? k.substring(0, slashBefore + 1) : "";
                                break;
                            }
                        }
                    }

                    for (var mk = 0; mk < macKeys.length; mk++) {
                        var mKey = macKeys[mk];
                        var mObj = macToolZip.files[mKey];
                        if (appBase ? mKey.startsWith(appBase) : (mKey.indexOf("Updater CE.app") !== -1 || mKey.indexOf(".app") !== -1)) {
                            var targetPath = appBase ? mKey.substring(appBase.length) : mKey;
                            if (mObj.dir) {
                                macOutZip.folder(targetPath);
                            } else {
                                var mData = await mObj.async("uint8array");
                                macOutZip.file(targetPath, mData);
                            }
                        }
                    }

                    var romBuffer = await romBlob.arrayBuffer();
                    macOutZip.file(zipName, romBuffer);

                    var macReadme =
                        "Innioasis Updater CE & Firmware Bundle\n" +
                        "=====================================\n\n" +
                        "Quick Start Guide for macOS:\n" +
                        "1. Drag \"Updater CE.app\" into your Applications folder.\n" +
                        "2. If macOS prevents opening the app:\n" +
                        "   Go to System Settings > Privacy & Security, scroll down to the Security section, and click \"Open Anyway\" (or \"Run Anyway\").\n" +
                        "3. Launch Updater CE from Applications, and select the included \"" + zipName + "\" firmware file when prompted.\n";
                    macOutZip.file("README.txt", macReadme);

                    var macFinalBlob = await macOutZip.generateAsync({ type: "blob" });
                    saveAsFile(macFinalBlob, zipName);
                } else {
                    saveAsFile(romBlob, zipName);
                }
            } else {
                saveAsFile(romBlob, zipName);
            }

            markCompleted();
        } catch (err) {
            clearFinishTimers();
            console.warn("Stream download encountered an issue, falling back to direct browser download:", err);
            if (label) label.textContent = "Starting direct download in browser…";
            if (bar) bar.style.width = "100%";
            if (metrics) metrics.textContent = "";
            var fallbackLink = document.createElement("a");
            fallbackLink.href = zipUrl;
            fallbackLink.download = zipName;
            document.body.appendChild(fallbackLink);
            fallbackLink.click();
            setTimeout(function () {
                document.body.removeChild(fallbackLink);
                markCompleted();
            }, 1000);
        }
    }

    function initFirmwareDirectory() {
        var table = document.getElementById("lumen-firmware-table");
        if (!table || !Array.isArray(window.INNIOASIS_FIRMWARE_CATALOG)) return;
        var model = document.getElementById("lumen-model-filter");
        var typeSelect = document.getElementById("lumen-type-filter");
        var typeField = document.getElementById("lumen-type-field");
        var software = document.getElementById("lumen-software-filter");
        var status = document.getElementById("lumen-release-status");
        var y2Switch = document.querySelector("[data-y2-switch]");
        var filterSection = document.getElementById("firmware-filters");
        var catalog = window.INNIOASIS_FIRMWARE_CATALOG;
        var releases = {};
        var releaseState = {};
        var fetchedRepos = {};
        if (window.INNIOASIS_HARDCODED_RELEASES) {
            Object.keys(window.INNIOASIS_HARDCODED_RELEASES).forEach(function (repo) {
                releases[repo] = window.INNIOASIS_HARDCODED_RELEASES[repo].slice();
                releaseState[repo] = "cached";
            });
        }
        /* URL filters: ?model=Y1|Y2 and ?software=slug preselect the dropdowns,
           so a link can point straight at one model's release list. The legacy
           #y1 / #y2 hash anchors still work for older links. */
        var searchParams = new URLSearchParams(window.location.search);
        var modelParam = (searchParams.get("model") || "").toUpperCase();
        var typeParam = (searchParams.get("type") || "").toUpperCase();
        var viewParam = (searchParams.get("view") || "software").toLowerCase();
        var heroKicker = document.querySelector("#main > header .lumen-kicker");
        var heroH1 = document.querySelector("#main > header h1");
        var heroLead = document.querySelector("#main > header .lead");
        if (viewParam === "firmware") {
            if (heroKicker) heroKicker.textContent = "Innioasis & Timmkoo Firmware Downloads";
            if (heroH1) heroH1.textContent = "Software Updates and Firmware";
            if (heroLead) heroLead.textContent = "Browse verified Original Software and community custom firmwares for the Innioasis Y1 and Y2. Download standalone packages or install directly with Updater CE. Timmkoo Q5 and Q3 install from the firmware ZIP and RAR packages Timmkoo supplies.";
        } else {
            if (heroKicker) heroKicker.textContent = "Innioasis Software Updates & Downloads";
            if (heroH1) heroH1.textContent = "Software Updates and Firmware";
            if (heroLead) heroLead.textContent = "Browse verified Original Software and community custom firmwares for the Innioasis Y1 and Y2. Download standalone packages or install directly with Updater CE. Timmkoo Q5 and Q3 install from the firmware ZIP and RAR packages Timmkoo supplies.";
        }
        /* Nightly / pre-release filter, mirroring the Updater app's
           "Show nightly builds" checkbox. Off by default: stable releases
           only. Tick it to see preview, nightly, and RC builds. The URL
           ?nightly=1 param wins so filtered views stay shareable; without
           it we reuse the same preference as the home page table. */
        var nightly = document.getElementById("lumen-nightly-filter");
        var storedNightly = false;
        if (!window.INNIOASIS_PRIVACY || window.INNIOASIS_PRIVACY.allows("nightly")) {
            try { storedNightly = localStorage.getItem("innioasis-show-nightly") === "1"; } catch (_) {}
        }
        var showNightly = (searchParams.get("nightly") || "") === "1" ? true : storedNightly;
        if (nightly) {
            nightly.checked = showNightly;
            nightly.addEventListener("change", function () {
                showNightly = nightly.checked;
                if (!window.INNIOASIS_PRIVACY || window.INNIOASIS_PRIVACY.allows("nightly")) {
                    try { localStorage.setItem("innioasis-show-nightly", showNightly ? "1" : "0"); } catch (_) {}
                }
                render();
                syncUrl();
            });
        }
        function fillModelFilter() {
            if (!model) return;
            var availableModels = [];
            catalog.forEach(function (item) {
                if (item.model && availableModels.indexOf(item.model) === -1) {
                    availableModels.push(item.model);
                }
            });
            if (availableModels.indexOf("Y1") === -1) availableModels.unshift("Y1");
            if (availableModels.indexOf("Y2") === -1) {
                var y1Idx = availableModels.indexOf("Y1");
                availableModels.splice(y1Idx + 1, 0, "Y2");
            }
            var currentVal = model.value || "Y1";
            model.innerHTML = availableModels.map(function (m) {
                return '<option value="' + escapeHtml(m) + '">' + escapeHtml(m) + '</option>';
            }).join("");
            if (availableModels.indexOf(currentVal) !== -1) {
                model.value = currentVal;
            } else {
                model.value = availableModels[0] || "Y1";
            }
        }
        fillModelFilter();

        /* Y1 shipped in two hardware revisions, and the ROMs are not
           interchangeable, so the app asks for the type alongside the model.
           Here the same choice narrows the release list and the packages
           offered for download. Type A is the default because a bare
           rom.zip is a Type A package, matching the app. */
        if (typeSelect && (typeParam === "A" || typeParam === "B")) typeSelect.value = typeParam;
        function typeForItem(item) {
            if (!item || String(item.model || "").toUpperCase() !== "Y1") return "";
            return typeSelect && typeSelect.value ? typeSelect.value.toUpperCase() : "A";
        }
        function syncTypeField() {
            if (!typeField) return;
            typeField.hidden = !(model && model.value === "Y1");
        }
        syncTypeField();

        var availableModels = Array.from(new Set(catalog.map(function (item) { return item.model; }).concat(["Y1", "Y2"])));
        var hashModel = (window.location.hash || "").slice(1).toUpperCase();
        var wantedModel = (availableModels.indexOf(modelParam) !== -1) ? modelParam : ((availableModels.indexOf(hashModel) !== -1) ? hashModel : "");
        if (model && wantedModel) {
            model.value = wantedModel;
            /* The Device type field follows the model, so a ?model=Y2 or
               #y2 link must not leave the Y1-only type control on screen. */
            syncTypeField();
            if (filterSection) window.setTimeout(function () { filterSection.scrollIntoView({ block: "start" }); }, 0);
        }
        /* ?software=slug preselects a project; the slug embeds the model (original-y1, rockbox-y2). */
        var softwareParam = (searchParams.get("software") || "").toLowerCase();
        if (softwareParam && model) {
            var paramItem = catalog.find(function (item) { return item.slug === softwareParam; });
            if (paramItem) {
                if (!wantedModel) { model.value = paramItem.model; syncTypeField(); }
                if (filterSection && !wantedModel) window.setTimeout(function () { filterSection.scrollIntoView({ block: "start" }); }, 0);
            }
        }
        /* Original Software is the default software filter for the page. */
        function originalSlug() {
            var curModel = model ? model.value : "Y1";
            var item = catalog.find(function (it) {
                return it.model === curModel && it.type === "original";
            });
            if (item) return item.slug;
            return (curModel === "Y2") ? "original-y2" : "original-y1";
        }
        if (y2Switch) {
            y2Switch.addEventListener("click", function (event) {
                event.preventDefault();
                if (model) {
                    model.value = "Y2";
                    syncTypeField();
                    fillSoftwareFilter();
                    render();
                    refreshLive();
                    if (filterSection) filterSection.scrollIntoView({ block: "start" });
                }
            });
        }

        /* The Software filter always names one project, so a single row set
           (never an "all software" view) is rendered. */
        function matchingItems() {
            var selectedModel = model ? model.value : "Y1";
            var selectedSoftware = software ? software.value : "";
            return catalog.filter(function (item) {
                return item.model === selectedModel && item.slug === selectedSoftware;
            });
        }

        /* The Software filter always names one project, so only that project's
           repos are fetched. Shared repos (stock, Solar, JJ Launcher) hold
           releases for both models, so per-item matching still applies. */
        function activeRepos() {
            return Array.from(new Set(matchingItems().map(function (item) { return item.repo; })));
        }

        /* A release belongs to an item only when it actually carries that
           model's package. Shared repos (stock, Solar, JJ Launcher) hold
           releases for both models, so a Y2-only release must not appear
           under the Y1 row or the other way round. Returns null when the
           repo has releases but none fit the selected model. */
        function releasesForItem(item) {
            var repoReleases = releases[item.repo];
            if (!Array.isArray(repoReleases) || !repoReleases.length) return null;
            var matching = matchingReleases(repoReleases, item, typeForItem(item));
            return matching.length ? matching : null;
        }

        /* Apply the nightly filter on top of the model-matched releases.
           Unchecked: stable releases only. Checked: every release, with
           stable builds still included alongside previews. Returns null
           when releases exist but the current filter hides them all. */
        function visibleReleases(item) {
            var all = releasesForItem(item);
            if (!all) return null;
            if (!showNightly) all = all.filter(function (release) { return !isNightly(release); });
            if (!all.length) return null;
            /* Newest version first: timestamp/semver order with the published
               date as tiebreaker, mirroring the Updater app. GitHub's own
               order is creation-based, which scrambles same-day releases. */
            all = all.slice().sort(function (a, b) {
                return compareReleaseKeys(releaseSortKey(b), releaseSortKey(a));
            });
            return all;
        }

        /* Release details list only the zips that belong to the selected
           item's model, so a combined release never offers a rom_y2.zip
           under the Y1 row or a rom.zip under the Y2 row. */
        function releaseDetails(release, item, type) {
            if (!release) return '';
            var names = packageNamesFor(item, type);
            var assets = zipAssets(release);
            var links = [];
            assets.forEach(function (asset) {
                var aName = (asset.name || "").toLowerCase();
                var assetType = zipType(aName);
                /* Never offer the other hardware revision's ROM. */
                if (type && assetType && assetType !== type) return;
                if (names.indexOf(aName) !== -1 || aName === (item.packageName || "").toLowerCase() || aName.indexOf(item.model.toLowerCase()) !== -1) {
                    var entry = MODEL_ZIPS.find(function (candidate) { return candidate.name === aName; });
                    var label = entry ? entry.label : (assetType ? item.model + " · Type " + assetType : item.model + " package");
                    var title = entry ? entry.title : ("For " + item.model + " players" + (assetType ? " · Type " + assetType : ""));
                    links.push('<li><a class="lumen-download-link" href="' + escapeHtml(asset.browser_download_url) + '" download="' + escapeHtml(asset.name) + '" title="' + escapeHtml(title) + '">' + escapeHtml(asset.name) + ' <span class="lumen-meta">' + escapeHtml(label) + '</span></a></li>');
                }
            });
            var assetLinks = links.length ? links.join("") : '<li>No ZIP asset was found in this release.</li>';
            return '<details class="lumen-release-details"><summary>Release details and zip</summary><p><strong>' + escapeHtml(release.name || release.tag_name || "Public release") + '</strong>' + (release.published_at ? ' · ' + escapeHtml(release.published_at.slice(0, 10)) : '') + '</p><ul>' + assetLinks + '</ul></details>';
        }

        function resolveFirmwareIcon(release, item) {
            if (release && Array.isArray(release.assets)) {
                var updaterAsset = release.assets.find(function (a) {
                    return a.name && /^updater\.(png|webp|jpe?g|svg)$/i.test(a.name.trim());
                });
                if (updaterAsset && updaterAsset.browser_download_url) {
                    return '<span class="lumen-firmware-icon-box" style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:9px;background:#141721;border:1px solid rgba(255,255,255,0.14);box-shadow:0 1px 4px rgba(0,0,0,0.3);overflow:hidden;flex-shrink:0;"><img src="' + escapeHtml(updaterAsset.browser_download_url) + '" width="28" height="28" style="width:28px;height:28px;object-fit:cover;display:block;" alt="" aria-hidden="true"></span>';
                }
            }
            if (item && item.icon) {
                return '<span class="lumen-firmware-icon-box" style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:9px;background:#141721;border:1px solid rgba(255,255,255,0.14);box-shadow:0 1px 4px rgba(0,0,0,0.3);overflow:hidden;flex-shrink:0;"><img src="' + escapeHtml(item.icon) + '" width="28" height="28" style="width:28px;height:28px;object-fit:cover;display:block;" alt="" aria-hidden="true"></span>';
            }
            return '<span class="lumen-firmware-icon-box" style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:9px;background:#141721;border:1px solid rgba(255,255,255,0.14);box-shadow:0 1px 4px rgba(0,0,0,0.3);color:var(--lumen-accent,#6366f1);flex-shrink:0;"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg></span>';
        }

        /* A version written in a release title: an optional leading v, a
           dotted numeric core, and an optional suffix such as -beta.2,
           +build.7 or hotfix4. Only the token at the start or the end of
           the title is a title version; punctuation may sit either side. */
        var TITLE_VERSION = "[vV]?\\d+\\.\\d+(?:\\.\\d+)?(?:[-+][0-9A-Za-z][0-9A-Za-z.+-]*|[0-9]*[A-Za-z]+\\d*)?";
        var TITLE_VERSION_START = new RegExp("^(" + TITLE_VERSION + ")(?=$|[\\s:;,()\\[\\]\\u2013\\u2014-])");
        var TITLE_VERSION_END = new RegExp("(?:^|[\\s:;,()\\[\\]\\u2013\\u2014-])(" + TITLE_VERSION + ")(?=[.,;:!?'\")\\]\\u201d\\u2019]*$)");
        var TITLE_VERSION_MIDDLE = new RegExp("(?:^|\\s)(" + TITLE_VERSION + ")(?=$|\\s)");

        /* The semantic version the release title announces. Titles like
           "V2.5", "Rockbox Y2 Beta v0.2.0" or "JJ Launcher ROM
           v0.11.6hotfix4" name the build directly, so the title is read
           before the tag. A version in the middle of the title is used only
           when neither end carries one. */
        function versionFromTitle(title) {
            var text = String(title || "").trim();
            if (!text) return "";
            var startMatch = text.match(TITLE_VERSION_START);
            if (startMatch) return startMatch[1];
            var endMatch = text.match(TITLE_VERSION_END);
            if (endMatch) return endMatch[1];
            var middleMatch = text.match(TITLE_VERSION_MIDDLE);
            return middleMatch ? middleMatch[1] : "";
        }

        /* List a release by the semantic version its GitHub title carries at
           the start or end, and parse the tag for a version only when the
           title has none to show. */
        function extractReleaseVersion(release, item) {
            if (!release) return item ? item.name : "Public release";
            var name = (release.name || "").trim();
            var tag = (release.tag_name || "").trim();
            if (name) {
                var titleVersion = versionFromTitle(name);
                if (titleVersion) return titleVersion;
            }
            return tag ? displayVersion(tag) : (name || "Public release");
        }

        function releaseRows(release, item, state) {
            /* The Release column label with icon and semver detection. */
            var iconHtml = resolveFirmwareIcon(release, item);
            var versionLabel = release ? extractReleaseVersion(release, item)
                : state === "failed" ? item.name
                : state === "empty" ? "No public releases"
                : state === "nomatch" ? "No release with " + item.packageName
                : state === "filtered-stable" ? "No stable release yet"
                : "Checking public releases";
            var versionHtml = (state === "failed" && !release)
                ? "<strong>" + escapeHtml(versionLabel) + "</strong>"
                : '<span class="lumen-version-pill" style="font-weight:700;font-size:0.95rem;">' + escapeHtml(versionLabel) + '</span>';
            var hint = release ? '' : state === "filtered-stable" ? '<span class="lumen-muted-inline">Tick the nightly-builds option to see previews</span>' : '';
            var guideUrl = 'guide.html?model=' + encodeURIComponent(item.model) + '&software=' + encodeURIComponent(item.slug);
            var updater = '<a class="lumen-updater-button lumen-updater-button--table" href="' + guideUrl + '" aria-label="Get ' + escapeHtml(item.name) + ' for ' + escapeHtml(item.model) + ' on Innioasis Updater"><img src="mtkclient/gui/images/icon.png" width="28" height="28" alt=""><span><strong>Get it on Updater</strong><small>with guided install</small></span></a>';

            var zipBtn = '';
            if (release) {
                var rowType = typeForItem(item);
                var names = packageNamesFor(item, rowType);
                var assets = zipAssets(release);
                var primaryAsset = null;
                for (var z = 0; z < MODEL_ZIPS.length; z++) {
                    var entry = MODEL_ZIPS[z];
                    if (rowType && entry.type && entry.type !== rowType) continue;
                    if (names.indexOf(entry.name) !== -1) {
                        var found = assets.find(function (a) { return a.name && a.name.toLowerCase() === entry.name; });
                        if (found) { primaryAsset = found; break; }
                    }
                }
                if (!primaryAsset && assets.length) {
                    primaryAsset = assets.find(function (a) {
                        var an = (a.name || "").toLowerCase();
                        var assetType = zipType(an);
                        if (rowType && assetType && assetType !== rowType) return false;
                        return names.indexOf(an) !== -1 || an === (item.packageName || "").toLowerCase() || an.indexOf(item.model.toLowerCase()) !== -1;
                    }) || (rowType ? null : assets[0]);
                }
                if (primaryAsset) {
                    zipBtn = ' <button type="button" class="lumen-zip-download-button lumen-zip-download-button--table" data-zip-url="' + escapeHtml(primaryAsset.browser_download_url) + '" data-zip-name="' + escapeHtml(primaryAsset.name) + '" data-release-tag="' + escapeHtml(release.tag_name || release.name || "release") + '" data-item-name="' + escapeHtml(item.name) + '" data-item-model="' + escapeHtml(item.model) + '" data-portable-zips="' + escapeHtml(item.portable_zips || "") + '" aria-label="Download standalone ' + escapeHtml(primaryAsset.name) + ' ZIP package">' +
                        '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 16h12M10 3v9m0 0l-3.5-3.5M10 12l3.5-3.5"/></svg>' +
                        '<span><strong>Download ZIP</strong><small>standalone package</small></span>' +
                        '</button>';
                }
            }

            /* The Software name is not shown here: the software filter above
               already sets the project, so every row belongs to it. */
            /* The reader goes to our own release-notes page. Never fall back
               to a source-host URL when a release tag is missing. */
            var releaseNotesUrl = docsReleaseNotesHref(item, release && release.tag_name ? release.tag_name : "") ||
                siteReleaseNotesHref(item, "");            return '<tr data-release-tag="' + escapeHtml(release && (release.tag_name || release.name) || "") + '">' +
                '<td><div style="display:flex;align-items:center;gap:10px;">' + iconHtml + '<div>' + versionHtml + (release && release.published_at ? '<br><span class="lumen-meta">' + escapeHtml(release.published_at.slice(0, 10)) + '</span>' : '') + '</div></div></td>' +
                /* The package is not shown: the Release details expander lists
                   the rom zips this release is packaged in. */
                '<td><div class="lumen-actions">' + updater + zipBtn + hint + '</div>' + releaseDetails(release, item, typeForItem(item)) + '</td>' +
                '<td><a class="lumen-release-notes-link" href="' + releaseNotesUrl + '" aria-label="Read the release notes for ' + escapeHtml(release && release.tag_name ? release.tag_name : item.name) + '">' +                '<svg viewBox="0 0 20 20" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 3h6l3 3v11H6z"/><path d="M12 3v3h3"/><path d="M8.5 10h5M8.5 13h5"/></svg></a></td>' +
                '</tr>';
        }

        function render() {
            var items = matchingItems();
            if (!items.length) {
                table.innerHTML = '<tr><td colspan="3">No software project is currently listed for this model and filter. Try another project or check the project release pages.</td></tr>';
                return;
            }
            var rows = [];
            items.forEach(function (item) {
                var itemReleases = visibleReleases(item);
                var modelReleases = releasesForItem(item);
                if (itemReleases) {
                    itemReleases.forEach(function (release) { rows.push(releaseRows(release, item, "loaded")); });
                } else if (modelReleases) {
                    /* The repo has model-matched releases, but the stable
                       filter hides them all: no stable build exists yet.
                       In nightly mode every release is shown, so this
                       state can only happen when the filter is off. */
                    rows.push(releaseRows(null, item, "filtered-stable"));
                } else {
                    var repoReleases = releases[item.repo];
                    var repoLoaded = Array.isArray(repoReleases) && repoReleases.length > 0;
                    rows.push(releaseRows(null, item, repoLoaded ? "nomatch" : (releaseState[item.repo] || "loading")));
                }
            });
            table.innerHTML = rows.join("");
            /* Model, type, software and release are all known here: hand them
               to the notice card so it can re-rank and surface what applies. */
            syncNoticeContext();
        }

        /* ---- Contextual community notices ----
           This screen is the one place that knows which player, hardware type,
           software project and release the visitor is looking at, so it feeds
           that context to the shared notice card in nav.js. The card itself
           shows one notice at a time and rotates through the eligible ones. */
        function currentReleaseVersion(item) {
            var visible = item ? visibleReleases(item) : null;
            if (!visible || !visible.length) return "";
            var latest = visible[0];
            return (latest && (latest.tag_name || latest.name)) || "";
        }
        function syncNoticeContext(releaseTag) {
            var item = matchingItems()[0] || null;
            /* An empty dimension is dropped by the notice engine, so a stale
               repo or version can never keep a notice alive. */
            var patch = {
                model: model ? model.value : "",
                deviceType: typeForItem(item),
                software: item ? item.name : "",
                repo: item ? item.repo : "",
                version: releaseTag || currentReleaseVersion(item)
            };
            var notices = window.InnioasisNotices;
            if (notices && typeof notices.setContext === "function") {
                notices.setContext(patch);
            } else {
                /* nav.js may not have run yet; it reads this on mount. */
                window.INNIOASIS_NOTICE_CONTEXT = patch;
            }
        }

        function fillSoftwareFilter() {
            if (!software) return;
            var previous = software.value;
            var items = catalog.filter(function (item) { return !model || item.model === model.value; });
            var options = Array.from(new Map(items.map(function (item) { return [item.slug, item.name]; })).entries()).sort(function (a, b) { return a[1].localeCompare(b[1]); });
            software.innerHTML = options.map(function (entry) { return '<option value="' + escapeHtml(entry[0]) + '">' + escapeHtml(entry[1]) + '</option>'; }).join("");
            var requested = softwareParam && options.some(function (entry) { return entry[0] === softwareParam; }) ? softwareParam : previous;
            software.value = options.some(function (entry) { return entry[0] === requested; }) ? requested : originalSlug();
            if (y2Switch) {
                var selectedModel = model ? model.value : "Y1";
                if (selectedModel === "Y2") {
                    y2Switch.setAttribute("aria-hidden", "true");
                    y2Switch.setAttribute("tabindex", "-1");
                    y2Switch.textContent = "Y2";
                } else {
                    y2Switch.removeAttribute("aria-hidden");
                    y2Switch.removeAttribute("tabindex");
                    y2Switch.textContent = "Y2 ready";
                }
            }
        }


        function refreshLive() {
            var repos = activeRepos();
            var selectedItem = matchingItems()[0] || null;
            var softwareName = selectedItem ? selectedItem.name : (software && software.options && software.options.length ? software.options[software.selectedIndex].textContent : "");
            var pending = repos.filter(function (repo) { return !fetchedRepos[repo]; });
            var hasCached = repos.some(function (repo) { return releases[repo] && releases[repo].length > 0; });
            if (status) {
                if (hasCached) {
                    status.textContent = "Showing " + softwareName + " releases from catalogue · Checking for live updates…";
                } else if (pending.length) {
                    status.textContent = "Loading " + softwareName + " releases…";
                }
            }
            if (table) table.setAttribute("aria-busy", "true");
            pending.forEach(function (repo) {
                if (!releases[repo] || !releases[repo].length) {
                    releaseState[repo] = "loading";
                }
            });
            Promise.all(pending.map(function (repo) {
                return fetchAllReleases(repo, 1, [])
                    .then(function (result) {
                        fetchedRepos[repo] = true;
                        if (result && Array.isArray(result.releases) && result.releases.length > 0) {
                            releases[repo] = result.releases;
                            releaseState[repo] = result.complete ? "loaded" : "partial";
                            render();
                        } else if (!releases[repo] || !releases[repo].length) {
                            releaseState[repo] = "failed";
                        }
                    })
                    .catch(function () {
                        fetchedRepos[repo] = true;
                        if (!releases[repo] || !releases[repo].length) {
                            releaseState[repo] = "failed";
                        }
                    });
            })).then(function () {
                render();
                if (table) table.setAttribute("aria-busy", "false");
                var liveLoaded = repos.filter(function (repo) { return releaseState[repo] === "loaded" || releaseState[repo] === "partial"; }).length;
                var cachedActive = repos.filter(function (repo) { return releaseState[repo] === "cached"; }).length;
                if (status) {
                    if (liveLoaded) {
                        status.textContent = "All public " + softwareName + " releases loaded.";
                    } else if (cachedActive) {
                        status.textContent = "Showing " + softwareName + " releases from the catalogue archive.";
                    } else {
                        status.textContent = "Release information is not available right now. The project links remain available.";
                    }
                }
            });
        }

        /* Keep the address bar shareable: mirror the chosen filters back
           into the URL whenever the user changes them. */
        function syncUrl() {
            if (!model) return;
            var params = new URLSearchParams(window.location.search);
            if (model.value) params.set("model", model.value);
            else params.delete("model");
            if (software && software.value) params.set("software", software.value);
            else params.delete("software");
            if (typeSelect && model && model.value === "Y1") params.set("type", typeSelect.value);
            else params.delete("type");
            if (showNightly) params.set("nightly", "1");
            else params.delete("nightly");
            var qs = params.toString();
            try { history.replaceState(null, "", "?" + qs + window.location.hash); } catch (_) {}
        }

        table.addEventListener("click", function (event) {
            var btn = event.target.closest(".lumen-zip-download-button");
            if (!btn) return;
            event.preventDefault();
            var zipUrl = btn.getAttribute("data-zip-url");
            var zipName = btn.getAttribute("data-zip-name") || "rom.zip";
            var itemName = btn.getAttribute("data-item-name") || "Software";
            var itemModel = btn.getAttribute("data-item-model") || "Y1";
            var releaseTag = btn.getAttribute("data-release-tag") || "release";
            var portableZips = btn.getAttribute("data-portable-zips") || "";
            startSmartZipDownload(zipUrl, zipName, itemName, itemModel, releaseTag, portableZips);
        });

        /* Opening a release's details means the visitor is reading about that
           exact version, so version-targeted notices apply from then on. */
        table.addEventListener("click", function (event) {
            var summary = event.target.closest ? event.target.closest(".lumen-release-details > summary") : null;
            if (!summary) return;
            var row = summary.closest("tr");
            var tag = row ? row.getAttribute("data-release-tag") : "";
            if (tag) syncNoticeContext(tag);
        });

        /* Opening a release's details means the visitor is reading about that
           exact version, so version-targeted notices apply from then on. */
        table.addEventListener("click", function (event) {
            var summary = event.target.closest ? event.target.closest(".lumen-release-details > summary") : null;
            if (!summary) return;
            var row = summary.closest("tr");
            var tag = row ? row.getAttribute("data-release-tag") : "";
            if (tag) syncNoticeContext(tag);
        });

        if (model) model.addEventListener("change", function () { syncTypeField(); fillSoftwareFilter(); render(); refreshLive(); syncUrl(); });
        if (typeSelect) typeSelect.addEventListener("change", function () { render(); refreshLive(); syncUrl(); });
        /* A new Software choice has its own repos to fetch (shared model repos
           are no longer pre-loaded), so the live feed refreshes here too. */
        if (software) software.addEventListener("change", function () { render(); refreshLive(); syncUrl(); });
        fillSoftwareFilter();
        render();
        refreshLive();
    }

    /* Compact "what can I install" table for the homepage. One row per
       Software, with a button per model that opens the matching release
       list in the full directory. Names come straight from the catalog
       (the Updater catalogue), so no release feeds are fetched here. */
    function initHomeFirmware() {
        var body = document.getElementById("lumen-home-firmware-table");
        if (!body || !Array.isArray(window.INNIOASIS_FIRMWARE_CATALOG)) return;
        var catalog = window.INNIOASIS_FIRMWARE_CATALOG;
        var groups = [];
        var seen = {};
        catalog.forEach(function (item) {
            if (!seen[item.name]) {
                seen[item.name] = { name: item.name, items: [] };
                groups.push(seen[item.name]);
            }
            seen[item.name].items.push(item);
        });
        if (!groups.length) {
            body.innerHTML = '<tr><td colspan="2">No software is currently listed for the Y1 or Y2. Check back soon.</td></tr>';
            return;
        }
        body.innerHTML = groups.map(function (group) {
            var first = group.items[0];
            /* One button per model; each opens the model-matched release
               list in the full firmware directory. */
            var releaseButtons = group.items.map(function (item) {
                return '<a class="lumen-button lumen-button--model" href="firmware.html?model=' + encodeURIComponent(item.model) + '&software=' + encodeURIComponent(item.slug) + '" aria-label="' + escapeHtml(item.model) + ' releases">' + escapeHtml(item.model) + '</a>';
            }).join(" ");
            var benefitLink = first.benefits ? '<a class="lumen-benefit-link" href="' + escapeHtml(first.benefits) + '">Why ' + escapeHtml(group.name) + '?</a>' : '';
            var guideHref = first.seoPage || first.guide || ('guide.html?model=' + encodeURIComponent(first.model) + '&software=' + encodeURIComponent(first.slug));
            return "<tr>" +
                '<td><a class="lumen-project-link" href="' + escapeHtml(guideHref) + '"><strong>' + escapeHtml(group.name) + "</strong></a>" + (benefitLink ? '<br>' + benefitLink : '') + "</td>" +
                "<td>" + releaseButtons + "</td>" +
                "</tr>";
        }).join("");
    }

    function initPersonalisedGuide() {
        var section = document.getElementById("personalised-steps");
        if (!section) return;
        var params = new URLSearchParams(window.location.search);
        var model = (params.get("model") || "").toUpperCase();
        var slug = params.get("software") || "";
        if (!model || !slug) return;
        var item = null;
        if (Array.isArray(window.INNIOASIS_FIRMWARE_CATALOG)) {
            item = window.INNIOASIS_FIRMWARE_CATALOG.find(function (entry) { return entry.model === model && entry.slug === slug; }) || null;
        }
        if (!item) return;
        var restoring = /original/.test(item.slug);
        var name = item.name;
        var heading = restoring ? "Restore Original Software on your " + model : "Install " + name + " on your " + model;
        var kicker = section.querySelector("[data-personalised-kicker]");
        if (kicker) kicker.textContent = restoring ? "Restore · " + model : name + " · " + model;
        var headingEl = section.querySelector("[data-personalised-heading]");
        if (headingEl) headingEl.textContent = heading;
        var lead = section.querySelector("[data-personalised-lead]");
        if (lead) lead.textContent = restoring
            ? "Follow these steps in Updater. The player you want to restore is the " + model + "."
            : "Follow these steps in Updater. You have the " + model + " and want " + name + " on it.";
        var steps = [
            "Open Updater on your computer, or install it first with the button below.",
            "In Device Model, select " + model + ".",
            restoring ? "In Software, select Original Software." : "In Software, select " + name + ".",
            "Select a stable release shown for the " + model + ".",
            "Click Install / Restore, then power off the player.",
            "Connect the player only when Updater says it is ready.",
            "Wait for the success message, then disconnect and start the player."
        ];
        var list = section.querySelector("[data-personalised-steps]");
        if (list) {
            list.innerHTML = "";
            steps.forEach(function (text) {
                var li = document.createElement("li");
                li.textContent = text;
                list.appendChild(li);
            });
            if (item.post_install || item.post_install2) {
                var postLi = document.createElement("li");
                postLi.setAttribute("data-post-install-step", "1");
                postLi.setAttribute("data-slug", item.slug);
                var titleText = "Complete post-install setup";
                var descText = "Some features on your player require post-install setup. Follow along with our post-install guide to finish setting up your player.";
                var buttonText = "Post-Install Setup Guide \u2192";
                if (item.slug === "reborn-y2linux-y2" || /reborn|y2linux/i.test(item.name)) {
                    titleText = "Complete final setup for Wi-Fi, FM radio & Bluetooth";
                    descText = "There are some final setup steps needed to get Wi-Fi, FM radio, and Bluetooth working on your Y2 using system.img. Follow along with our post-install guide to finish setting up your player.";
                } else if (item.slug === "rondo-y1" || /rondo/i.test(item.name)) {
                    titleText = "Complete post-install setup";
                    descText = "Follow along with the setup guide to complete post-install setup on your Y1.";
                    buttonText = "View Guide";
                }
                postLi.innerHTML = '<div style="display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;width:100%;">' +
                    '<div style="flex:1 1 240px;min-width:0;">' +
                    '<strong>' + escapeHtml(titleText) + '</strong>' +
                    '<p style="margin:4px 0 0;">' + escapeHtml(descText) + '</p>' +
                    '</div>' +
                    '<div style="flex-shrink:0;display:flex;gap:8px;flex-wrap:wrap;">' +
                    '<a class="lumen-button lumen-button--primary" href="' + escapeHtml(docsPostInstallHref(item.post_install, item)) + '" data-post-install-link data-slug="' + escapeHtml(item.slug || '') + '">' + escapeHtml(buttonText) + '</a>' +
                    (docsReleaseNotesHref(item) ? '<a class="lumen-button" href="' + escapeHtml(docsReleaseNotesHref(item)) + '">Release notes</a>' : '') +
                    '</div>' +
                    '</div>';
                list.appendChild(postLi);
            }
        }
        var postInstallEl = section.querySelector("[data-personalised-post-install]");
        if (postInstallEl) {
            postInstallEl.remove();
        }
        var note = section.querySelector("[data-personalised-note]");
        if (note) note.textContent = restoring
            ? "That puts the " + model + " back on its original software. The download and computer setup sections below still apply if you need them."
            : "That is the whole " + name + " install on the " + model + ". The download and computer setup sections below still apply if you need them.";
        /* The generic firmware guide page fills its copy with the project
           name and model from the URL, so any listed firmware gets a
           readable tutorial even without a dedicated page. */
        document.querySelectorAll("[data-personalised-software]").forEach(function (el) { el.textContent = name; });
        document.querySelectorAll("[data-personalised-model]").forEach(function (el) { el.textContent = model; });
        var missing = document.querySelector("[data-personalised-missing]");
        if (missing) missing.hidden = true;
        document.querySelectorAll("[data-personalised-reveal]").forEach(function (el) { el.hidden = false; });
        var guideLink = section.querySelector("[data-personalised-guide]");
        var dedicatedGuide = item.guide || item.seoPage || "";
        if (guideLink) {
            if (dedicatedGuide) {
                guideLink.href = dedicatedGuide;
                guideLink.textContent = restoring ? "Open the full " + model + " restore tutorial" : "Open the full " + name + " " + model + " tutorial";
            } else {
                /* No dedicated page yet: this URL-driven page is the guide. */
                guideLink.hidden = true;
            }
        }
        var headerKicker = document.querySelector("#main > header .lumen-kicker");
        if (headerKicker) headerKicker.textContent = (restoring ? "Restore " : "Install ") + name + " on " + model + " · beginner route";
        var h1 = document.querySelector("#main > header h1");
        if (h1) h1.textContent = heading + ".";
        document.title = heading + " | Innioasis Updater";
        section.hidden = false;
        if (!window.location.hash) {
            window.setTimeout(function () { section.scrollIntoView({ block: "start" }); }, 0);
        }
    }

    /* The "Software guides by model" cards, built from the catalog so any
       firmware in the Updater manifest gets a button. Projects with a
       dedicated guide link to it; everything else falls back to the generic
       URL-driven guide page (firmware-guide.html?model=…&software=…). */
    function initSoftwareGuideLinks() {
        if (!Array.isArray(window.INNIOASIS_FIRMWARE_CATALOG)) return;
        var catalog = window.INNIOASIS_FIRMWARE_CATALOG;
        ["Y1", "Y2"].forEach(function (model) {
            var slot = document.querySelector('[data-guides-model="' + model + '"]');
            if (!slot) return;
            /* Keep the restore path (Original Software) at the end of the
               card, matching the hand-written ordering it replaces. */
            var items = catalog.filter(function (item) { return item.model === model; })
                .sort(function (a, b) {
                    return (/original/.test(a.slug) ? 1 : 0) - (/original/.test(b.slug) ? 1 : 0);
                });
            slot.innerHTML = items.map(function (item) {
                var dedicated = item.guide || item.seoPage || "";
                var href = dedicated || ("firmware-guide.html?model=" + encodeURIComponent(item.model) + "&software=" + encodeURIComponent(item.slug));
                return '<a class="lumen-button" href="' + escapeHtml(href) + '">' + escapeHtml(item.name) + '</a>';
            }).join("");
        });
    }

    /* Tap / hover hint modals (.lumen-tip). A toggle button shows a small
       popover on hover (mouse) and on tap (click), so dotfile tips work
       on both pointer and touch. Hover is bound to pointerenter only for
       pointerType mouse: on touch, the browser fires a synthetic mouseenter
       before click, which would open the popover and then the click would
       toggle it straight back closed. Escape and a click elsewhere close
       the popover. */
    function initLumenTips() {
        document.querySelectorAll("[data-lumen-tip]").forEach(function (tip) {
            var toggle = tip.querySelector(".lumen-tip-toggle");
            var popover = tip.querySelector(".lumen-tip-popover");
            if (!toggle || !popover) return;
            var open = false;
            var openedBy = null;
            var hideTimer = null;
            function show(source) {
                clearTimeout(hideTimer);
                open = true;
                openedBy = source;
                popover.hidden = false;
                toggle.setAttribute("aria-expanded", "true");
            }
            function hide() {
                clearTimeout(hideTimer);
                open = false;
                openedBy = null;
                popover.hidden = true;
                toggle.setAttribute("aria-expanded", "false");
            }
            function scheduleHide() {
                clearTimeout(hideTimer);
                hideTimer = setTimeout(hide, 120);
            }
            function onPointerEnter(event) {
                if (event.pointerType === "mouse") show("pointer");
            }
            function onPointerLeave(event) {
                if (event.pointerType === "mouse") scheduleHide();
            }
            toggle.addEventListener("pointerenter", onPointerEnter);
            toggle.addEventListener("pointerleave", onPointerLeave);
            toggle.addEventListener("focus", function () { show("focus"); });
            toggle.addEventListener("blur", scheduleHide);
            /* The click toggles only when the popover was itself opened by a
               previous click; a hover- or focus-opened popover stays open on
               the first click so touch taps (which fire focus + click) and
               mouse clicks never flash open then shut. */
            toggle.addEventListener("click", function (event) {
                event.stopPropagation();
                if (open && openedBy === "click") hide(); else show("click");
            });
            popover.addEventListener("pointerenter", onPointerEnter);
            popover.addEventListener("pointerleave", onPointerLeave);
            document.addEventListener("click", function (event) {
                if (open && !tip.contains(event.target)) hide();
            });
            document.addEventListener("keydown", function (event) {
                if (event.key === "Escape" && open) hide();
            });
        });
    }

    /* ------------------------------------------------------------------
       Docs reader. A firmware's post_install can point at a Markdown file
       in the project's own repository; those open in post_install.html (our
       own styled page) instead of a bare file view. The viewer is loaded on
       demand so every guide page gets it without its own script tag. */    var docsViewerPromise = null;
    function ensureDocsViewer() {
        if (window.InnioasisDocs) return Promise.resolve(window.InnioasisDocs);
        if (docsViewerPromise) return docsViewerPromise;
        docsViewerPromise = new Promise(function (resolve) {
            var path = window.location.pathname || "";
            var prefix = /\/guides\/|\/notices\/|\/Troubleshooting\//.test(path) ? "../" : "";
            var script = document.createElement("script");
            script.src = prefix + "docs-viewer.js?v=20261107silo";            script.async = true;
            script.onload = function () { resolve(window.InnioasisDocs || null); };
            script.onerror = function () { resolve(null); };
            document.head.appendChild(script);
        });
        return docsViewerPromise;
    }
    function docsPostInstallHref(value, item) {
        var D = window.InnioasisDocs;
        if (!D || typeof D.postInstallHref !== "function") return value || "";
        /* post_install2 is the page a project shows visitors who keep donation
           appeals on; without it this is the ordinary post_install value. */
        var target = typeof D.postInstallTarget === "function" ? D.postInstallTarget(item, value) : (value || "");
        if (!target) return "";
        return D.postInstallHref(target, {            software: item && item.slug ? item.slug : "",
            model: item && item.model ? item.model : "",
            repo: item && item.repo ? item.repo : "",
            name: item && item.name ? item.name : ""
        });
    }
    function siteReleaseNotesHref(item, tag) {
        if (!item || !item.slug) return "release_notes.html";
        var path = window.location.pathname || "";
        var prefix = /\/guides\/|\/notices\/|\/Troubleshooting\//.test(path) ? "../" : "";
        var D = window.InnioasisDocs;
        /* Always the parser page: the generated copies are for search engines
           and are never linked from the site. */
        if (D && typeof D.releaseNotesHref === "function") {
            return prefix + D.releaseNotesHref({
                repo: item.repo || "", tag: tag || "", model: item.model || "",
                software: item.slug, name: item.name || ""
            });
        }
        var query = "software=" + encodeURIComponent(item.slug) +
            (item.repo ? "&repo=" + encodeURIComponent(item.repo) : "") +
            (tag ? "&tag=" + encodeURIComponent(tag) : "");
        return prefix + "release_notes.html?" + query;
    }

    function docsReleaseNotesHref(item, tag) {
        return siteReleaseNotesHref(item, tag);    }

    function initGuidePostInstall() {
        if (!Array.isArray(window.INNIOASIS_FIRMWARE_CATALOG)) return;
        var catalog = window.INNIOASIS_FIRMWARE_CATALOG;

        document.querySelectorAll("[data-post-install-link]").forEach(function (link) {
            var slug = link.getAttribute("data-slug");
            if (!slug) {
                var parentStep = link.closest("[data-post-install-step]");
                if (parentStep) slug = parentStep.getAttribute("data-slug");
            }
            if (slug) {
                var item = catalog.find(function (entry) { return entry.slug === slug; });
                if (item && item.post_install) {
                    link.href = docsPostInstallHref(item.post_install, item);
                }
            }
        });

        var stepsList = document.querySelector(".lumen-guide .lumen-steps:not([data-personalised-steps])");
        if (stepsList) {
            var currentPath = window.location.pathname;
            var matchedItem = catalog.find(function (entry) {
                if (entry.guide && (currentPath.endsWith(entry.guide) || currentPath.endsWith("/" + entry.guide.replace(/^guides\//, "")))) {
                    return true;
                }
                if (entry.seoPage && currentPath.endsWith(entry.seoPage)) {
                    return true;
                }
                return false;
            });
            if (!matchedItem) {
                var ctaLink = document.querySelector('a[href*="software="]');
                if (ctaLink) {
                    var match = ctaLink.href.match(/software=([^&]+)/);
                    if (match) {
                        var slug = decodeURIComponent(match[1]);
                        matchedItem = catalog.find(function (entry) { return entry.slug === slug; });
                    }
                }
            }
            if (matchedItem && (matchedItem.post_install || matchedItem.post_install2)) {
                var existingStep = stepsList.querySelector("[data-post-install-step]");
                if (!existingStep) {
                    var postLi = document.createElement("li");
                    postLi.setAttribute("data-post-install-step", "1");
                    postLi.setAttribute("data-slug", matchedItem.slug);
                    var titleText = "Complete post-install setup";
                    var descText = "Some features on your player require post-install setup. Follow along with our post-install guide to finish setting up your player.";
                    var buttonText = "Post-Install Setup Guide \u2192";
                    if (matchedItem.slug === "reborn-y2linux-y2" || /reborn|y2linux/i.test(matchedItem.name)) {
                        titleText = "Complete final setup for Wi-Fi, FM radio & Bluetooth";
                        descText = "There are some final setup steps needed to get Wi-Fi, FM radio, and Bluetooth working on your Y2 using system.img. Follow along with our post-install guide to finish setting up your player.";
                    } else if (matchedItem.slug === "rondo-y1" || /rondo/i.test(matchedItem.name)) {
                        titleText = "Complete post-install setup";
                        descText = "Follow along with the setup guide to complete post-install setup on your Y1.";
                        buttonText = "View Guide";
                    }
                    postLi.innerHTML = '<div style="display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;width:100%;">' +
                        '<div style="flex:1 1 240px;min-width:0;">' +
                        '<strong>' + escapeHtml(titleText) + '</strong>' +
                        '<p style="margin:4px 0 0;">' + escapeHtml(descText) + '</p>' +
                        '</div>' +
                        '<div style="flex-shrink:0;display:flex;gap:8px;flex-wrap:wrap;">' +
                        '<a class="lumen-button lumen-button--primary" href="' + escapeHtml(docsPostInstallHref(matchedItem.post_install, matchedItem)) + '" data-post-install-link data-slug="' + escapeHtml(matchedItem.slug) + '">' + escapeHtml(buttonText) + '</a>' +
                        (docsReleaseNotesHref(matchedItem) ? '<a class="lumen-button" href="' + escapeHtml(docsReleaseNotesHref(matchedItem)) + '">Release notes</a>' : '') +
                        '</div>' +
                        '</div>';
                    stepsList.appendChild(postLi);
                } else {
                    var existingLink = existingStep.querySelector("a[data-post-install-link]");
                    if (existingLink && (matchedItem.post_install || matchedItem.post_install2)) {                        existingLink.href = docsPostInstallHref(matchedItem.post_install, matchedItem);
                    }
                }
            }
        }
    }

    function loadAndMergeManifest() {
        var manifestPath = "slidia_manifest.xml";
        if (window.location.pathname.indexOf("/guides/") !== -1 || window.location.pathname.indexOf("/guides") !== -1) {
            manifestPath = "../slidia_manifest.xml";
        }
        return fetch(manifestPath, { cache: "no-cache" })
            .then(function (res) {
                if (!res.ok) throw new Error("HTTP " + res.status);
                return res.text();
            })
            .then(function (xmlText) {
                var parser = new DOMParser();
                var doc = parser.parseFromString(xmlText, "application/xml");
                if (doc.querySelector("parsererror")) return;
                var packages = doc.querySelectorAll("package");
                if (!packages.length || !Array.isArray(window.INNIOASIS_FIRMWARE_CATALOG)) return;
                var catalog = window.INNIOASIS_FIRMWARE_CATALOG;
                packages.forEach(function (pkg) {
                    var name = (pkg.getAttribute("name") || "").trim();
                    var repo = (pkg.getAttribute("repo") || "").trim();
                    var device = (pkg.getAttribute("device") || "").toUpperCase().trim();
                    var icon = (pkg.getAttribute("icon") || "").trim();
                    var postInstall = (pkg.getAttribute("post_install") || "").trim();
                    var postInstall2 = (pkg.getAttribute("post_install2") || "").trim();
                    var portableZips = (pkg.getAttribute("portable_zips") || "").trim();                    var handler = pkg.getAttribute("handler") || "";
                    if (!name || /please update/i.test(name)) return;
                    if (handler && handler !== "Custom Firmware") return;

                    var match = catalog.find(function (item) {
                        return (item.repo && repo && item.repo.toLowerCase() === repo.toLowerCase() && item.model === device) ||
                               (item.name.toLowerCase() === name.toLowerCase() && item.model === device);
                    });
                    if (match) {
                        if (icon && !match.icon) match.icon = icon;
                        /* The manifest is what Updater CE actually reads, so its
                           repository wins: it is the one whose releases the
                           firmware list and release pages must show. */
                        if (repo) match.repo = repo;
                        if (postInstall) match.post_install = postInstall;
                        if (postInstall2) match.post_install2 = postInstall2;
                        if (portableZips) match.portable_zips = portableZips;                    } else if (name && device) {
                        var slug = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
                        catalog.push({
                            name: name,
                            model: device,
                            slug: slug + "-" + device.toLowerCase(),
                            repo: repo,
                            icon: icon,
                            post_install: postInstall,
                            post_install2: postInstall2,
                            portable_zips: portableZips,                            packageName: "rom.zip",
                            description: "Community firmware package for the " + device + "."
                        });
                    }
                });
                initHomeFirmware();
            })
            .catch(function () {});
    }

    document.addEventListener("DOMContentLoaded", function () {
        /* Start the docs viewer early: guide pages rewrite their post-install
           links to it as soon as the manifest is merged. */
        ensureDocsViewer();
        /* Before the carousel caches each iframe src, so the player language
           sticks when a slide is shown again. */
        applyEmbedLanguage();
        document.querySelectorAll("[data-lumen-carousel]").forEach(initCarousel);
        document.querySelectorAll("[data-lumen-feedback]").forEach(initFeedback);
        initPlatformReveal();
        initCopyButtons();
        initDownloadConfirm();
        initEdgeKeepHelp();
        initLumenTips();

        loadAndMergeManifest().then(function () {
            initHomeFirmware();
            initPersonalisedGuide();
            initGuidePostInstall();
            initSoftwareGuideLinks();
            return loadGithubTokens();
        }).catch(function () {
            initHomeFirmware();
            initPersonalisedGuide();
            initGuidePostInstall();
            initSoftwareGuideLinks();
            return loadGithubTokens();
        }).then(function () {
            initFirmwareDirectory();
        }).catch(function () {
            initFirmwareDirectory();
        });
    });
})();
