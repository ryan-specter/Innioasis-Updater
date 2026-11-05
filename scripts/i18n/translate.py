#!/usr/bin/env python3
"""
Translate the source catalog into every locale.

    python scripts/i18n/translate.py --provider google-web --locales all
    python scripts/i18n/translate.py --provider google-cloud --locales de,fr,ja
    python scripts/i18n/translate.py --check

The translator is incremental and resumable: each locale keeps a cache of
finished strings, so a run that is interrupted (or a later edit to one page)
only pays for what is new. Writes i18n/catalogs/<locale>.json, which the
runtime and the pre-renderer both read.

Providers
---------
google-web   Google Translate's public endpoint, no key, rate limited.
google-cloud Official API, needs GOOGLE_TRANSLATE_API_KEY.
deepl        Needs DEEPL_API_KEY; covers a subset of Google's languages.
libre        Self-hosted LibreTranslate; needs LIBRETRANSLATE_URL.

Brand names are masked before a string is sent so a translator cannot turn
"Solar" into the sun or "Rondo" into a musical form, then restored afterwards.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from i18n_core import base_of, load_locales  # noqa: E402

CONFIG_PATH = os.path.join(ROOT, "i18n", "config.json")
LOCALES_PATH = os.path.join(ROOT, "i18n", "locales.json")

# A practical launch set: the audiences the firmware archive actually hears
# from. "--locales all" covers every language Google Translate supports.
CORE_LOCALES = [
    "de", "fr", "es", "pt-BR", "it", "nl", "pl", "ru", "uk", "tr",
    "ar", "he", "fa", "hi", "bn", "id", "ms", "fil", "vi", "th",
    "ja", "ko", "zh-CN", "zh-TW", "sv", "da", "fi", "no", "cs", "ro",
]

DEEPL_TARGETS = {
    "bg": "BG", "cs": "CS", "da": "DA", "de": "DE", "el": "EL", "en": "EN",
    "es": "ES", "et": "ET", "fi": "FI", "fr": "FR", "hu": "HU", "id": "ID",
    "it": "IT", "ja": "JA", "ko": "KO", "lt": "LT", "lv": "LV", "nl": "NL",
    "no": "NB", "pl": "PL", "pt": "PT-PT", "ro": "RO", "ru": "RU", "sk": "SK",
    "sl": "SL", "sv": "SV", "tr": "TR", "uk": "UK", "zh-CN": "ZH",
}


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


class Masker:
    """Hide brand names behind numbered tokens for the round trip."""

    def __init__(self, terms: Sequence[str]):
        # Longest first so "Innioasis Updater" wins over "Innioasis".
        self.terms = sorted({term for term in terms if term}, key=len, reverse=True)
        self.pattern = (
            re.compile("|".join(re.escape(term) for term in self.terms)) if self.terms else None
        )
        self.token_re = re.compile(r"\[\[\s*(\d+)\s*\]\]")

    def mask(self, text: str) -> Tuple[str, List[str]]:
        if not self.pattern:
            return text, []
        found: List[str] = []

        def swap(match: "re.Match[str]") -> str:
            found.append(match.group(0))
            return f"[[{len(found) - 1}]]"

        return self.pattern.sub(swap, text), found

    def restore(self, text: str, found: Sequence[str]) -> str:
        def swap(match: "re.Match[str]") -> str:
            index = int(match.group(1))
            return found[index] if 0 <= index < len(found) else match.group(0)

        return self.token_re.sub(swap, text)


def http_post(url: str, data: bytes, headers: Dict[str, str], timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def http_get(url: str, timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "innioasis-site-i18n/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


class Provider:
    name = "base"
    max_chars = 4000
    sleep = 0.0

    def translate(self, texts: Sequence[str], target: str) -> List[str]:
        raise NotImplementedError


class GoogleWeb(Provider):
    """translate_a/single with client=gtx: no key, one request carries a batch."""

    name = "google-web"
    endpoint = "https://translate.googleapis.com/translate_a/single"

    def __init__(self, config: dict):
        self.max_chars = int(config.get("maxCharsPerRequest", 4200))
        self.sleep = float(config.get("sleepSeconds", 0.12))
        self.endpoint = config.get("endpoint", self.endpoint)

    def translate(self, texts: Sequence[str], target: str) -> List[str]:
        query = urllib.parse.urlencode(
            {"client": "gtx", "sl": "en", "tl": target, "dt": "t", "q": "\n".join(texts)}
        )
        raw = http_get(f"{self.endpoint}?{query}")
        payload = json.loads(raw.decode("utf-8"))
        segments = payload[0] if payload else []
        joined = "".join(
            segment[0] for segment in segments if isinstance(segment, list) and segment and segment[0]
        )
        return [joined]


class GoogleCloud(Provider):
    name = "google-cloud"
    endpoint = "https://translation.googleapis.com/language/translate/v2"

    def __init__(self, config: dict):
        self.max_chars = int(config.get("maxCharsPerRequest", 8000))
        self.endpoint = config.get("endpoint", self.endpoint)
        self.key = os.environ.get(config.get("envKey", "GOOGLE_TRANSLATE_API_KEY"), "")
        if not self.key:
            raise SystemExit(
                "GOOGLE_TRANSLATE_API_KEY is not set. Use --provider google-web, or export the key."
            )

    def translate(self, texts: Sequence[str], target: str) -> List[str]:
        body = json.dumps({"q": list(texts), "target": target, "format": "text"}).encode("utf-8")
        raw = http_post(
            f"{self.endpoint}?key={urllib.parse.quote(self.key)}",
            body,
            {"Content-Type": "application/json"},
        )
        payload = json.loads(raw.decode("utf-8"))
        items = payload["data"]["translations"]
        return [item["translatedText"] for item in items]


class DeepL(Provider):
    name = "deepl"
    endpoint = "https://api-free.deepl.com/v2/translate"

    def __init__(self, config: dict):
        self.max_chars = int(config.get("maxCharsPerRequest", 4000))
        self.endpoint = config.get("endpoint", self.endpoint)
        self.key = os.environ.get(config.get("envKey", "DEEPL_API_KEY"), "")
        if not self.key:
            raise SystemExit("DEEPL_API_KEY is not set.")

    def translate(self, texts: Sequence[str], target: str) -> List[str]:
        body = urllib.parse.urlencode(
            [("source_lang", "EN"), ("target_lang", target)] + [("text", text) for text in texts]
        ).encode("utf-8")
        raw = http_post(
            self.endpoint,
            body,
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"DeepL-Auth-Key {self.key}",
            },
        )
        payload = json.loads(raw.decode("utf-8"))
        return [item["text"] for item in payload["translations"]]


class LibreTranslate(Provider):
    name = "libre"
    max_chars = 3000

    def __init__(self, config: dict):
        self.endpoint = os.environ.get(config.get("envUrl", "LIBRETRANSLATE_URL"), "").rstrip("/")
        self.key = os.environ.get(config.get("envKey", "LIBRETRANSLATE_API_KEY"), "")
        if not self.endpoint:
            raise SystemExit("LIBRETRANSLATE_URL is not set.")

    def translate(self, texts: Sequence[str], target: str) -> List[str]:
        body = json.dumps(
            {"q": list(texts), "source": "en", "target": target, "format": "text", "api_key": self.key}
        ).encode("utf-8")
        raw = http_post(self.endpoint + "/translate", body, {"Content-Type": "application/json"})
        payload = json.loads(raw.decode("utf-8"))
        if "translatedText" in payload and isinstance(payload["translatedText"], str):
            return [payload["translatedText"]]
        return [item["translatedText"] for item in payload.get("translations", [])]


PROVIDERS = {
    "google-web": GoogleWeb,
    "google-cloud": GoogleCloud,
    "deepl": DeepL,
    "libre": LibreTranslate,
}


def chunk(texts: Sequence[str], max_chars: int) -> Iterable[List[str]]:
    batch: List[str] = []
    size = 0
    for text in texts:
        if batch and size + len(text) + 1 > max_chars:
            yield batch
            batch, size = [], 0
        batch.append(text)
        size += len(text) + 1
    if batch:
        yield batch


def split_translation(translated: str, expected: int) -> Optional[List[str]]:
    """Google keeps our newlines; if it merged them, the batch is unusable."""
    if expected == 1:
        return [translated.strip()]
    parts = [part.strip() for part in translated.split("\n")]
    parts = [part for part in parts if part]
    if len(parts) != expected:
        return None
    return parts


def translate_texts(
    provider: Provider,
    texts: Sequence[str],
    target: str,
    masker: Masker,
    retries: int = 4,
) -> Dict[str, str]:
    """Translate a list of source strings, returning only the ones that changed."""
    result: Dict[str, str] = {}
    total_batches = 0
    failed = 0

    for batch in chunk(texts, provider.max_chars):
        total_batches += 1
        masked: List[str] = []
        masks: List[List[str]] = []
        for text in batch:
            hidden, found = masker.mask(text)
            masked.append(hidden)
            masks.append(found)

        translated: Optional[List[str]] = None
        last_error: Optional[Exception] = None
        for attempt in range(retries):
            try:
                raw = provider.translate(masked, target)
                if len(raw) == len(batch):
                    translated = [item.strip() for item in raw]
                else:
                    translated = split_translation(raw[0] if raw else "", len(batch))
                if translated is not None:
                    break
                last_error = ValueError("segment count changed")
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, KeyError) as error:
                last_error = error
                backoff = min(8.0, 0.6 * (2**attempt))
                time.sleep(backoff)
            if translated is None and attempt < retries - 1:
                time.sleep(min(4.0, 0.4 * (2**attempt)))

        if translated is None:
            # Retry one at a time: a single awkward string should not take a
            # whole batch down with it.
            translated = []
            for text in masked:
                try:
                    single = provider.translate([text], target)
                    translated.append(single[0].strip() if single else "")
                except Exception:  # noqa: BLE001 - reported through the counter
                    translated.append("")
                time.sleep(provider.sleep)
            failed += 1

        for source, target_language_text, found in zip(batch, translated, masks):
            if not target_language_text:
                continue
            restored = masker.restore(target_language_text, found)
            if restored.strip() and restored.strip() != source:
                result[source] = restored.strip()
        if provider.sleep:
            time.sleep(provider.sleep)

    if failed:
        print(f"    {failed}/{total_batches} batches needed per-string retries", file=sys.stderr)
    return result


def select_locales(requested: str, bases: List[dict], variants: List[dict]) -> List[dict]:
    by_code = {entry["code"]: entry for entry in bases}
    variant_by_code = {entry["code"]: entry for entry in variants}

    if requested.strip().lower() == "all":
        return bases
    if requested.strip().lower() == "core":
        return [by_code[code] for code in CORE_LOCALES if code in by_code] or bases

    selected: List[dict] = []
    for raw in requested.split(","):
        code = raw.strip()
        if not code or code == "en":
            continue
        if code in by_code:
            selected.append(by_code[code])
        elif code in variant_by_code:
            base = variant_by_code[code]["base"]
            if base in by_code and by_code[base] not in selected:
                selected.append(by_code[base])
        else:
            print(f"Skipping unknown locale: {code}", file=sys.stderr)
    return selected


def coverage(strings_file: str, catalog_dir: str, bases: List[dict]) -> int:
    if not os.path.exists(strings_file):
        print("No source catalog yet. Run extract_strings.py first.", file=sys.stderr)
        return 2
    source = load_json(strings_file)["strings"]
    print(f"{'locale':<10} {'strings':>8} {'done':>8} {'missing':>8}  catalog")
    incomplete = 0
    for entry in bases:
        path = os.path.join(catalog_dir, entry["code"] + ".json")
        done = 0
        if os.path.exists(path):
            done = len(load_json(path).get("strings", {}))
        missing = max(0, len(source) - done)
        if missing:
            incomplete += 1
        print(f"{entry['code']:<10} {len(source):>8} {done:>8} {missing:>8}  {'yes' if os.path.exists(path) else 'no'}")
    print(f"\n{incomplete} locale(s) still incomplete.")
    return 0


def write_locale_index(locales: List[dict], variants: List[dict], catalog_dir: str) -> None:
    """A small file the browser shell fetches to build its language picker."""
    available = []
    for entry in locales:
        path = os.path.join(catalog_dir, entry["code"] + ".json")
        if not os.path.exists(path):
            continue
        available.append(
            {
                "code": entry["code"],
                "name": entry.get("name", entry["code"]),
                "native": entry.get("native", entry.get("name", entry["code"])),
                "dir": entry.get("dir", "ltr"),
            }
        )
    for entry in variants:
        base = entry.get("base", "")
        if not any(available_entry["code"] == base for available_entry in available):
            continue
        available.append(
            {
                "code": entry["code"],
                "name": entry.get("name", entry["code"]),
                "native": entry.get("native", entry.get("name", entry["code"])),
                "dir": entry.get("dir", "ltr"),
                "base": base,
            }
        )
    available.sort(key=lambda item: item["code"])
    save_json(
        os.path.join(ROOT, "i18n", "site-locales.json"),
        {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "locales": available},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--provider", default="google-web", choices=sorted(PROVIDERS))
    parser.add_argument("--locales", default="core", help="'all', 'core', or a comma-separated list")
    parser.add_argument("--limit", type=int, default=0, help="Translate at most N strings per locale")
    parser.add_argument("--check", action="store_true", help="Report coverage and exit")
    parser.add_argument("--force", action="store_true", help="Ignore the cache and redo every string")
    args = parser.parse_args()

    config = load_json(CONFIG_PATH)
    locales_data = load_json(LOCALES_PATH)
    bases, variants = locales_data["locales"], locales_data.get("variants", [])
    bases = [entry for entry in bases if entry["code"] != "en"]

    catalog_dir = os.path.join(ROOT, config["catalogDir"])
    strings_file = os.path.join(ROOT, config["stringsFile"])

    if args.check:
        return coverage(strings_file, catalog_dir, bases)

    if not os.path.exists(strings_file):
        print("No source catalog. Run: python scripts/i18n/extract_strings.py", file=sys.stderr)
        return 2

    source = load_json(strings_file)["strings"]
    # Longest strings last so a batch fails small rather than with a huge tail.
    texts = sorted(source.keys(), key=len)
    if args.limit:
        texts = texts[: args.limit]

    selected = select_locales(args.locales, bases, variants)
    if not selected:
        print("No locales selected.", file=sys.stderr)
        return 2

    provider = PROVIDERS[args.provider](config["providers"].get(args.provider, {}))
    masker = Masker(config.get("protectedTerms", []))

    print(f"Provider : {provider.name}")
    print(f"Strings  : {len(texts)}")
    print(f"Locales  : {len(selected)}")
    print("")

    started = time.time()
    for position, entry in enumerate(selected, start=1):
        code = entry["code"]
        target = entry.get("google") or code
        if provider.name == "deepl":
            mapped = DEEPL_TARGETS.get(code)
            if not mapped:
                print(f"[{position}/{len(selected)}] {code:<8} skipped (DeepL has no model)")
                continue
            target = mapped

        cache_path = os.path.join(ROOT, config["cacheDir"], f"{code}.json")
        catalog_path = os.path.join(catalog_dir, code + ".json")
        cache: Dict[str, str] = {}
        if os.path.exists(cache_path) and not args.force:
            cache = load_json(cache_path).get("strings", {})
        elif os.path.exists(catalog_path) and not args.force:
            cache = load_json(catalog_path).get("strings", {})

        pending = [text for text in texts if text not in cache]
        print(f"[{position}/{len(selected)}] {code:<8} {len(cache):>5} cached, {len(pending):>5} to go", flush=True)

        if pending:
            produced = translate_texts(provider, pending, target, masker)
            cache.update(produced)
            save_json(cache_path, {"locale": code, "strings": cache})

        save_json(
            catalog_path,
            {
                "locale": code,
                "name": entry.get("name", code),
                "native": entry.get("native", entry.get("name", code)),
                "dir": entry.get("dir", "ltr"),
                "source": "en",
                "provider": provider.name,
                "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "count": len(cache),
                "strings": dict(sorted(cache.items())),
            },
        )

    write_locale_index(bases, variants, catalog_dir)
    elapsed = time.time() - started
    print(f"\nDone in {elapsed:.0f}s. Catalog: {os.path.relpath(catalog_dir, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
