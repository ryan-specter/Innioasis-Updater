/*!
 * China region mode
 * ---------------------------------------------------------------
 * Visitors from mainland China get a Simplified Chinese page that lists
 * firmware and offers portable flashing packages (ROM ZIP) or the
 * project's standalone ZIP instead of Innioasis Updater CE. The app's
 * online features (release lookup, sign-in, package hosts) depend on
 * services that are unreliable or unreachable from mainland networks,
 * so the app is not offered there.
 *
 * Detection order:
 *   1. ?region=cn / ?region=intl (also remembered in localStorage)
 *   2. Browser language zh / zh-CN / zh-Hans (zh-TW, zh-HK, zh-MO get
 *      the international page)
 *   3. Asia/Shanghai and the other mainland time zones
 *   4. Cloudflare's same-origin /cdn-cgi/trace, when the site is proxied
 *
 * Nothing here runs on the international page: the region attribute and
 * the extra stylesheet are only added in China mode.
 * ---------------------------------------------------------------
 */
(function () {
    "use strict";

    var STORAGE_KEY = "innioasis-region";
    var MAINLAND_TZ = /^asia\/(shanghai|chongqing|urumqi|harbin)$/i;

    var root = document.documentElement;

    function readRegionParam() {
        var raw = "";
        try {
            raw = new URLSearchParams(window.location.search).get("region") || "";
        } catch (_) {}
        var value = String(raw).trim().toLowerCase();
        if (value === "cn" || value === "china" || value === "zh" || value === "zh-cn") return "cn";
        if (value === "intl" || value === "international" || value === "global" || value === "en") return "intl";
        return "";
    }

    function readStoredRegion() {
        try {
            var value = window.localStorage.getItem(STORAGE_KEY);
            if (value === "cn" || value === "intl") return value;
        } catch (_) {}
        return "";
    }

    function rememberRegion(region) {
        try { window.localStorage.setItem(STORAGE_KEY, region); } catch (_) {}
    }

    function speaksChinese() {
        var list = (navigator.languages && navigator.languages.length)
            ? navigator.languages
            : [navigator.language || ""];
        for (var i = 0; i < list.length; i += 1) {
            var tag = String(list[i] || "").toLowerCase();
            if (!/^zh(-|$)/.test(tag)) continue;
            /* Taiwan, Hong Kong and Macau are served the international page. */
            if (/^zh-(tw|hk|mo)/.test(tag)) continue;
            return true;
        }
        return false;
    }

    function inMainlandTime() {
        try {
            var tz = String(Intl.DateTimeFormat().resolvedOptions().timeZone || "");
            return MAINLAND_TZ.test(tz) || tz.toUpperCase() === "PRC";
        } catch (_) {
            return false;
        }
    }

    var paramRegion = readRegionParam();
    /* A link that names an edition is a choice: keep it for the rest of the
       visit, so the next page opens in the same edition. */
    if (paramRegion) rememberRegion(paramRegion);
    var chosenRegion = paramRegion || readStoredRegion();
    var autoRegion = (speaksChinese() || inMainlandTime()) ? "cn" : "intl";
    var state = {
        region: chosenRegion || autoRegion,
        chosen: chosenRegion || ""
    };

    /* Text rules. Exact matches only: a sentence is translated whole, so a
       project name or a code snippet in the middle of English prose is
       never rewritten by accident. */
    var STRINGS = [
        /* Navigation and footer */
        ["Skip to content", "跳到主要内容"],
        ["Software Updates", "软件更新"],
        ["Firmware Downloads", "固件下载"],
        ["Themes", "主题"],
        ["Firmware Archive", "固件档案"],
        ["Updater CE", "Updater CE"],
        ["Innioasis Updater", "Innioasis 固件下载"],
        ["Themes Gallery", "主题画廊"],
        ["Innioasis Sites", "Innioasis 站点"],
        ["Switch site", "切换站点"],
        ["Notices", "公告"],
        ["All notices →", "全部公告 →"],
        ["All notices &rarr;", "全部公告 →"],
        ["Loading notices...", "正在加载公告…"],
        ["Theme", "主题"],
        ["Auto", "自动"],
        ["Dark", "深色"],
        ["High contrast", "高对比度"],
        ["Software & Guides", "软件与指南"],
        ["Installation Guide", "安装指南"],
        ["Player Updates and Firmware", "播放器更新与固件"],
        ["Custom Firmware Downloads", "自定义固件下载"],
        ["Rockbox on Innioasis", "Innioasis 上的 Rockbox"],
        ["Reborn (Y2Linux) for Y2", "Y2 的 Reborn（Y2Linux）"],
        ["Rondo for Y1", "Y1 的 Rondo"],
        ["Which tool should I use?", "应该使用哪个工具？"],
        ["Troubleshooting", "故障排除"],
        ["Developers", "开发者"],
        ["Developer Guide & Tooling", "开发者指南与工具"],
        ["Discord Server", "Discord 服务器"],
        ["r/innioasis on Reddit", "Reddit 上的 r/innioasis"],
        ["Support Independent Projects", "支持独立项目"],
        ["Credits", "制作人员"],
        ["Copyleft - Innioasis and Ryan Specter", "Copyleft · Innioasis 与 Ryan Specter"],
        ["Copyleft · Innioasis users and contributors, for the community.", "Copyleft · 属于 Innioasis 用户与贡献者，服务社区。"],

        /* Home */
        ["Software Updates and Firmware", "固件下载与软件更新"],
        ["Browse firmware", "浏览固件"],
        ["Help me choose", "帮我选择"],
        ["Software for every Innioasis and Timmkoo player", "适用于所有 Innioasis 与 Timmkoo 播放器"],
        ["See what you can install.", "看看可以安装哪些软件"],
        ["Open the full release list", "查看完整版本列表"],
        ["Software", "软件"],
        ["Releases", "版本"],
        ["Device coverage", "支持机型"],
        ["Innioasis & Timmkoo Firmware Downloads: Supported Models", "支持机型：Innioasis 与 Timmkoo 固件下载"],
        ["Browse all downloads", "浏览所有下载"],
        ["Innioasis Y1 & Y2", "Innioasis Y1 与 Y2"],
        ["Official software, restore files, and custom systems. Rockbox, Better-Y, Solar, and more.", "官方固件、恢复包与自定义系统，包括 Rockbox、Better-Y、Solar 等。"],
        ["Y1 Firmware", "Y1 固件"],
        ["Y2 Firmware", "Y2 固件"],
        ["Innioasis G1, G3 & G5", "Innioasis G1、G3 与 G5"],
        ["Official software and recovery files for the touchscreen players. Restore factory apps or unbrick.", "触屏播放器的官方固件与恢复文件，可恢复出厂应用或救砖。"],
        ["Find G-Series ROMs", "查找 G 系列 ROM"],
        ["Innioasis Q8, R1 & PR1", "Innioasis Q8、R1 与 PR1"],
        ["Original software and recovery files for the audio players.", "音频播放器的原厂固件与恢复文件。"],
        ["Find Q & R ROMs", "查找 Q 与 R 系列 ROM"],
        ["Timmkoo A5, Q5 & Q3", "Timmkoo A5、Q5 与 Q3"],
        ["Updater CE installs the files Timmkoo supplies. Hosted downloads are on the way.", "Timmkoo 提供的固件包正在整理，稍后会在这里提供直接下载。"],
        ["How Timmkoo support works", "Timmkoo 支持说明"],
        ["Every package here is tested before it goes up. New builds and models appear as soon as they're ready.", "这里的每个固件包都会在发布前检查。新版本与新机型准备好后会立即上架。"],
        ["Support Updater and the Themes Gallery.", "支持固件档案与主题画廊。"],
        ["Support Updater and the Themes Gallery", "支持固件档案与主题画廊"],
        ["Innioasis Updater and the Themes Gallery are independent projects.", "Innioasis 固件档案与主题画廊都是独立的社区项目。"],
        ["They are kept going by one developer and the community, and they cost real money to keep online and up to date. If they helped you, support the work.", "它们由开发者和社区共同维护，域名、托管与更新都需要持续投入。如果它们帮到了你，欢迎支持这项工作。"],

        /* Firmware directory */
        ["Innioasis & Timmkoo Firmware Archive", "Innioasis 与 Timmkoo 固件档案"],
        ["Release notes", "版本说明"],
        ["Add your project", "提交你的项目"],
        ["Device model", "设备型号"],
        ["Use the model printed on the player.", "请使用播放器上印的型号。"],
        ["Device type", "设备类型"],
        ["Type A", "A 型"],
        ["Type B", "B 型"],
        ["Y1 only. Type A players shipped with software 2.0.0 or later; Type B players shipped with an earlier version.", "仅 Y1。A 型播放器出厂系统为 2.0.0 或更高；B 型为更早的版本。"],
        ["Choose the software you want to run.", "选择要运行的软件。"],
        ["Show nightly builds", "显示预览/每日构建"],
        ["Show preview and nightly builds alongside stable releases.", "在稳定版本之外显示预览版与每日构建。"],
        ["Y2 ready", "Y2 可用"],
        ["Loading Original Software releases…", "正在加载固件版本…"],
        ["Downloading…", "正在下载…"],
        ["Dismiss", "关闭"],
        ["Install with Updater CE", "下载刷机包"],
        ["Release", "版本"],
        ["The safe way back", "恢复原厂固件"],
        ["Check the model", "确认机型"],
        ["Y1 and Y2 Software is not interchangeable. Re-select the model in Updater CE and start again.", "Y1 与 Y2 的固件不能混用。请重新选择机型后再试。"],
        ["Wait for the prompt", "等待提示"],
        ["Supported Devices & Official Stock Firmware Archive", "支持机型与原厂固件档案"],
        ["The Innioasis Firmware Archive preserves and hosts verified stock firmware, original factory restore images, unbrick packages, and custom operating systems for the following devices:", "Innioasis 固件档案保存并托管以下机型的原厂固件、恢复镜像、救砖包与自定义系统："],

        /* Release rows and download buttons */
        ["Checking public releases", "正在检查公开版本…"],
        ["No public releases", "没有公开版本"],
        ["Not available right now", "暂不可用"],
        ["Held back from this list.", "此版本暂未提供。"],
        ["No stable release yet", "还没有稳定版本"],
        ["Tick the nightly-builds option to see previews", "勾选每日构建选项以查看预览版"],
        ["Download ZIP", "下载刷机包 ZIP"],
        ["standalone package", "独立固件包"],
        ["Release details and zip", "版本详情与 ZIP"],
        ["No ZIP asset was found in this release.", "此版本没有 ZIP 文件。"],
        ["Downloading firmware…", "正在下载固件…"],
        ["Starting portable package download…", "正在开始下载便携刷机包…"],

        /* Guide */
        ["Quick start", "快速开始"],
        ["Get Innioasis Updater CE", "获取 Innioasis Updater CE"],
        ["Get Updater CE", "获取 Updater CE"],

        /* Static firmware list */
        ["Firmware list: every release, model and download", "固件列表：所有版本、机型与下载"],
        ["Open the installer view", "打开固件下载页"],
        ["Atom feed", "Atom 订阅"],
        ["JSON data", "JSON 数据"],
        ["Version", "版本"],
        ["Package", "固件包"],
        ["Download", "下载"],
        ["Original download", "原始下载地址"],
        ["Portable packages", "便携刷机包"],
        ["Notes", "说明"],
        ["Project page", "项目页面"],
        ["Install guide", "安装指南"],
        ["Innioasis Y1 software and firmware", "Innioasis Y1 软件与固件"],
        ["Innioasis Y2 software and firmware", "Innioasis Y2 软件与固件"],
        ["Every listed release for this model, with the original download URL and the portable packages built for each computer.", "该机型的全部公开版本，含原始下载地址与为各平台打包的便携刷机包。"],
        ["No published releases are listed for this software yet.", "该软件还没有公开版本。"],

        /* Region banner and nav */
        ["International", "国际版"],
        ["China edition", "中国版"],

        /* Extra filters and statuses rendered by lumen-site.js */
        ["Show pre-3.0.7 stock firmware / nightly builds", "显示 3.0.7 之前的原厂固件 / 每日构建"],
        ["Show pre-0.5 Rockbox / nightly builds", "显示 0.5 之前的 Rockbox / 每日构建"],
        ["Y1 stock firmware older than 3.0.7 and nightly builds are hidden by default. Tick to include them.", "3.0.7 之前的 Y1 原厂固件与每日构建默认隐藏，勾选后可显示。"],
        ["Rockbox Y1 builds older than 0.5 and nightly builds are hidden by default. Tick to include them.", "0.5 之前的 Rockbox Y1 版本与每日构建默认隐藏，勾选后可显示。"],
        ["Tick the pre-3.0.7 stock firmware / nightly-builds option to see older builds", "勾选 3.0.7 之前的原厂固件 / 每日构建选项以查看更早版本"],
        ["Tick the pre-0.5 Rockbox / nightly-builds option to see older builds", "勾选 0.5 之前的 Rockbox / 每日构建选项以查看更早版本"],
        ["All public releases are shown.", "已显示全部公开版本。"],
        ["Release information is not available right now. The project links remain available.", "暂时无法获取版本信息，但项目链接仍然可用。"],
        ["No software project is currently listed for this model and filter. Try another project or check the project release pages.", "当前机型与筛选条件下没有列出的软件项目。请尝试其他项目，或查看项目的发布页面。"],
        ["Latest release:", "最新版本："],
        ["No releases", "暂无版本"]
    ];

    /* Sentences built with a project name cannot be matched exactly. These
       rules cover the status line above the release table. */
    var RULES = [
        [/^Loading (.+) releases…$/, "正在加载 $1 版本…"],
        [/^Showing (.+) releases from catalogue · Checking for live updates…$/, "正在显示 $1 的缓存版本 · 正在检查更新…"],
        [/^Showing (.+) releases from the catalogue archive\.$/, "正在显示 $1 的存档版本。"],
        [/^All public (.+) releases loaded\.$/, "已加载全部公开的 $1 版本。"],
        [/^No release with (.+)$/, "没有找到包含 $1 的版本"]
    ];

    var TITLES = {
        "Innioasis Updater | Flash Tool for Innioasis & Timmkoo Players": "Innioasis 固件下载 | Innioasis 与 Timmkoo 播放器刷机包",
        "Innioasis Firmware Archive - Innioasis Firmware Downloads": "Innioasis 固件档案 - 固件与便携刷机包下载",
        "Getting started with Innioasis Updater CE | Install or restore firmware on any Innioasis or Timmkoo player - Innioasis Updater": "Innioasis 播放器固件刷机说明 - Innioasis 固件下载",
        "Firmware list - every Innioasis and Timmkoo release | Innioasis Updater": "固件列表 - Innioasis 与 Timmkoo 全部版本 | Innioasis 固件下载",
        "Firmware list - every Innioasis and Timmkoo release - Innioasis Firmware Downloads": "固件列表 - Innioasis 与 Timmkoo 全部版本 | Innioasis 固件下载",
        "Innioasis Firmware Archive - Innioasis Firmware Downloads": "Innioasis 固件档案 - 固件与便携刷机包下载"
    };

    var EXACT = Object.create(null);
    (function buildExact() {
        for (var i = 0; i < STRINGS.length; i += 1) {
            EXACT[String(STRINGS[i][0]).replace(/\s+/g, " ")] = STRINGS[i][1];
        }
    })();

    var SKIP_TAGS = {
        SCRIPT: 1, STYLE: 1, PRE: 1, CODE: 1, KBD: 1, SAMP: 1, TEXTAREA: 1
    };

    var observer = null;
    var applying = false;
    var stylesLoaded = false;

    function translateValue(value) {
        var text = String(value == null ? "" : value);
        var parts = /^(\s*)([\s\S]*?)(\s*)$/.exec(text);
        if (!parts) return value;
        var core = parts[2].replace(/\s+/g, " ");
        if (!core) return value;
        var zh = EXACT[core];
        if (zh === undefined) {
            for (var i = 0; i < RULES.length; i += 1) {
                if (RULES[i][0].test(core)) {
                    zh = core.replace(RULES[i][0], RULES[i][1]);
                    break;
                }
            }
        }
        return zh === undefined ? value : parts[1] + zh + parts[3];
    }

    function translateNode(rootNode) {
        if (!rootNode) return;
        if (rootNode.nodeType === 3) {
            var next = translateValue(rootNode.nodeValue);
            if (next !== rootNode.nodeValue) rootNode.nodeValue = next;
            return;
        }
        if (rootNode.nodeType !== 1 && rootNode.nodeType !== 9 && rootNode.nodeType !== 11) return;
        if (rootNode.nodeType === 1) {
            if (SKIP_TAGS[rootNode.tagName] || rootNode.hasAttribute("data-cn-skip")) return;
        }
        for (var node = rootNode.firstChild; node; node = node.nextSibling) {
            if (node.nodeType === 3) {
                var value = translateValue(node.nodeValue);
                if (value !== node.nodeValue) node.nodeValue = value;
            } else if (node.nodeType === 1) {
                translateNode(node);
            }
        }
    }

    function injectStyles() {
        if (stylesLoaded || document.getElementById("cn-region-styles")) return;
        stylesLoaded = true;
        var self = document.currentScript && document.currentScript.src ? document.currentScript.src : "";
        var base = self ? self.replace(/[^/]*$/, "") : "";
        var link = document.createElement("link");
        link.id = "cn-region-styles";
        link.rel = "stylesheet";
        link.href = base + "cn-region.css?v=20261105";
        (document.head || root).appendChild(link);
    }

    function regionLinks() {
        /* Keep the visitor's place when switching editions. */
        var url = new URL(window.location.href);
        url.searchParams.set("region", "intl");
        return url.pathname + url.search + url.hash;
    }

    function chinaLinks() {
        var url = new URL(window.location.href);
        url.searchParams.set("region", "cn");
        return url.pathname + url.search + url.hash;
    }

    function buildBanner() {
        var banner = document.createElement("div");
        banner.className = "cn-region-banner";
        banner.id = "cn-region-banner";
        banner.setAttribute("role", "note");
        banner.innerHTML =
            '<span class="cn-region-badge">中国版</span>' +
            '<span class="cn-region-copy">本站为中国大陆用户提供<strong>固件列表</strong>与<strong>便携刷机包 / 独立 ZIP</strong> 下载。Innioasis Updater CE 的在线功能在中国大陆可能无法正常使用，因此这里不再提供该应用。</span>' +
            '<a class="cn-region-banner-link" data-cn-region="intl" href="' + regionLinks() + '">查看国际版 →</a>';
        return banner;
    }

    function insertBanner() {
        var main = document.querySelector("main");
        if (!main || document.getElementById("cn-region-banner")) return;
        main.insertBefore(buildBanner(), main.firstChild);
    }

    function addNavToggle() {
        if (document.querySelector(".cn-region-toggle")) return;
        var tools = document.querySelector("#nav-root .nav-tools") || document.querySelector(".nav-tools");
        if (!tools) return;
        var cn = state.region === "cn";
        var link = document.createElement("a");
        link.className = "cn-region-toggle";
        link.href = cn ? regionLinks() : chinaLinks();
        link.setAttribute("data-cn-region", cn ? "intl" : "cn");
        link.title = cn ? "Switch to the international page" : "查看中国版页面";
        link.textContent = cn ? "国际版" : "中国版";
        tools.insertBefore(link, tools.firstChild);
    }

    function removeUpdaterEntries() {
        Array.prototype.forEach.call(document.querySelectorAll(".lumen-site-switcher-item"), function (item) {
            if (/Updater CE/i.test(item.textContent || "")) {
                var li = item.parentNode;
                if (li && li.parentNode) li.parentNode.removeChild(li);
            }
        });
        Array.prototype.forEach.call(document.querySelectorAll("#footer-root a"), function (item) {
            var label = String(item.textContent || "").trim();
            if (label === "Updater CE" || label === "Updater CE Source Code") {
                if (item.parentNode) item.parentNode.removeChild(item);
            }
        });
    }

    function revealChinaBlocks() {
        Array.prototype.forEach.call(document.querySelectorAll("[data-cn-only]"), function (block) {
            block.removeAttribute("hidden");
            /* The inline display:none keeps a page-level display rule from
               showing the block before this script runs (and on the
               international page, where this stylesheet is not loaded). */
            if (block.style && block.style.display === "none") block.style.display = "";
        });
    }

    function localizeDocument() {
        if (state.region !== "cn" || !document.body) return;
        injectStyles();
        revealChinaBlocks();
        insertBanner();
        addNavToggle();
        removeUpdaterEntries();
        var brand = document.getElementById("lumen-brand-title");
        if (brand) brand.textContent = "Innioasis 固件下载";
        translateNode(document.body);
        var key = String(document.title || "").replace(/\s+/g, " ").trim();
        if (TITLES[key]) document.title = TITLES[key];
        var description = document.querySelector('meta[name="description"]');
        if (description && /firmware|updater|flash tool/i.test(description.getAttribute("content") || "")) {
            description.setAttribute("content", "Innioasis 与 Timmkoo 播放器固件下载：官方固件、恢复包，以及 Rockbox、Better-Y、Solar、JJ Launcher 等系统的便携刷机包与独立 ZIP 下载。");
        }
    }

    function watchChanges() {
        if (observer || !document.body || typeof MutationObserver !== "function") return;
        observer = new MutationObserver(function (records) {
            if (applying || state.region !== "cn") return;
            applying = true;
            try {
                for (var i = 0; i < records.length; i += 1) {
                    var record = records[i];
                    if (record.type === "childList") {
                        for (var j = 0; j < record.addedNodes.length; j += 1) {
                            var added = record.addedNodes[j];
                            if (added.nodeType === 3) translateNode(added);
                            else if (added.nodeType === 1) {
                                if (added.id === "cn-region-banner") continue;
                                translateNode(added);
                            }
                        }
                        if (record.target && record.target.nodeType === 1) {
                            translateNode(record.target);
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

    function applyRegion() {
        var cn = state.region === "cn";
        root.setAttribute("data-region", cn ? "cn" : "intl");
        if (cn) {
            root.classList.add("cn-region");
            root.setAttribute("lang", "zh-Hans");
            localizeDocument();
            watchChanges();
        } else {
            root.classList.remove("cn-region");
            /* Only show a way back when the visitor chose the international
               page themselves; automatic international visits stay clean. */
            if (state.chosen === "intl") addNavToggle();
        }
    }

    function setRegion(region) {
        state.region = region;
        state.chosen = region;
        rememberRegion(region);
        applyRegion();
    }

    document.addEventListener("click", function (event) {
        var link = event.target && event.target.closest ? event.target.closest("[data-cn-region]") : null;
        if (!link) return;
        rememberRegion(link.getAttribute("data-cn-region"));
    }, true);

    window.InnioasisRegion = {
        get region() { return state.region; },
        isChina: function () { return state.region === "cn"; },
        set: setRegion
    };

    applyRegion();

    /* Confirm with Cloudflare's own view of the visitor. The trace endpoint
       only exists behind Cloudflare, and a failed lookup changes nothing. */
    if (!state.chosen && state.region === "intl") {
        try {
            var controller = typeof AbortController === "function" ? new AbortController() : null;
            var timer = setTimeout(function () { if (controller) controller.abort(); }, 2000);
            fetch("/cdn-cgi/trace", { cache: "no-store", signal: controller ? controller.signal : undefined })
                .then(function (response) { return response.ok ? response.text() : ""; })
                .then(function (text) {
                    var match = /(?:^|\n)loc=([A-Z]{2})(?:\n|$)/.exec(text || "");
                    clearTimeout(timer);
                    if (match && match[1] === "CN") setRegion("cn");
                })
                .catch(function () { clearTimeout(timer); });
        } catch (_) {}
    }
})();
