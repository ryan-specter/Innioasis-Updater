/**
 * Innioasis docs viewer.
 *
 * Renders third-party Markdown (a project's install instructions, a GitHub
 * release body, a README) inside the Innioasis site instead of sending the
 * reader to a bare GitHub page. Two pages use it:
 *
 *   post_install.html   verbatim post-install instructions
 *   release_notes.html  the notes for one firmware release, with our own
 *                       download buttons and the "Get it in Updater" guide
 *
 * scripts/generate_doc_pages.py writes static equivalents of both for every
 * release in slidia_manifest.xml using the same rules (source resolution,
 * relative link rewriting, Markdown features), so a crawler or an answer
 * engine sees the same document the browser renders.
 */
(function (global) {
  "use strict";

  /* Where repackaged portable ZIPs are published. The Python generator reads
     this same constant out of this file, so the site and the static pages
     never disagree about the mirror. Override with PORTABLE_MIRROR_REPO in
     the workflow if the mirror ever moves. */
  var PORTABLE_MIRROR_REPO = "y1-community/innioasis-portable-packages";

  var SITE = "https://innioasis.app";
  var MARKDOWN_EXT = /\.(md|markdown|mdown|mkd|mdx)$/i;
  var GITHUB_HOSTS = /^(www\.)?github\.com$/i;

  var GUIDE_URL = SITE + "/guide.html";

  /* Sources a project README tends to cite instead of our own guide: an old
     download page, the support page, a driver mirror and a handful of Drive
     files. They all point at the guide, which carries the current packages
     and drivers. */
  var SUPERSEDED_LINKS = [
    /^https?:\/\/(?:www\.)?innioasis\.com\/pages\/(?:download|support-center|support\/download-[a-z0-9-]+)\/?(?:[?#].*)?$/i,
    /^https?:\/\/(?:www\.)?wooabc\.cn\/download\/MTPUSBDriverForWin10\.rar(?:[?#].*)?$/i,
    /^https?:\/\/drive\.google\.com\/file\/d\/(?:1gJHvXXhqf9Q2fjxdy6-atErvdiyOHToh|1LJMk1cQAQkQtPszzjZTGB3--23YjdRvc|1gPFGBCdANa7atpGxKBPuXus0t-EI_byW|1mMvuX95VE_pKihilj6BSXdrZ6Y8UDxjF)\b/i
  ];

  function supersededGuideLink(href) {
    var url = String(href || "").trim();
    if (!url) return "";
    for (var i = 0; i < SUPERSEDED_LINKS.length; i += 1) {
      if (SUPERSEDED_LINKS[i].test(url)) return GUIDE_URL;
    }
    return "";
  }

  /* A link whose visible text is the address itself should not keep showing
     the retired address once the target moves. */
  /* The same addresses can appear as visible text, either inside a link or
     on their own. Code samples keep whatever they already show. */
  var SUPERSEDED_TEXT = /(^|[^"'=\w])((?:(?:https?:\/\/)?(?:www\.)?innioasis\.com\/pages\/(?:download|support-center|support\/download-[a-z0-9-]+))|(?:(?:https?:\/\/)?(?:www\.)?wooabc\.cn\/download\/MTPUSBDriverForWin10\.rar)|(?:(?:https?:\/\/)?drive\.google\.com\/file\/d\/(?:1gJHvXXhqf9Q2fjxdy6-atErvdiyOHToh|1LJMk1cQAQkQtPszzjZTGB3--23YjdRvc|1gPFGBCdANa7atpGxKBPuXus0t-EI_byW|1mMvuX95VE_pKihilj6BSXdrZ6Y8UDxjF)\b))/gi;
  var ANCHOR_OR_CODE = /(<a\b[^>]*>[\s\S]*?<\/a>|<(?:pre|code)\b[^>]*>[\s\S]*?<\/(?:pre|code)>)/i;

  function linkifySupersededText(html) {
    var parts = String(html || "").split(new RegExp(ANCHOR_OR_CODE.source, "gi"));
    for (var i = 0; i < parts.length; i += 1) {
      var part = parts[i];
      if (!part) continue;
      if (/^<a\b/i.test(part)) {
        parts[i] = part.replace(SUPERSEDED_TEXT, function (_match, lead) { return lead + GUIDE_URL; });
      } else if (/^<(?:pre|code)\b/i.test(part)) {
        continue;
      } else {
        parts[i] = part.replace(SUPERSEDED_TEXT, function (_match, lead) {
          return lead + '<a href="' + GUIDE_URL + '">' + GUIDE_URL + "</a>";
        });
      }
    }
    return parts.join("");
  }

  function linkTextIsUrl(label, href) {
    var text = String(label || "").replace(/<[^>]*>/g, "")
      .replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#39;/g, "'").trim();
    if (!/^https?:\/\//i.test(text)) return false;
    var left = text.replace(/[?#].*$/, "").replace(/\/+$/, "").toLowerCase();
    var right = String(href || "").replace(/[?#].*$/, "").replace(/\/+$/, "").toLowerCase();
    return left === right;
  }

  /* ------------------------------------------------------------------ *
   * Source resolution
   * ------------------------------------------------------------------ */

  function splitPath(pathname) {
    return String(pathname || "").split("/").filter(function (p) { return p !== ""; });
  }

  function decode(segment) {
    try { return decodeURIComponent(segment); } catch (_) { return segment; }
  }

  function dirname(path) {
    var parts = String(path || "").split("/");
    parts.pop();
    return parts.join("/");
  }

  function joinUrl(base, rel) {
    try { return new URL(rel, base).href; } catch (_) { return rel; }
  }

  /**
   * Work out what a post_install (or any doc) URL really points at.
   * Returns null when the link is not a Markdown document we can import —
   * the caller then just opens it normally, which is the right behaviour for
   * a plain website, a PDF, or a forum thread.
   */
  function parseSource(input, base) {
    if (!input) return null;
    var raw = String(input).trim();
    if (!raw) return null;
    var url;
    try {
      url = new URL(raw, base || (typeof location !== "undefined" ? location.href : SITE + "/"));
    } catch (_) {
      return null;
    }
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;

    var host = url.hostname.toLowerCase();
    var seg = splitPath(url.pathname);
    var anchor = url.hash || "";

    /* GitHub blob / raw: the shape a post_install link usually takes. */
    if (GITHUB_HOSTS.test(host) && seg.length >= 4 && (seg[2] === "blob" || seg[2] === "raw")) {
      var ref = decode(seg[3]);
      var rest = seg.slice(4).map(decode);
      /* A ref may itself contain slashes (refs/heads/main). Peel those off
         until the remaining path looks like the file. */
      while (rest.length > 1 && !MARKDOWN_EXT.test(rest[rest.length - 1]) && /^refs$/i.test(ref)) {
        ref += "/" + rest.shift();
      }
      var path = rest.join("/");
      if (!path || !MARKDOWN_EXT.test(path)) return null;
      return githubSource(decode(seg[0]) + "/" + decode(seg[1]), ref, path, url.href, anchor);
    }

    if (host === "raw.githubusercontent.com" && seg.length >= 4) {
      var rawRepo = decode(seg[0]) + "/" + decode(seg[1]);
      var rawRef = decode(seg[2]);
      var rawRest = seg.slice(3).map(decode);
      while (rawRest.length > 1 && /^refs$/i.test(rawRef) && /^(heads|tags)$/i.test(rawRest[0])) {
        rawRef += "/" + rawRest.shift() + "/" + rawRest.shift();
      }
      var rawPath = rawRest.join("/");
      if (!rawPath || !MARKDOWN_EXT.test(rawPath)) return null;
      var rawSource = githubSource(rawRepo, rawRef, rawPath, url.href, anchor);
      rawSource.kind = "github-raw";
      rawSource.rawUrl = url.href.split("#")[0];
      return rawSource;
    }

    /* Gists: always Markdown-ish, and the raw endpoint is CORS-friendly. */
    if (host === "gist.github.com" && seg.length >= 2) {
      var gistId = decode(seg[1]);
      if (seg[0] === "raw") return null;
      var gistRaw = "https://gist.githubusercontent.com/" + decode(seg[0]) + "/" + gistId + "/raw";
      return {
        kind: "gist",
        host: "GitHub Gist",
        repo: "",
        ref: "",
        path: seg.slice(2).map(decode).join("/") || gistId,
        sourceUrl: url.href,
        rawUrl: gistRaw,
        blobUrl: url.href.split("#")[0],
        dirRaw: gistRaw + "/",
        dirBlob: url.href.split("#")[0],
        fileLabel: seg.slice(2).join("/") || "gist",
        anchor: anchor
      };
    }

    if (host === "gist.githubusercontent.com" && seg.length >= 3) {
      return {
        kind: "gist",
        host: "GitHub Gist",
        repo: "",
        ref: "",
        path: seg.slice(2).map(decode).join("/"),
        sourceUrl: url.href,
        rawUrl: url.href.split("#")[0],
        blobUrl: url.href.split("#")[0],
        dirRaw: url.href.split("#")[0],
        dirBlob: url.href.split("#")[0],
        fileLabel: seg[seg.length - 1],
        anchor: anchor
      };
    }

    /* GitLab: /group/project/-/blob/<ref>/<path> and /-/raw/. */
    if (host === "gitlab.com" && seg.indexOf("-") !== -1) {
      var dash = seg.indexOf("-");
      if (seg[dash + 1] === "blob" || seg[dash + 1] === "raw") {
        var glRepo = seg.slice(0, dash).map(decode).join("/");
        var glRef = decode(seg[dash + 2] || "");
        var glPath = seg.slice(dash + 3).map(decode).join("/");
        if (!glPath || !MARKDOWN_EXT.test(glPath)) return null;
        var glRaw = "https://gitlab.com/" + glRepo + "/-/raw/" + glRef + "/" + glPath;
        return {
          kind: "gitlab",
          host: "GitLab",
          repo: glRepo,
          ref: glRef,
          path: glPath,
          sourceUrl: url.href,
          rawUrl: glRaw,
          blobUrl: "https://gitlab.com/" + glRepo + "/-/blob/" + glRef + "/" + glPath,
          dirRaw: "https://gitlab.com/" + glRepo + "/-/raw/" + glRef + "/" + dirname(glPath) + "/",
          dirBlob: "https://gitlab.com/" + glRepo + "/-/blob/" + glRef + "/" + dirname(glPath) + "/",
          fileLabel: glPath.split("/").pop(),
          anchor: anchor
        };
      }
    }

    /* Codeberg / Forgejo: /owner/repo/raw/branch/<ref>/<path>. */
    if ((host === "codeberg.org" || host === "git.disroot.org") && seg.length >= 5 && seg[2] === "raw") {
      var cbRepo = decode(seg[0]) + "/" + decode(seg[1]);
      var cbRef = decode(seg[4] || seg[3]);
      var cbPath = seg.slice(5).map(decode).join("/");
      if (!cbPath || !MARKDOWN_EXT.test(cbPath)) return null;
      var cbRaw = "https://" + host + "/" + cbRepo + "/raw/branch/" + cbRef + "/" + cbPath;
      return {
        kind: "codeberg",
        host: "Codeberg",
        repo: cbRepo,
        ref: cbRef,
        path: cbPath,
        sourceUrl: url.href,
        rawUrl: cbRaw,
        blobUrl: "https://" + host + "/" + cbRepo + "/src/branch/" + cbRef + "/" + cbPath,
        dirRaw: "https://" + host + "/" + cbRepo + "/raw/branch/" + cbRef + "/" + dirname(cbPath) + "/",
        dirBlob: "https://" + host + "/" + cbRepo + "/src/branch/" + cbRef + "/" + dirname(cbPath) + "/",
        fileLabel: cbPath.split("/").pop(),
        anchor: anchor
      };
    }

    /* A Markdown file attached to a release, the shape a project uses for
       notes it does not put in the release body:
       /owner/repo/releases/download/<tag>/<file>.md */
    if (GITHUB_HOSTS.test(host) && seg.length >= 6 && seg[2] === "releases" && seg[3] === "download") {
      var assetTag = decode(seg[4]);
      var assetFile = seg.slice(5).map(decode).join("/");
      if (!assetFile || !MARKDOWN_EXT.test(assetFile)) return null;
      var assetRepo = decode(seg[0]) + "/" + decode(seg[1]);
      var assetPage = "https://github.com/" + assetRepo + "/releases/tag/" + encodeURIComponent(assetTag);
      return {
        kind: "github-asset",
        host: "GitHub",
        repo: assetRepo,
        ref: assetTag,
        path: assetFile,
        sourceUrl: url.href,
        rawUrl: url.href.split("#")[0],
        blobUrl: assetPage,
        dirRaw: url.href.split("#")[0].replace(/[^/]*$/, ""),
        dirBlob: assetPage,
        fileLabel: assetFile,
        anchor: anchor
      };
    }

    /* Anything that ends in a Markdown extension is fetched as-is. This
       covers project sites (jarvissax.github.io/rondo/README.md), raw
       documentation servers, and our own same-origin docs. */
    if (MARKDOWN_EXT.test(url.pathname)) {
      var directDir = url.href.split("#")[0].replace(/[^/]*$/, "");
      return {
        kind: "direct",
        host: url.hostname,
        repo: "",
        ref: "",
        path: decode(url.pathname.split("/").pop() || ""),
        sourceUrl: url.href,
        rawUrl: url.href.split("#")[0],
        blobUrl: url.href.split("#")[0],
        dirRaw: directDir,
        dirBlob: directDir,
        fileLabel: decode(url.pathname.split("/").pop() || ""),
        anchor: anchor
      };
    }

    return null;
  }

  function githubSource(repo, ref, path, sourceUrl, anchor) {
    var dir = dirname(path);
    return {
      kind: "github",
      host: "GitHub",
      repo: repo,
      ref: ref,
      path: path,
      sourceUrl: sourceUrl,
      rawUrl: "https://raw.githubusercontent.com/" + repo + "/" + ref + "/" + path,
      blobUrl: "https://github.com/" + repo + "/blob/" + ref + "/" + path,
      dirRaw: "https://raw.githubusercontent.com/" + repo + "/" + ref + "/" + (dir ? dir + "/" : ""),
      dirBlob: "https://github.com/" + repo + "/blob/" + ref + "/" + (dir ? dir + "/" : ""),
      fileLabel: path.split("/").pop(),
      anchor: anchor
    };
  }

  /** GitHub page for a release tag. Kept for API compatibility; pages no
      longer offer it as a hand-off. */
  function releasePageUrl(repo, tag) {
    if (!repo) return "";
    if (tag) return "https://github.com/" + repo + "/releases/tag/" + encodeURIComponent(tag);
    return "https://github.com/" + repo + "/releases";
  }

  function siteUrl(path) {
    return String(SITE || "https://innioasis.app/")
      .replace(/\/+$/, "") + "/" + String(path || "").replace(/^\/+/, "");
  }

  /** Our release notes page for a project's GitHub releases link. */
  function internalReleasePath(repo, tag) {
    var catalog = global.INNIOASIS_FIRMWARE_CATALOG || [];
    var entry = null;
    for (var i = 0; i < catalog.length; i += 1) {
      if (catalog[i].repo && String(catalog[i].repo).toLowerCase() === String(repo || "").toLowerCase()) {
        entry = catalog[i];
        break;
      }
    }
    /* The parser reads any release on demand; static copies are generated for
       search engines and are never a link target. */
    if (entry) {
      return siteUrl(releaseNotesHref({
        repo: repo, tag: tag, software: entry.slug,
        model: entry.model || "", name: entry.name || ""
      }));
    }
    return siteUrl(releaseNotesHref({ repo: repo, tag: tag }));
  }

  /* ------------------------------------------------------------------ *
   * Links into the viewer
   * ------------------------------------------------------------------ */

  function buildHref(page, params) {
    var query = [];
    Object.keys(params || {}).forEach(function (key) {
      var value = params[key];
      if (value === undefined || value === null || value === "") return;
      query.push(encodeURIComponent(key) + "=" + encodeURIComponent(String(value)));
    });
    return page + (query.length ? "?" + query.join("&") : "");
  }

  /**
   * Link to our post-install reader for a given post_install value.
   * Importable Markdown becomes a viewer link; everything else is returned
   * untouched so ordinary guides still open in a normal browser tab.
   */
  function postInstallHref(postInstallUrl, meta) {
    var source = parseSource(postInstallUrl);
    if (!source) return postInstallUrl || "";
    var info = meta || {};
    var params = {
      url: postInstallUrl,
      software: info.software || "",
      model: info.model || "",
      repo: info.repo || "",
      tag: info.tag || "",
      name: info.name || ""
    };
    if (source.anchor) params.anchor = source.anchor.replace(/^#/, "");
    return buildHref("post_install.html", params);
  }

  /* Donation appeals on by default; a visitor who turned them off sees the
     ordinary guides. */
  function donationsEnabled() {
    try {
      if (typeof global.isY1DonationsDisabled === "function") return !global.isY1DonationsDisabled();
    } catch (_) {}
    return true;
  }

  /* Russian readers get the ordinary post-install page: the donation tie-in
     on the alternate page points at services that are not available there. */
  function russianReader() {
    try {
      var locale = (navigator.languages && navigator.languages[0]) || navigator.language || "";
      if (/^ru\b/i.test(String(locale))) return true;
      var zone = "";
      try { zone = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (_) {}
      return /^(Europe\/(Moscow|Kaliningrad|Samara|Volgograd|Saratov|Kirov)|Asia\/(Yekaterinburg|Omsk|Novosibirsk|Barnaul|Tomsk|Krasnoyarsk|Irkutsk|Chita|Yakutsk|Vladivostok|Magadan|Sakhalin|Kamchatka|Anadyr))$/i.test(zone);
    } catch (_) {
      return false;
    }
  }

  /* post_install2 is the page a project wants donations-enabled visitors to
     see; without one, post_install behaves exactly as before. */
  function postInstallTarget(item, fallbackUrl) {
    var info = item || {};
    var ordinary = info.post_install || fallbackUrl || "";
    if (donationsEnabled() && info.post_install2 && !russianReader()) return info.post_install2;
    return ordinary;
  }

  function postInstallHrefFor(item, fallbackUrl, meta) {
    var info = meta || item || {};
    var target = postInstallTarget(item, fallbackUrl);
    if (!target) return "";
    return postInstallHref(target, {
      software: info.software || info.slug || "",
      model: info.model || "",
      repo: info.repo || "",
      tag: info.tag || "",
      name: info.name || ""
    });
  }

  /* The mirror republishes each portable package under a platform name
     (rom_windows-x64.zip). Visitors should still get it under the name the
     project's own package uses, so every mirror download is saved as the
     originating rom ZIP. */
  function mirrorDownloadName(release, item) {
    var assets = (release && release.assets) || [];
    var wanted = String((item && item.packageName) || "").toLowerCase();
    var names = assets.map(function (asset) { return String(asset.name || ""); })
      .filter(function (name) { return /^rom[^/]*\.zip$/i.test(name); });
    var exact = names.filter(function (name) { return name.toLowerCase() === wanted; })[0];
    if (exact) return exact;
    var plain = names.filter(function (name) { return /^rom(?:_y2|_type_a)?\.zip$/i.test(name); })[0];
    return plain || names[0] || (item && item.packageName) || "rom.zip";
  }

  /* Save a download under the package's own name. Browsers ignore the
     download attribute for cross-origin files, so read the file here and hand
     it over as a blob; when the mirror does not allow that, the ordinary link
     still downloads it. */
  function saveDownload(link) {
    var name = link.getAttribute("data-save-as") || "";
    var href = link.getAttribute("href") || "";
    if (!name || !href) return false;
    if (link.getAttribute("data-save-busy") === "1") return false;
    link.setAttribute("data-save-busy", "1");
    fetch(href, { credentials: "omit" }).then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.blob();
    }).then(function (blob) {
      var url = URL.createObjectURL(blob);
      var anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = name;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 10000);
    }).catch(function () {
      window.location.href = href;
    }).then(function () {
      link.removeAttribute("data-save-busy");
    });
    return true;
  }

  document.addEventListener("click", function (event) {
    var target = event.target;
    var link = target && target.closest ? target.closest("a[data-save-as]") : null;
    if (!link) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || (event.button && event.button > 0)) return;
    if (saveDownload(link)) event.preventDefault();
  }, false);

  /* Generated pages link straight at their static post-install page. A
     donations-enabled visitor whose project publishes post_install2 gets that
     page instead, and the choice follows the setting when it changes. */
  function applyPostInstall2Links(root) {
    var scope = root || document;
    var links = scope.querySelectorAll ? scope.querySelectorAll("a[data-post-install2]") : [];
    Array.prototype.forEach.call(links, function (link) {
      var variant = link.getAttribute("data-post-install2") || "";
      if (!variant) return;
      if (!link.getAttribute("data-plain-href")) link.setAttribute("data-plain-href", link.getAttribute("href") || "");
      link.setAttribute("href", donationsEnabled() && !russianReader() ? variant : link.getAttribute("data-plain-href"));
    });
  }

  document.addEventListener("y1-donations-change", function () {
    applyPostInstall2Links(document);
  });

  /** Link to our release-notes reader for a repository release. */
  function releaseNotesHref(meta) {
    var info = meta || {};
    var repo = String(info.repo || "");
    var parts = repo.split("/");
    var author = info.author || parts[0] || "";
    var project = info.project || parts[1] || "";
    var version = info.version || info.tag || "";
    return buildHref("release_notes.html", {
      author: author,
      project: project,
      version: version,
      repo: repo,
      tag: version,
      model: info.model || "",
      software: info.software || "",
      name: info.name || ""
    });
  }

  /** Static path written by scripts/generate_doc_pages.py. */
  function staticReleasePath(softwareSlug, tag) {
    if (!softwareSlug || !tag) return "";
    return "release-notes/" + softwareSlug + "/" + tagSlug(tag) + ".html";
  }

  function tagSlug(tag) {
    return String(tag || "")
      .toLowerCase()
      .replace(/[^a-z0-9._-]+/g, "-")
      .replace(/^-+|-+$/g, "") || "release";
  }

  /** Rewrite every [data-post-install-link] on a page to the reader. */
  function applyPostInstallLinks(root, catalog) {
    var scope = root || document;
    var items = Array.isArray(catalog) ? catalog : (global.INNIOASIS_FIRMWARE_CATALOG || []);
    scope.querySelectorAll("[data-post-install-link]").forEach(function (link) {
      var slug = link.getAttribute("data-slug") || "";
      var item = items.find(function (entry) { return entry.slug === slug; }) || null;
      var value = postInstallTarget(item, link.getAttribute("data-post-install-url") || "");
      if (!value) return;
      var href = postInstallHref(value, {
        software: item ? item.slug : slug,
        model: item ? item.model : (link.getAttribute("data-model") || ""),
        repo: item ? item.repo : "",
        name: item ? item.name : ""
      });
      /* A document we cannot import is still worth opening exactly as the
         project published it. */
      if (href === value) {
        link.setAttribute("target", "_blank");
        link.setAttribute("rel", "noopener noreferrer");
      } else {
        link.removeAttribute("target");
        link.removeAttribute("rel");
        link.setAttribute("data-doc-view", "1");
      }
      link.setAttribute("href", href);
    });
  }

  /* ------------------------------------------------------------------ *
   * Markdown -> HTML
   * ------------------------------------------------------------------ */

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function escapeAttr(value) {
    return esc(value).replace(/`/g, "&#96;");
  }

  function resolveAsset(href, ctx) {
    if (!ctx) return href;
    if (!href || /^(https?:|mailto:|tel:|data:|#)/i.test(href)) return href;
    var base = ctx.dirRaw || ctx.dirBlob;
    if (!base) return href;
    if (href.charAt(0) === "/") {
      /* Root-relative paths in a repo doc point at the repo root. */
      if (ctx.repo && ctx.ref) {
        return "https://raw.githubusercontent.com/" + ctx.repo + "/" + ctx.ref + href;
      }
      return href;
    }
    return joinUrl(base, href);
  }

  function resolveLink(href, ctx) {
    if (!href) return "#";
    href = String(href).replace(/&amp;/gi, "&").trim();
    if (!href) return "#";
    if (/^(mailto:|tel:|data:)/i.test(href)) return href;
    if (href.charAt(0) === "#") return href;
    if (/^https?:\/\/(?:www\.)?innioasis\.app(?:\/|$)/i.test(href)) return href;
    if (!/^https?:/i.test(href)) {
      if (!ctx) return href;
      if (href.charAt(0) === "/") {
        if (ctx.repo && ctx.ref) {
          href = "https://github.com/" + ctx.repo + "/blob/" + ctx.ref + href;
        } else {
          return href;
        }
      } else {
        href = joinUrl(ctx.dirBlob || ctx.dirRaw, href);
      }
    }
    if (/^https?:/i.test(href)) {
      var superseded = supersededGuideLink(href);
      if (superseded) return superseded;
      /* Rockbox-Y1 theme documentation links point to our static Updater CE
         theme transfer guide. */
      if (/^https?:\/\/(?:www\.)?(?:github\.com|raw\.githubusercontent\.com)\/rockbox-y1\/rockbox\/(?:(?:blob|raw)\/[^/]+\/|[^/]+\/)?THEMES\.md(?:[?#].*)?$/i.test(href) ||
          /^https?:\/\/(?:www\.)?github\.com\/rockbox-y1\/themes(?:\/|$)/i.test(href)) {
        return siteUrl("rockbox-y1-themes.html");
      }
      /* Any Markdown link whose path contains both "install" and ".md"
         (e.g. INSTALLATION.md, docs/install.md) routes to our own firmware
         installation instructions for that project. */
      var pathOnly = href.split(/[?#]/)[0];
      if (/(?:^|\/)[^?#]*install[^?#]*\.(?:md|markdown|mdown|mkd|mdx)$/i.test(pathOnly)) {
        var ghRepoMatch = href.match(/^https?:\/\/(?:www\.)?(?:github\.com|raw\.githubusercontent\.com)\/([^/?#]+\/[^/?#]+)/i);
        var targetRepo = (ghRepoMatch && ghRepoMatch[1]) || (ctx && ctx.repo) || "";
        return installGuideFor(targetRepo, ctx);
      }
      /* A release's own files are never listed here, so an asset link inside
         the notes is left as plain text. */
      if (/^https?:\/\/(?:www\.)?github\.com\/[^/]+\/[^/]+\/releases\/download\//i.test(href)) {
        return "";
      }
      /* A link to the project's GitHub releases page points at our own release
         notes page for the same release. */
      var release = href.match(/^https?:\/\/(?:www\.)?github\.com\/([^/?#]+)\/([^/?#]+)\/releases(?:\/tag\/([^?#]+))?/i);
      if (release) {
        return internalReleasePath(release[1] + "/" + release[2],
          release[3] ? decodeURIComponent(release[3]) : "");
      }
      /* A "Full Changelog" compare link is the project's release notes by
         another name: send it to our release history for that software. */
      var compare = href.match(/^https?:\/\/(?:www\.)?github\.com\/([^/?#]+)\/([^/?#]+)\/compare\//i);
      if (compare) return internalReleasePath(compare[1] + "/" + compare[2], "");
      /* A link to a project's own repository is the project's listing here,
         not a hand-off to a bare GitHub page. Deeper paths (a source file, an
         issue) stay on GitHub because a release listing cannot represent
         them. */
      var project = href.match(/^https?:\/\/(?:www\.)?github\.com\/([^/?#]+)\/([^/?#]+?)(?:\.git)?\/?(?:[?#].*)?$/i);
      if (project) {
        var listing = firmwarePageFor(project[1] + "/" + project[2]);
        if (listing) return listing;
      }
      /* A link to another Markdown file on GitHub becomes another reading
         page here rather than a jump out to GitHub. */
      var parsed = parseSource(href);
      if (parsed && parsed.kind === "github") {
        /* Absolute so the link also works from a generated page that lives
           two directories down (release-notes/<slug>/). */
        return SITE + buildHref("/post_install.html", { url: href, anchor: parsed.anchor.replace(/^#/, "") });
      }
      return href;
    }
    return href;
  }

  /* A firmware project's listing for the repository it ships from. */
  function firmwarePageFor(repo) {
    var key = String(repo || "").toLowerCase();
    var catalog = global.INNIOASIS_FIRMWARE_CATALOG || [];
    for (var i = 0; i < catalog.length; i += 1) {
      var item = catalog[i];
      if (!item || !item.repo || !item.slug) continue;
      if (String(item.repo).toLowerCase() !== key) continue;
      return siteUrl("firmware.html?model=" + encodeURIComponent(item.model || "") +
        "&software=" + encodeURIComponent(item.slug));
    }
    return "";
  }

  /* Our own firmware installation instructions for a repository. */
  function installGuideFor(repo, ctx) {
    var key = String(repo || (ctx && ctx.repo) || "").toLowerCase();
    var catalog = global.INNIOASIS_FIRMWARE_CATALOG || [];
    for (var i = 0; i < catalog.length; i += 1) {
      var item = catalog[i];
      if (!item || !item.repo || !item.slug) continue;
      if (String(item.repo).toLowerCase() !== key) continue;
      if (item.guide) return siteUrl(item.guide);
      return siteUrl("guide.html?model=" + encodeURIComponent(item.model || "") +
        "&software=" + encodeURIComponent(item.slug));
    }
    return GUIDE_URL;
  }

  /* Embeddable video links become a thumbnail card that opens a player here,
     so a README never sends the reader away just to watch a clip. */
  function videoFor(href) {
    var url = String(href || "");
    var startMatch = url.match(/[?&](?:t|start)=(\d+)/);
    var start = startMatch ? parseInt(startMatch[1], 10) || 0 : 0;
    var youtube = url.match(/^https?:\/\/(?:www\.|m\.)?(?:youtube\.com\/(?:watch\?(?:[^#]*&)?v=|shorts\/|embed\/)|youtu\.be\/)([\w-]{6,})/i);
    if (youtube) {
      return {
        href: url,
        embed: "https://www.youtube-nocookie.com/embed/" + youtube[1] +
          "?autoplay=1&rel=0" + (start ? "&start=" + start : ""),
        poster: "https://i.ytimg.com/vi/" + youtube[1] + "/hqdefault.jpg"
      };
    }
    var vimeo = url.match(/^https?:\/\/(?:www\.)?(?:vimeo\.com\/(?:video\/)?|player\.vimeo\.com\/video\/)(\d+)/i);
    if (vimeo) {
      return {
        href: url,
        embed: "https://player.vimeo.com/video/" + vimeo[1] + "?autoplay=1" +
          (start ? "#t=" + start + "s" : ""),
        poster: ""
      };
    }
    return null;
  }

  function videoCard(video, label) {
    var caption = String(label || "Watch the video");
    return '<a class="lumen-video-link" href="' + escapeAttr(video.href) + '"' +
      ' data-video-embed="' + escapeAttr(video.embed) + '"' +
      ' data-video-title="' + escapeAttr(caption) + '"' +
      ' target="_blank" rel="noopener noreferrer">' +
      '<span class="lumen-video-frame">' +
        (video.poster ? '<img class="lumen-video-poster" src="' + escapeAttr(video.poster) + '" alt="" loading="lazy" decoding="async">' : '') +
        '<span class="lumen-video-play" aria-hidden="true">&#9654;</span>' +
      '</span>' +
      '<span class="lumen-video-label">' + caption + '</span>' +
    '</a>';
  }

  var videoModal = null;

  function openVideoModal(embed, title) {
    if (!embed) return;
    if (!videoModal) {
      videoModal = document.createElement("div");
      videoModal.className = "lumen-video-modal";
      videoModal.setAttribute("role", "dialog");
      videoModal.setAttribute("aria-modal", "true");
      videoModal.innerHTML = '<div class="lumen-video-modal-backdrop" data-video-close></div>' +
        '<div class="lumen-video-modal-panel">' +
          '<button type="button" class="lumen-video-modal-close" data-video-close aria-label="Close video">&times;</button>' +
          '<div class="lumen-video-modal-frame"></div>' +
        '</div>';
      videoModal.hidden = true;
      videoModal.addEventListener("click", function (event) {
        if (event.target && event.target.closest && event.target.closest("[data-video-close]")) closeVideoModal();
      });
      document.body.appendChild(videoModal);
    }
    var frame = videoModal.querySelector(".lumen-video-modal-frame");
    if (frame) {
      frame.innerHTML = '<iframe src="' + escapeAttr(embed) + '" title="' + escapeAttr(title || "Video") + '"' +
        ' allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"' +
        ' allowfullscreen loading="lazy"></iframe>';
    }
    videoModal.hidden = false;
    document.documentElement.classList.add("lumen-video-open");
    var close = videoModal.querySelector(".lumen-video-modal-close");
    if (close) close.focus();
  }

  function closeVideoModal() {
    if (!videoModal) return;
    videoModal.hidden = true;
    var frame = videoModal.querySelector(".lumen-video-modal-frame");
    /* Clearing the player is what actually stops playback. */
    if (frame) frame.innerHTML = "";
    document.documentElement.classList.remove("lumen-video-open");
  }

  document.addEventListener("click", function (event) {
    var link = event.target && event.target.closest ? event.target.closest("a[data-video-embed]") : null;
    if (!link) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || (event.button && event.button > 0)) return;
    event.preventDefault();
    openVideoModal(link.getAttribute("data-video-embed"), link.getAttribute("data-video-title"));
  }, false);

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeVideoModal();
  });

  /* Inline spans: code, images, links, emphasis, strikethrough, autolinks. */
  function inline(source, ctx) {
    if (source == null || source === "") return "";
    var text = String(source);

    /* Pull code spans out first: their contents must stay literal. */
    var codeSpans = [];
    text = text.replace(/(`+)([\s\S]*?)\1/g, function (match, ticks, body) {
      var token = "\u0000C" + codeSpans.length + "\u0000";
      codeSpans.push("<code>" + esc(body.trim()) + "</code>");
      return token;
    });

    text = text.replace(/<(https?:\/\/[^\s<>]+)>/g, "$1");
    text = esc(text);

    /* Images before links: the leading ! would otherwise be swallowed. */
    text = text.replace(/!\[([^\]]*)\]\(\s*([^\s)]+)(?:\s+&quot;([^&]*)&quot;)?\s*\)/g, function (m, alt, src, title) {
      var resolved = resolveAsset(src, ctx);
      return '<img src="' + escapeAttr(resolved) + '" alt="' + alt + '"' +
        (title ? ' title="' + title + '"' : "") + ' loading="lazy" decoding="async">';
    });

    text = text.replace(/\[([^\]]+)\]\(\s*([^\s)]+)(?:\s+&quot;([^&]*)&quot;)?\s*\)/g, function (m, label, href, title) {
      var video = videoFor(href);
      if (video) return videoCard(video, label);
      var resolved = resolveLink(href, ctx);
      if (!resolved) return label;
      var shown = supersededGuideLink(href) && linkTextIsUrl(label, href) ? resolved : label;
      var external = /^https?:/i.test(resolved) && resolved.indexOf("innioasis.app") === -1;
      return '<a href="' + escapeAttr(resolved) + '"' +
        (title ? ' title="' + title + '"' : "") +
        (external ? ' target="_blank" rel="noopener noreferrer"' : "") + ">" + shown + "</a>";
    });

    /* Bare URLs, but not ones already inside an href attribute. Release
       assets stay as plain text; release pages point at our own notes. */
    text = text.replace(/(^|[\s(])(https?:\/\/[^\s<)"]+)/g, function (m, lead, url) {
      var target = resolveLink(url, ctx);
      if (!target) return lead + url;
      var shownUrl = supersededGuideLink(url) ? target : url;
      var external = /^https?:/i.test(target) && target.indexOf("innioasis.app") === -1;
      return lead + '<a href="' + escapeAttr(target) + '"' +
        (external ? ' target="_blank" rel="noopener noreferrer"' : "") + ">" + shownUrl + "</a>";
    });

    text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/__([^_]+)__/g, "<strong>$1</strong>");
    text = text.replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,;:!?]|$)/g, "$1<em>$2</em>");
    text = text.replace(/(^|[\s(])_([^_\n]+)_(?=[\s).,;:!?]|$)/g, "$1<em>$2</em>");
    text = text.replace(/~~([^~]+)~~/g, "<del>$1</del>");
    text = text.replace(/\n/g, " ");

    codeSpans.forEach(function (html, index) {
      text = text.replace("\u0000C" + index + "\u0000", html);
    });
    return text;
  }

  function splitRow(line) {
    var cells = [];
    var current = "";
    var escaped = false;
    for (var i = 0; i < line.length; i += 1) {
      var ch = line.charAt(i);
      if (escaped) { current += ch; escaped = false; continue; }
      if (ch === "\\") { escaped = true; continue; }
      if (ch === "|") { cells.push(current); current = ""; continue; }
      current += ch;
    }
    cells.push(current);
    if (cells.length && cells[0].trim() === "" && line.trim().indexOf("|") === 0) cells.shift();
    if (cells.length && cells[cells.length - 1].trim() === "" && line.trim().slice(-1) === "|") cells.pop();
    return cells.map(function (c) { return c.trim(); });
  }

  function isTableDelimiter(line) {
    if (line.indexOf("|") === -1 && line.indexOf("-") === -1) return false;
    var cells = splitRow(line);
    if (!cells.length) return false;
    return cells.every(function (cell) { return /^:?-{2,}:?$/.test(cell.replace(/\s/g, "")); });
  }

  var BLOCK_START = /^\s{0,3}(#{1,6}\s|>|```|~~~|[-*+]\s|\d+[.)]\s|\|)/;

  function renderMarkdown(markdown, ctx) {
    var text = String(markdown == null ? "" : markdown)
      .replace(/\r\n?/g, "\n")
      .replace(/\t/g, "    ")
      .replace(/\u00a0/g, " ");
    var lines = text.split("\n");
    var out = [];
    var i = 0;

    while (i < lines.length) {
      var line = lines[i];

      if (!line.trim()) { i += 1; continue; }

      /* Fenced code. */
      var fence = line.match(/^\s{0,3}(`{3,}|~{3,})\s*([\w+#.-]*)\s*$/);
      if (fence) {
        var marker = fence[1].charAt(0);
        var lang = fence[2];
        var code = [];
        i += 1;
        while (i < lines.length && !new RegExp("^\\s{0,3}" + marker + "{3,}\\s*$").test(lines[i])) {
          code.push(lines[i]);
          i += 1;
        }
        i += 1;
        out.push('<pre><code' + (lang ? ' class="language-' + escapeAttr(lang) + '"' : "") + ">" +
          esc(code.join("\n")) + "</code></pre>");
        continue;
      }

      /* Indented code block. */
      if (/^ {4}\S/.test(line)) {
        var indented = [];
        while (i < lines.length && (/^ {4}/.test(lines[i]) || !lines[i].trim())) {
          indented.push(lines[i].replace(/^ {4}/, ""));
          i += 1;
        }
        while (indented.length && !indented[indented.length - 1].trim()) indented.pop();
        out.push("<pre><code>" + esc(indented.join("\n")) + "</code></pre>");
        continue;
      }

      /* Raw HTML block: passed through, then sanitised at the end. */
      if (/^\s{0,3}<[a-zA-Z!/]/.test(line)) {
        var html = [];
        while (i < lines.length && lines[i].trim()) { html.push(lines[i]); i += 1; }
        out.push(html.join("\n"));
        continue;
      }

      var heading = line.match(/^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$/);
      if (heading) {
        var level = Math.min(6, heading[1].length);
        var headingId = heading[2].toLowerCase().replace(/[^a-z0-9\s-]/g, "").trim().replace(/\s+/g, "-");
        out.push("<h" + level + (headingId ? ' id="' + escapeAttr(headingId) + '"' : "") + ">" +
          inline(heading[2], ctx) + "</h" + level + ">");
        i += 1;
        continue;
      }

      /* Setext heading. */
      if (i + 1 < lines.length && /^\s{0,3}(=+|-{2,})\s*$/.test(lines[i + 1]) && line.trim()) {
        var seLevel = lines[i + 1].trim().charAt(0) === "=" ? 1 : 2;
        out.push("<h" + seLevel + ">" + inline(line.trim(), ctx) + "</h" + seLevel + ">");
        i += 2;
        continue;
      }

      if (/^\s{0,3}([-*_])(\s*\1){2,}\s*$/.test(line)) {
        out.push("<hr>");
        i += 1;
        continue;
      }

      /* Table. */
      if (line.indexOf("|") !== -1 && i + 1 < lines.length && isTableDelimiter(lines[i + 1])) {
        var header = splitRow(line);
        var align = splitRow(lines[i + 1]).map(function (cell) {
          var trimmed = cell.replace(/\s/g, "");
          if (/^:-+:$/.test(trimmed)) return "center";
          if (/^:-+$/.test(trimmed)) return "left";
          if (/^-+:$/.test(trimmed)) return "right";
          return "";
        });
        i += 2;
        var rows = [];
        while (i < lines.length && lines[i].trim() && lines[i].indexOf("|") !== -1) {
          rows.push(splitRow(lines[i]));
          i += 1;
        }
        var tableHtml = "<table><thead><tr>";
        header.forEach(function (cell, index) {
          tableHtml += "<th" + (align[index] ? ' style="text-align:' + align[index] + '"' : "") + ">" +
            inline(cell, ctx) + "</th>";
        });
        tableHtml += "</tr></thead><tbody>";
        rows.forEach(function (row) {
          tableHtml += "<tr>";
          header.forEach(function (_, index) {
            tableHtml += "<td" + (align[index] ? ' style="text-align:' + align[index] + '"' : "") + ">" +
              inline(row[index] || "", ctx) + "</td>";
          });
          tableHtml += "</tr>";
        });
        tableHtml += "</tbody></table>";
        out.push(tableHtml);
        continue;
      }

      /* Blockquote (rendered recursively so lists and code inside work). */
      if (/^\s{0,3}>/.test(line)) {
        var quoted = [];
        while (i < lines.length && (/^\s{0,3}>/.test(lines[i]) || (quoted.length && lines[i].trim()))) {
          quoted.push(lines[i].replace(/^\s{0,3}>\s?/, ""));
          i += 1;
        }
        out.push("<blockquote>" + renderMarkdown(quoted.join("\n"), ctx) + "</blockquote>");
        continue;
      }

      /* Lists, with nesting by indentation. */
      if (/^\s{0,3}([-*+]|\d+[.)])\s+/.test(line)) {
        var listResult = parseList(lines, i, ctx);
        out.push(listResult.html);
        i = listResult.next;
        continue;
      }

      /* Paragraph: collect until a blank line or another block starts. */
      var para = [];
      while (i < lines.length && lines[i].trim()) {
        if (para.length && (BLOCK_START.test(lines[i]) || /^\s{0,3}<[a-zA-Z!/]/.test(lines[i]))) break;
        if (para.length && i + 1 < lines.length && /^\s{0,3}(=+|-{2,})\s*$/.test(lines[i + 1])) break;
        para.push(lines[i]);
        i += 1;
      }
      var joined = para.map(function (row) {
        var hardBreak = /(\s{2,}|\\)$/.test(row);
        var clean = row.replace(/\\(\s*)$/, "$1").replace(/\s+$/, "");
        return inline(clean, ctx) + (hardBreak ? "<br>" : "");
      }).join("\n");
      out.push("<p>" + joined.replace(/\n/g, " ") + "</p>");
    }

    return out.join("\n");
  }

  function parseList(lines, start, ctx) {
    var items = [];
    var ordered = /^\s{0,3}\d+[.)]\s+/.test(lines[start]);
    var i = start;

    while (i < lines.length) {
      var match = lines[i].match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
      if (!match) {
        /* Continuation of the previous item: an indented block or a blank
           line followed by more of the same list. */
        if (items.length && lines[i].trim() && /^\s{2,}/.test(lines[i])) {
          items[items.length - 1].push(lines[i].replace(/^\s{2,4}/, ""));
          i += 1;
          continue;
        }
        if (items.length && !lines[i].trim()) {
          var probe = i + 1;
          while (probe < lines.length && !lines[probe].trim()) probe += 1;
          if (probe < lines.length && /^\s{0,3}([-*+]|\d+[.)])\s+/.test(lines[probe])) {
            i = probe;
            continue;
          }
        }
        break;
      }
      var indent = match[1].replace(/\t/g, "    ").length;
      var isOrdered = /^\d+[.)]$/.test(match[2]);
      if (items.length && (indent >= 2 ? false : isOrdered !== ordered)) {
        /* A different list type at the same indent starts a new list. */
        if (indent < 2) break;
      }
      if (indent >= 2 && items.length) {
        /* Nested item: fold it into the previous item's text with its own
           marker so parseNested can build a sub-list. */
        items[items.length - 1].push(match[2] + " " + match[3]);
        i += 1;
        continue;
      }
      items.push([match[3]]);
      i += 1;
    }

    var tag = ordered ? "ol" : "ul";
    var html = "<" + tag + ">";
    items.forEach(function (itemLines) {
      var head = itemLines[0] || "";
      var task = head.match(/^\[( |x|X)\]\s+(.*)$/);
      var checkbox = "";
      if (task) {
        checkbox = '<input type="checkbox" disabled' + (task[1].toLowerCase() === "x" ? " checked" : "") + "> ";
        head = task[2];
      }
      var nested = itemLines.slice(1);
      var nestedHtml = "";
      if (nested.length && /^([-*+]|\d+[.)])\s+/.test(nested[0])) {
        nestedHtml = parseList(nested, 0, ctx).html;
      } else if (nested.length) {
        nestedHtml = "<p>" + nested.map(function (row) { return inline(row.trim(), ctx); }).join(" ") + "</p>";
      }
      html += "<li>" + checkbox + inline(head, ctx) + nestedHtml + "</li>";
    });
    html += "</" + tag + ">";
    return { html: html, next: i };
  }

  /* ------------------------------------------------------------------ *
   * Sanitiser
   *
   * The Markdown above escapes its own text, but GitHub READMEs and release
   * bodies regularly contain raw HTML (centred logos, <details>, badges).
   * That HTML is kept only when it is on the allowlist and carries no
   * handlers or script URLs.
   * ------------------------------------------------------------------ */

  var ALLOWED_TAGS = {
    A: 1, ABBR: 1, B: 1, BLOCKQUOTE: 1, BR: 1, CAPTION: 1, CENTER: 1, CODE: 1,
    COL: 1, COLGROUP: 1, DD: 1, DEL: 1, DETAILS: 1, DIV: 1, DL: 1, DT: 1,
    EM: 1, FIGCAPTION: 1, FIGURE: 1, H1: 1, H2: 1, H3: 1, H4: 1, H5: 1,
    H6: 1, HR: 1, I: 1, IMG: 1, INPUT: 1, KBD: 1, LI: 1, MARK: 1, OL: 1,
    P: 1, PICTURE: 1, PRE: 1, Q: 1, S: 1, SAMP: 1, SMALL: 1, SOURCE: 1,
    SPAN: 1, STRIKE: 1, STRONG: 1, SUB: 1, SUMMARY: 1, SUP: 1, TABLE: 1,
    TBODY: 1, TD: 1, TFOOT: 1, TH: 1, THEAD: 1, TR: 1, U: 1, UL: 1,
    VAR: 1, VIDEO: 1, WBR: 1
  };

  var ALLOWED_ATTRS = {
    A: "href title rel target name id data-video-embed data-video-title",
    IMG: "src alt title width height loading decoding align",
    SOURCE: "src srcset type media",
    VIDEO: "src controls width height poster muted loop playsinline",
    INPUT: "type checked disabled",
    TD: "colspan rowspan align style",
    TH: "colspan rowspan align style",
    TABLE: "align",
    COL: "span width",
    COLGROUP: "span width",
    DETAILS: "",
    SUMMARY: "",
    DIV: "align",
    P: "align",
    H1: "align id", H2: "align id", H3: "align id", H4: "align id", H5: "align id", H6: "align id",
    SPAN: "",
    "*": "id class align"
  };

  var DROP_TAGS = {
    SCRIPT: 1, STYLE: 1, IFRAME: 1, OBJECT: 1, EMBED: 1, FORM: 1, BUTTON: 1,
    SELECT: 1, TEXTAREA: 1, META: 1, LINK: 1, BASE: 1, NOSCRIPT: 1, TEMPLATE: 1
  };

  function sanitizeHtml(html, ctx) {
    if (!html) return "";
    if (typeof DOMParser === "undefined") return html;
    var doc;
    try {
      doc = new DOMParser().parseFromString('<div id="innioasis-doc-root">' + html + "</div>", "text/html");
    } catch (_) {
      return html;
    }
    var root = doc.getElementById("innioasis-doc-root");
    if (!root) return html;

    var walker = doc.createTreeWalker(root, NodeFilter.SHOW_ELEMENT, null);
    var doomed = [];
    while (walker.nextNode()) {
      var el = walker.currentNode;
      var tag = el.tagName.toUpperCase();
      if (DROP_TAGS[tag]) { doomed.push({ node: el, mode: "drop" }); continue; }
      if (!ALLOWED_TAGS[tag]) { doomed.push({ node: el, mode: "unwrap" }); continue; }

      var allowed = (ALLOWED_ATTRS[tag] || "") + " " + (ALLOWED_ATTRS["*"] || "");
      var allowList = allowed.split(/\s+/).filter(Boolean);
      Array.prototype.slice.call(el.attributes).forEach(function (attr) {
        var name = attr.name.toLowerCase();
        var value = String(attr.value || "");
        if (name.indexOf("on") === 0 || name === "srcdoc" || name === "formaction") {
          el.removeAttribute(attr.name);
          return;
        }
        if (allowList.indexOf(name) === -1) {
          el.removeAttribute(attr.name);
          return;
        }
        if ((name === "href" || name === "src" || name === "poster") && /^\s*(javascript|vbscript|data:text\/html)/i.test(value)) {
          el.removeAttribute(attr.name);
        }
      });
      /* Raw HTML from a README often points at sibling files with relative
         paths (images/screenshot.png). Those only resolve inside the repo, so
         rewrite them against the document's own directory. */
      if (tag === "IMG" || tag === "SOURCE") {
        var rawSrc = el.getAttribute("src");
        if (rawSrc) el.setAttribute("src", resolveAsset(rawSrc, ctx));
        var srcset = el.getAttribute("srcset");
        if (srcset) {
          el.setAttribute("srcset", srcset.split(",").map(function (part) {
            var bits = part.trim().split(/\s+/);
            if (bits[0]) bits[0] = resolveAsset(bits[0], ctx);
            return bits.join(" ");
          }).join(", "));
        }
        if (tag === "IMG") {
          el.setAttribute("loading", "lazy");
          el.setAttribute("decoding", "async");
        }
      }
      if (tag === "A") {
        var rawHref = el.getAttribute("href");
        if (rawHref) el.setAttribute("href", resolveLink(rawHref, ctx));
        if (rawHref && supersededGuideLink(rawHref) && linkTextIsUrl(el.textContent, rawHref)) {
          el.textContent = el.getAttribute("href") || GUIDE_URL;
        }
        var finalHref = el.getAttribute("href") || "";
        if (/^https?:/i.test(finalHref) && finalHref.indexOf("innioasis.app") === -1) {
          el.setAttribute("rel", "noopener noreferrer");
          el.setAttribute("target", "_blank");
        }
      }
      if (tag === "IMG" && !el.getAttribute("src")) {
        doomed.push({ node: el, mode: "drop" });
      }
    }

    doomed.forEach(function (entry) {
      var node = entry.node;
      if (!node.parentNode) return;
      if (entry.mode === "drop") {
        node.parentNode.removeChild(node);
        return;
      }
      while (node.firstChild) node.parentNode.insertBefore(node.firstChild, node);
      node.parentNode.removeChild(node);
    });

    return root.innerHTML;
  }

  /** Full pipeline: Markdown text in, safe styled HTML out. */
  function markdownToHtml(markdown, ctx) {
    return linkifySupersededText(sanitizeHtml(renderMarkdown(markdown, ctx), ctx));
  }

  /* ------------------------------------------------------------------ *
   * Fetching
   * ------------------------------------------------------------------ */

  var SCRIPT_BASE = (function () {
    try {
      var script = document.currentScript;
      if (script && script.src) return new URL(".", script.src).href;
    } catch (_) {}
    return "";
  })();

  /* Access tokens published with the site in config.ini. Entries are often
     stored without the github_pat_ prefix and some carry quotes, so every
     value is normalised before it is offered to the API. */
  var githubTokens = null;
  var tokensRequest = null;

  function normalizeToken(raw) {
    var value = String(raw == null ? "" : raw).trim().replace(/^["']+/, "").replace(/["']+$/, "").trim();
    if (!value || /^(your|token|paste|none|xxx)/i.test(value)) return "";
    if (/^github_pat_/i.test(value)) return "github_pat_" + value.slice(11);
    if (/^(ghp_|gho_|ghu_|ghs_|github_pat)/i.test(value)) return value;
    return "github_pat_" + value;
  }

  function parseTokenConfig(text) {
    var tokens = [];
    String(text || "").split(/\r?\n/).forEach(function (line) {
      if (!/^(key_\d+|token)\s*=/.test(line.trim())) return;
      var token = normalizeToken(line.split("=").slice(1).join("="));
      if (token.length > 12 && tokens.indexOf(token) === -1) tokens.push(token);
    });
    return tokens;
  }

  /* Reuse the pool the release directory already loaded, so a page never asks
     for config.ini twice. */
  function loadGithubTokens() {
    if (Array.isArray(githubTokens)) return Promise.resolve(githubTokens);
    var shared = global.INNIOASIS_GITHUB_TOKENS;
    if (Array.isArray(shared) && shared.length) {
      githubTokens = shared.slice();
      return Promise.resolve(githubTokens);
    }
    if (tokensRequest) return tokensRequest;
    tokensRequest = fetch(SCRIPT_BASE + "config.ini", { cache: "no-store", credentials: "omit" })
      .then(function (res) { return res.ok ? res.text() : ""; })
      .then(function (text) { githubTokens = parseTokenConfig(text); return githubTokens; })
      .catch(function () { githubTokens = []; return githubTokens; });
    return tokensRequest;
  }

  function requestText(url, timeoutMs, token, accept) {
    var controller = null;
    var timer = null;
    var init = { cache: "no-store", credentials: "omit", mode: "cors" };
    init.headers = { Accept: accept || "application/vnd.github+json" };
    if (token) init.headers.Authorization = "Bearer " + token;
    if (typeof AbortController !== "undefined") {
      controller = new AbortController();
      init.signal = controller.signal;
      timer = setTimeout(function () { try { controller.abort(); } catch (_) {} }, timeoutMs || 12000);
    }
    return fetch(url, init).then(function (res) {
      if (timer) clearTimeout(timer);
      if (!res.ok) {
        var error = new Error("HTTP " + res.status);
        error.status = res.status;
        throw error;
      }
      return res.text();
    }).catch(function (error) {
      if (timer) clearTimeout(timer);
      throw error;
    });
  }

  function fetchText(url, timeoutMs) {
    return requestText(url, timeoutMs, "");
  }

  /* GitHub API calls go through a token first: the anonymous allowance is
     small and shared, so every reader on the site would spend it. A token is
     tried, then the next, then the call is repeated anonymously; a token the
     API rejects is dropped so it is never offered again. */
  function fetchGithubText(url, timeoutMs, accept) {
    return loadGithubTokens().then(function () {
      var tried = [];
      function attempt() {
        var available = githubTokens.filter(function (value) { return tried.indexOf(value) === -1; });
        var token = available.length ? available[Math.floor(Math.random() * available.length)] : "";
        if (token) tried.push(token);
        return requestText(url, timeoutMs, token, accept).catch(function (error) {
          if (error && error.status === 401 && token) {
            var at = githubTokens.indexOf(token);
            if (at !== -1) githubTokens.splice(at, 1);
            return attempt();
          }
          if (token) return attempt();
          throw error;
        });
      }
      return attempt();
    });
  }

  function fetchGithubJson(url) {
    return fetchGithubText(url).then(function (body) { return JSON.parse(body); });
  }

  /**
   * Load a Markdown document, trying the cheapest CORS-friendly URL first.
   * GitHub's raw host is the normal path; the jsDelivr mirror and the
   * contents API are fallbacks for network setups that block it.
   */
  function loadMarkdown(input) {
    var source = parseSource(input);
    if (!source) return Promise.reject(new Error("not-markdown"));
    var attempts = [];

    if (source.kind === "github" || source.kind === "github-raw") {
      attempts.push(function () {
        return fetchText(source.rawUrl).catch(function () {
          return fetchText("https://cdn.jsdelivr.net/gh/" + source.repo + "@" + source.ref + "/" + source.path);
        });
      });
      attempts.push(function () {
        return fetchGithubText("https://api.github.com/repos/" + source.repo + "/contents/" + source.path +
          "?ref=" + encodeURIComponent(source.ref), 12000)
          .then(function (body) {
            var data = JSON.parse(body);
            if (!data || !data.content) throw new Error("empty");
            return decodeBase64Utf8(data.content.replace(/\s/g, ""));
          });
      });
    } else if (source.kind === "github-asset") {
      /* A release asset is not a repo path, so it is looked up in the
         release's asset list and read through the API's binary endpoint. */
      attempts.push(function () {
        return fetchRelease(source.repo, source.ref).then(function (release) {
          var wanted = source.path.toLowerCase();
          var asset = ((release && release.assets) || []).filter(function (candidate) {
            return String(candidate.name || "").toLowerCase() === wanted;
          })[0];
          if (!asset) throw new Error("no-asset");
          return fetchAssetMarkdown(source.repo, asset);
        }).then(function (found) { return found.markdown; });
      });
      attempts.push(function () { return fetchText(source.rawUrl); });
    } else {
      attempts.push(function () { return fetchText(source.rawUrl); });
    }

    return attempts.reduce(function (chain, attempt) {
      return chain.catch(attempt);
    }, Promise.reject(new Error("no-source"))).then(function (markdown) {
      return { markdown: markdown, source: source };
    });
  }

  function decodeBase64Utf8(base64) {
    try {
      var binary = atob(base64);
      var bytes = new Uint8Array(binary.length);
      for (var i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
      if (typeof TextDecoder !== "undefined") return new TextDecoder("utf-8").decode(bytes);
      return binary;
    } catch (_) {
      return "";
    }
  }

  /* ------------------------------------------------------------------ *
   * Release notes written as files
   * ------------------------------------------------------------------ */

  /* Markdown files a release ships as assets, notes-looking ones first. */
  var NOTES_NAME = /(release[-_ .]?notes|changelog|whats?[-_ ]?new|notes|install|readme)/i;

  function markdownAssets(release) {
    return ((release && release.assets) || []).filter(function (asset) {
      return MARKDOWN_EXT.test(String(asset.name || ""));
    }).sort(function (a, b) {
      var left = NOTES_NAME.test(String(a.name || "")) ? 0 : 1;
      var right = NOTES_NAME.test(String(b.name || "")) ? 0 : 1;
      return left - right || String(a.name || "").localeCompare(String(b.name || ""));
    });
  }

  /* Where a project keeps its notes when the release body is empty. Only
     files that are notes rather than documentation are named here: a README
     is the project's front page, not the notes for one build. */
  function notesFileCandidates(release) {
    var fromAssets = markdownAssets(release).map(function (asset) { return String(asset.name || ""); });
    return fromAssets.concat([
      "RELEASE-NOTES.md",
      "RELEASE_NOTES.md",
      "release-notes.md",
      "CHANGELOG.md",
      "CHANGELOG",
      "docs/RELEASE-NOTES.md"
    ]).filter(function (name, index, all) { return all.indexOf(name) === index; });
  }

  /* Read one Markdown file out of a repo at a ref. The contents API goes
     first so the site's tokens carry the call, then the raw host and the
     jsDelivr mirror cover networks that block the API. */
  function fetchRepoMarkdown(repo, ref, path) {
    return fetchGithubText("https://api.github.com/repos/" + repo + "/contents/" + path +
      "?ref=" + encodeURIComponent(ref), 12000)
      .then(function (body) {
        var data = JSON.parse(body);
        if (!data || !data.content) throw new Error("empty");
        return decodeBase64Utf8(String(data.content).replace(/\s/g, ""));
      })
      .catch(function () {
        return fetchText("https://raw.githubusercontent.com/" + repo + "/" + ref + "/" + path)
          .catch(function () {
            return fetchText("https://cdn.jsdelivr.net/gh/" + repo + "@" + ref + "/" + path);
          });
      })
      .then(function (markdown) {
        if (!markdown || !String(markdown).trim()) throw new Error("empty");
        return {
          markdown: markdown,
          path: path,
          url: "https://github.com/" + repo + "/blob/" + ref + "/" + path
        };
      });
  }

  /* A Markdown file attached to a release. GitHub answers the asset endpoint
     with a redirect to its CDN, which a browser page may not be allowed to
     read, so this is a best-effort attempt: the caller still has the file's
     own URL to show when it fails. */
  function fetchAssetMarkdown(repo, asset) {
    var name = String((asset && asset.name) || "");
    var attempt = asset && asset.id
      ? fetchGithubText("https://api.github.com/repos/" + repo + "/releases/assets/" + asset.id,
        12000, "application/octet-stream")
      : Promise.reject(new Error("no-asset"));
    return attempt
      .catch(function () {
        if (!asset || !asset.browser_download_url) throw new Error("no-url");
        return fetchText(asset.browser_download_url);
      })
      .then(function (markdown) {
        if (!markdown || !String(markdown).trim()) throw new Error("empty");
        return {
          markdown: markdown,
          path: name,
          url: (asset && (asset.browser_download_url || asset.url)) || ""
        };
      });
  }

  /**
   * The notes for one release. The release's own Markdown body wins when it
   * has one; otherwise the first readable notes file is pulled in: a Markdown
   * asset first, then a notes file in the repo at that tag. The resolved
   * object always carries the URL of the original file so a page can link to
   * it when the reader wants the source.
   */
  function releaseNotesMarkdown(repo, tag) {
    if (!repo || !tag) return Promise.reject(new Error("no-release"));
    return fetchRelease(repo, tag).then(function (release) {
      var body = String((release && release.body) || "").trim();
      if (body) {
        return {
          markdown: body,
          path: "",
          url: releasePageUrl(repo, tag),
          release: release,
          fromBody: true
        };
      }
      var chain = Promise.reject(new Error("no-notes"));
      notesFileCandidates(release).forEach(function (path) {
        chain = chain.catch(function () { return fetchRepoMarkdown(repo, tag, path); });
      });
      var asset = markdownAssets(release)[0];
      if (asset) {
        chain = chain.catch(function () { return fetchAssetMarkdown(repo, asset); });
      }
      return chain.then(function (found) {
        found.release = release;
        return found;
      });
    });
  }

  /* ------------------------------------------------------------------ *
   * GitHub releases
   * ------------------------------------------------------------------ */

  var releaseCache = {};

  function fetchRelease(repo, tag) {
    if (!repo) return Promise.reject(new Error("no-repo"));
    var key = repo + "@" + (tag || "latest");
    if (releaseCache[key]) return releaseCache[key];
    var url = tag
      ? "https://api.github.com/repos/" + repo + "/releases/tags/" + encodeURIComponent(tag)
      : "https://api.github.com/repos/" + repo + "/releases/latest";
    releaseCache[key] = fetchGithubJson(url).catch(function (error) {
      delete releaseCache[key];
      throw error;
    });
    return releaseCache[key];
  }

  function fetchReleases(repo, pages) {
    if (!repo) return Promise.resolve([]);
    var perPage = 100;
    var wanted = Math.max(1, Math.min(3, pages || 1));
    var collected = [];
    var chain = Promise.resolve();
    for (var page = 1; page <= wanted; page += 1) {
      (function (n) {
        chain = chain.then(function () {
          return fetchGithubJson("https://api.github.com/repos/" + repo + "/releases?per_page=" + perPage + "&page=" + n)
            .then(function (list) {
              if (!Array.isArray(list) || !list.length) return false;
              collected = collected.concat(list);
              return list.length === perPage;
            })
            .catch(function () { return false; });
        });
      })(page);
    }
    return chain.then(function () { return collected; });
  }

  /* A mirror that has not been created yet would otherwise be asked for the
     same missing releases on every page view. Remember the empty answer for
     the browser session. */
  var MIRROR_CACHE_KEY = "innioasis-mirror-empty";

  /** Repackaged portable assets published by the mirror repo. */
  function fetchMirrorAssets(repo, tag) {
    if (!PORTABLE_MIRROR_REPO || !repo || !tag) return Promise.resolve([]);
    try {
      if (sessionStorage.getItem(MIRROR_CACHE_KEY) === "1") return Promise.resolve([]);
    } catch (_) {}
    var repoSlug = repo.replace("/", "-").toLowerCase();
    var tagKey = String(tag).toLowerCase();
    var releaseTag = repoSlug + "@" + tagKey;
    return fetchReleases(PORTABLE_MIRROR_REPO, 2).then(function (releases) {
      var matches = [];
      releases.forEach(function (release) {
        var names = [release.tag_name, release.name].filter(Boolean).map(function (v) { return String(v).toLowerCase(); });
        var exact = names.some(function (name) {
          return name === releaseTag || name === tagKey + "@" + repoSlug ||
            name.indexOf(repoSlug + "@" + tagKey) !== -1 || name.indexOf(releaseTag) !== -1;
        });
        (release.assets || []).forEach(function (asset) {
          var lower = String(asset.name || "").toLowerCase();
          var named = lower.indexOf(repoSlug) !== -1 && lower.indexOf(tagKey) !== -1;
          var zip = /\.(zip|7z|tar\.gz)$/.test(lower);
          if (exact || named) {
            if (zip) matches.push({ asset: asset, exact: exact, release: release });
          }
        });
      });
      matches.sort(function (a, b) { return (b.exact ? 1 : 0) - (a.exact ? 1 : 0); });
      if (!releases.length) {
        try { sessionStorage.setItem(MIRROR_CACHE_KEY, "1"); } catch (_) {}
      }
      return matches;
    }).catch(function () { return []; });
  }

  /* ------------------------------------------------------------------ *
   * Small helpers shared with the pages
   * ------------------------------------------------------------------ */

  /* Cheap existence check used before sending a reader to a generated page. */
  function headOk(url) {
    if (!url) return Promise.resolve(false);
    return fetch(url, { method: "HEAD", cache: "no-store" }).then(function (res) {
      return res.ok;
    }).catch(function () { return false; });
  }

  function formatBytes(bytes) {
    var size = Number(bytes);
    if (!isFinite(size) || size <= 0) return "";
    var units = ["B", "KB", "MB", "GB"];
    var index = 0;
    while (size >= 1024 && index < units.length - 1) { size /= 1024; index += 1; }
    return (size >= 10 || index === 0 ? Math.round(size) : size.toFixed(1)) + " " + units[index];
  }

  function formatDate(value) {
    if (!value) return "";
    var date = new Date(value);
    if (isNaN(date.getTime())) return String(value);
    try {
      return date.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
    } catch (_) {
      return date.toISOString().slice(0, 10);
    }
  }

  function queryParam(name) {
    try {
      return new URLSearchParams(location.search).get(name) || "";
    } catch (_) {
      return "";
    }
  }

  /** Release notes written in Markdown, or a sensible one-line summary. */
  function releaseBody(release) {
    if (!release) return "";
    var body = (release.body || "").trim();
    if (body) return body;
    if (release.name) return "_" + release.name + " has no published notes yet._";
    return "_This release has no published notes yet._";
  }

  var api = {
    PORTABLE_MIRROR_REPO: PORTABLE_MIRROR_REPO,
    parseSource: parseSource,
    postInstallHref: postInstallHref,
    postInstallHrefFor: postInstallHrefFor,
    postInstallTarget: postInstallTarget,
    applyPostInstall2Links: applyPostInstall2Links,
    mirrorDownloadName: mirrorDownloadName,
    donationsEnabled: donationsEnabled,
    releaseNotesHref: releaseNotesHref,
    releasePageUrl: releasePageUrl,
    staticReleasePath: staticReleasePath,
    tagSlug: tagSlug,
    applyPostInstallLinks: applyPostInstallLinks,
    renderMarkdown: renderMarkdown,
    markdownToHtml: markdownToHtml,
    sanitizeHtml: sanitizeHtml,
    loadMarkdown: loadMarkdown,
    releaseNotesMarkdown: releaseNotesMarkdown,
    fetchRepoMarkdown: fetchRepoMarkdown,
    markdownAssets: markdownAssets,
    fetchText: fetchText,
    fetchRelease: fetchRelease,
    fetchReleases: fetchReleases,
    fetchMirrorAssets: fetchMirrorAssets,
    headOk: headOk,
    formatBytes: formatBytes,
    formatDate: formatDate,
    queryParam: queryParam,
    releaseBody: releaseBody
  };

  global.InnioasisDocs = api;
})(typeof window !== "undefined" ? window : globalThis);
