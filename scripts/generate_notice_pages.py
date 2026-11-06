#!/usr/bin/env python3
"""Render one static HTML page per entry in notice.xml.

The notices page loads notice.xml at runtime; search engines and answer
engines only see that rendering if they execute scripts. This generator
writes an equivalent page per notice so each has a stable, crawlable URL:
    https://innioasis.app/notices/<id>.html
It also refreshes notices/index.html and the sitemap entries.
"""
import html
import pathlib
import re
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://innioasis.app"
BRAND = "Innioasis Updater"


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r'<img src="\2" alt="\1" loading="lazy">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def markdown_to_html(md):
    out, para, items, ordered, fence = [], [], [], False, False
    def flush_para():
        nonlocal para
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []
    def flush_list():
        nonlocal items, ordered
        if items:
            tag = "ol" if ordered else "ul"
            out.append("<%s>" % tag + "".join("<li>" + inline(i) + "</li>" for i in items) + "</%s>" % tag)
            items = []
    for raw in md.replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        if line.strip().startswith("```"):
            flush_para(); flush_list()
            if not fence:
                out.append("<pre><code>")
            else:
                out.append("</code></pre>")
            fence = not fence
            continue
        if fence:
            out.append(html.escape(line))
            continue
        if not line.strip():
            flush_para(); flush_list(); continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush_para(); flush_list()
            n = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (n, inline(m.group(2)), n)); continue
        if re.match(r"^(-{3,}|\*{3,})$", line.strip()):
            flush_para(); flush_list(); out.append("<hr>"); continue
        if line.startswith(">"):
            flush_para(); flush_list()
            out.append("<blockquote><p>" + inline(line.lstrip("> ").strip()) + "</p></blockquote>"); continue
        m = re.match(r"^\s*[-*]\s+(.*)$", line)
        if m:
            flush_para()
            if ordered or not items and ordered: pass
            if ordered: flush_list()
            items.append(m.group(1)); ordered = False; continue
        m = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if m:
            flush_para()
            if items and not ordered: flush_list()
            items.append(m.group(1)); ordered = True; continue
        para.append(line.strip())
    flush_para(); flush_list()
    return "\n".join(x for x in out if x)


HEAD = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="author" content="Ryan Specter &amp; Innioasis Community">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} - {brand}</title>
  <meta name="description" content="{desc}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{title} - {brand}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:site_name" content="{brand}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title} - {brand}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{site}/assets/og-image.png">
  <link rel="icon" href="{up}y1_illustration.png">
  <link rel="stylesheet" href="{up}site-theme.css?v=20260803">
  <link rel="stylesheet" href="{up}lumen.css?v=20261105hero">
  <link rel="stylesheet" href="{up}site-pages.css?v=20260818">
  <link rel="stylesheet" href="{up}site-toolbar.css?v=20261105dockclose">
  <script src="{up}site-init.js?v=20260803" defer></script>
</head>
<body class="site-themes-app"><a class="lumen-skip-link" href="#main">Skip to content</a><div id="nav-root"></div>
"""

FOOT = """<div id="footer-root"></div><div id="support-toolbar-slot"></div>
<script src="{up}firmware-catalog.js?v=20261106mirror" defer></script>
<script src="{up}nav.js?v=20261105copyleft" defer></script>
<script src="{up}lumen-site.js?v=20260817" defer></script>
<script src="{up}site-i18n.js?v=20260830" defer></script>
</body></html>
"""


def window(n):
    """Name every target a notice was written for, in the same order the
    website and the app show them. These pages are the unfiltered view, so a
    reader must be able to tell who a notice was addressed to."""
    parts = []
    if n.get("from"):
        parts.append("From " + n.get("from"))
    if n.get("until"):
        parts.append("until " + n.get("until"))
    if n.get("models"):
        parts.append("Models: " + n.get("models"))
    if n.get("device_type"):
        parts.append("Type " + n.get("device_type"))
    if n.get("firmware_repo"):
        repos = [repo.strip().split("/")[-1] for repo in n.get("firmware_repo").split(",") if repo.strip()]
        if repos:
            parts.append("Software: " + ", ".join(repos))
    if n.get("firmware_version"):
        parts.append("Version " + n.get("firmware_version"))
    return " · ".join(parts)


def build():
    tree = ET.parse(ROOT / "notice.xml")
    notices = []
    for n in tree.getroot().findall("notice"):
        title = (n.findtext("title") or "").strip()
        content = (n.findtext("content") or n.findtext("body") or "").strip()
        full = (n.findtext("full_content") or content).strip()
        url = (n.findtext("url") or n.findtext("link") or "").strip()
        if url.rstrip("/") == SITE:
            url = ""
        notices.append({"id": n.get("id"), "title": title, "content": content,
                        "full": full, "url": url, "meta": window(n),
                        "severity": (n.get("severity") or "info")})
    noticees_dir = ROOT / "notices"
    noticees_dir.mkdir(exist_ok=True)
    written = []
    for n in notices:
        desc = re.sub(r"\s+", " ", re.sub(r"[*_`#>\[\]]|\(([^)]*)\)", r"\1", n["content"]))[:180].strip()
        canonical = "%s/notices/%s.html" % (SITE, n["id"])
        body = [HEAD.format(title=html.escape(n["title"]), brand=BRAND, desc=html.escape(desc),
                            canonical=canonical, site=SITE, up="../")]
        body.append('<main id="main" class="lumen-guide">\n<header><p class="lumen-kicker">%s</p>'
                    '<h1>%s</h1><p class="lead">%s</p><p class="lumen-meta">%s</p></header>\n'
                    % (html.escape(n["meta"] or "Notice"), html.escape(n["title"]),
                       html.escape(n["content"]), html.escape(n["meta"])))
        body.append('<section class="lumen-guide-section lumen-notice-body">%s</section>\n'
                    % markdown_to_html(n["full"]))
        if n["url"]:
            body.append('<p class="lumen-actions"><a class="lumen-button lumen-button--primary" href="%s" rel="noopener">Open the linked page</a></p>\n' % html.escape(n["url"]))
        body.append('<p class="lumen-notice-back"><a href="index.html">← All notices</a></p>\n</main>\n')
        body.append(FOOT.format(up="../"))
        (noticees_dir / (n["id"] + ".html")).write_text("".join(body), encoding="utf-8")
        written.append(n)
    idx = [HEAD.format(title="Notices", brand=BRAND, desc="Current Innioasis Updater notices and device safety advisories.",
                       canonical=SITE + "/notices/index.html", site=SITE, up="../")]
    idx.append('<main id="main" class="lumen-guide">\n<header><p class="lumen-kicker">Notices</p><h1>Current notices</h1>'
               '<p class="lead">Device safety advisories and release notes shown in Innioasis Updater.</p></header>\n<section class="lumen-guide-section"><div class="lumen-grid">')
    for n in written:
        idx.append('<article class="lumen-card"><small>%s</small><h3><a href="%s.html">%s</a></h3><p>%s</p></article>'
                   % (html.escape(n["meta"]), n["id"], html.escape(n["title"]), html.escape(n["content"])))
    idx.append('</div></section></main>\n' + FOOT.format(up="../"))
    (noticees_dir / "index.html").write_text("".join(idx), encoding="utf-8")
    # sitemap
    sp = ROOT / "sitemap.xml"
    if sp.exists():
        s = sp.read_text(encoding="utf-8")
        for n in written:
            loc = "%s/notices/%s.html" % (SITE, n["id"])
            if loc not in s:
                s = s.replace("</urlset>", "  <url><loc>%s</loc><changefreq>weekly</changefreq></url>\n</urlset>" % loc)
        if "%s/notices/" % SITE not in s:
            s = s.replace("</urlset>", "  <url><loc>%s/notices/index.html</loc><changefreq>weekly</changefreq></url>\n</urlset>" % SITE)
        sp.write_text(s, encoding="utf-8")
    print("generated %d notice pages" % len(written))


if __name__ == "__main__":
    build()
