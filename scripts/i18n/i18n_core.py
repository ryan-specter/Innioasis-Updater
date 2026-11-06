"""
Shared HTML string handling for the locale pipeline.

The site is plain static HTML, so translation works on the source text itself:
catalogs are keyed by the normalised English string. That keeps the runtime
(which walks text nodes) and the pre-renderer (which walks the raw markup)
using exactly the same lookup, and it means a phrase reused on forty pages is
translated once.

Nothing here depends on a third-party parser; the tokenizer only needs to know
where tags end, which it tracks with quote awareness so an attribute containing
'>' does not split a tag in half.

Skip regions are tracked as a stack of element names, not a depth counter: a
counter cannot tell which closing tag it is looking at, and one unbalanced
</script> would silently discard the rest of the page.
"""

from __future__ import annotations

import html as html_lib
import json
import re
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

# Elements whose text is code, not prose. Their contents are never translated.
DEFAULT_SKIP_TAGS = frozenset(
    {"script", "style", "pre", "code", "kbd", "samp", "textarea"}
)

VOID_TAGS = frozenset(
    {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }
)

# Meta tags whose content is user-facing prose worth translating.
META_CONTENT_NAMES = frozenset(
    {
        "description", "keywords", "og:title", "og:description",
        "og:site_name", "twitter:title", "twitter:description",
    }
)

# Accepts both <div ...> and </div>.
TAG_NAME_RE = re.compile(r"<\s*/?\s*([A-Za-z][A-Za-z0-9:-]*)")
ATTR_RE = re.compile(
    r"""([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*("([^"]*)"|'([^']*)'|([^\s"'=<>`]+))"""
)
# Boolean attributes carry no value: <section data-cn-only hidden>. They are
# what the region system actually uses, so they must be read too.
BARE_ATTR_RE = re.compile(r"\s([A-Za-z_:][-A-Za-z0-9_:.]*)(?=\s|/?>)")
QUOTED_RE = re.compile(r'"[^"]*"|\'[^\']*\'')
HAS_LETTER_RE = re.compile(r"[A-Za-z\u00c0-\u024f\u0400-\u04ff\u0370-\u03ff]")
# Source copy is English. A string already written in CJK belongs to another
# edition and must never enter the English catalog as if it were source.
NON_SOURCE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")

TRANSLATABLE_ATTRIBUTES = ("title", "alt", "placeholder", "aria-label", "aria-description")


def tokenize(markup: str) -> Iterator[Tuple[str, str]]:
    """Yield ('tag'|'text', raw) pairs.

    Comments, doctypes and processing instructions come back as 'tag' tokens so
    they are passed through untouched.
    """
    index = 0
    length = len(markup)
    while index < length:
        start = markup.find("<", index)
        if start < 0:
            yield ("text", markup[index:])
            return
        if start > index:
            yield ("text", markup[index:start])

        if markup.startswith("<!--", start):
            end = markup.find("-->", start + 4)
            end = length if end < 0 else end + 3
            yield ("tag", markup[start:end])
            index = end
            continue

        cursor = start + 1
        quote = ""
        while cursor < length:
            char = markup[cursor]
            if quote:
                if char == quote:
                    quote = ""
            elif char in "\"'":
                quote = char
            elif char == ">":
                break
            cursor += 1
        end = cursor + 1 if cursor < length else length
        yield ("tag", markup[start:end])
        index = end


def tag_name(tag: str) -> str:
    match = TAG_NAME_RE.match(tag)
    return match.group(1).lower() if match else ""


def is_end_tag(tag: str) -> bool:
    return tag.startswith("</")


def is_self_closing(tag: str) -> bool:
    name = tag_name(tag)
    return name in VOID_TAGS or tag.rstrip().endswith("/>")


def attributes(tag: str) -> Dict[str, str]:
    """Return the tag's attributes, entity-decoded, name lowercased."""
    found: Dict[str, str] = {}
    for match in ATTR_RE.finditer(tag):
        name = match.group(1).lower()
        value = match.group(3)
        if value is None:
            value = match.group(4)
        if value is None:
            value = match.group(5) or ""
        found.setdefault(name, html_lib.unescape(value))

    # Anything left is a value-less attribute. Quoted values are blanked first
    # so a word inside title="..." is never mistaken for an attribute name.
    without_values = QUOTED_RE.sub('""', tag)
    for match in BARE_ATTR_RE.finditer(without_values):
        name = match.group(1).lower()
        if name not in found:
            found[name] = ""
    return found


def opens_skip_region(tag: str, name: str, attrs: Dict[str, str], skip: Iterable[str]) -> bool:
    if is_self_closing(tag):
        return False
    if name in skip:
        return True
    if "data-i18n-skip" in attrs:
        return True
    if attrs.get("translate", "").lower() == "no":
        return True
    # Copy that is already in another language is that edition's source, not
    # English prose to translate. The China edition writes its blocks in
    # Chinese and is applied by cn-region.js, so it is left untouched here.
    lang = (attrs.get("lang") or "").strip().lower()
    if lang and not lang.startswith("en"):
        return True
    if "data-cn-only" in attrs or "data-cn-hide" in attrs:
        return True
    return False


def normalise(text: str) -> str:
    """Collapse runs of whitespace so markup indentation never changes the key."""
    return re.sub(r"\s+", " ", text).strip()


def is_translatable(text: str) -> bool:
    """Cheap gate: prose, not a number, a symbol or a lone identifier."""
    core = normalise(text)
    if len(core) < 2:
        return False
    return bool(HAS_LETTER_RE.search(core))


def _split_edges(raw: str) -> Tuple[str, str, str]:
    match = re.match(r"^(\s*)([\s\S]*?)(\s*)$", raw)
    if not match:
        return "", raw, ""
    return match.group(1), match.group(2), match.group(3)


def decode_entities(value: str) -> str:
    return html_lib.unescape(value)


def encode_text(value: str) -> str:
    """Minimal escaping for a text node, keeping a no-break space as &nbsp;."""
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return value.replace("\u00a0", "&nbsp;")


def encode_attr(value: str) -> str:
    return html_lib.escape(value, quote=True).replace("&#x27;", "&#39;")


def lookup(core: str, strings: Dict[str, str], rules: Sequence[Sequence[str]] = ()) -> Optional[str]:
    """Find a translation for one normalised source string."""
    direct = strings.get(core)
    if direct is not None:
        return direct
    # The page may carry the entity form ("&amp;") while the catalog stores
    # the decoded text.
    if "&" in core:
        decoded = normalise(decode_entities(core))
        if decoded in strings:
            return strings[decoded]
    for rule in rules:
        pattern, replacement = rule[0], rule[1]
        try:
            if re.search(pattern, core):
                return re.sub(pattern, replacement.replace("$", "\\"), core)
        except re.error:
            continue
    return None


def extract(markup: str, skip_tags: Iterable[str] = DEFAULT_SKIP_TAGS) -> List[Tuple[str, str]]:
    """Collect translatable strings as (kind, normalised text).

    kind is 'text' for a text node, 'attr:<name>' for an attribute, and
    'meta:<name>' for a meta description-style value.
    """
    skip = {tag.lower() for tag in skip_tags}
    found: List[Tuple[str, str]] = []
    skip_open: List[str] = []

    for kind, raw in tokenize(markup):
        if kind == "tag":
            name = tag_name(raw)
            if not name:
                continue
            if is_end_tag(raw):
                if skip_open and skip_open[-1] == name:
                    skip_open.pop()
                continue

            attrs = attributes(raw)
            if not skip_open and not NON_SOURCE_RE.search(raw):
                for attr_name in TRANSLATABLE_ATTRIBUTES:
                    value = attrs.get(attr_name)
                    if value and is_translatable(value):
                        found.append(("attr:" + attr_name, normalise(decode_entities(value))))
                if name == "meta":
                    meta_name = (attrs.get("name") or attrs.get("property") or "").lower()
                    if meta_name in META_CONTENT_NAMES:
                        content = attrs.get("content") or ""
                        if is_translatable(content):
                            found.append(("meta:" + meta_name, normalise(decode_entities(content))))

            if opens_skip_region(raw, name, attrs, skip):
                skip_open.append(name)
            continue

        if skip_open:
            continue
        decoded = decode_entities(raw)
        if not is_translatable(decoded) or NON_SOURCE_RE.search(decoded):
            continue
        found.append(("text", normalise(decoded)))

    return found


def apply_catalog(
    markup: str,
    strings: Dict[str, str],
    rules: Sequence[Sequence[str]] = (),
    skip_tags: Iterable[str] = DEFAULT_SKIP_TAGS,
    translate_attributes: bool = True,
) -> Tuple[str, int]:
    """Return (translated markup, number of replacements)."""
    skip = {tag.lower() for tag in skip_tags}
    out: List[str] = []
    skip_open: List[str] = []
    replaced = 0

    for kind, raw in tokenize(markup):
        if kind == "tag":
            name = tag_name(raw)
            if not name:
                out.append(raw)
                continue
            if is_end_tag(raw):
                if skip_open and skip_open[-1] == name:
                    skip_open.pop()
                out.append(raw)
                continue

            attrs = attributes(raw)
            if not skip_open and translate_attributes:
                rewritten = raw
                for attr_name in TRANSLATABLE_ATTRIBUTES:
                    if attr_name not in attrs:
                        continue
                    source = normalise(decode_entities(attrs[attr_name]))
                    if not is_translatable(source):
                        continue
                    target = lookup(source, strings, rules)
                    if target is None or target == source:
                        continue
                    rewritten = _replace_attribute(rewritten, attr_name, encode_attr(target))
                    replaced += 1
                if name == "meta":
                    meta_name = (attrs.get("name") or attrs.get("property") or "").lower()
                    if meta_name in META_CONTENT_NAMES and "content" in attrs:
                        source = normalise(decode_entities(attrs["content"]))
                        if is_translatable(source):
                            target = lookup(source, strings, rules)
                            if target is not None and target != source:
                                rewritten = _replace_attribute(
                                    rewritten, "content", encode_attr(target)
                                )
                                replaced += 1
                raw = rewritten

            if opens_skip_region(raw, name, attrs, skip):
                skip_open.append(name)
            out.append(raw)
            continue

        if skip_open:
            out.append(raw)
            continue

        prefix, core, suffix = _split_edges(raw)
        source = normalise(decode_entities(core))
        if not is_translatable(source):
            out.append(raw)
            continue
        target = lookup(source, strings, rules)
        if target is None:
            out.append(raw)
            continue
        out.append(prefix + encode_text(target) + suffix)
        replaced += 1

    return "".join(out), replaced


_ATTR_PATTERNS: Dict[str, "re.Pattern[str]"] = {}


def _replace_attribute(tag: str, name: str, value: str) -> str:
    pattern = _ATTR_PATTERNS.get(name)
    if pattern is None:
        pattern = re.compile(
            r"(\s" + re.escape(name) + r"""\s*=\s*)(["'])([\s\S]*?)\2""", re.IGNORECASE
        )
        _ATTR_PATTERNS[name] = pattern
    return pattern.sub(lambda m: m.group(1) + m.group(2) + value + m.group(2), tag, count=1)


def _region_drops(attrs: Dict[str, str], region: str, availability: Dict[str, bool]) -> bool:
    def listed(value: str) -> List[str]:
        return [part.strip().lower() for part in value.split(",") if part.strip()]

    only = attrs.get("data-region-only")
    if only is not None and region.lower() not in listed(only):
        return True
    hide = attrs.get("data-region-hide")
    if hide is not None and region.lower() in listed(hide):
        return True
    need = attrs.get("data-availability")
    if need is not None and not availability.get(need.strip().lower(), True):
        return True
    deny = attrs.get("data-availability-hide")
    if deny is not None and availability.get(deny.strip().lower(), False):
        return True
    return False


def strip_by_region(markup: str, region: str, availability: Dict[str, bool]) -> str:
    """Drop elements a region must not show.

    Supported attributes:
      data-region-only="cn,ru"          keep only in those regions
      data-region-hide="cn"             drop in those regions
      data-availability="updater"       keep only when the region has it
      data-availability-hide="updater"  drop when the region has it
    """
    out: List[str] = []
    drop_open: List[str] = []

    for kind, raw in tokenize(markup):
        if kind == "text":
            if not drop_open:
                out.append(raw)
            continue

        name = tag_name(raw)
        if not name:
            out.append(raw)
            continue

        if is_end_tag(raw):
            if drop_open and drop_open[-1] == name:
                drop_open.pop()
                continue
            if not drop_open:
                out.append(raw)
            continue

        if drop_open:
            if not is_self_closing(raw):
                drop_open.append(name)
            continue

        if _region_drops(attributes(raw), region, availability):
            if not is_self_closing(raw):
                drop_open.append(name)
            continue
        out.append(raw)

    return "".join(out)


def load_locales(path: str) -> Tuple[List[dict], List[dict]]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("locales", []), data.get("variants", [])


def base_of(code: str, bases: Dict[str, dict]) -> str:
    """Resolve a locale code to the catalog that actually stores its strings."""
    if code in bases:
        return code
    language = code.split("-")[0]
    if language in bases:
        return language
    if language == "zh":
        return "zh-CN"
    return "en"
