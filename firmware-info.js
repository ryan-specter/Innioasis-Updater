/* Firmware README reader.
 *
 * Two pages share this script:
 *   firmware-info/<repo>.html   static copies the generator writes when a
 *                               project README names Updater CE
 *   firmware_info.html          live reader for every other project
 *
 * The Markdown parser is docs-viewer.js (window.InnioasisDocs), so a README
 * renders with the same link rewriting, images, tables and code blocks as the
 * release notes. The only figure shown is the archive download total, read
 * from the repository API: a token from config.ini first, then the next
 * token, then an anonymous call, so the page keeps working when the tokens
 * are missing or rate-limited.
 */
(function () {
  "use strict";

  var D = null;
  var root = null;
  var item = null;
  var repo = "";
  var params = new URLSearchParams(window.location.search);

  function docs() {
    if (!D && window.InnioasisDocs) D = window.InnioasisDocs;
    return D;
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>'"]/g, function (char) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char];
    });
  }

  function catalog() {
    return Array.isArray(window.INNIOASIS_FIRMWARE_CATALOG) ? window.INNIOASIS_FIRMWARE_CATALOG : [];
  }

  function sameRepo(a, b) {
    return String(a || "").toLowerCase() === String(b || "").toLowerCase();
  }

  /* The catalog item named by ?software=<slug>, then by ?repo=<owner/name>,
     or the page's own data-repo attribute (static pages know their project). */
  function resolveItem() {
    var slug = (params.get("software") || "").toLowerCase();
    var wanted = params.get("repo") || root.getAttribute("data-repo") || "";
    var list = catalog();
    var bySlug = null;
    var byRepo = null;
    list.forEach(function (entry) {
      if (slug && entry.slug === slug) bySlug = entry;
      if (wanted && !byRepo && sameRepo(entry.repo, wanted)) byRepo = entry;
    });
    return bySlug || byRepo || null;
  }

  /* Every model a repository ships for, so one README page can say Y1 and Y2. */
  function itemsForRepo(target) {
    return catalog().filter(function (entry) { return sameRepo(entry.repo, target); });
  }

  function readmePage(repoName) {
    var map = window.INNIOASIS_README_PAGES || {};
    var entry = map[String(repoName || "").toLowerCase()];
    return entry && entry.page ? entry.page : "";
  }

  function sourceCtx(repoName) {
    var api = docs();
    var source = api && api.parseSource("https://github.com/" + repoName + "/blob/HEAD/README.md");
    if (source) return source;
    return {
      repo: repoName,
      ref: "HEAD",
      dirRaw: "https://raw.githubusercontent.com/" + repoName + "/HEAD/",
      dirBlob: "https://github.com/" + repoName + "/blob/HEAD/"
    };
  }

  /* ---------------------------------------------------------------- identity */

  function paintIcon(source) {
    var box = document.getElementById("fi-icon");
    if (!box) return;
    if (source) {
      box.innerHTML = '<img src="' + escapeHtml(source) + '" width="40" height="40" alt="" loading="lazy" style="width:40px;height:40px;object-fit:cover;border-radius:10px;display:block;">';
      return;
    }
    box.innerHTML = box.getAttribute("data-generic") || "";
  }

  function iconFor(entries, base) {
    var icon = "";
    entries.forEach(function (entry) {
      if (!icon && entry.icon) icon = entry.icon;
    });
    if (icon) return icon;
    var map = window.INNIOASIS_RELEASE_ICONS || {};
    var asset = map[String(base.repo || "").toLowerCase()];
    return asset || "";
  }

  function paintIdentity(entries) {
    var primary = entries[0] || item || {};
    var name = primary.name || repo.split("/").pop();
    var models = [];
    entries.forEach(function (entry) {
      if (entry.model && models.indexOf(entry.model) === -1) models.push(entry.model);
    });
    document.title = "README for " + name + (models.length ? " (" + models.join(", ") + ")" : "") + " - Innioasis Updater";
    var title = document.getElementById("fi-title");
    if (title) title.textContent = name + " README";
    var kicker = document.getElementById("fi-kicker");
    if (kicker) kicker.textContent = "Firmware README · " + (models.join(" · ") || "project");
    var lead = document.getElementById("fi-lead");
    if (lead) {
      lead.textContent = primary.description ||
        "The project's own README, shown here so you can read about the firmware without leaving the site.";
    }
    paintIcon(iconFor(entries, primary));

    var meta = document.getElementById("fi-meta");
    if (meta) {
      meta.innerHTML = models.length ? escapeHtml(models.join(" · ")) : "";
    }

    var actions = document.getElementById("fi-actions");
    if (actions) {
      var buttons = [];
      if (primary.guide) {
        buttons.push('<a class="lumen-button lumen-button--primary" href="' + escapeHtml(relative(primary.guide)) + '">Open the ' + escapeHtml(name) + " guide</a>");
      }
      var directory = "firmware.html" + (primary.slug ? "?model=" + encodeURIComponent(primary.model || "") + "&software=" + encodeURIComponent(primary.slug) : "");
      buttons.push('<a class="lumen-button" href="' + escapeHtml(relative(directory)) + '">Install with Updater CE</a>');
      if (primary.benefits) {
        buttons.push('<a class="lumen-button" href="' + escapeHtml(relative(primary.benefits)) + '">Why ' + escapeHtml(name) + "?</a>");
      }
      var staticPage = readmePage(repo);
      if (staticPage && window.location.pathname.indexOf("/firmware-info/") === -1) {
        buttons.push('<a class="lumen-button" href="' + escapeHtml(staticPage) + '">Permanent copy</a>');
      }
      actions.innerHTML = buttons.join("");
    }
  }

  /* Static pages sit one folder down, so their links take one ../ step. */
  function relative(href) {
    if (!href) return "";
    if (/^(https?:|mailto:|#|\/)/.test(href)) return href;
    return window.location.pathname.indexOf("/firmware-info/") !== -1 ? "../" + href : href;
  }

  /* ------------------------------------------------------------------- stats */

  /* The repository API allows more calls with a configured token, so the
     site's pool is tried first and an anonymous call is the fallback. */
  var tokenPool = null;
  function loadTokens() {
    if (tokenPool) return tokenPool;
    tokenPool = fetch("config.ini", { cache: "no-store" })
      .then(function (response) { return response.ok ? response.text() : ""; })
      .then(function (text) {
        return String(text || "").split(/\r?\n/)
          .map(function (line) { return line.trim(); })
          .filter(function (line) { return /^(key_\d+|token)\s*=/.test(line); })
          .map(function (line) { return line.split("=").slice(1).join("=").trim(); })
          .filter(function (value) { return value.length > 10; })
          .map(function (value) {
            return /^(github_pat_|ghp_|gho_|ghu_)/.test(value) ? value : "github_pat_" + value;
          });
      })
      .catch(function () { return []; });
    return tokenPool;
  }

  /* One repository API call: rotate the configured tokens, then go anonymous. */
  function apiJson(url) {
    return loadTokens().then(function (tokens) {
      var tried = [];
      function attempt() {
        var available = tokens.filter(function (token) { return tried.indexOf(token) === -1; });
        var token = available.length ? available[Math.floor(Math.random() * available.length)] : "";
        if (token) tried.push(token);
        var headers = { Accept: "application/vnd.github+json" };
        if (token) headers.Authorization = "Bearer " + token;
        return fetch(url, { headers: headers })
          .then(function (response) {
            if (!response.ok) {
              var error = new Error("HTTP " + response.status);
              error.status = response.status;
              throw error;
            }
            return response.json();
          })
          .catch(function (error) {
            if (token && (error.status === 401 || error.status === 403 || error.status === 429)) return attempt();
            throw error;
          });
      }
      return attempt();
    });
  }

  function number(value) {
    return typeof value === "number" && isFinite(value) ? value.toLocaleString() : "—";
  }

  function setStat(name, value) {
    var el = root ? root.querySelector('[data-stat="' + name + '"]') : null;
    if (el && value !== undefined && value !== null && value !== "") el.textContent = value;
  }

  /* Downloads from Firmware Archive: every asset download across the
     project's public releases. Nothing else is counted or shown. */
  function paintDownloads(releases) {
    var downloads = 0;
    (releases || []).forEach(function (release) {
      if (!release || release.draft) return;
      (release.assets || []).forEach(function (asset) {
        downloads += Number(asset.download_count) || 0;
      });
    });
    setStat("downloads", number(downloads));
  }

  function loadStats() {
    var collected = [];
    function page(index) {
      if (index > 3) { paintDownloads(collected); return; }
      apiJson("https://api.github.com/repos/" + repo + "/releases?per_page=100&page=" + index)
        .then(function (batch) {
          if (!Array.isArray(batch) || !batch.length) { paintDownloads(collected); return; }
          collected = collected.concat(batch);
          if (batch.length < 100) { paintDownloads(collected); return; }
          page(index + 1);
        })
        .catch(function () {
          if (collected.length) { paintDownloads(collected); return; }
          var note = document.getElementById("fi-stats-note");
          if (note) note.textContent = "Download totals are unavailable right now.";
        });
    }
    page(1);
  }

  /* ------------------------------------------------------------------- readme */

  var README_PATHS = ["README.md", "readme.md", "Readme.md", "README.markdown", "README.MD", "docs/README.md"];

  function loadReadme() {
    var body = document.getElementById("fi-body");
    if (!body) return;
    /* Static pages already carry the rendered README, so a failed API call
       must never replace them with an error. */
    if (window.location.pathname.indexOf("/firmware-info/") !== -1) return;
    var api = docs();
    if (!api || typeof api.fetchRepoMarkdown !== "function") {
      body.innerHTML = '<p class="lumen-doc-status">The README reader did not load. ' +
        '<a href="' + escapeHtml(relative((item && item.guide) || "firmware.html")) + '">Open the install guide</a> instead.</p>';
      return;
    }
    function attempt(index) {
      if (index >= README_PATHS.length) {
        body.innerHTML = '<p class="lumen-doc-status">This project has no README the site can read. ' +
          'Read the <a href="' + escapeHtml(relative((item && item.guide) || "firmware.html")) + '">install guide</a> instead.</p>';
        return;
      }
      api.fetchRepoMarkdown(repo, "HEAD", README_PATHS[index])
        .then(function (result) {
          var markdown = result && result.markdown ? result.markdown : "";
          if (!markdown.trim()) throw new Error("empty");
          body.innerHTML = api.markdownToHtml(markdown, sourceCtx(repo));
          body.setAttribute("data-readme-path", README_PATHS[index]);
        })
        .catch(function () { attempt(index + 1); });
    }
    attempt(0);
  }

  /* -------------------------------------------------------------------- mount */

  function mount() {
    root = document.querySelector("[data-firmware-info]");
    if (!root) return;
    item = resolveItem();
    repo = (item && item.repo) || params.get("repo") || root.getAttribute("data-repo") || "";
    if (!repo || repo.indexOf("/") === -1) {
      var body = document.getElementById("fi-body");
      if (body) {
        body.innerHTML = '<p class="lumen-doc-status">No firmware project was named. ' +
          '<a href="firmware.html">Open the firmware directory</a> and pick a release first.</p>';
      }
      return;
    }
    var entries = itemsForRepo(repo);
    if (!entries.length && item) entries = [item];
    paintIdentity(entries);
    loadStats();
    loadReadme();
  }

  window.InnioasisFirmwareInfo = {
    mount: mount,
    readmePage: readmePage
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
