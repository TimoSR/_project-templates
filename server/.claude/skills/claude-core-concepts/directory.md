# The `.claude/` directory

## Contents

* Choose the file
* File reference
* Frontmatter fields
* Not in the explorer
* Application data

## Choose the file

| You want to | Edit | Scope |
|---|---|---|
| Project context and conventions | `CLAUDE.md` | project or global |
| Allow or block tool calls | `settings.json` `permissions`, or `hooks` | project or global |
| Run a script before/after tool calls | `settings.json` `hooks` | project or global |
| Env vars for the session | `settings.json` `env` | project or global |
| Personal overrides, out of git | `settings.local.json` | project only |
| A prompt or capability invoked by `/name` | `skills/<name>/SKILL.md` | project or global |
| A specialized subagent | `agents/*.md` | project or global |
| Orchestrate many subagents | `workflows/*.js` | project or global |
| External tools over MCP | `.mcp.json` | project only |
| Response format and tone | `output-styles/*.md` | project or global |

## File reference

Project scope = repo (`.claude/`, or root for `CLAUDE.md`, `.mcp.json`, `.worktreeinclude`). Global = `~/.claude/`.

| File | Scope | Commit | Purpose |
|---|---|---|---|
| `CLAUDE.md` | both | ✓ | instructions loaded every session |
| `rules/*.md` | both | ✓ | topic instructions, optionally path-gated |
| `settings.json` | both | ✓ | permissions, hooks, env, model defaults |
| `settings.local.json` | project | ✗ | personal overrides, gitignored; highest user-editable file |
| `.mcp.json` | project | ✓ | team-shared MCP servers |
| `.worktreeinclude` | project | ✓ | gitignored files to copy into new worktrees |
| `skills/<name>/SKILL.md` | both | ✓ | `/name` or auto-invoked; bundles supporting files read on demand |
| `commands/*.md` | both | ✓ | single-file prompts; same mechanism as skills (prefer skills) |
| `output-styles/*.md` | both | ✓ | custom instruction sets, applied to every response |
| `agents/*.md` | both | ✓ | subagent definitions |
| `workflows/*.js` | both | ✓ | each file becomes `/<name>` |
| `agent-memory/<name>/MEMORY.md` | both | ✓ | subagent's own memory; first 200 lines / 25KB load into its prompt |
| `~/.claude.json` | global | ✗ | app state, OAuth, UI toggles, personal MCP servers |
| `~/.claude/projects/<p>/memory/` | global | ✗ | auto memory; `MEMORY.md` loads at start (200 lines / 25KB), topic files on demand |
| `keybindings.json` | global | ✗ | shortcuts, hot-reloaded |
| `themes/*.json` | global | ✗ | color themes |

Precedence, high to low: managed settings (org) > CLI flags > `settings.local.json` > project `settings.json` > user `settings.json`. Some env vars override their setting.

## Frontmatter fields

| File | Fields |
|---|---|
| `skills/*/SKILL.md` | `name`, `description`, `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`, `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell`, `metadata`, `license`, `compatibility` |
| `commands/*.md` | skill fields except `name`, `paths` |
| `agents/*.md` | `name`, `description`, `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`, `isolation`, `color`, `initialPrompt`, `omitClaudeMd`, `experimental` |
| `output-styles/*.md` | `name`, `description`, `keep-coding-instructions`, `force-for-plugin` |
| `rules/*.md` | `paths` |

Example path-scoped rule (loads only when Claude Reads, Writes or Edits a matching file, then lives in history and is lost on compaction):

```markdown
---
paths: ["src/api/**"]
---
# API conventions
...
```

## Not in the explorer

| File | Location | Purpose |
|---|---|---|
| `managed-settings.json` | system level, per OS | org-enforced, not overridable |
| `CLAUDE.local.md` | project root | private preferences next to CLAUDE.md; create by hand and gitignore |
| `AGENTS.md` | root, `.claude/`, any dir | instructions for other agents; Claude Code can load it alone or with CLAUDE.md |
| Installed plugins | `~/.claude/plugins` | marketplaces, versions, `installed_plugins.json`; synced ones under `plugins/synced/` |

## Application data

`~/.claude` also holds transcripts, prompt history, file snapshots, caches, logs. All **plaintext**: file contents, command output and pasted text that passed through a tool are on disk. Debug config that isn't taking effect with the docs page `debug-your-config`.
