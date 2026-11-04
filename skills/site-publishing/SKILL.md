---
name: site-publishing
description: Publishing firmware to innioasis.app — slidia_manifest.xml, firmware-catalog.js, the static release/post-install generators, sitemap and llms.txt, and the SEO contract for programmatically displayed Markdown. Use when adding a project, release or documentation page.
---

# Publishing to innioasis.app

The site is static HTML plus a few JavaScript readers. It is also the Updater's
catalogue: the same manifest that drives the site drives what users can install.

## The data chain

```
slidia_manifest.xml  ──┐
firmware-catalog.js  ──┼──> scripts/generate_doc_pages.py ──> release-notes/, post-install/
                       │                                      sitemap.xml
                       └──> scripts/generate_firmware_info.py ──> firmware-info/
                            scripts/generate_notice_pages.py  ──> notices/
                            scripts/generate_sitemap.py       ──> audit/repair sitemap
```

- `slidia_manifest.xml` — the package list: `name`, `repo`, `device`, `url`,
  `type`, `handler`, optional `portable_zips`, `post_install`, `derivative`,
  `icon`.
- `firmware-catalog.js` — the browser catalogue: slug, model, repo, guide,
  description, download metadata. The generators read it too.
- `docs-viewer.js` — the runtime Markdown renderer. The Python generator
  intentionally mirrors its rules so the static page and the reader agree.
- `scripts/generate_doc_pages.py` — writes one static page per release and per
  imported Markdown document, and appends new URLs to `sitemap.xml`.
- `scripts/generate_firmware_info.py` — writes `firmware-info/<slug>.html` from
  each project's README and calls the doc generator for discovered documents.
- `scripts/generate_notice_pages.py` — writes `notices/<id>.html` from
  `notice.xml`.
- `scripts/generate_sitemap.py` — audits/repairs the sitemap; `--check` is the
  CI gate.
- `.github/workflows/generate-doc-pages.yml` — runs hourly and commits generated
  output with the bot identity. Generated pages are expected in the repository.

## Adding a project or release

1. Add or update the `<package>` entry in `slidia_manifest.xml`. One line per
   model if the same repo supports Y1 and Y2.
2. Add the matching catalogue entry in `firmware-catalog.js` (slug, model,
   repo, name, guide, description). The slug is the directory name under
   `release-notes/` and `post-install/`.
3. Add the guide page and link it from `firmware.html`, `llms.txt` and the
   relevant hub if the project has one.
4. Set `post_install` to a Markdown URL. Use a GitHub blob URL with a branch or
   tag; a relative link inside that document is resolved against the repo.
5. Publish a GitHub release with a body that names the assets, their sizes,
   hashes and install caveats. The release body is the source of the static
   notes page.
6. Run the generators (below) and inspect the new pages, not just the exit code.
7. Add a sitemap entry if the generator did not (it appends automatically), and
   run `generate_sitemap.py --check`.

## The Markdown-to-static-HTML contract

The site displays Markdown in three places:

- `release_notes.html` — a release body;
- `post_install.html` — a project's post-install guide or any linked doc;
- `firmware_info.html` — a project README.

Every one of those must have a static HTML equivalent, because search engines,
LLMs and RAG pipelines do not execute the reader's JavaScript. The generator:

- resolves GitHub blob/raw URLs to raw content;
- rewrites relative links and images against the repository;
- renders headings, tables, nested lists, task lists, fenced code, images,
  quotes and a small allowlist of raw HTML;
- turns links to other Markdown documents into site reader links **and**
  registers the target for a static page;
- writes nested documents recursively, so a release note → validation report →
  architecture note chain is fully covered.

When you change the renderer, change both sides: `docs-viewer.js` for the live
reader and `scripts/generate_doc_pages.py` for the static page. A feature that
exists only in one is a bug: the reader and the crawlable page must show the
same document.

### What "complete" means

- No Markdown document reachable from a release, post-install link or README is
  missing a page in `post-install/`.
- A document from a repository that is not itself in the manifest (for example
  Y2Reborn, linked by Y2Linux docs) still gets a page, attributed to that repo.
- Each generated page has a canonical URL, a title, a description, and a link
  back into the site.
- The post-install index links the static page, not only the live reader.
- `sitemap.xml` contains every generated page.

## Commands

```bash
# Regenerate release notes, post-install docs and README pages.
python scripts/generate_doc_pages.py
python scripts/generate_firmware_info.py
python scripts/generate_notice_pages.py

# Audit/repair the sitemap; CI uses --check.
python scripts/generate_sitemap.py --check

# Local preview (any static server works).
python -m http.server 8000
```

Use `--refresh` on the doc generator to bypass the cached GitHub responses when
you have just published a release. The cache lives in `.cache/doc-pages/`
(gitignored).

## SEO and LLM surfaces

- `sitemap.xml` — every page, including generated release/doc pages.
- `llms.txt` — the curated index for answer engines; add new skills, hubs and
  major docs here.
- `robots.txt` — allow the static pages; do not block `/release-notes/`,
  `/post-install/` or `/firmware-info/`.
- Canonical URLs — every generated page declares one; keep the
  `https://innioasis.app/...` form.
- Titles/descriptions — derived from the document's first heading and first
  paragraph. If a page has a bad title, fix the Markdown heading, not the
  generator.
- Internal links — the index pages must link the static pages so crawlers can
  reach them without JavaScript.

## Safety and repository hygiene

- Do not commit `.env`, credentials or `config.ini` secrets.
- Do not hand-edit generated pages; rerun the generator.
- Do not sweep unrelated modified files into a docs commit. Check
  `git status` and stage only the generator, skills and generated output you
  changed.
- The hourly workflow commits its own output; a local run should produce the
  same bytes for the same inputs. If it does not, the generator is
  non-deterministic (ordering, timestamps, cache) — fix that before committing.
- Generated pages may contain third-party text and images. Keep the project's
  licence and attribution in the page footer/citations.

## Source map

| Question | File |
| --- | --- |
| Package manifest | `slidia_manifest.xml` |
| Catalogue and slugs | `firmware-catalog.js` |
| Runtime renderer | `docs-viewer.js` |
| Static generator | `scripts/generate_doc_pages.py` |
| README pages | `scripts/generate_firmware_info.py` |
| Notice pages | `scripts/generate_notice_pages.py` |
| Sitemap audit | `scripts/generate_sitemap.py` |
| Hourly workflow | `.github/workflows/generate-doc-pages.yml` |
| LLM index | `llms.txt` |
