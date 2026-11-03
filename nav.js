(function () {
  "use strict";

  /* Donation appeals. A link can turn every request for support off with
     ?donations=false, and the donation panel's "Don't show donation appeals
     again" box stores the same choice. The choice is remembered per site, so
     the site switcher and footer links pass the flag on to the other
     Innioasis sites (different origins keep their own copy). ?donations=true
     turns the appeals back on. */
  var DONATIONS_KEY = "innioasis-donations-off";

  function donationsParam() {
    try {
      var raw = new URLSearchParams(window.location.search).get("donations");
      if (raw === null) return null;
      var value = String(raw).trim().toLowerCase();
      if (value === "false" || value === "0" || value === "no" || value === "off") return false;
      if (value === "true" || value === "1" || value === "yes" || value === "on") return true;
    } catch (_) {}
    return null;
  }

  function donationsStored() {
    try { return window.localStorage.getItem(DONATIONS_KEY) === "1"; } catch (_) {}
    return false;
  }

  function isY1DonationsDisabled() {
    if (donationsParam() === false) return true;
    return donationsStored();
  }

  var DONATIONS_CSS =
    "html.y1-donations-off [data-donations-appeal]," +
    "html.y1-donations-off .y1-contributor-stream-box { display: none !important; }";

  function applyDonationsState() {
    var root = document.documentElement;
    if (!root) return;
    root.classList.toggle("y1-donations-off", isY1DonationsDisabled());
    if (document.getElementById("y1-donations-css")) return;
    var style = document.createElement("style");
    style.id = "y1-donations-css";
    style.textContent = DONATIONS_CSS;
    (document.head || root).appendChild(style);
  }

  window.isY1DonationsDisabled = isY1DonationsDisabled;
  window.setY1DonationsDisabled = function (disabled) {
    try {
      if (disabled) window.localStorage.setItem(DONATIONS_KEY, "1");
      else window.localStorage.removeItem(DONATIONS_KEY);
    } catch (_) {}
    applyDonationsState();
    try {
      window.dispatchEvent(new CustomEvent("y1-donations-change", { detail: { disabled: !!disabled } }));
    } catch (_) {}
  };

  (function rememberDonationChoiceFromUrl() {
    var fromUrl = donationsParam();
    if (fromUrl === null) return;
    try {
      if (fromUrl) window.localStorage.removeItem(DONATIONS_KEY);
      else window.localStorage.setItem(DONATIONS_KEY, "1");
    } catch (_) {}
  })();

  applyDonationsState();
  /* The other Innioasis site is a different origin and cannot read this
     site's remembered choice, so links to it carry the flag along. This
     covers menu, footer, and in-page links, including ones added later. */
  document.addEventListener("click", function (event) {
    if (!isY1DonationsDisabled()) return;
    var link = event.target && event.target.closest ? event.target.closest("a[href]") : null;
    if (!link) return;
    var url;
    try { url = new URL(link.getAttribute("href"), window.location.origin); } catch (_) { return; }
    if (url.origin === window.location.origin) return;
    if (!/(^|\.)innioasis\.app$/i.test(url.hostname)) return;
    url.searchParams.set("donations", "false");
    link.href = url.toString();
  }, true);


  function detectPersona() {
    var path = (window.location.pathname || "").toLowerCase();
    if (
      path === "/" ||
      path.endsWith("/index.html") ||
      path.endsWith("/guide.html") ||
      path.endsWith("/installguide.html") ||
      path.endsWith("/troubleshooting.html") ||
      path.endsWith("/credits.html") ||
      path.endsWith("/support_devs.html") ||
      path.endsWith("/updater-comparison.html")
    ) {
      return "updater";
    }
    return "firmware";
  }

  function decorateCrossDomainHref(href) {
    if (!href) return href;
    try {
      var u = new URL(href, window.location.origin);
      if (window.isY1DonationsDisabled && window.isY1DonationsDisabled()) {
        u.searchParams.set("donations", "false");
      }
      return u.toString();
    } catch (_) {}
    return href;
  }

  var isThemesSite = (window.location.hostname === "themes.innioasis.app") || (window.location.port === "8081") || !!document.querySelector(".gallery-topbar");

  function decorateMainSiteHref(path) {
    if (!path) return path;
    if (isThemesSite) {
      var base = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
        ? (window.location.protocol + "//" + window.location.hostname + ":8080")
        : "https://innioasis.app";
      return decorateCrossDomainHref(base + path);
    }
    return decorateCrossDomainHref(path);
  }

  var persona = detectPersona();
  var isFirmwarePersona = persona === "firmware";
  var activeTitle = isThemesSite ? "Themes Gallery" : (isFirmwarePersona ? "Firmware Archive" : "Updater CE");
  var activeHomeHref = isFirmwarePersona ? "/firmware.html" : "/";

  (function updateDocumentTitle() {
    var path = (window.location.pathname || "").toLowerCase();
    var t = document.title || "";
    if (isThemesSite) {
      if (path === "" || path === "/" || path.endsWith("/index.html")) {
        document.title = "Innioasis Themes Gallery - Y1 and Y2 Rockbox themes";
        return;
      }
      if (t.indexOf("Themes Gallery") === -1) {
        var themeBase = t.split(/\s+[|\u00b7-]\s+Innioasis/)[0].trim();
        document.title = (themeBase || t) + " - Innioasis Themes Gallery";
      }
      return;
    }
    if (isFirmwarePersona) {
      if (t.indexOf("Innioasis Firmware Downloads") === -1) {
        var base = t.replace(/\s+[|·-]\s+Innioasis [^|·-]*$/, "").trim();
        document.title = (base || t) + " - Innioasis Firmware Downloads";
      }
    } else if (t.indexOf("Innioasis Updater") === -1) {
      var uBase = t.replace(/\s+[|·-]\s+Innioasis [^|·-]*$/, "").trim();
      document.title = (uBase || t) + " - Innioasis Updater";
    }
  })();

  var allSwitcherItems = [
    {
      id: "firmware",
      title: "Innioasis Firmware Archive",
      subtitle: "Original Software, custom ROMs & guides",
      href: "/firmware.html",
      icon: '<span class="lumen-app-icon lumen-app-icon--firmware" style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:8px;background:#181a24;border:1px solid rgba(255,255,255,0.14);box-shadow:0 2px 6px rgba(0,0,0,0.35);font-size:16px;line-height:1;flex-shrink:0;" aria-hidden="true">📚</span>'
    },
    {
      id: "updater",
      title: "Updater CE",
      subtitle: "One-click installer for Windows, macOS & Linux",
      href: "/",
      icon: '<span class="lumen-app-icon lumen-app-icon--updater" style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:8px;background:#181a24;border:1px solid rgba(255,255,255,0.14);box-shadow:0 2px 6px rgba(0,0,0,0.35);overflow:hidden;flex-shrink:0;" aria-hidden="true"><img src="/mtkclient/gui/images/icon.png" width="34" height="34" style="width:34px;height:34px;max-width:none;display:block;margin:-3px;" alt="" aria-hidden="true"></span>'
    },
    {
      id: "themes",
      title: "Themes Gallery",
      subtitle: "Themes for Innioasis Y1 & Y2 players",
      href: "https://themes.innioasis.app/",
      external: true,
      icon: '<span class="lumen-app-icon lumen-app-icon--themes" style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:8px;background:#181a24;border:1px solid rgba(255,255,255,0.14);box-shadow:0 2px 6px rgba(0,0,0,0.35);font-size:16px;line-height:1;flex-shrink:0;" aria-hidden="true">🎨</span>'
    }
  ];

  /* Only show the other two community sites that the user is not currently on */
  var switcherListHtml = allSwitcherItems
    .filter(function (item) {
      return item.id !== persona;
    })
    .map(function (item) {
      var href = item.external ? decorateCrossDomainHref(item.href) : item.href;
      return (
        '<li>' +
        '<a class="lumen-site-switcher-item" href="' + escapeHtml(href) + '"' + (item.external ? ' data-cross-site-link="1"' : '') + '>' +
        '<span class="lumen-site-switcher-item-icon">' + item.icon + '</span>' +
        '<span class="lumen-site-switcher-item-copy">' +
        '<strong>' + escapeHtml(item.title) + '</strong>' +
        '<small>' + escapeHtml(item.subtitle) + '</small>' +
        '</span>' +
        '</a>' +
        '</li>'
      );
    }).join("");

  function detectUserPlatformLabel() {
    var ua = (typeof navigator !== "undefined" && (navigator.userAgentData && navigator.userAgentData.platform) || navigator.userAgent || "").toLowerCase();
    if (/mac|iphone|ipad|ipod/i.test(ua)) return "for macOS";
    if (/win/i.test(ua)) return "for Windows";
    if (/linux|x11|android/i.test(ua)) return "for Linux";
    return "";
  }
  var platformSuffix = detectUserPlatformLabel();
  var ctaLabel = platformSuffix ? ("Get Updater " + platformSuffix) : "Get Updater CE";

  var brandIconHtml = isFirmwarePersona
    ? '<span class="lumen-brand-icon lumen-brand-icon--firmware" style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:8px;background:#141721;border:1px solid rgba(255,255,255,0.14);box-shadow:0 1px 4px rgba(0,0,0,0.3);font-size:16px;line-height:1;margin-right:8px;flex-shrink:0;" aria-hidden="true">📚</span>'
    : '<span class="lumen-brand-icon lumen-brand-icon--updater" style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:8px;background:#141721;border:1px solid rgba(255,255,255,0.14);box-shadow:0 1px 4px rgba(0,0,0,0.3);overflow:hidden;margin-right:8px;flex-shrink:0;" aria-hidden="true"><img src="/mtkclient/gui/images/icon.png" width="38" height="38" style="width:38px;height:38px;max-width:none;display:block;margin:-5px;" alt="" aria-hidden="true"></span>';

  (function ensureNavStyles() {
    if (document.getElementById("lumen-nav-styles")) return;
    var style = document.createElement("style");
    style.id = "lumen-nav-styles";
    style.textContent =
      '.logo { flex-shrink: 0 !important; white-space: nowrap !important; }' +
      '.lumen-brand-switcher-wrap { position: relative; display: inline-flex; align-items: center; flex-shrink: 0 !important; white-space: nowrap !important; }' +
      '.lumen-brand-bar { display: inline-flex; align-items: center; flex-shrink: 0 !important; white-space: nowrap !important; }' +
      '.lumen-brand-home { display: inline-flex; align-items: center; text-decoration: none !important; color: var(--lumen-text, #f8fafc) !important; flex-shrink: 0 !important; white-space: nowrap !important; }' +
      '.lumen-brand-title { color: var(--lumen-text, #f8fafc) !important; font-size: 1.15rem; font-weight: 700; letter-spacing: -0.02em; line-height: 1.2; white-space: nowrap !important; word-break: keep-all !important; flex-shrink: 0 !important; }' +
      ':root[data-lumen-theme="light"] .lumen-brand-title, :root[data-lumen-theme="light"] .lumen-brand-home { color: #0f172a !important; }' +
      ':root[data-lumen-theme="dark"] .lumen-brand-title, :root[data-lumen-theme="dark"] .lumen-brand-home { color: #f8fafc !important; }' +
      ':root[data-lumen-theme="2077"] .lumen-brand-title, :root[data-lumen-theme="2077"] .lumen-brand-home { color: #00f0ff !important; }' +
      ':root[data-lumen-theme="high-contrast"] .lumen-brand-title, :root[data-lumen-theme="high-contrast"] .lumen-brand-home { color: #ffffff !important; }' +
      '@media (prefers-color-scheme: light) { :root:not([data-lumen-theme="dark"]):not([data-lumen-theme="2077"]):not([data-lumen-theme="high-contrast"]) .lumen-brand-title, :root:not([data-lumen-theme="dark"]):not([data-lumen-theme="2077"]):not([data-lumen-theme="high-contrast"]) .lumen-brand-home { color: #0f172a !important; } }' +
      '.lumen-site-switcher-toggle { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; margin-left: 6px; padding: 0; border-radius: 6px; border: 1px solid var(--lumen-line, rgba(255,255,255,0.14)); background: var(--lumen-panel-soft, rgba(255,255,255,0.06)); color: var(--lumen-muted, #94a3b8); cursor: pointer; transition: all 0.15s ease; flex-shrink: 0 !important; }' +
      '.lumen-site-switcher-toggle:hover { background: var(--lumen-accent-wash, rgba(99,102,241,0.15)); color: var(--lumen-paper, #fff); border-color: var(--lumen-accent, #6366f1); }' +
      ':root[data-lumen-theme="light"] .lumen-site-switcher-toggle { background: rgba(0,0,0,0.04); border-color: rgba(0,0,0,0.12); color: #475569; }' +
      ':root[data-lumen-theme="light"] .lumen-site-switcher-toggle:hover { background: rgba(0,0,0,0.08); color: #0f172a; }' +
      ':root[data-lumen-theme="2077"] .lumen-site-switcher-toggle { background: rgba(35,230,224,0.08); border-color: rgba(35,230,224,0.3); color: #23e6e0; }' +
      ':root[data-lumen-theme="2077"] .lumen-site-switcher-toggle:hover { background: rgba(255,30,60,0.18); border-color: #ff1e3c; color: #ff1e3c; }' +
      '@media (prefers-color-scheme: light) { :root[data-lumen-theme="auto"] .lumen-site-switcher-toggle { background: rgba(0,0,0,0.04); border-color: rgba(0,0,0,0.12); color: #475569; } }' +
      '.lumen-site-switcher-tray { position: absolute; top: calc(100% + 8px); left: 0; width: max-content; min-width: min(320px, calc(100vw - 1.5rem)); max-width: min(400px, calc(100vw - 1.5rem)); background: var(--lumen-panel, #12141c); border: 1px solid var(--lumen-line-strong, rgba(255,255,255,0.18)); border-radius: 14px; padding: 12px; box-shadow: 0 12px 36px rgba(0,0,0,0.45); z-index: 10002; box-sizing: border-box; }' +
      ':root[data-lumen-theme="light"] .lumen-site-switcher-tray { background: #ffffff; border-color: rgba(0,0,0,0.12); box-shadow: 0 12px 36px rgba(0,0,0,0.15); }' +
      ':root[data-lumen-theme="2077"] .lumen-site-switcher-tray { background: #0c0d14; border-color: rgba(35,230,224,0.45); box-shadow: 0 12px 36px rgba(0,0,0,0.65), 0 0 16px rgba(35,230,224,0.2); }' +
      '@media (prefers-color-scheme: light) { :root[data-lumen-theme="auto"] .lumen-site-switcher-tray { background: #ffffff; border-color: rgba(0,0,0,0.12); box-shadow: 0 12px 36px rgba(0,0,0,0.15); } }' +
      '.lumen-site-switcher-heading { margin: 0 0 8px 4px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--lumen-muted, #94a3b8); }' +
      ':root[data-lumen-theme="light"] .lumen-site-switcher-heading { color: #64748b; }' +
      ':root[data-lumen-theme="2077"] .lumen-site-switcher-heading { color: #ff1e3c; }' +
      '@media (prefers-color-scheme: light) { :root[data-lumen-theme="auto"] .lumen-site-switcher-heading { color: #64748b; } }' +
      '.lumen-site-switcher-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }' +
      '.lumen-site-switcher-item { display: flex; align-items: center; gap: 12px; padding: 8px 10px; border-radius: 9px; text-decoration: none; background: transparent; border: 1px solid transparent; transition: all 0.15s ease; }' +
      '.lumen-site-switcher-item:hover { background: var(--lumen-accent-wash, rgba(99,102,241,0.1)); border-color: var(--lumen-line, rgba(255,255,255,0.1)); }' +
      ':root[data-lumen-theme="light"] .lumen-site-switcher-item:hover { background: rgba(0,0,0,0.04); border-color: rgba(0,0,0,0.08); }' +
      '@media (prefers-color-scheme: light) { :root[data-lumen-theme="auto"] .lumen-site-switcher-item:hover { background: rgba(0,0,0,0.04); border-color: rgba(0,0,0,0.08); } }' +
      '.lumen-site-switcher-item-icon { display: flex; align-items: center; justify-content: center; flex-shrink: 0; }' +
      '.lumen-site-switcher-item-copy { display: flex; flex-direction: column; gap: 2px; min-width: 0; }' +
      '.lumen-site-switcher-item-copy strong { font-size: 0.92rem; font-weight: 700; color: var(--lumen-text, #f8fafc); line-height: 1.2; }' +
      '.lumen-site-switcher-item-copy small { font-size: 0.78rem; color: var(--lumen-muted, #94a3b8); line-height: 1.25; white-space: normal; overflow-wrap: break-word; }' +
      ':root[data-lumen-theme="light"] .lumen-site-switcher-item-copy strong { color: #0f172a; }' +
      ':root[data-lumen-theme="light"] .lumen-site-switcher-item-copy small { color: #64748b; }' +
      ':root[data-lumen-theme="2077"] .lumen-site-switcher-item-copy strong { color: #e9f0f5; }' +
      ':root[data-lumen-theme="2077"] .lumen-site-switcher-item-copy small { color: #aab8c8; }' +
      '@media (prefers-color-scheme: light) { :root[data-lumen-theme="auto"] .lumen-site-switcher-item-copy strong { color: #0f172a; } :root[data-lumen-theme="auto"] .lumen-site-switcher-item-copy small { color: #64748b; } }' +
      '.lumen-nav-install-cta { display: inline-flex !important; align-items: center !important; justify-content: center !important; padding: 6px 14px !important; border-radius: 9999px !important; font-weight: 700 !important; font-size: 0.85rem !important; line-height: 1.2 !important; text-decoration: none !important; background: linear-gradient(135deg, rgba(56, 189, 248, 0.28), rgba(99, 102, 241, 0.36)) !important; border: 1px solid rgba(56, 189, 248, 0.55) !important; color: #f0f9ff !important; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25) !important; transition: transform 0.15s ease, background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease !important; flex-shrink: 0 !important; }' +
      '.lumen-nav-install-cta:hover { transform: translateY(-1px) !important; background: linear-gradient(135deg, rgba(56, 189, 248, 0.42), rgba(99, 102, 241, 0.52)) !important; border-color: rgba(56, 189, 248, 0.8) !important; color: #ffffff !important; box-shadow: 0 4px 14px rgba(56, 189, 248, 0.35) !important; }' +
      ':root[data-lumen-theme="light"] .lumen-nav-install-cta { background: linear-gradient(135deg, #0284c7, #4f46e5) !important; border-color: #0284c7 !important; color: #ffffff !important; box-shadow: 0 2px 8px rgba(2, 132, 199, 0.25) !important; }' +
      ':root[data-lumen-theme="light"] .lumen-nav-install-cta:hover { background: linear-gradient(135deg, #0369a1, #4338ca) !important; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.4) !important; }' +
      ':root[data-lumen-theme="2077"] .lumen-nav-install-cta { background: rgba(255, 30, 60, 0.18) !important; border-color: #ff1e3c !important; color: #ff1e3c !important; box-shadow: 0 0 10px rgba(255, 30, 60, 0.35) !important; }' +
      ':root[data-lumen-theme="2077"] .lumen-nav-install-cta:hover { background: #ff1e3c !important; color: #0d0e15 !important; box-shadow: 0 0 18px rgba(255, 30, 60, 0.7) !important; }' +
      '@media (prefers-color-scheme: light) { :root[data-lumen-theme="auto"] .lumen-nav-install-cta { background: linear-gradient(135deg, #0284c7, #4f46e5) !important; border-color: #0284c7 !important; color: #ffffff !important; box-shadow: 0 2px 8px rgba(2, 132, 199, 0.25) !important; } }' +
      '.lumen-notices-wrap { position: relative; display: inline-flex; align-items: center; }' +
      '.lumen-notices-btn { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--lumen-line, rgba(255,255,255,0.14)); background: var(--lumen-panel-soft, rgba(255,255,255,0.06)); color: var(--lumen-text, #f8fafc); cursor: pointer; position: relative; transition: all 0.15s ease; }' +
      '.lumen-notices-btn:hover { background: rgba(255,255,255,0.12); color: var(--lumen-text, #fff); }' +
      ':root[data-lumen-theme="light"] .lumen-notices-btn { background: rgba(0,0,0,0.04); border-color: rgba(0,0,0,0.12); color: #0f172a; }' +
      ':root[data-lumen-theme="light"] .lumen-notices-btn:hover { background: rgba(0,0,0,0.08); color: #0f172a; }' +
      '@media (prefers-color-scheme: light) { :root:not([data-lumen-theme="dark"]):not([data-lumen-theme="2077"]):not([data-lumen-theme="high-contrast"]) .lumen-notices-btn { background: rgba(0,0,0,0.04); border-color: rgba(0,0,0,0.12); color: #0f172a; } :root:not([data-lumen-theme="dark"]):not([data-lumen-theme="2077"]):not([data-lumen-theme="high-contrast"]) .lumen-notices-btn:hover { background: rgba(0,0,0,0.08); color: #0f172a; } }' +
      ':root[data-lumen-theme="2077"] .lumen-notices-btn { background: rgba(35,230,224,0.08); border-color: rgba(35,230,224,0.35); color: #23e6e0; }' +
      ':root[data-lumen-theme="2077"] .lumen-notices-btn:hover { background: rgba(255,30,60,0.18); border-color: #ff1e3c; color: #ff1e3c; }' +
      '.lumen-notices-badge { position: absolute; top: -3px; right: -3px; min-width: 16px; height: 16px; border-radius: 9999px; background: #ef4444; color: #fff; font-size: 0.68rem; font-weight: 800; display: flex; align-items: center; justify-content: center; padding: 0 4px; box-sizing: border-box; pointer-events: none; }' +
      '.lumen-notices-badge[hidden] { display: none !important; }' +
      '.lumen-notices-tray { position: fixed; z-index: 10003; box-sizing: border-box; width: 350px; max-width: calc(100vw - 24px); max-height: calc(100vh - 170px); max-height: calc(100dvh - 170px); overflow-y: auto; -webkit-overflow-scrolling: touch; background: var(--lumen-panel, #12141c); border: 1px solid var(--lumen-line-strong, rgba(255,255,255,0.18)); border-radius: 14px; padding: 14px; box-shadow: 0 16px 48px rgba(0,0,0,0.6); font-family: inherit; }' +
      '@media (max-width: 640px) { .lumen-notices-tray { left: 12px !important; right: 12px !important; width: auto !important; max-width: calc(100vw - 24px) !important; } }' +
      ':root[data-lumen-theme="light"] .lumen-notices-tray { background: #ffffff; border-color: rgba(0,0,0,0.12); box-shadow: 0 16px 48px rgba(0,0,0,0.18); color: #0f172a; }' +
      ':root[data-lumen-theme="2077"] .lumen-notices-tray { background: #0c0d14; border-color: #23e6e0; box-shadow: 0 16px 48px rgba(0,0,0,0.8), 0 0 18px rgba(35,230,224,0.3); color: #e9f0f5; }' +
      ':root[data-lumen-theme="high-contrast"] .lumen-notices-tray { background: #000000; border-color: #ffffff; color: #ffffff; box-shadow: 0 0 0 2px #ffffff; }' +
      ':root[data-lumen-theme="high-contrast"] .lumen-notices-tray-header strong { color: #ffffff; }' +
      ':root[data-lumen-theme="high-contrast"] .lumen-notices-all-link { color: #ffff00; }' +
      ':root[data-lumen-theme="high-contrast"] .lumen-notice-card { background: #000000; border-color: #ffffff; }' +
      ':root[data-lumen-theme="high-contrast"] .lumen-notice-type { background: #ffffff; color: #000000; }' +
      ':root[data-lumen-theme="high-contrast"] .lumen-notice-title { color: #ffffff; }' +
      ':root[data-lumen-theme="high-contrast"] .lumen-notice-summary { color: #e2e8f0; }' +
      ':root[data-lumen-theme="high-contrast"] .lumen-notice-link { color: #ffff00; }' +
      '@media (prefers-color-scheme: light) {' +
      '  :root[data-lumen-theme="auto"] .lumen-notices-tray { background: #ffffff; border-color: rgba(0,0,0,0.12); box-shadow: 0 16px 48px rgba(0,0,0,0.18); color: #0f172a; }' +
      '  :root[data-lumen-theme="auto"] .lumen-notices-tray-header strong { color: #0f172a; }' +
      '  :root[data-lumen-theme="auto"] .lumen-notice-card { background: #f8fafc; border-color: #e2e8f0; }' +
      '  :root[data-lumen-theme="auto"] .lumen-notice-title { color: #0f172a; }' +
      '  :root[data-lumen-theme="auto"] .lumen-notice-summary { color: #475569; }' +
      '}' +
      '.lumen-notices-tray-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--lumen-line, rgba(255,255,255,0.1)); }' +
      '.lumen-notices-tray-header strong { font-size: 0.9rem; font-weight: 700; letter-spacing: -0.01em; color: var(--lumen-text, #f8fafc); }' +
      ':root[data-lumen-theme="light"] .lumen-notices-tray-header strong { color: #0f172a; }' +
      ':root[data-lumen-theme="2077"] .lumen-notices-tray-header strong { color: #23e6e0; }' +
      '.lumen-notices-all-link { font-size: 0.78rem; font-weight: 600; text-decoration: none; color: var(--lumen-accent, #6366f1); }' +
      ':root[data-lumen-theme="2077"] .lumen-notices-all-link { color: #ff1e3c; }' +
      '.lumen-notice-card { border-radius: 10px; padding: 10px 12px; margin-bottom: 8px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); text-align: left; }' +
      ':root[data-lumen-theme="light"] .lumen-notice-card { background: #f8fafc; border-color: #e2e8f0; }' +
      ':root[data-lumen-theme="2077"] .lumen-notice-card { background: rgba(35,230,224,0.04); border-color: rgba(35,230,224,0.22); }' +
      '.lumen-notice-meta { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; font-size: 0.7rem; }' +
      '.lumen-notice-type { font-weight: 800; font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; background: rgba(59,130,246,0.18); color: #60a5fa; }' +
      ':root[data-lumen-theme="2077"] .lumen-notice-type { background: rgba(35,230,224,0.15); color: #23e6e0; }' +
      '.lumen-notice-models { font-weight: 600; color: var(--lumen-muted, #94a3b8); }' +
      '.lumen-notice-date { color: var(--lumen-muted, #94a3b8); margin-left: auto; }' +
      '.lumen-notice-title { margin: 4px 0 3px 0; font-size: 0.86rem; font-weight: 700; line-height: 1.3; color: var(--lumen-text, #f8fafc); }' +
      ':root[data-lumen-theme="light"] .lumen-notice-title { color: #0f172a; }' +
      ':root[data-lumen-theme="2077"] .lumen-notice-title { color: #e9f0f5; }' +
      '.lumen-notice-summary { margin: 0 0 6px 0; font-size: 0.78rem; line-height: 1.4; color: var(--lumen-muted, #94a3b8); }' +
      ':root[data-lumen-theme="light"] .lumen-notice-summary { color: #475569; }' +
      ':root[data-lumen-theme="2077"] .lumen-notice-summary { color: #aab8c8; }' +
      '.lumen-notice-full { max-height: 190px; overflow-y: auto; -webkit-overflow-scrolling: touch; margin: 2px 0 8px; padding-right: 4px; font-size: 0.8rem; line-height: 1.5; color: var(--lumen-muted, #94a3b8); }' +
      '.lumen-notice-full > :first-child { margin-top: 0; }' +
      '.lumen-notice-full p { margin: 0 0 8px; }' +
      '.lumen-notice-full ul, .lumen-notice-full ol { margin: 0 0 8px; padding-left: 18px; }' +
      '.lumen-notice-full li { margin: 3px 0; }' +
      '.lumen-notice-full h2, .lumen-notice-full h3, .lumen-notice-full h4 { margin: 10px 0 4px; font-size: 0.86rem; line-height: 1.3; color: var(--lumen-text, #f8fafc); }' +
      '.lumen-notice-full a { color: var(--lumen-accent, #6366f1); text-decoration: underline; }' +
      '.lumen-notice-full code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .92em; background: rgba(255,255,255,.08); padding: 1px 4px; border-radius: 4px; }' +
      '.lumen-notice-full pre { background: rgba(255,255,255,.06); padding: 8px 10px; border-radius: 8px; overflow-x: auto; }' +
      '.lumen-notice-full pre code { background: none; padding: 0; }' +
      '.lumen-notice-full blockquote { margin: 0 0 8px; padding-left: 10px; border-left: 2px solid var(--lumen-line-strong, rgba(255,255,255,.2)); }' +
      '.lumen-notice-full img { display: block; max-width: 100%; height: auto; margin: 8px 0; border-radius: 8px; }' +
      '.lumen-notice-full hr { border: none; border-top: 1px solid var(--lumen-line, rgba(255,255,255,.12)); margin: 10px 0; }' +
      ':root[data-lumen-theme="light"] .lumen-notice-full { color: #475569; }' +
      ':root[data-lumen-theme="light"] .lumen-notice-full h2, :root[data-lumen-theme="light"] .lumen-notice-full h3, :root[data-lumen-theme="light"] .lumen-notice-full h4 { color: #0f172a; }' +
      '.lumen-notice-actions { display: flex; align-items: center; gap: 10px; }' +
      '.lumen-notice-open { display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 50%; border: 1px solid var(--lumen-line, rgba(255,255,255,0.16)); color: var(--lumen-muted, #94a3b8); text-decoration: none; transition: color .15s ease, border-color .15s ease, background .15s ease; }' +
      '.lumen-notice-open:hover { color: var(--lumen-text, #fff); border-color: var(--lumen-line-strong, rgba(255,255,255,0.3)); background: rgba(255,255,255,0.08); }' +
      '.lumen-notice-open svg { width: 15px; height: 15px; display: block; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }' +
      ':root[data-lumen-theme="high-contrast"] .lumen-notice-open { border-color: #ffffff; color: #ffffff; }' +
      '.lumen-notice-link { font-size: 0.76rem; font-weight: 600; text-decoration: none; color: var(--lumen-accent, #6366f1); }' +
      ':root[data-lumen-theme="2077"] .lumen-notice-link { color: #ff1e3c; }' +
      /* Contextual notice card: mounted by a page that knows what the visitor
         is looking at (firmware.html). One notice at a time, rotating through
         the eligible set. The tray beside the bell always lists every notice. */
      '.lumen-context-notice-slot:empty { display: none; }' +
      '.lumen-context-notice { display: block; margin: 0 0 14px; padding: 11px 14px 10px; border-radius: 12px; border: 1px solid var(--lumen-line, rgba(255,255,255,0.12)); border-left: 3px solid var(--lumen-accent, #6366f1); background: var(--lumen-panel-soft, rgba(255,255,255,0.04)); transition: opacity .16s ease; }' +
      '.lumen-context-notice.is-fading { opacity: 0; }' +
      '.lumen-context-notice[data-severity="warning"] { border-left-color: #f59e0b; }' +
      '.lumen-context-notice[data-severity="critical"] { border-left-color: #ef4444; }' +
      '.lumen-context-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: .72rem; }' +
      '.lumen-context-kicker { font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--lumen-muted, #94a3b8); }' +
      '.lumen-context-severity { font-weight: 800; font-size: .64rem; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; letter-spacing: .05em; background: rgba(59,130,246,0.16); color: #60a5fa; }' +
      '.lumen-context-notice[data-severity="warning"] .lumen-context-severity { background: rgba(245,158,11,0.18); color: #fbbf24; }' +
      '.lumen-context-notice[data-severity="critical"] .lumen-context-severity { background: rgba(239,68,68,0.18); color: #f87171; }' +
      '.lumen-context-target { color: var(--lumen-muted, #94a3b8); font-weight: 600; }' +
      ':root[data-lumen-theme="light"] .lumen-context-kicker, :root[data-lumen-theme="light"] .lumen-context-target { color: #64748b; }' +
      ':root[data-lumen-theme="2077"] .lumen-context-kicker { color: #23e6e0; }' +
      '.lumen-context-all { margin-left: auto; font-weight: 600; color: var(--lumen-accent, #6366f1); text-decoration: none; }' +
      ':root[data-lumen-theme="2077"] .lumen-context-all { color: #ff1e3c; }' +
      '.lumen-context-title { margin: 6px 0 3px; font-size: .95rem; font-weight: 700; line-height: 1.3; color: var(--lumen-text, #f8fafc); }' +
      ':root[data-lumen-theme="light"] .lumen-context-title { color: #0f172a; }' +
      '.lumen-context-title a { color: inherit; text-decoration: none; }' +
      '.lumen-context-title a:hover { text-decoration: underline; }' +
      '.lumen-context-summary { margin: 0; font-size: .82rem; line-height: 1.45; color: var(--lumen-muted, #94a3b8); }' +
      ':root[data-lumen-theme="light"] .lumen-context-summary { color: #475569; }' +
      '.lumen-context-foot { display: flex; align-items: center; gap: 10px; margin-top: 8px; }' +
      '.lumen-context-dots { display: flex; align-items: center; gap: 2px; }' +
      '.lumen-context-dot { position: relative; width: 28px; height: 28px; padding: 0; border: none; border-radius: 50%; background: transparent; cursor: pointer; }' +
      '.lumen-context-dot::before { content: ""; position: absolute; inset: 10px; border-radius: 50%; background: var(--lumen-line-strong, rgba(255,255,255,.25)); transition: background .15s ease, transform .15s ease; }' +
      '.lumen-context-dot.is-active::before { background: var(--lumen-accent, #6366f1); transform: scale(1.3); }' +
      '.lumen-context-dot:hover::before { background: var(--lumen-text, #fff); }' +
      '.lumen-context-dot:focus-visible { outline: 2px solid var(--lumen-accent, #6366f1); outline-offset: 2px; }' +
      ':root[data-lumen-theme="2077"] .lumen-context-dot.is-active::before { background: #23e6e0; }' +
      ':root[data-lumen-theme="high-contrast"] .lumen-context-dot::before { background: #ffffff; }' +
      '.lumen-context-link { margin-left: auto; font-size: .76rem; font-weight: 600; color: var(--lumen-accent, #6366f1); text-decoration: none; }' +
      ':root[data-lumen-theme="2077"] .lumen-context-link { color: #ff1e3c; }' +
      '@media (prefers-reduced-motion: reduce) { .lumen-context-notice { transition: none; } .lumen-context-dot::before { transition: none; } }' +
      '.lumen-nav-social-btn { display: inline-flex !important; align-items: center !important; justify-content: center !important; width: auto !important; height: auto !important; min-width: 0 !important; min-height: 0 !important; padding: 4px 6px !important; background: transparent !important; border: none !important; box-shadow: none !important; border-radius: 0 !important; text-decoration: none !important; transition: transform 0.15s ease, opacity 0.15s ease, color 0.15s ease !important; flex-shrink: 0 !important; cursor: pointer !important; opacity: 0.88 !important; }' +
      '.lumen-nav-social-btn:hover { opacity: 1 !important; transform: scale(1.15) !important; background: transparent !important; border: none !important; box-shadow: none !important; }' +
      '.lumen-nav-social-btn--reddit { color: #ff4500 !important; }' +
      '.lumen-nav-social-btn--reddit:hover { color: #ff5722 !important; filter: drop-shadow(0 0 6px rgba(255, 69, 0, 0.5)) !important; }' +
      '.lumen-nav-social-btn--discord { color: #5865f2 !important; }' +
      '.lumen-nav-social-btn--discord:hover { color: #7289da !important; filter: drop-shadow(0 0 6px rgba(88, 101, 242, 0.5)) !important; }' +
      '.lumen-nav-social-btn svg { display: block !important; width: 22px !important; height: 22px !important; }' +
      '@media (max-width: 1040px) { body.site-themes-app .nav-links a { padding: 0.4rem 0.45rem; font-size: 0.82rem; } .nav-container { padding: 0.5rem 1rem; gap: 0.35rem; } }' +
      /* The header collapses into the hamburger only when nav.js decides the
         inline links no longer fit, so links are never squeezed out of the bar. */
      '.nav-container.nav-compact { position: relative !important; }' +
      '.nav-container.nav-compact .nav-links { display: none !important; position: fixed; top: 72px; right: 12px; left: auto; margin: 0 !important; padding: .5rem !important; list-style: none; flex-flow: row wrap !important; align-items: stretch !important; align-content: flex-start !important; gap: .15rem !important; width: min(300px, calc(100vw - 1.5rem)); max-height: min(72vh, 520px); overflow-y: auto; overscroll-behavior: contain; -webkit-overflow-scrolling: touch; border: 1px solid var(--lumen-line-strong, rgba(255,255,255,0.18)); border-radius: 14px; background: var(--lumen-panel, #12141c); box-shadow: 0 18px 50px rgba(0,0,0,0.55); z-index: 10002; box-sizing: border-box; }' +
      '.nav-container.nav-compact .nav-links.active { display: flex !important; }' +
      '.nav-container.nav-compact .nav-links li { flex: 1 0 100%; width: 100%; margin: 0 !important; padding: 0 !important; list-style: none; }' +
      '.nav-container.nav-compact .nav-links a { display: flex !important; width: 100%; min-height: 0 !important; height: auto !important; align-items: center; justify-content: flex-start !important; padding: .7rem .8rem !important; border-radius: 10px; white-space: nowrap; font-size: .92rem; line-height: 1.3; }' +
      '.nav-container.nav-compact .nav-links a:hover, .nav-container.nav-compact .nav-links a:focus-visible { background: rgba(255,255,255,0.07) !important; }' +
      '.nav-container.nav-compact .nav-links .lumen-nav-install-cta { justify-content: center !important; padding: .75rem 1rem !important; }' +
      /* The two social icons share one row instead of taking a row each. */
      '.nav-container.nav-compact .nav-links li:has(> .lumen-nav-social-btn) { flex: 0 0 auto; width: auto; }' +
      '.nav-container.nav-compact .nav-links a.lumen-nav-social-btn { width: 44px !important; min-height: 44px !important; justify-content: center !important; padding: 0 !important; }' +
      /* The icon is three stacked bars; switching it on must not line them up. */
      '.nav-container.nav-compact .hamburger { display: inline-flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; gap: 4px !important; }' +
      '.nav-container.nav-compact .hamburger span { width: 20px !important; height: 2px !important; margin: 0 !important; border-radius: 2px; transition: transform .2s ease, opacity .15s ease; }' +
      '.nav-container.nav-compact .hamburger.is-active span:nth-child(1) { transform: translateY(6px) rotate(45deg); }' +
      '.nav-container.nav-compact .hamburger.is-active span:nth-child(2) { opacity: 0; }' +
      '.nav-container.nav-compact .hamburger.is-active span:nth-child(3) { transform: translateY(-6px) rotate(-45deg); }' +
      /* A phone header must fit its own width: the brand gives way, the theme
         select stops claiming a wide box, and the menu button stays reachable. */
      '@media (max-width: 640px) {' +
      '  #nav-root .nav-container { padding: .5rem .7rem !important; gap: .45rem !important; }' +
      '  #nav-root .nav-container .lumen-brand-switcher-wrap { flex: 1 1 auto !important; min-width: 0 !important; }' +
      '  #nav-root .nav-container .lumen-brand-bar { min-width: 0 !important; }' +
      '  #nav-root .nav-container .lumen-brand-title { font-size: .95rem !important; min-width: 0 !important; overflow: hidden !important; text-overflow: ellipsis !important; white-space: nowrap !important; }' +
      '  #nav-root .nav-container .nav-tools { gap: .3rem !important; flex: 0 0 auto !important; }' +
      '  #nav-root .nav-container .lumen-theme-control { min-width: 0 !important; }' +
      '  #nav-root .nav-container .lumen-theme-control select { max-width: 84px !important; padding-left: .4rem !important; }' +
      '}';
    document.head.appendChild(style);
  })();

  var root = document.getElementById("nav-root");
  if (root) {
    root.innerHTML =
      '<nav aria-label="Primary navigation">' +
      '<div class="nav-container">' +
      '<div class="logo lumen-brand-switcher-wrap">' +
      '<div class="lumen-brand-bar">' +
      '<a class="lumen-brand-home" href="' + escapeHtml(activeHomeHref) + '">' +
      brandIconHtml +
      '<span class="lumen-brand-title" id="lumen-brand-title">' + escapeHtml(activeTitle) + '</span>' +
      '</a>' +
      '<button type="button" class="lumen-site-switcher-toggle" id="lumen-site-switcher-toggle" aria-expanded="false" aria-controls="lumen-site-switcher-tray" aria-label="Switch Innioasis site persona" title="Switch site">' +
      '<svg class="lumen-site-switcher-glyph" viewBox="0 0 16 16" width="12" height="12" fill="currentColor" aria-hidden="true"><path d="M4.2 6.2a.75.75 0 0 1 1.06 0L8 8.94l2.74-2.74a.75.75 0 1 1 1.06 1.06l-3.27 3.27a.75.75 0 0 1-1.06 0L4.2 7.26a.75.75 0 0 1 0-1.06z"/></svg>' +
      '</button>' +
      '</div>' +
      '<div class="lumen-site-switcher-tray" id="lumen-site-switcher-tray" hidden role="menu" aria-label="Switch between Themes Gallery, Updater CE, and Firmware Archive">' +
      '<p class="lumen-site-switcher-heading">Innioasis Community Sites</p>' +
      '<ul class="lumen-site-switcher-list">' + switcherListHtml + '</ul>' +
      '</div>' +
      '</div>' +
      '<div class="nav-tools">' +
      '<div class="lumen-notices-wrap" id="lumen-notices-wrap">' +
      '<button type="button" class="lumen-notices-btn" id="lumen-notices-btn" aria-expanded="false" aria-controls="lumen-notices-tray" aria-label="Community notices and device safety alerts" title="Notices">' +
      '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 2.5a4.5 4.5 0 0 0-4.5 4.5v2.6c0 .8-.3 1.6-.8 2.2L3.5 13.2h13l-1.2-1.4a3.4 3.4 0 0 1-.8-2.2V7A4.5 4.5 0 0 0 10 2.5z"/><path d="M8.2 15.5a2 2 0 0 0 3.6 0"/></svg>' +
      '<span class="lumen-notices-badge" id="lumen-notices-badge" hidden style="display: none;"></span>' +
      '</button>' +
      '<div class="lumen-notices-tray" id="lumen-notices-tray" hidden role="region" aria-label="Community notices">' +
      '<div class="lumen-notices-tray-header">' +
      '<strong>Community Notices</strong>' +
      '<a href="' + escapeHtml(decorateMainSiteHref("/notices.html")) + '" class="lumen-notices-all-link">All notices &rarr;</a>' +
      '</div>' +
      '<div class="lumen-notices-tray-body" id="lumen-notices-tray-body">' +
      '<p class="lumen-notices-empty">Loading notices...</p>' +
      '</div>' +
      '</div>' +
      '</div>' +
      '<label class="lumen-theme-control"><span>Theme</span><select id="lumen-theme-select" aria-label="Choose site colour theme"><option value="auto">Auto</option><option value="light">Light</option><option value="dark">Dark</option><option value="high-contrast">High contrast</option><option value="2077">2077</option></select></label>' +
      '<button class="hamburger" id="hamburger" type="button" aria-label="Open navigation menu" aria-controls="navLinks" aria-expanded="false"><span></span><span></span><span></span></button>' +
      '</div>' +
      '<ul class="nav-links" id="navLinks">' +
      '<li><a class="lumen-nav-install-cta" id="lumen-nav-install-cta" href="' + escapeHtml(decorateMainSiteHref("/guide.html")) + '">' + escapeHtml(ctaLabel) + '</a></li>' +
      '<li><a href="' + escapeHtml(decorateMainSiteHref("/firmware.html?view=software")) + '">Software Updates</a></li>' +
      '<li><a href="' + escapeHtml(decorateMainSiteHref("/firmware.html?view=firmware")) + '">Firmware Downloads</a></li>' +
      '<li><a href="' + escapeHtml(decorateCrossDomainHref("https://themes.innioasis.app/")) + '" data-cross-site-link="1">Themes</a></li>' +
      '<li><a href="https://reddit.com/r/innioasis" target="_blank" rel="noopener noreferrer" class="lumen-nav-social-btn lumen-nav-social-btn--reddit" aria-label="r/innioasis on Reddit" title="Reddit r/innioasis"><svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true"><path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 0 0 .029-.463.33.33 0 0 0-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 0 0-.232-.095z"/></svg></a></li>' +
      '<li><a href="https://discord.gg/zHrT2zrcek" target="_blank" rel="noopener noreferrer" class="lumen-nav-social-btn lumen-nav-social-btn--discord" aria-label="Join our Discord community" title="Discord community"><svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.061 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.894.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.028zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg></a></li>' +
      '</ul>' +
      '</div>' +
      '</nav>';
  }

  /* Site Switcher Dropdown Logic */
  var switcherToggle = document.getElementById("lumen-site-switcher-toggle");
  var switcherTray = document.getElementById("lumen-site-switcher-tray");
  function setSwitcherOpen(open) {
    if (!switcherToggle || !switcherTray) return;
    if (open) {
      setNoticesOpen(false);
      setMenuOpen(false);
    }
    switcherTray.hidden = !open;
    switcherToggle.setAttribute("aria-expanded", open ? "true" : "false");
  }
  if (switcherToggle && switcherTray) {
    switcherToggle.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      setNoticesOpen(false);
      setSwitcherOpen(switcherTray.hidden);
    });
  }

  /* Notices Bell Logic */
  var noticesBtn = document.getElementById("lumen-notices-btn");
  var noticesTray = document.getElementById("lumen-notices-tray");
  var noticesBadge = document.getElementById("lumen-notices-badge");
  var noticesBody = document.getElementById("lumen-notices-tray-body");

  function adjustNoticesTrayPosition() {
    if (!noticesTray || !noticesBtn) return;
    var rect = noticesBtn.getBoundingClientRect();
    var navEl = noticesBtn.closest("nav") || noticesBtn.closest(".navbar") || noticesBtn.closest(".nav-container");
    var navBottom = navEl ? navEl.getBoundingClientRect().bottom : rect.bottom;
    var topPos = Math.round(Math.max(rect.bottom + 8, navBottom + 6));

    var dockEl = document.getElementById("y1-site-dock-bar") || document.getElementById("support-toolbar-container") || document.querySelector(".y1-site-dock-wrap") || document.querySelector(".y1-site-dock-bar");
    var viewportH = window.innerHeight || document.documentElement.clientHeight || 600;
    var dockTop = (dockEl && !dockEl.hidden) ? dockEl.getBoundingClientRect().top : (viewportH - 80);
    var maxTrayBottom = Math.min(dockTop - 12, viewportH - 84);
    var maxAvailableHeight = Math.max(140, Math.floor(maxTrayBottom - topPos));

    noticesTray.style.position = "fixed";
    noticesTray.style.top = topPos + "px";
    noticesTray.style.maxHeight = maxAvailableHeight + "px";
    noticesTray.style.overflowY = "auto";
    noticesTray.style.webkitOverflowScrolling = "touch";

    if (window.innerWidth <= 640) {
      noticesTray.style.left = "12px";
      noticesTray.style.right = "12px";
      noticesTray.style.width = "auto";
      noticesTray.style.maxWidth = "calc(100vw - 24px)";
      return;
    }

    var trayWidth = Math.min(360, window.innerWidth - 24);
    var bellCenter = rect.left + (rect.width / 2);
    var desiredLeft = Math.round(bellCenter - (trayWidth / 2));
    desiredLeft = Math.max(12, Math.min(desiredLeft, window.innerWidth - trayWidth - 12));

    noticesTray.style.left = desiredLeft + "px";
    noticesTray.style.right = "auto";
    noticesTray.style.width = trayWidth + "px";
    noticesTray.style.maxWidth = "calc(100vw - 24px)";
  }

  function setNoticesOpen(open) {
    if (!noticesBtn || !noticesTray) return;
    if (open) {
      setSwitcherOpen(false);
      setMenuOpen(false);
    }
    noticesTray.hidden = !open;
    noticesBtn.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      adjustNoticesTrayPosition();
      noticesTray.scrollTop = 0;
      if (noticesBadge) {
        try {
          var ids = (noticesTray.getAttribute("data-notice-ids") || "").split(",").filter(Boolean);
          if (ids.length) localStorage.setItem("y1_seen_notices", ids.join(","));
        } catch (_) {}
        noticesBadge.textContent = "";
        noticesBadge.hidden = true;
        noticesBadge.style.display = "none";
      }
    }
  }

  window.addEventListener("resize", function () {
    if (noticesTray && !noticesTray.hidden) adjustNoticesTrayPosition();
  });
  window.addEventListener("scroll", function () {
    if (noticesTray && !noticesTray.hidden) adjustNoticesTrayPosition();
  }, { passive: true });

  if (noticesBtn && noticesTray) {
    noticesBtn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      setSwitcherOpen(false);
      setNoticesOpen(noticesTray.hidden);
    });
  }

  /* Minimal, safe Markdown for a notice's <full_content>: images, headings, lists,
     quotes, fenced code, rules, bold, italic, inline code and https links/images.
     The text is escaped before anything is added, so a notice can never
     inject markup or script into the page. */
  function renderNoticeMarkdown(source) {
    var text = String(source == null ? "" : source).replace(/\r\n?/g, "\n").trim();
    if (!text) return "";
    function esc(s) {
      return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    }
    function inline(s) {
      var out = esc(s);
      out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
      out = out.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)/g, function (m, alt, src) {
      return '<img src="' + src + '" alt="' + alt + '" loading="lazy" decoding="async" class="notice-image">';
    });
    out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
      out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
      out = out.replace(/__([^_]+)__/g, "<strong>$1</strong>");
      out = out.replace(/(^|[\s(])\*([^*\n]+)\*/g, "$1<em>$2</em>");
      out = out.replace(/(^|[\s(])_([^_\n]+)_/g, "$1<em>$2</em>");
      return out;
    }
    var lines = text.split("\n");
    var html = [];
    var para = [];
    var i = 0;
    function flush() {
      if (!para.length) return;
      html.push("<p>" + para.map(inline).join("<br>") + "</p>");
      para = [];
    }
    while (i < lines.length) {
      var line = lines[i];
      if (/^\s*```/.test(line)) {
        flush();
        var code = [];
        i += 1;
        while (i < lines.length && !/^\s*```/.test(lines[i])) { code.push(lines[i]); i += 1; }
        i += 1;
        html.push("<pre><code>" + esc(code.join("\n")) + "</code></pre>");
        continue;
      }
      if (!line.trim()) { flush(); i += 1; continue; }
      var heading = line.match(/^(#{1,6})\s+(.*)$/);
      if (heading) {
        flush();
        var level = Math.min(6, heading[1].length + 1);
        html.push("<h" + level + ">" + inline(heading[2]) + "</h" + level + ">");
        i += 1;
        continue;
      }
      if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) { flush(); html.push("<hr>"); i += 1; continue; }
      if (/^\s*>\s?/.test(line)) {
        flush();
        var quote = [];
        while (i < lines.length && /^\s*>\s?/.test(lines[i])) { quote.push(lines[i].replace(/^\s*>\s?/, "")); i += 1; }
        html.push("<blockquote>" + quote.map(inline).join("<br>") + "</blockquote>");
        continue;
      }
      if (/^\s*([-*+]|\d+[.)])\s+/.test(line)) {
        flush();
        var ordered = /^\s*\d+[.)]\s+/.test(line);
        var items = [];
        while (i < lines.length && /^\s*([-*+]|\d+[.)])\s+/.test(lines[i])) {
          items.push(lines[i].replace(/^\s*([-*+]|\d+[.)])\s+/, ""));
          i += 1;
        }
        var tag = ordered ? "ol" : "ul";
        html.push("<" + tag + ">" + items.map(function (item) { return "<li>" + inline(item) + "</li>"; }).join("") + "</" + tag + ">");
        continue;
      }
      para.push(line);
      i += 1;
    }
    flush();
    return html.join("\n");
  }

  /* Every notice has its own page, so "read more" never dumps the visitor on
     the site root. A notice whose <url>/<link> is just the bare site is
     treated as having no destination. */
  function noticeIsBareSiteUrl(raw) {
    if (!raw) return true;
    try {
      var url = new URL(raw, window.location.origin);
      if (!/(^|\.)innioasis\.app$/i.test(url.hostname)) return false;
      return !url.pathname.replace(/\//g, "") && !url.search && !url.hash;
    } catch (_) {
      return true;
    }
  }

  function noticeDetailHref(id) {
    var path = "/notices.html?notice=" + encodeURIComponent(String(id || ""));
    try {
      if (typeof decorateMainSiteHref === "function") return decorateMainSiteHref(path);
    } catch (_) {}
    return path;
  }

  window.y1NoticeMarkdown = renderNoticeMarkdown;
  window.y1NoticeIsBareUrl = noticeIsBareSiteUrl;
  window.y1NoticeDetailHref = noticeDetailHref;

  function parseNoticesXml(xmlText) {
    if (!xmlText || !xmlText.trim()) return [];
    try {
      var parser = new DOMParser();
      var doc = parser.parseFromString(xmlText, "application/xml");
      var errorNode = doc.querySelector("parsererror");
      if (errorNode) return [];
      var nodes = doc.querySelectorAll("notice");
      var list = [];
      nodes.forEach(function (n) {
        var textOf = function (tag) {
          var el = n.querySelector(tag);
          return el && el.textContent ? el.textContent.trim() : "";
        };
        list.push({
          id: n.getAttribute("id") || "",
          type: n.getAttribute("type") || n.getAttribute("severity") || "info",
          date: n.getAttribute("date") || n.getAttribute("from") || "",
          from: n.getAttribute("from") || n.getAttribute("date") || "",
          until: n.getAttribute("until") || "",
          persistent: (n.getAttribute("persistent") || "").toLowerCase() === "true",
          models: n.getAttribute("models") || "",
          deviceType: n.getAttribute("device_type") || "",
          firmwareRepo: n.getAttribute("firmware_repo") || "",
          firmwareVersion: n.getAttribute("firmware_version") || "",
          title: textOf("title"),
          summary: textOf("summary") || textOf("content") || textOf("body"),
          link: textOf("url") || textOf("link"),
          fullContent: textOf("full_content") || textOf("content") || textOf("body")
        });
      });
      return list;
    } catch (_) {
      return [];
    }
  }

  /* ---- Contextual notices ---------------------------------------------------
     One feed, two jobs. The bell tray and the Notices page list every current
     notice with no filtering, so those views always show what everyone was
     told. A page that knows what the visitor is looking at (device model,
     hardware type, software repo, release tag) puts the same id on a slot and
     the card below shows exactly ONE notice at a time, rotating through the
     eligible set: every broadcast notice plus every notice whose targeting
     matches the current context. See the specification in notice.xml. */
  var noticeFeed = [];
  var noticeContext = {};
  var noticeCard = null;
  var noticeRotateMs = 9000;
  var noticeSeverityRank = { critical: 3, warning: 2, info: 1 };

  function noticeSplit(value) {
    return String(value == null ? "" : value).split(",").map(function (part) {
      return part.trim();
    }).filter(Boolean);
  }
  function noticeIsAny(value) {
    var text = String(value == null ? "" : value).trim();
    return !text || text === "*";
  }
  function noticeRepoKey(value) {
    return String(value == null ? "" : value).trim().toLowerCase()
      .replace(/^https?:\/\/(www\.)?github\.com\//, "")
      .replace(/\.git$/, "")
      .replace(/\/+$/, "");
  }
  function noticeVersionKey(value) {
    return String(value == null ? "" : value).trim().toLowerCase().replace(/^v(?=\d)/, "");
  }
  function noticeVersionMatches(pattern, version) {
    var want = noticeVersionKey(pattern);
    var have = noticeVersionKey(version);
    if (!want || want === "*") return true;
    if (!have) return false;
    if (want.indexOf("*") === -1) return want === have;
    var rx = new RegExp("^" + want.replace(/[.+?^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*") + "$");
    return rx.test(have);
  }
  function noticeListMatches(raw, value, compare) {
    if (noticeIsAny(raw)) return true;
    if (!value) return false;
    return noticeSplit(raw).some(function (entry) {
      return noticeIsAny(entry) || compare(entry, value);
    });
  }
  function noticeModelEquals(a, b) {
    return String(a).toUpperCase() === String(b).toUpperCase();
  }

  /* Fail closed: a dimension the context does not know cannot satisfy a
     notice that declares it. */
  function noticeMatches(notice, context) {
    var ctx = context || {};
    return noticeListMatches(notice.models, ctx.model, noticeModelEquals) &&
      noticeListMatches(notice.deviceType, ctx.deviceType, noticeModelEquals) &&
      noticeListMatches(notice.firmwareRepo, ctx.repo, function (a, b) { return noticeRepoKey(a) === noticeRepoKey(b); }) &&
      noticeListMatches(notice.firmwareVersion, ctx.version, noticeVersionMatches);
  }

  function noticeHasTargeting(notice) {
    return !noticeIsAny(notice.models) || !noticeIsAny(notice.deviceType) ||
      !noticeIsAny(notice.firmwareRepo) || !noticeIsAny(notice.firmwareVersion);
  }

  function noticeTargetLabel(notice) {
    var bits = [];
    if (!noticeIsAny(notice.models)) bits.push(noticeSplit(notice.models).join(", ").toUpperCase());
    if (!noticeIsAny(notice.deviceType)) bits.push("Type " + noticeSplit(notice.deviceType).join(", ").toUpperCase());
    if (!noticeIsAny(notice.firmwareRepo)) bits.push(noticeSplit(notice.firmwareRepo).map(function (repo) {
      var parts = String(repo).split("/");
      return parts[parts.length - 1];
    }).join(", "));
    if (!noticeIsAny(notice.firmwareVersion)) bits.push(noticeSplit(notice.firmwareVersion).join(", "));
    return bits.join(" · ");
  }

  function noticeToday() {
    var now = new Date();
    var pad = function (n) { return (n < 10 ? "0" : "") + n; };
    return now.getFullYear() + "-" + pad(now.getMonth() + 1) + "-" + pad(now.getDate());
  }
  function noticeIsActive(notice, today) {
    var day = today || noticeToday();
    if (notice.from && String(notice.from).slice(0, 10) > day) return false;
    if (notice.until && String(notice.until).slice(0, 10) < day) return false;
    return true;
  }
  function noticeRank(a, b) {
    var weight = (noticeSeverityRank[String(b.type || "").toLowerCase()] || 1) -
      (noticeSeverityRank[String(a.type || "").toLowerCase()] || 1);
    if (weight) return weight;
    var dateA = String(a.date || "").slice(0, 10);
    var dateB = String(b.date || "").slice(0, 10);
    if (dateA !== dateB) return dateA < dateB ? 1 : -1;
    return String(a.id) < String(b.id) ? -1 : 1;
  }
  function noticeEligible(context) {
    var ctx = context || noticeContext;
    var today = noticeToday();
    return noticeFeed.filter(function (notice) {
      return noticeIsActive(notice, today) && noticeMatches(notice, ctx);
    }).sort(noticeRank);
  }

  function noticeCardMarkup(notice, index, total) {
    var severity = String(notice.type || "info").toLowerCase();
    var target = noticeTargetLabel(notice);
    var detail = noticeDetailHref(notice.id);
    var pageUrl = (notice.link && !noticeIsBareSiteUrl(notice.link)) ? notice.link : "";
    var dots = "";
    if (total > 1) {
      var buttons = [];
      for (var i = 0; i < total; i++) {
        buttons.push('<button type="button" class="lumen-context-dot' + (i === index ? " is-active" : "") +
          '" data-notice-index="' + i + '" aria-label="Show community notice ' + (i + 1) + ' of ' + total + '"' +
          (i === index ? ' aria-current="true"' : "") + '></button>');
      }
      dots = '<div class="lumen-context-dots" role="group" aria-label="Community notices">' + buttons.join("") + '</div>';
    }
    return '<div class="lumen-context-head">' +
      '<span class="lumen-context-kicker">Community notice' + (total > 1 ? " " + (index + 1) + "/" + total : "") + '</span>' +
      '<span class="lumen-context-severity">' + escapeHtml(severity.toUpperCase()) + '</span>' +
      (target ? '<span class="lumen-context-target">' + escapeHtml(target) + '</span>' : '') +
      '<a class="lumen-context-all" href="' + escapeHtml(decorateMainSiteHref("/notices.html")) + '">All notices &rarr;</a>' +
      '</div>' +
      '<p class="lumen-context-title"><a href="' + escapeHtml(detail) + '">' + escapeHtml(notice.title || "Community notice") + '</a></p>' +
      (notice.summary ? '<p class="lumen-context-summary">' + escapeHtml(notice.summary) + '</p>' : "") +
      ((dots || pageUrl)
        ? '<div class="lumen-context-foot">' + dots +
          (pageUrl ? '<a class="lumen-context-link" href="' + escapeHtml(pageUrl) + '" target="_blank" rel="noopener noreferrer">Open linked page</a>' : "") +
          '</div>'
        : "");
  }

  function clearNoticeTimer() {
    if (noticeCard && noticeCard.timer) {
      clearTimeout(noticeCard.timer);
      noticeCard.timer = null;
    }
  }
  function scheduleNoticeRotation() {
    if (!noticeCard) return;
    clearNoticeTimer();
    if (noticeCard.paused) return;
    if (!noticeCard.items || noticeCard.items.length < 2) return;
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    noticeCard.timer = window.setTimeout(function () {
      noticeCardShow(noticeCard.index + 1, false);
    }, noticeRotateMs);
  }
  function noticeCardShow(index, manual) {
    if (!noticeCard) return;
    var items = noticeCard.items || [];
    var el = noticeCard.el;
    if (!items.length) {
      el.innerHTML = "";
      el.hidden = true;
      clearNoticeTimer();
      return;
    }
    el.hidden = false;
    if (index < 0) index = items.length - 1;
    if (index >= items.length) index = 0;
    noticeCard.index = index;
    var notice = items[index];
    el.setAttribute("data-severity", String(notice.type || "info").toLowerCase());
    function paint() {
      el.innerHTML = noticeCardMarkup(notice, index, items.length);
      el.classList.remove("is-fading");
    }
    clearTimeout(noticeCard.fadeTimer);
    if (manual) {
      paint();
    } else {
      el.classList.add("is-fading");
      noticeCard.fadeTimer = window.setTimeout(paint, 140);
    }
    scheduleNoticeRotation();
  }
  function renderNoticeCard(freshIds) {
    if (!noticeCard) return;
    var previous = noticeCard.items && noticeCard.items[noticeCard.index];
    var items = noticeEligible();
    if (freshIds && freshIds.length) {
      /* A notice that just became relevant (the visitor picked Y2, or Rockbox)
         is what they should see next, not whatever was already on screen. */
      items.sort(function (a, b) {
        var freshA = freshIds.indexOf(a.id) === -1 ? 1 : 0;
        var freshB = freshIds.indexOf(b.id) === -1 ? 1 : 0;
        return freshA - freshB || noticeRank(a, b);
      });
    }
    var key = items.map(function (notice) { return notice.id; }).join("|");
    var unchanged = key === noticeCard.key;
    noticeCard.items = items;
    if (unchanged && !(freshIds && freshIds.length)) return;
    noticeCard.key = key;
    if (!items.length) {
      noticeCardShow(0, true);
      return;
    }
    var targetIndex = 0;
    var i;
    if (freshIds && freshIds.length) {
      for (i = 0; i < items.length; i++) {
        if (freshIds.indexOf(items[i].id) !== -1) { targetIndex = i; break; }
      }
    } else if (previous) {
      for (i = 0; i < items.length; i++) {
        if (items[i].id === previous.id) { targetIndex = i; break; }
      }
    }
    noticeCardShow(targetIndex, false);
  }
  function pauseNoticeCard() {
    if (!noticeCard) return;
    noticeCard.paused = true;
    clearNoticeTimer();
  }
  function resumeNoticeCard() {
    if (!noticeCard) return;
    noticeCard.paused = false;
    scheduleNoticeRotation();
  }
  function bindNoticeCard(el) {
    el.addEventListener("click", function (event) {
      var dot = event.target && event.target.closest ? event.target.closest("[data-notice-index]") : null;
      if (!dot) return;
      event.preventDefault();
      pauseNoticeCard();
      noticeCardShow(parseInt(dot.getAttribute("data-notice-index"), 10) || 0, true);
    });
    el.addEventListener("pointerenter", pauseNoticeCard);
    el.addEventListener("pointerleave", resumeNoticeCard);
    el.addEventListener("focusin", pauseNoticeCard);
    el.addEventListener("focusout", function (event) {
      if (!el.contains(event.relatedTarget)) resumeNoticeCard();
    });
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) pauseNoticeCard();
      else if (!el.contains(document.activeElement)) resumeNoticeCard();
    });
  }

  function mountNoticeCard() {
    var el = document.getElementById("lumen-context-notice");
    if (!el || noticeCard) return noticeCard;
    noticeCard = { el: el, items: [], index: 0, timer: null, fadeTimer: null, paused: false, key: "" };
    bindNoticeCard(el);
    var stored = window.INNIOASIS_NOTICE_CONTEXT;
    if (stored && typeof stored === "object") {
      Object.keys(stored).forEach(function (key) {
        var value = stored[key];
        if (value !== undefined && value !== null && value !== "") noticeContext[key] = value;
      });
    }
    renderNoticeCard([]);
    return noticeCard;
  }

  /* A page calls this whenever the viewer's selection changes. Dimensions left
     empty are forgotten, so a stale repo cannot keep a notice alive. */
  function setNoticeContext(patch) {
    var before = noticeEligible().map(function (notice) { return notice.id; });
    Object.keys(patch || {}).forEach(function (key) {
      var value = patch[key];
      if (value === undefined || value === null || value === "") delete noticeContext[key];
      else noticeContext[key] = value;
    });
    window.INNIOASIS_NOTICE_CONTEXT = {};
    Object.keys(noticeContext).forEach(function (key) {
      window.INNIOASIS_NOTICE_CONTEXT[key] = noticeContext[key];
    });
    var eligible = noticeEligible();
    var fresh = eligible.filter(function (notice) { return before.indexOf(notice.id) === -1; })
      .map(function (notice) { return notice.id; });
    if (!noticeCard) mountNoticeCard();
    renderNoticeCard(fresh);
    return { eligible: eligible, fresh: fresh };
  }

  window.InnioasisNotices = {
    setContext: setNoticeContext,
    getContext: function () {
      var copy = {};
      Object.keys(noticeContext).forEach(function (key) { copy[key] = noticeContext[key]; });
      return copy;
    },
    getNotices: function () { return noticeFeed.slice(); },
    eligible: function (context) { return noticeEligible(context); },
    matches: noticeMatches,
    isTargeted: noticeHasTargeting,
    refresh: function () {
      if (!noticeCard) mountNoticeCard();
      else renderNoticeCard([]);
    }
  };

  var noticesLoaded = false;
  function loadCommunityNotices() {
    if (noticesLoaded || !noticesBody) return;
    /* One feed only: /notice.xml. The plural spelling used to sit in this
       list as a fallback, so a stray plural feed could silently win. */
    var candidates = [
      "/notice.xml",
      "notice.xml",
      "https://innioasis.app/notice.xml"
    ];
    var idx = 0;
    function tryFetch() {
      if (idx >= candidates.length) {
        noticesBody.innerHTML = '<p class="lumen-notices-empty">No community notices at this time.</p>';
        if (noticesBadge) {
          noticesBadge.textContent = "";
          noticesBadge.hidden = true;
          noticesBadge.style.display = "none";
        }
        return;
      }
      var target = candidates[idx++];
      fetch(target, { cache: "no-cache" })
        .then(function (res) {
          if (!res.ok) throw new Error("HTTP " + res.status);
          return res.text();
        })        .then(function (xmlText) {
          var items = parseNoticesXml(xmlText);

          if (!items || !items.length) {
            tryFetch();
            return;
          }
          noticesLoaded = true;
          var seenIds = (localStorage.getItem("y1_seen_notices") || "").split(",").filter(Boolean);
          var allIds = [];
          var unreadCount = 0;

          var html = items.map(function (item) {
            if (item.id) {
              allIds.push(item.id);
              if (seenIds.indexOf(item.id) === -1) unreadCount++;
            }
            var typeTag = (item.type || "INFO").toUpperCase();
            /* The tray is the unfiltered view: every current notice is listed
               whatever its targeting, with its targets named so a reader can
               tell who it was written for. */
            var targetLabel = noticeTargetLabel(item);
            var modelsBadge = targetLabel
              ? '<span class="lumen-notice-models">' + escapeHtml(targetLabel) + '</span>'
              : '';
            /* The tray opens the notice itself. A notice that only points at
               the bare site has no page of its own to send anyone to. */
            var detailHref = item.id ? noticeDetailHref(item.id) : "";
            var linkHtml = detailHref
              ? '<a class="lumen-notice-link" href="' + escapeHtml(detailHref) + '">Read more &rarr;</a>'
              : '';
            /* The card carries the whole notice, Markdown and images included,
               in its own scroll box so a long warning stays readable in place. */
            var fullHtml = renderNoticeMarkdown(item.fullContent || item.summary || "");
            var pageUrl = (item.link && !noticeIsBareSiteUrl(item.link)) ? item.link : "";
            var openHtml = pageUrl
              ? '<a class="lumen-notice-open" href="' + escapeHtml(pageUrl) + '" target="_blank" rel="noopener noreferrer" title="Open the linked page" aria-label="Open the linked page">' +
                '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9"></circle><path d="M3 12h18"></path><path d="M12 3c2.5 2.4 3.9 5.5 3.9 9S14.5 18.6 12 21c-2.5-2.4-3.9-5.5-3.9-9S9.5 5.4 12 3Z"></path></svg></a>'
              : "";
            return (
              '<article class="lumen-notice-card lumen-notice-card--' + escapeHtml(item.type) + '">' +
              '<div class="lumen-notice-meta">' +
              '<span class="lumen-notice-type">' + escapeHtml(typeTag) + '</span>' +
              modelsBadge +
              (item.date ? '<time class="lumen-notice-date">' + escapeHtml(item.date) + '</time>' : '') +
              '</div>' +
              '<h4 class="lumen-notice-title">' + escapeHtml(item.title) + '</h4>' +
              '<div class="lumen-notice-full">' + fullHtml + '</div>' +
              ((linkHtml || openHtml) ? '<div class="lumen-notice-actions">' + linkHtml + openHtml + '</div>' : '') +
              '</article>'
            );
          }).join("");

          if (window.location.pathname.endsWith("/notices.html") || window.location.pathname.endsWith("/notices")) {
            try {
              if (allIds.length) localStorage.setItem("y1_seen_notices", allIds.join(","));
              unreadCount = 0;
            } catch (_) {}
          }

          noticeFeed = items;
          mountNoticeCard();
          try {
            document.dispatchEvent(new CustomEvent("innioasis:notices", { detail: items }));
          } catch (_) {}
          noticesBody.innerHTML = html;
          noticesTray.setAttribute("data-notice-ids", allIds.join(","));
          if (noticesBadge) {
            if (unreadCount > 0) {
              noticesBadge.textContent = String(unreadCount);
              noticesBadge.hidden = false;
              noticesBadge.style.display = "flex";
            } else {
              noticesBadge.textContent = "";
              noticesBadge.hidden = true;
              noticesBadge.style.display = "none";
            }
          }
        })
        .catch(function () {
          tryFetch();
        });
    }
    tryFetch();
  }
  loadCommunityNotices();

  /* Global dismissal when clicking outside switcher or notices trays */
  document.addEventListener("click", function (e) {
    if (switcherTray && !switcherTray.hidden) {
      if (!switcherTray.contains(e.target) && !switcherToggle.contains(e.target)) {
        setSwitcherOpen(false);
      }
    }
    if (noticesTray && !noticesTray.hidden) {
      if (!noticesTray.contains(e.target) && !noticesBtn.contains(e.target)) {
        setNoticesOpen(false);
      }
    }
  });

  /* Theme Switcher Logic */
  var themeSelect = document.getElementById("lumen-theme-select");
  var storedTheme = "auto";
  try {
    storedTheme = localStorage.getItem("lumen-theme") || "auto";
  } catch (_) {}
  if (themeSelect) {
    themeSelect.value =
      ["auto", "light", "dark", "high-contrast", "2077"].indexOf(storedTheme) >= 0
        ? storedTheme
        : "auto";
    themeSelect.addEventListener("change", function () {
      var value = themeSelect.value;
      document.documentElement.setAttribute("data-lumen-theme", value);
      try {
        localStorage.setItem("lumen-theme", value);
      } catch (_) {}
    });
  }

  /* Hamburger Toggle for Mobile */
  var menu = document.getElementById("navLinks");
  var hamburger = document.getElementById("hamburger");
  function setMenuOpen(open) {
    if (!menu || !hamburger) return;
    if (open) {
      /* Only one header tray is ever open at a time. */
      setSwitcherOpen(false);
      setNoticesOpen(false);
    }
    menu.classList.toggle("active", open);
    if (open) positionCompactMenu();
    hamburger.classList.toggle("is-active", open);
    hamburger.setAttribute("aria-expanded", open ? "true" : "false");
    hamburger.setAttribute("aria-label", open ? "Close navigation menu" : "Open navigation menu");
  }
  if (hamburger) {
    hamburger.addEventListener("click", function (event) {
      event.stopPropagation();
      setMenuOpen(!menu.classList.contains("active"));
    });
  }
  /* A menu that only closes by tapping a link feels stuck: close it on an
     outside click or Escape too, like the other header trays. */
  document.addEventListener("click", function (event) {
    if (!menu || !menu.classList.contains("active")) return;
    var target = event.target;
    if (target && target.closest && (target.closest("#navLinks") || target.closest("#hamburger"))) return;
    setMenuOpen(false);
  });
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    if (menu && menu.classList.contains("active")) setMenuOpen(false);
  });
  /* The panel is fixed to the viewport and placed from the button's real
     rectangle, so a header wider than the screen cannot drag it off the edge. */
  function positionCompactMenu() {
    if (!menu || !hamburger) return;
    if (!navShell || !navShell.classList.contains("nav-compact")) return;
    var rect = hamburger.getBoundingClientRect();
    var top = Math.round(rect.bottom + 8);
    menu.style.position = "fixed";
    menu.style.top = top + "px";
    menu.style.left = "auto";
    menu.style.right = Math.max(12, Math.round(window.innerWidth - rect.right)) + "px";
    menu.style.maxHeight = Math.max(180, Math.round(window.innerHeight - top - 16)) + "px";
  }
  window.addEventListener("resize", function () {
    if (menu && menu.classList.contains("active")) positionCompactMenu();
  });
  if (menu) {
    menu.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        setMenuOpen(false);
      });
    });
  }

  /* Responsive header: as soon as the inline links stop fitting next to the
     brand and the tool buttons, collapse the whole menu into the hamburger.
     Measuring instead of guessing a breakpoint means no link is ever squeezed
     out of the bar, whatever the viewport, font size or translated title. */
  var navShell = document.querySelector("#nav-root .nav-container");
  function navLinksFit(shell) {
    var links = document.getElementById("navLinks");
    var brand = shell.querySelector(".lumen-brand-switcher-wrap");
    var tools = shell.querySelector(".nav-tools");
    if (!links || !brand || !tools) return true;
    var styles = window.getComputedStyle(shell);
    var space = shell.clientWidth - (parseFloat(styles.paddingLeft) || 0) - (parseFloat(styles.paddingRight) || 0);
    var gaps = (parseFloat(styles.columnGap) || 0) * 2;
    var needed = brand.getBoundingClientRect().width + tools.getBoundingClientRect().width + links.scrollWidth + gaps;
    return needed <= space + 1;
  }
  function syncNavCompact() {
    if (!navShell) return;
    var wasCompact = navShell.classList.contains("nav-compact");
    if (wasCompact) navShell.classList.remove("nav-compact");
    var compact = !navLinksFit(navShell);
    if (compact) navShell.classList.add("nav-compact");
    if (compact !== wasCompact) setMenuOpen(false);
  }
  var navSyncQueued = false;
  function queueNavSync() {
    if (navSyncQueued) return;
    navSyncQueued = true;
    window.setTimeout(function () {
      navSyncQueued = false;
      syncNavCompact();
    }, 0);
  }
  queueNavSync();
  window.addEventListener("resize", queueNavSync);
  window.addEventListener("orientationchange", queueNavSync);
  window.addEventListener("load", queueNavSync);
  if (document.fonts && document.fonts.ready && typeof document.fonts.ready.then === "function") {
    document.fonts.ready.then(queueNavSync, function () {});
  }
  if (typeof window.ResizeObserver === "function" && navShell) {
    var lastNavBox = "";
    var navResizeObserver = new window.ResizeObserver(function () {
      var brand = navShell.querySelector(".lumen-brand-switcher-wrap");
      var tools = navShell.querySelector(".nav-tools");
      var box = [
        navShell.clientWidth,
        brand ? Math.round(brand.getBoundingClientRect().width) : 0,
        tools ? Math.round(tools.getBoundingClientRect().width) : 0
      ].join("|");
      if (box === lastNavBox) return;
      lastNavBox = box;
      queueNavSync();
    });
    navResizeObserver.observe(navShell);
    var navBrandEl = navShell.querySelector(".lumen-brand-switcher-wrap");
    if (navBrandEl) navResizeObserver.observe(navBrandEl);
    var navToolsEl = navShell.querySelector(".nav-tools");
    if (navToolsEl) navResizeObserver.observe(navToolsEl);
  }
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      setMenuOpen(false);
      setSwitcherOpen(false);
      setNoticesOpen(false);
    }
  });

  /* Footer Injection */
  var footerRoot = document.getElementById("footer-root");
  if (!footerRoot && document.body && !document.querySelector("footer")) {
    /* Pages that forget the mount point still get a footer. */
    footerRoot = document.createElement("div");
    footerRoot.id = "footer-root";
    var toolbarSlot = document.getElementById("support-toolbar-slot");
    if (toolbarSlot && toolbarSlot.parentNode === document.body) {
      document.body.insertBefore(footerRoot, toolbarSlot);
    } else {
      document.body.appendChild(footerRoot);
    }
  }
  if (footerRoot) {
    footerRoot.innerHTML =
      '<footer class="site-footer ' + (isFirmwarePersona ? "site-footer--firmware" : "site-footer--updater") + '">' +
      '<div class="footer-grid">' +
      '<div class="footer-col">' +
      '<h4>Community Software &amp; Guides</h4>' +
      '<a href="' + escapeHtml(decorateMainSiteHref("/guide.html")) + '">Installation Guide</a>' +
      (isThemesSite
        ? '<a href="' + escapeHtml(decorateMainSiteHref("/firmware.html")) + '">Player Updates and Firmware</a>'
        : '<a href="' + escapeHtml(decorateMainSiteHref("/firmware.html?view=software")) + '">Software Updates</a>' +
          '<a href="' + escapeHtml(decorateMainSiteHref("/firmware.html?view=firmware")) + '">Custom Firmware Downloads</a>'
      ) +
      '<a href="' + escapeHtml(decorateMainSiteHref("/rockbox-benefits.html")) + '">Rockbox on Innioasis</a>' +
      '<a href="' + escapeHtml(decorateMainSiteHref("/reborn-y2linux-benefits.html")) + '">Reborn (Y2Linux) for Y2</a>' +
      '<a href="' + escapeHtml(decorateMainSiteHref("/updater-comparison.html")) + '">Which tool should I use?</a>' +
      '<a href="' + escapeHtml(decorateMainSiteHref("/troubleshooting.html")) + '">Troubleshooting</a>' +
      '</div>' +
      '<div class="footer-col">' +
      '<h4>Developers &amp; Community</h4>' +
      '<a href="' + escapeHtml(decorateMainSiteHref("/developers.html")) + '">Developer Guide &amp; Tooling</a>' +
      '<a href="' + escapeHtml(decorateCrossDomainHref("https://themes.innioasis.app/")) + '" data-cross-site-link="1">Themes Gallery</a>' +
      '<a href="https://discord.gg/zHrT2zrcek" target="_blank" rel="noopener noreferrer">Discord Server</a>' +
      '<a href="https://reddit.com/r/innioasis" target="_blank" rel="noopener noreferrer">r/innioasis on Reddit</a>' +
      '<a href="https://github.com/y1-community/Innioasis-Updater" target="_blank" rel="noopener noreferrer">Updater CE Source Code</a>' +
      '<a href="' + escapeHtml(decorateMainSiteHref("/credits.html#donate")) + '" data-donations-appeal>Support Independent Community Projects</a>' +
      '<a href="' + escapeHtml(decorateMainSiteHref("/credits.html")) + '">Community Credits</a>' +
      '</div>' +
      '</div>' +
      '<div class="footer-bottom">Copyleft - Ryan Specter and the Innioasis Community</div>' +
      '</footer>';
  }

  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }
})();