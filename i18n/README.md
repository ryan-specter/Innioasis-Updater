# Site locales and region editions

> **Status: the locale runtime is disabled for now.** Pages are served in
> English only: no page loads `site-locale.js`, and the China edition
> (`cn-region.js`, `cn-region.css`) has been removed. The pipeline below is
> kept so real translations can be dropped in later — set `ENABLED = True` in
> `scripts/i18n/install_runtime.py` and re-run it to bring the picker back.

The site is written in English and ships in every language Google Translate
supports. Two things are independent:

- **Locale** decides the language of the page.
- **Region** decides what the page is allowed to offer. Mainland China does not
  get the Updater app; Russia and Iran do not get Discord, PayPal or GitHub;
  India has no TikTok. Region copy overrides say that in the reader's language.

## How translation works

Every user-facing string is keyed by its own normalised English text. That one
decision keeps the whole pipeline simple:

- a sentence reused on forty pages is translated once;
- the runtime (browser) and the pre-renderer (build) use the same lookup;
- a missing translation falls back to English instead of showing a key name.

```
i18n/
  locales.json        every Google Translate language + regional variants
  regions.json        what each region offers, and its copy overrides
  config.json         tiers, protected brand terms, provider settings
  strings/en.json     the extracted source: the translation work list
  strings/ui.json     copy rendered by nav.js and friends (harvested)
  catalogs/<lc>.json  the translations, one file per language
  site-locales.json   small index the browser uses to build the language picker
  cache/<lc>.json     resumable per-language cache (safe to delete)
```

`site-locale.js` runs on every page. It resolves the language (URL prefix,
`?lang=`, stored choice, then browser language), loads the matching catalog,
translates text nodes, `title`/`alt`/`placeholder`/`aria-label` and the meta
description, sets `lang` and `dir`, and re-applies itself to content that the
JS shell renders after load. English visits load no catalog at all.

`<html dir>` follows the catalog, so Arabic, Hebrew, Persian, Urdu, Pashto,
Sindhi, Uyghur, Divehi, Kurdish (Sorani), Yiddish and Malay (Jawi) render
right-to-left without a separate stylesheet.

## Commands

```bash
# 1. Harvest copy that only exists in the JS shell (nav, footer, directory UI)
python scripts/i18n/harvest_ui_strings.py

# 2. Extract the source catalog from the pages (core = hand-written pages)
python scripts/i18n/extract_strings.py --tiers core
python scripts/i18n/extract_strings.py --tiers full   # also generated docs

# 3. Translate. Incremental: only new strings cost anything.
python scripts/i18n/translate.py --locales core       # the 30 launch languages
python scripts/i18n/translate.py --locales all        # every Google language
python scripts/i18n/translate.py --locales de,fr,ja   # just these

# 4. Pre-render the translated copies (this is what search engines index)
python scripts/i18n/prerender.py --locales all --tiers core --out dist

# 5. Report coverage
python scripts/i18n/translate.py --check
```

Run step 3 with six workers by splitting the language list, for example:

```bash
python -c "import json;print('\n'.join(l['code'] for l in json.load(open('i18n/locales.json'))['locales']))" \
  | xargs -P 6 -I LC sh -c 'python scripts/i18n/translate.py --locales LC'
```

## Providers

The default is `google-web`: Google Translate's public endpoint, no key, fine
for public marketing copy and rate limited. The pipeline is incremental, so a
throttled run resumes instead of restarting.

| Provider | Needs | Use when |
| --- | --- | --- |
| `google-web` | nothing | default |
| `google-cloud` | `GOOGLE_TRANSLATE_API_KEY` | you want the official API and billing |
| `deepl` | `DEEPL_API_KEY` | European languages, better tone, subset only |
| `libre` | `LIBRETRANSLATE_URL`, optional `LIBRETRANSLATE_API_KEY` | self-hosted, no Google dependency |

Keys are read from the environment and never written to a catalog.

## Brand names

`config.json` lists protected terms — Innioasis, Timmkoo, Rockbox, Solar,
Rondo, SP Flash Tool and so on. They are masked with `[[0]]`-style tokens
before a string is sent and restored afterwards, so a translator cannot turn
"Solar" into the sun or "Rondo" into a musical form. Add a term there before
the first translation of any new product, not after.

## Region rules

Attributes on any element:

| Attribute | Effect |
| --- | --- |
| `data-region-only="cn,ru"` | only shown in those regions |
| `data-region-hide="cn"` | hidden in those regions |
| `data-availability="updater"` | shown only where that capability exists |
| `data-availability-hide="updater"` | hidden where it exists |

Available capabilities: `updater`, `portable-zip`, `themes`, `github`,
`discord`, `reddit`, `youtube`, `tiktok`, `kofi`, `paypal`, `patreon`,
`revolut`, `boosty`, `bitcoin`.

Both the runtime and the pre-renderer apply these, so a region copy is already
clean in its HTML. Region copy overrides run *after* translation and may be
written in any language the region serves:

```json
"Support Updater and the Themes Gallery.": {
  "en": "Support the project on Boosty or with Bitcoin.",
  "ru": "Поддержите проект на Boosty или биткойном."
}
```

A visitor can force an edition with `?region=cn`, and the choice is remembered.

## Pre-rendered copies

`prerender.py` writes `<out>/<locale>/<page>.html` for every selected page:

- text already translated in the HTML, so crawlers see it without running JS;
- region-gated elements already removed for that locale's region;
- `lang` and `dir` on `<html>`;
- canonical and `og:url` pointing at the locale copy;
- `hreflang` alternates for `x-default` and the locale;
- assets rewritten to root-absolute URLs, so the copies share one CSS/JS/image
  tree and only HTML is duplicated;
- internal `.html` links stay relative, so a click inside `/de/` stays there.

`sitemap-i18n.xml` carries the full matrix as `xhtml:link` alternates. The
`dist/` directory is build output and is not committed.

## Adding a language or changing copy

1. Add the code to `i18n/locales.json` (`locales` for a new base language,
   `variants` for a regional flavour of an existing one).
2. Run `translate.py --locales <code>`. Only the new catalog is produced.
3. Run `prerender.py --locales <code>` to publish its copies.

After editing English copy, re-run extraction and translation; unchanged
strings are cached, so only the edited sentences are sent again.

## What is deliberately not translated

- Code, keyboard shortcuts, file paths and `<pre>` blocks.
- Product names in `protectedTerms` (kept verbatim).
- The China edition's own Chinese blocks (`data-cn-only`), which are that
  edition's source text, not English prose.
- Third-party long-form docs are in the `full` tier and are translated only
  when that tier is asked for. They are large and change often.

## Quality

The catalogs are machine translations, reviewed where it matters. Program and
model names are protected, and a native-speaker pass over `catalogs/<lc>.json`
is the intended next step for the launch languages: it is a plain JSON file of
`"English source": "translation"` pairs, so it can be edited directly, and
re-running the translator will not overwrite a hand-edited value unless
`--force` is used.

## Current state

The pipeline, the browser runtime and the region rules are in place and
verified end to end: extraction finds 4,555 source strings across the shared
shell and hand-written pages, the runtime is loaded by all 1,028 pages, the
pre-renderer emits 612 pages for the six launch locales, and the China edition
correctly drops the Updater calls to action while the German copy keeps them.

The six launch languages (de, fr, es, pt-BR, ja, zh-CN) ship hand-reviewed copy
for the shell, home page and picker. The remaining strings and the remaining
183 languages are produced by `translate.py`. A bulk run needs an unblocked
network: while this machine was being rate limited the public Google endpoint
answered `302` with an HTML body, and the translator now stops after three
failed batches instead of sending more traffic. Retry
`python scripts/i18n/translate.py --locales all`, or set
`GOOGLE_TRANSLATE_API_KEY` and run with `--provider google-cloud`.
