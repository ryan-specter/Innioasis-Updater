# AI skills for the Innioasis community toolchain

These are the reusable instructions that let coding agents and assistants
(Cursor, Claude Code, Warp, Windsurf/Devin, Cline, OpenCode, Antigravity, Grok,
Copilot, Codex, …) install firmware with our tools, guide a user through the
app, or build and publish a firmware package.

The skills follow the open [Agent Skills](https://agentskills.io/specification)
layout: a directory with `SKILL.md` (YAML `name`/`description` frontmatter plus
instructions) and optional `references/`, `scripts/`, `assets/`.

## The skills

| Skill | Use it when | What it does |
|---|---|---|
| [`flash-innioasis-device`](../.agents/skills/flash-innioasis-device/SKILL.md) | a user wants firmware installed, restored or unbricked | automates the flash with the app's headless MTKClient entry point or SP Flash Tool console mode, then verifies, prints post-install steps and offers the one-time donation ask |
| [`guide-updater-ce-install`](../.agents/skills/guide-updater-ce-install/SKILL.md) | the user should drive the app | walks through app install, portable ROM.zip packs, every screen, the failure cards and the completion appeal |
| [`develop-y1-y2-firmware`](../.agents/skills/develop-y1-y2-firmware/SKILL.md) | someone is making or publishing firmware | targets existing Y1/Y2 images, explains `slidia_manifest.xml`, scatters/keylayouts, packaging, mirroring and the archive rules |

`updater-ce-workflow` (in the same directory) remains the developer/verification
runbook for this repository.

## Where each tool looks

Canonical content lives in `.agents/skills/`. The same trees are mirrored (by
`scripts/sync_agent_skills.py`) into the directories that some agents only
read:

| Tool | Project instructions | Skills |
|---|---|---|
| Cursor | `AGENTS.md`, `.cursor/rules/` | `.agents/skills/`, `.cursor/skills/` |
| Claude Code | `AGENTS.md` (read in place of `CLAUDE.md`) | `.claude/skills/` |
| Warp | `AGENTS.md` (or `WARP.md`) | `.agents/skills/` |
| Windsurf / Devin | `AGENTS.md`, `.devin/rules/` | `.agents/skills/`, `.devin/skills/` |
| Cline | `AGENTS.md`, `.clinerules/` | `.cline/skills/` (mirrored) |
| OpenCode | `AGENTS.md` | `.agents/skills/` |
| Antigravity | `AGENTS.md` / `GEMINI.md`, `.agents/rules/` | `.agents/skills/` |
| GitHub Copilot | `AGENTS.md`, `.github/copilot-instructions.md` | `.github/skills/` (mirrored) |
| Grok / Grok CLI | `AGENTS.md` at repo root | `.agents/skills/` |

`AGENTS.md` points at these skills, so a tool that reads only instructions
files still finds them.

## Editing

Edit `.agents/skills/<name>/` only, then run:

```bash
python3 scripts/sync_agent_skills.py          # refresh mirrors
python3 scripts/sync_agent_skills.py --check  # validate frontmatter + detect drift (CI)
```

Frontmatter rules (enforced by `--check`): `name` must equal the directory and
be lowercase-hyphenated, `description` must say what the skill does *and* when
to use it, max 1024 characters, no XML-looking tags.

## Alignment across the Innioasis ecosystem

Several agents work on this ecosystem at once (this updater, the firmware
mirrors, the website). Keep the shared facts identical:

| Fact | Canonical value |
|---|---|
| Catalogue | `https://innioasis.app/slidia_manifest.xml` |
| Firmware archive | `https://github.com/y1-community` |
| App/tool source | `https://github.com/y1-community/updater-ce-neo` |
| Donation link | `https://ko-fi.com/teamslide` |
| Donation rule | once, only after a successful flash, never blocking, skipped when declined |
| Install modes | Download Only (`-c download`, `<download-only/>`); never format |
| Package contract | one scatter + every image it lists + optional `fw_package.ini` |

If a sibling repository needs the same capabilities, copy its `SKILL.md` — or
the whole `.agents/skills` tree plus this script — rather than writing a
different procedure. Tool names, engine order (MTKClient ⇄ SP Flash Tool),
completion markers and error guidance must match, or two agents will give one
user two different answers.

## Safety

Flashing writes a device's storage. The skills require a package that matches
the player, a preflight before any write, and a report of the tool's own
completion line before success is claimed. They do not invent raw partition
writes, and they never ask a user to format a player.
