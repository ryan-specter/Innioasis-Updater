(function () {
  "use strict";

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

  function decorateMainSiteHref(path) {
    if (!path) return path;
    var isThemesSite = (window.location.hostname === "themes.innioasis.app") || (window.location.port === "8081");
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
  var activeTitle = isFirmwarePersona ? "Firmware Archive" : "Updater CE";
  var activeHomeHref = isFirmwarePersona ? "/firmware.html" : "/";

  (function updateDocumentTitle() {
    var path = (window.location.pathname || "").toLowerCase();
    var t = document.title || "";
    if (path.endsWith("/firmware.html")) {
      document.title = "Innioasis and Timmkoo Software Updates and Custom Firmware - Community Firmware Archive";
      return;
    }
    if (isFirmwarePersona) {
      if (t.indexOf("Firmware Archive") === -1) {
        var base = t.split(/\s+[|·-]\s+(?:Innioasis|Community)/)[0].trim();
        document.title = (base || t) + " - Firmware Archive";
      }
    } else {
      if (t.indexOf("Updater CE") === -1) {
        var uBase = t.split(/\s+[|·-]\s+Innioasis/)[0].trim();
        document.title = (uBase || t) + " - Innioasis Updater CE";
      }
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
      '.lumen-site-switcher-tray { position: absolute; top: calc(100% + 8px); left: 0; width: 320px; max-width: 90vw; background: var(--lumen-panel, #12141c); border: 1px solid var(--lumen-line-strong, rgba(255,255,255,0.18)); border-radius: 14px; padding: 12px; box-shadow: 0 12px 36px rgba(0,0,0,0.45); z-index: 10002; box-sizing: border-box; }' +
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
      '.lumen-site-switcher-item-copy { display: flex; flex-direction: column; gap: 2px; }' +
      '.lumen-site-switcher-item-copy strong { font-size: 0.92rem; font-weight: 700; color: var(--lumen-text, #f8fafc); line-height: 1.2; }' +
      '.lumen-site-switcher-item-copy small { font-size: 0.78rem; color: var(--lumen-muted, #94a3b8); line-height: 1.25; }' +
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
      '.lumen-notices-btn:hover { background: rgba(255,255,255,0.12); color: #fff; }' +
      ':root[data-lumen-theme="light"] .lumen-notices-btn { background: rgba(0,0,0,0.04); border-color: rgba(0,0,0,0.12); color: #0f172a; }' +
      ':root[data-lumen-theme="light"] .lumen-notices-btn:hover { background: rgba(0,0,0,0.08); }' +
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
      '.lumen-notice-link { font-size: 0.76rem; font-weight: 600; text-decoration: none; color: var(--lumen-accent, #6366f1); }' +
      ':root[data-lumen-theme="2077"] .lumen-notice-link { color: #ff1e3c; }' +
      '.lumen-nav-social-btn { display: inline-flex !important; align-items: center !important; justify-content: center !important; width: auto !important; height: auto !important; min-width: 0 !important; min-height: 0 !important; padding: 4px 6px !important; background: transparent !important; border: none !important; box-shadow: none !important; border-radius: 0 !important; text-decoration: none !important; transition: transform 0.15s ease, opacity 0.15s ease, color 0.15s ease !important; flex-shrink: 0 !important; cursor: pointer !important; opacity: 0.88 !important; }' +
      '.lumen-nav-social-btn:hover { opacity: 1 !important; transform: scale(1.15) !important; background: transparent !important; border: none !important; box-shadow: none !important; }' +
      '.lumen-nav-social-btn--reddit { color: #ff4500 !important; }' +
      '.lumen-nav-social-btn--reddit:hover { color: #ff5722 !important; filter: drop-shadow(0 0 6px rgba(255, 69, 0, 0.5)) !important; }' +
      '.lumen-nav-social-btn--discord { color: #5865f2 !important; }' +
      '.lumen-nav-social-btn--discord:hover { color: #7289da !important; filter: drop-shadow(0 0 6px rgba(88, 101, 242, 0.5)) !important; }' +
      '.lumen-nav-social-btn svg { display: block !important; width: 22px !important; height: 22px !important; }' +
      '@media (max-width: 1040px) { body.site-themes-app .nav-links a { padding: 0.4rem 0.45rem; font-size: 0.82rem; } .nav-container { padding: 0.5rem 1rem; gap: 0.35rem; } }';
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
      '<a href="/notices.html" class="lumen-notices-all-link">All notices &rarr;</a>' +
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
        list.push({
          id: n.getAttribute("id") || "",
          type: n.getAttribute("type") || "info",
          date: n.getAttribute("date") || "",
          models: n.getAttribute("models") || "",
          title: (n.querySelector("title") && n.querySelector("title").textContent) || "",
          summary: (n.querySelector("summary") && n.querySelector("summary").textContent) || "",
          link: (n.querySelector("link") && n.querySelector("link").textContent) || ""
        });
      });
      return list;
    } catch (_) {
      return [];
    }
  }

  var noticesLoaded = false;
  function loadCommunityNotices() {
    if (noticesLoaded || !noticesBody) return;
    var candidates = [
      "/notice.xml",
      "/notices.xml",
      "notice.xml",
      "notices.xml",
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
        })
        .then(function (xmlText) {
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
            var rawModels = (item.models || "").trim();
            var isAllModels = !rawModels || /^(all|all\s+models|\*)$/i.test(rawModels);
            var modelsBadge = (!isAllModels && rawModels)
              ? '<span class="lumen-notice-models">' + escapeHtml(rawModels) + '</span>'
              : '';
            var linkHtml = item.link
              ? '<a class="lumen-notice-link" href="' + escapeHtml(item.link) + '">Learn more &rarr;</a>'
              : '';
            return (
              '<article class="lumen-notice-card lumen-notice-card--' + escapeHtml(item.type) + '">' +
              '<div class="lumen-notice-meta">' +
              '<span class="lumen-notice-type">' + escapeHtml(typeTag) + '</span>' +
              modelsBadge +
              (item.date ? '<time class="lumen-notice-date">' + escapeHtml(item.date) + '</time>' : '') +
              '</div>' +
              '<h4 class="lumen-notice-title">' + escapeHtml(item.title) + '</h4>' +
              '<p class="lumen-notice-summary">' + escapeHtml(item.summary) + '</p>' +
              linkHtml +
              '</article>'
            );
          }).join("");

          if (window.location.pathname.endsWith("/notices.html") || window.location.pathname.endsWith("/notices")) {
            try {
              if (allIds.length) localStorage.setItem("y1_seen_notices", allIds.join(","));
              unreadCount = 0;
            } catch (_) {}
          }
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
    menu.classList.toggle("active", open);
    hamburger.classList.toggle("is-active", open);
    hamburger.setAttribute("aria-expanded", open ? "true" : "false");
    hamburger.setAttribute("aria-label", open ? "Close navigation menu" : "Open navigation menu");
  }
  if (hamburger) {
    hamburger.addEventListener("click", function () {
      setMenuOpen(!menu.classList.contains("active"));
    });
  }
  if (menu) {
    menu.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        setMenuOpen(false);
      });
    });
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
      '<a href="' + escapeHtml(decorateMainSiteHref("/credits.html#donate")) + '">Support Independent Community Projects</a>' +
      '<a href="' + escapeHtml(decorateMainSiteHref("/credits.html")) + '">Community Credits</a>' +
      '</div>' +
      '</div>' +
      '<div class="footer-bottom">Copyleft - Innioasis users and contributors, for the community.</div>' +
      '</footer>';
  }

  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }
})();