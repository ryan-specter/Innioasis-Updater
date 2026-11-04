#!/usr/bin/env python3
"""Keep the repository's AI skills in one place and mirrored where tools look.

Canonical skills live in ``.agents/skills/<name>/SKILL.md`` (the Agent Skills
layout most agents read). A few agents only look in their own directory, so the
same trees are mirrored there:

    .agents/skills  ->  .claude/skills   (Claude Code)
                    ->  .cline/skills    (Cline)
                    ->  .github/skills   (GitHub Copilot coding agent)

Edit the canonical copy only, then run this script. ``--check`` validates the
frontmatter and reports drift without writing, so CI can fail on a stale
mirror. Other Innioasis repositories can copy this file as-is.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL = REPO_ROOT / ".agents" / "skills"
MIRRORS = (
    REPO_ROOT / ".claude" / "skills",
    REPO_ROOT / ".cline" / "skills",
    REPO_ROOT / ".github" / "skills",
)

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _frontmatter(text: str) -> dict:
    """Minimal frontmatter reader: top-level keys, plain or folded scalars."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data: dict = {}
    key = None
    for raw in match.group(1).splitlines():
        if not raw.strip():
            continue
        if raw[:1] not in " \t" and ":" in raw:
            key, _, value = raw.partition(":")
            key = key.strip()
            value = value.strip()
            if value in (">", ">-", ">+", "|", "|-", "|+"):
                data[key] = ""
            else:
                data[key] = value.strip('"\'')
        elif key is not None:
            data[key] = (data.get(key, "") + " " + raw.strip()).strip()
    return data


def validate_skill(folder: Path) -> list:
    """Frontmatter problems for one skill directory (empty when valid)."""
    problems = []
    skill = folder / "SKILL.md"
    if not skill.is_file():
        return [f"{folder.name}: no SKILL.md"]
    text = skill.read_text(encoding="utf-8", errors="ignore")
    meta = _frontmatter(text)
    name = meta.get("name", "")
    description = meta.get("description", "")
    if not name:
        problems.append(f"{folder.name}: frontmatter has no name")
    else:
        if not NAME_RE.match(name):
            problems.append(f"{folder.name}: name {name!r} is not lowercase-hyphenated")
        if name != folder.name:
            problems.append(f"{folder.name}: name {name!r} does not match the directory")
        if len(name) > 64:
            problems.append(f"{folder.name}: name is longer than 64 characters")
    if not description:
        problems.append(f"{folder.name}: frontmatter has no description")
    else:
        if len(description) > 1024:
            problems.append(f"{folder.name}: description is {len(description)} characters (max 1024)")
        if "<" in description or ">" in description:
            problems.append(f"{folder.name}: description contains XML-looking tags")
    # The body is loaded on activation; keep it inside the recommended budget.
    body_tokens = len(text.split())
    if body_tokens > 5000:
        problems.append(f"{folder.name}: body is ~{body_tokens} words (keep under ~5000 tokens)")
    return problems


def skill_dirs(root: Path) -> list:
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())


def _tree(folder: Path) -> dict:
    return {
        str(path.relative_to(folder)): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def drift(mirror: Path) -> list:
    """Skills whose mirrored copy differs from the canonical one."""
    missing = []
    canonical = {d.name: d for d in skill_dirs(CANONICAL)}
    mirrored = {d.name: d for d in skill_dirs(mirror)}
    for name, source in canonical.items():
        target = mirrored.get(name)
        if target is None:
            missing.append(f"{mirror.name}: missing skill {name}")
        elif _tree(source) != _tree(target):
            missing.append(f"{mirror.name}: {name} differs from .agents/skills")
    for name in mirrored:
        if name not in canonical:
            missing.append(f"{mirror.name}: stale skill {name}")
    return missing


def sync() -> None:
    for mirror in MIRRORS:
        mirror.mkdir(parents=True, exist_ok=True)
        canonical = {d.name: d for d in skill_dirs(CANONICAL)}
        for stale in skill_dirs(mirror):
            if stale.name not in canonical:
                shutil.rmtree(stale)
        for name, source in canonical.items():
            target = mirror / name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(
                source, target,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
            )
        print(f"synced {len(canonical)} skill(s) -> {mirror.relative_to(REPO_ROOT)}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="validate and report drift, write nothing")
    args = parser.parse_args(argv)

    if not CANONICAL.is_dir():
        print(f"{CANONICAL.relative_to(REPO_ROOT)} does not exist", file=sys.stderr)
        return 1

    problems = []
    for folder in skill_dirs(CANONICAL):
        problems.extend(validate_skill(folder))
    if args.check:
        for mirror in MIRRORS:
            problems.extend(drift(mirror))
        for problem in problems:
            print(problem, file=sys.stderr)
        if problems:
            print("Run scripts/sync_agent_skills.py to fix the mirrors.", file=sys.stderr)
            return 1
        print(f"{len(skill_dirs(CANONICAL))} skill(s) valid and in sync")
        return 0

    for problem in problems:
        print(f"warning: {problem}", file=sys.stderr)
    sync()
    return 0


if __name__ == "__main__":
    sys.exit(main())
