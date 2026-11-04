---
name: release-notes-archive
description: Mining the Innioasis site's generated release notes, imported Markdown docs and feeds for device facts, regressions and fixes. Use when answering "when did X change", finding a workaround, or grounding a modding answer in a real release.
---

# The release notes archive

This repository is also a mirror of every community project's release history
and documentation. The site generates static pages from GitHub releases and from
Markdown linked by those releases, post-install links and READMEs. That archive
is the fastest way to find when a behaviour changed and why.

## Where the knowledge lives

| Path | Contents |
| --- | --- |
| `release-notes/<software>/index.html` | Every release of one project, newest first |
| `release-notes/<software>/<tag>.html` | One release's notes, downloads and install guide |
| `release-notes/index.html` | The archive index, one card per software |
| `post-install/<slug>.html` | Imported project Markdown (post-install guides, docs, changelogs) |
| `post-install/index.html` | Index of imported docs, grouped by firmware |
| `firmware-info/<software>.html` | A project's README rendered as a page |
| `feeds/releases.json`, `feeds/firmware-releases.json` | Machine-readable release index |
| `feeds/*/…`, `feeds/releases.xml`, `feeds/firmware-feed.xml` | Per-owner feeds and the combined XML feed |
| `sitemap.xml` | Every static URL, including generated pages |

The generated pages are plain HTML: no JavaScript is needed to read them, which
is why they are also the best corpus for RAG or an LLM.

## What release notes are good for

Unlike a README, a release note is dated and specific. The Y2Linux notes, for
example, record the cause of a bug, the fix, and the device measurement that
proved it. That is exactly the context an agent needs when a user reports the
same symptom months later.

Look for:

- **Cause → fix → verification** sentences ("the sleep helper retried Bluetooth
  off for up to 25 s... fixed by ...; checked on the player: off after 1.1 s").
- **Hardware facts** that never made it into a manual (panel type, codec
  ceiling, GPIO, partition, current draw).
- **Compatibility boundaries** (a release that raises a firmware level, a
  package that only works on Stock 3.1.7).
- **Known issues** that are still open; they stop you from "fixing" normal
  behaviour.
- **Exact filenames, sizes and hashes** for a package you must verify.

## Search strategy

1. Find the project directory: `release-notes/<slug>/`. The slug comes from
   `firmware-catalog.js` (e.g. `reborn-y2linux-y2`, `rockbox-y1`, `rondo-y1`).
2. Search the generated HTML for the symptom or component:
   `rg -i "suspend|bluetooth|wheel|panel" release-notes/<slug>/`.
3. Search the imported docs too: `rg -i "<term>" post-install/`.
4. Open the release page and read the **whole** entry, not the snippet. The
   cause is often in the second paragraph.
5. Follow links to the project's own validation report for the raw evidence.
6. Check the date and the version; a fix in Beta 9.3.7 does not describe Beta
   9.2.10.
7. Quote the release tag and date in your answer so the user can verify.

Useful `rg` shapes:

```bash
rg -l -i "regression|reverted|workaround" release-notes/
rg -i -C 2 "panel|gc9503|st7701" release-notes/ post-install/
rg -i "only .*stock 3\\.1\\.7|requires .*firmware" release-notes/ post-install/
rg -i "hash|sha-?256|checksum" release-notes/<slug>/
```

## Reading a release page

A generated release page contains:

- the release name, tag, date and prerelease flag;
- the project's Markdown body, rendered with the site's own links (firmware
  page, install guide, related releases);
- download buttons for the project's assets and the portable mirror;
- source citations and a "Get it in Updater CE" action.

If a release body links to another Markdown file (a validation report, an
architecture note), the generator imports it and writes a static page in
`post-install/`. Nested links are followed recursively, so a report linked from
a release and a doc linked from that report are both available.

## Turning notes into a skill or an answer

- Prefer the **newest** statement, but keep the version boundary. "Fixed in
  9.3.7" is not "fixed in 9.2".
- Separate **observed** from **inferred**: release notes often say "not yet
  tried on a player". Repeat that caveat.
- When two projects disagree (e.g. a panel or a partition size), trust the one
  with a device reading or a source file, and say which.
- Do not copy a release note's marketing sentence as a technical fact; look for
  the file, command or measurement behind it.
- If the archive has no answer, go to the project's repository docs, then the
  source. The archive is a finding aid, not the only authority.

## Keeping the archive complete

The generator discovers Markdown from:

- each project's GitHub releases (the body);
- the manifest's `post_install` link;
- Markdown links inside those documents, recursively;
- project READMEs rendered by `generate_firmware_info.py`.

If a document is displayed by the site but has no static page, the crawl did not
reach it. Check `DISCOVERED_MD_SOURCES` in `scripts/generate_doc_pages.py`, the
source URL shape (GitHub blob/raw, relative link), and whether the owning repo is
in the manifest. `site-publishing/SKILL.md` explains the generator contract.

## Source map

| Question | File |
| --- | --- |
| Generated release pages | `release-notes/` |
| Generated imported docs | `post-install/` |
| README pages | `firmware-info/` |
| Machine-readable feeds | `feeds/` |
| Generator | `scripts/generate_doc_pages.py` |
| Catalogue slugs | `firmware-catalog.js` |
