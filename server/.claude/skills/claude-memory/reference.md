# Claude Memory Reference

## Contents

1. Managed instructions
2. Excluding CLAUDE.md files
3. AGENTS.md details
4. Auto memory settings
5. Version requirements

## 1. Managed instructions

| OS | Managed CLAUDE.md path |
|---|---|
| macOS | `/Library/Application Support/ClaudeCode/CLAUDE.md` |
| Linux, WSL | `/etc/claude-code/CLAUDE.md` |
| Windows | `C:\Program Files\ClaudeCode\CLAUDE.md` |

* Distribute with MDM, Group Policy or Ansible. Applies to every session on the machine, loads before user and project files, and can't be excluded.
* Alternative: inline content in `managed-settings.json`. The `claudeMd` key works only in managed and policy settings; in user, project or local settings it does nothing.

```json
{
  "claudeMd": "Always run `make lint` before committing.\nNever push directly to main."
}
```

| Concern | Configure in |
|---|---|
| Block tools, commands or paths | managed settings `permissions.deny` (enforced by the client) |
| Sandbox isolation | managed settings `sandbox.enabled` |
| Env vars, API provider routing | managed settings `env` |
| Login method, org restriction | managed settings `forceLoginMethod`, `forceLoginOrgUUID` |
| Code style, data handling reminders, behavior | managed CLAUDE.md (guidance, not enforcement) |

## 2. Excluding CLAUDE.md files

Skip another team's ancestor CLAUDE.md or rules in a monorepo. Put it in `.claude/settings.local.json` to keep it personal:

```json
{
  "claudeMdExcludes": [
    "**/monorepo/CLAUDE.md",
    "/home/user/monorepo/other-team/.claude/rules/**"
  ]
}
```

* Globs match **absolute** paths. Works in user, project, local and managed settings; the arrays merge across layers.
* A symlinked rule is excluded when the pattern matches either the path under `.claude/rules/` or the link target.
* Managed CLAUDE.md can't be excluded.

## 3. AGENTS.md details

**Project instructions** values (`/config`, or settings below):

| Value | Claude reads |
|---|---|
| `claude-md-or-agents-md` (default) | CLAUDE.md files; AGENTS.md only when no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` exists in the cwd or above |
| `claude-md-and-agents-md` | both; per directory CLAUDE.md first, then AGENTS.md; an AGENTS.md already imported or symlinked isn't read twice |
| `claude-md` | CLAUDE.md files only |
| `managed-only` | managed CLAUDE.md and auto memory at launch; subdirectory CLAUDE.md, subdirectory rules and `paths:` rules still load on demand |

Set in a file: `~/.claude/settings.json`, a `--settings` file or managed settings. Ignored in project and local settings. Applies from the next message.

```json
{
  "pluginConfigs": {
    "agents-md@builtin": {
      "options": { "instructionFiles": "claude-md-and-agents-md" }
    }
  }
}
```

* Subdirectories: a subdirectory's `AGENTS.md` loads when Claude reads a file there and that subdirectory has none of the three CLAUDE.md files.
* Inside AGENTS.md: `@path` imports expand and `claudeMdExcludes` applies. Subagents that skip project instructions skip it too.
* Confirm it loaded: a line such as `no CLAUDE.md found; AGENTS.md loaded: <path>` at session start, or its path in `/memory`.
* Unavailable (Claude reads CLAUDE.md only, and **Project instructions** is missing from `/config`): version below the minimum (§5), the built-in `agents-md` plugin disabled in `/plugin`, or sometimes the first session after upgrading. Use the `@AGENTS.md` import there.

AGENTS.md read through the setting differs from CLAUDE.md:

| | CLAUDE.md | AGENTS.md via the setting |
|---|---|---|
| `InstructionsLoaded` hooks | fire | don't fire (they do for an imported or symlinked AGENTS.md) |
| `--add-dir` with `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` | loads | doesn't load |
| `@path` outside the working directory | approval dialog | loads only if external imports were already approved, no prompt |

Old workarounds, now that AGENTS.md loads directly:

| Setup | Action |
|---|---|
| `CLAUDE.md` with `@AGENTS.md` | keep it (never double-loads); delete it if it holds nothing else and every session can read AGENTS.md |
| `CLAUDE.md` saying "read AGENTS.md" in words | delete it, or replace the sentence with `@AGENTS.md` (Claude otherwise opens the file only if it decides to) |
| `CLAUDE.md` symlinked to AGENTS.md | nothing; Edit and Write refuse to write through the link and edit `AGENTS.md` instead |
| `SessionStart` hook printing AGENTS.md | remove it: it adds a second copy |

Migrating from another agent: `/import` appends a one-time copy of its instruction files (such as AGENTS.md) to the matching CLAUDE.md and brings over MCP servers, commands, subagents and skills.

## 4. Auto memory settings

* `autoMemoryDirectory`: absolute path or `~/...`; read from user, project, local, policy or `--settings`. From a project's `.claude/settings*.json` it follows the same workspace-trust rule as hooks. With `permissions.blockReadsOutsideWorkingDirectories` on, a directory chosen by a repo-supplied settings file is neither read nor written.
* `CLAUDE_CODE_PROJECT_DIR_NAME` with `CLAUDE_CONFIG_DIR`: fixes the `<project>` folder name, so every repo launched with that config dir shares one memory directory.
* Outside a git repo, `<project>` comes from the project root.
* On by default in local sessions; off by default in self-hosted environments (except Claude Tag sessions).
* The `/memory` toggle can turn memory off but not back on in a background session or in a session another Claude Code session started; run `claude` directly in a terminal and toggle it there.

## 5. Version requirements

| Feature | Minimum Claude Code |
|---|---|
| `/import` | v2.1.213 |
| `modified` timestamp in memory frontmatter | v2.1.214 |
| AGENTS.md read directly | v2.1.277 |
| AGENTS.md listed in `/memory` and `/context` | v2.1.280 |
| AGENTS.md on Bedrock or with telemetry disabled | v2.1.281 |
| `/doctor prompt-audit` | v2.1.283 |

Check with `claude --version`.
