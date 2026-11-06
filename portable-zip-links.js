/**
 * Portable packages for the archive's download links.
 *
 * A page may link at a project's own rom ZIP
 * (github.com/<owner>/<repo>/releases/download/<tag>/rom.zip) or at one of the
 * mirror's per-OS builds. On Windows and Linux (x86-64 and arm64) and on macOS
 * the y1-community mirror publishes a repackaged build of that same ZIP with
 * the matching flash tool beside it. When the mirror release exists for the
 * same tag and lists the file built for this OS and architecture, the click is
 * sent to the mirror file instead.
 *
 * Android, 32-bit x86, PowerPC and unknown systems keep the project's own
 * release, because the portable packages cannot run there. Type B packages
 * (rom_type_b.zip and its 240p/360p variants) follow exactly the same rule.
 *
 * The file is saved under the release's own name (rom.zip, rom_y2.zip,
 * rom_type_b.zip) rather than the mirror's OS-prefixed name. A cross-origin
 * response cannot be renamed by the download attribute, so when the
 * same-origin download proxy is available the bytes are streamed with real
 * progress and then written to Downloads under the release's name. Otherwise
 * the browser downloads the portable file directly; no page ever assembles a
 * ZIP itself.
 */
(function () {
    "use strict";

    var INDEX_URL = "https://raw.githubusercontent.com/%s/%s/index.json";
    var RELEASE_TAG = "https://api.github.com/repos/%s/releases/tags/%s";
    var ASSET_RE = /^https?:\/\/github\.com\/([^/]+)\/([^/]+)\/releases\/download\/([^/]+)\/([^/?#]+)/i;
    var PLATFORM_SUFFIX = {
        macos: "-macos.zip",
        windows: "-windows.zip",
        "windows-arm64": "-windows-arm64.zip",
        linux: "-linux.zip",
        "linux-arm64": "-linux-arm64.zip"
    };
    var PLATFORM_LABELS = {
        macos: "macOS",
        windows: "Windows",
        "windows-arm64": "Windows on ARM",
        linux: "Linux",
        "linux-arm64": "Linux on ARM"
    };

    /* Deferred scripts still expose currentScript, so the manifest is always
       fetched from the site root even on pages nested two folders deep. */
    var SELF = document.currentScript && document.currentScript.src ? document.currentScript.src : "";
    var SITE_ROOT = SELF ? SELF.replace(/[^/]*$/, "") : "";

    var indexCache = {};
    var releaseCache = {};
    var manifestCache = null;
    var platformCache = null;
    var proxyCache = {};

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

    function isFirmwareZip(name) {
        var value = String(name || "");
        return /\.zip$/i.test(value) && !/sources?|legal-info/i.test(value);
    }

    /* The mirror publishes x86-64 and arm64 builds plus one universal macOS
       package. Anything 32-bit, PowerPC or unrecognised keeps the original
       download rather than being handed a build it cannot run. Android is
       excluded: its download is the original rom zip (or the Type B build),
       because the portable package wraps a desktop flash tool. */
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
            indexCache[repo] = (async function () {
                /* main first, then master for the older mirrors. */
                var branches = ["main", "master"];
                for (var i = 0; i < branches.length; i++) {
                    try {
                        var res = await fetch(INDEX_URL.replace("%s", repo).replace("%s", branches[i]), { cache: "no-store" });
                        if (res.ok) return await res.json();
                    } catch (_) {}
                }
                return null;
            })();
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
        return entry && entry.suffix ? String(entry.suffix) : (PLATFORM_SUFFIX[key] || "");
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

    /* Confirm the candidate against the mirror's own release before the
       reader is sent there, and use the URL the API publishes so the tag and
       file name cannot drift. If api.github.com is rate-limited or blocked,
       the mirror's index.json (which carries the URL and byte size) is the
       fallback, so a usable portable package is not dropped for a 60/hour
       limit. */
    async function verifiedUrl(candidate, declaredSize) {
        var parts = parseAssetUrl(candidate);
        if (!parts) return "";
        var release = await fetchRelease(parts.repo, parts.tag);
        if (!release || !Array.isArray(release.assets)) {
            return Number(declaredSize) > 0 ? candidate : "";
        }
        var asset = release.assets.find(function (entry) {
            return entry && String(entry.name) === parts.name;
        });
        if (!asset || !asset.browser_download_url) return "";
        /* A listed asset can still be an empty placeholder while the mirror
           uploads it. An empty file is worse than the project's own release. */
        if (!(Number(asset.size) > 0)) return "";
        return asset.browser_download_url;
    }

    function parseMirrors(value) {
        return String(value || "").split(/[\s,]+/)
            .map(function (entry) { return entry.trim(); })
            .filter(function (entry) { return entry.indexOf("/") !== -1; });
    }

    /* Returns { url, platform, name } or null when this computer has no
       portable build for the release. */
    async function resolve(sourceUrl, mirrorsValue, tag, sourceName) {
        var parts = parseAssetUrl(sourceUrl);
        if (!parts) return null;
        var key = await platformKey();
        if (!key) return null;
        var repos = parseMirrors(mirrorsValue);
        if (!repos.length) {
            var map = await mirrorMap();
            repos = map[String(parts.repo).toLowerCase()] || [];
        }
        for (var i = 0; i < repos.length; i += 1) {
            var index = await fetchIndex(repos[i]);
            var asset = findAsset(index, tag || parts.tag, sourceName || parts.name, key);
            if (!asset || !asset.name) continue;
            var candidate = /^https:\/\/github\.com\//i.test(String(asset.url || ""))
                ? String(asset.url)
                : "https://github.com/" + repos[i] + "/releases/download/" +
                  encodeURIComponent(tag || parts.tag) + "/" + encodeURIComponent(asset.name);
            var url = await verifiedUrl(candidate, asset.size);
            if (url) return { url: url, platform: key, name: asset.name };
        }
        return null;
    }

    function withTimeout(promise, ms, fallback) {
        return Promise.race([
            promise,
            new Promise(function (done) { setTimeout(function () { done(fallback); }, ms); })
        ]);
    }

    function proxyUrl() {
        var meta = document.querySelector('meta[name="innioasis-download-proxy"]');
        var value = meta ? (meta.getAttribute("content") || "").trim() : "";
        if (value) return value;
        if (/^https?:$/.test(window.location.protocol)) return "/download-proxy";
        return "";
    }

    function proxyHref(assetUrl, filename) {
        var proxy = proxyUrl();
        if (!proxy) return Promise.resolve("");
        var href = proxy + (proxy.indexOf("?") === -1 ? "?" : "&") +
            "url=" + encodeURIComponent(assetUrl) +
            "&filename=" + encodeURIComponent(filename || "firmware.zip");
        if (proxyCache[href] === undefined) {
            proxyCache[href] = fetch(href, { method: "HEAD", cache: "no-store" })
                .then(function (res) { return Boolean(res.ok); })
                .catch(function () { return false; });
        }
        return proxyCache[href].then(function (usable) { return usable ? href : ""; });
    }

    /* --------------------------------------------------------------- toast */

    var toast = null;
    var toastTimer = null;

    function ensureToast() {
        if (toast && document.body.contains(toast)) return toast;
        toast = document.createElement("div");
        toast.id = "innioasis-download-toast";
        toast.setAttribute("role", "status");
        toast.setAttribute("aria-live", "polite");
        toast.innerHTML =
            '<div data-toast-box style="position:fixed;right:18px;bottom:18px;z-index:2147483000;width:min(340px,calc(100vw - 36px));padding:14px 15px;border:1px solid #4f46e5;border-radius:12px;background:#171a23;color:#f8fafc;box-shadow:0 12px 34px rgba(0,0,0,.38);font:14px/1.4 system-ui,-apple-system,Segoe UI,sans-serif;">' +
            '  <div style="display:flex;justify-content:space-between;gap:10px;align-items:start;">' +
            '    <strong data-toast-label style="font-size:.9rem;">Preparing your download…</strong>' +
            '    <button type="button" data-toast-dismiss aria-label="Dismiss" style="display:none;border:1px solid #4f46e5;background:#4f46e5;color:#fff;border-radius:99px;padding:2px 9px;font-size:.75rem;cursor:pointer;">OK</button>' +
            '  </div>' +
            '  <div style="margin:9px 0 6px;height:7px;border-radius:99px;background:#2c3140;overflow:hidden;">' +
            '    <div data-toast-bar style="width:2%;height:100%;border-radius:99px;background:#6366f1;transition:width .15s ease-out;"></div>' +
            '  </div>' +
            '  <div data-toast-meta style="font-size:.76rem;color:#a5b0c2;"></div>' +
            '</div>';
        document.body.appendChild(toast);
        var dismiss = toast.querySelector("[data-toast-dismiss]");
        dismiss.addEventListener("click", function () { toast.style.display = "none"; });
        return toast;
    }

    function toastNodes() {
        var root = ensureToast();
        return {
            root: root,
            label: root.querySelector("[data-toast-label]"),
            bar: root.querySelector("[data-toast-bar]"),
            meta: root.querySelector("[data-toast-meta]"),
            dismiss: root.querySelector("[data-toast-dismiss]")
        };
    }

    function toastProgress(loaded, total) {
        if (!toast) return;
        var nodes = toastNodes();
        var pct = total > 0 ? Math.min(99, Math.round((loaded / total) * 100)) : 0;
        nodes.bar.style.width = pct + "%";
        nodes.label.textContent = "Downloading…";
        nodes.meta.textContent = total > 0
            ? pct + "% · " + (loaded / 1024 / 1024).toFixed(1) + " of " + (total / 1024 / 1024).toFixed(1) + " MB"
            : (loaded / 1024 / 1024).toFixed(1) + " MB";
    }

    function toastDone(saveName, osLabel, streamed) {
        if (!toast) return;
        var nodes = toastNodes();
        nodes.root.style.display = "block";
        nodes.bar.style.width = "100%";
        nodes.label.textContent = streamed ? "Saved to Downloads as " + saveName : "Download started";
        nodes.meta.textContent = streamed
            ? (osLabel ? "Portable package for " + osLabel : "")
            : (osLabel ? "Portable package for " + osLabel : "Check your Downloads folder");
        nodes.dismiss.style.display = "inline-block";
        if (toastTimer) clearTimeout(toastTimer);
    }

    function startToast() {
        var nodes = toastNodes();
        nodes.root.style.display = "block";
        nodes.label.textContent = "Preparing your download…";
        nodes.bar.style.width = "2%";
        nodes.meta.textContent = "";
        nodes.dismiss.style.display = "none";
    }

    function osLabel(key) {
        return PLATFORM_LABELS[key] || "";
    }

    async function streamToDownloads(href, saveName, label) {
        var res = await fetch(href, { cache: "no-store" });
        if (!res.ok || !res.body) throw new Error("HTTP " + res.status);
        var total = Number(res.headers.get("Content-Length") || 0);
        var reader = res.body.getReader();
        var chunks = [];
        var loaded = 0;
        for (;;) {
            var step = await reader.read();
            if (step.done) break;
            chunks.push(step.value);
            loaded += step.value.length;
            toastProgress(loaded, total);
        }
        toastProgress(loaded, total || loaded);
        var nodes = toastNodes();
        nodes.label.textContent = "Saving to Downloads…";
        var blob = new Blob(chunks, { type: "application/octet-stream" });
        var objectUrl = URL.createObjectURL(blob);
        var link = document.createElement("a");
        link.href = objectUrl;
        link.download = saveName || "rom.zip";
        document.body.appendChild(link);
        link.click();
        setTimeout(function () {
            if (link.parentNode) link.parentNode.removeChild(link);
            URL.revokeObjectURL(objectUrl);
        }, 2000);
        toastDone(saveName || "rom.zip", label, true);
    }

    function directDownload(href, saveName, label) {
        var link = document.createElement("a");
        link.href = href;
        if (saveName) link.download = saveName;
        link.rel = "noopener";
        document.body.appendChild(link);
        link.click();
        setTimeout(function () {
            if (link.parentNode) link.parentNode.removeChild(link);
        }, 1000);
        toastDone(saveName, label, false);
    }

    async function downloadLink(link) {
        var href = link.getAttribute("href") || "";
        var sourceUrl = link.getAttribute("data-zip-url") || href;
        var parts = parseAssetUrl(sourceUrl);
        var saveName = link.getAttribute("data-zip-name") || (parts ? parts.name : "");
        var explicitPlatform = link.getAttribute("data-platform") || "";
        if (!isFirmwareZip(saveName)) return false;

        startToast();
        var label = osLabel(explicitPlatform);
        var target = null;
        if (explicitPlatform && parseAssetUrl(href)) {
            /* The reader picked a named OS build; honour that link, but save
               it under the release's own name. */
            target = { url: href, platform: explicitPlatform };
        } else {
            target = await withTimeout(
                resolve(sourceUrl, link.getAttribute("data-portable-zips") || "", link.getAttribute("data-release-tag") || "", saveName),
                9000,
                null
            );
            if (target) label = osLabel(target.platform);
        }
        if (!target) target = { url: href, platform: "" };

        var proxied = await proxyHref(target.url, saveName);
        if (proxied) {
            try {
                await streamToDownloads(proxied, saveName, label);
                return true;
            } catch (_) {
                /* Fall through to the browser's own download. */
            }
        }
        directDownload(target.url || href, saveName, label);
        return true;
    }

    document.addEventListener("click", function (event) {
        if (event.defaultPrevented || event.button !== 0) return;
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        var link = event.target && event.target.closest ? event.target.closest("a[href]") : null;
        if (!link || link.hasAttribute("data-save-as") || link.target) return;

        var href = link.getAttribute("href") || "";
        var declaredSource = link.getAttribute("data-zip-url") || "";
        var declaredName = link.getAttribute("data-zip-name") || "";
        var explicitPlatform = link.getAttribute("data-platform") || "";
        var parts = parseAssetUrl(declaredSource || href);
        if (!parts) return;
        if (!isFirmwareZip(declaredName || parts.name)) return;

        event.preventDefault();
        downloadLink(link).catch(function () {
            window.location.href = href;
        });
    }, false);

    /* Exposed so a page script or a test can ask the same question the click
       handler asks, without navigating. */
    window.InnioasisPortableZip = {
        resolve: resolve,
        platform: platformKey,
        download: downloadLink
    };
})();
