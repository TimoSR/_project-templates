---
name: claude-memory
description: Sets up, writes and debugs Claude Code's persistent instructions and auto memory - where CLAUDE.md, CLAUDE.local.md, .claude/rules/ and AGENTS.md files go and their load order, @path imports, path-scoped rules (paths frontmatter, globs), when AGENTS.md is read instead of CLAUDE.md, claudeMdExcludes, managed org instructions, and auto memory (MEMORY.md index, memory types, storage location, 200-line / 25KB limit, toggles). Use when creating or editing CLAUDE.md, CLAUDE.local.md, AGENTS.md or a rules file, scoping a rule to some files, importing a file into CLAUDE.md, sharing instructions across repos, worktrees or other coding agents (Cursor, Copilot, Codex), or when an instruction or AGENTS.md is not loading or not followed, a rule disappears after /compact, or the user asks what auto memory saved, where it lives, or how to turn it off. Not for choosing between CLAUDE.md, skills, hooks and subagents in general or for context-window cost (claude-core-concepts), or for writing a skill (building-skills).
---

# Claude Memory

Two mechanisms carry knowledge across sessions. Both load at session start as **context, not enforcement**: whatever must happen regardless of Claude's judgment is a hook (`PreToolUse`), not a memory line. Settings, managed policy, AGENTS.md details and version requirements: [reference.md](reference.md). Source: code.claude.com/docs/en/memory.

| | CLAUDE.md files | Auto memory |
|---|---|---|
| Written by | you | Claude |
| Holds | instructions, rules, conventions | your preferences, your corrections, project context not in the code |
| Scope | org, user, project, local | one git repo, shared by its worktrees; machine-local |
| Loaded | in full, every session (a file over 4 MiB is skipped) | `MEMORY.md`: first 200 lines or 25KB; topic files on demand |

## 1. Where an instruction goes

| The instruction is | Put it in |
|---|---|
| For everyone, every repo on the machine | managed `CLAUDE.md`, deployed by IT ([reference §1](reference.md#1-managed-instructions)) |
| Yours, every repo | `~/.claude/CLAUDE.md` or `~/.claude/rules/*.md` |
| The team's, this repo, every session | `./CLAUDE.md` or `./.claude/CLAUDE.md`, or `.claude/rules/*.md` without `paths:` |
| The team's, only for some files | `.claude/rules/*.md` with `paths:` (§4) |
| Only for one subdirectory | `<dir>/CLAUDE.md`, loads when Claude reads a file in `<dir>` |
| Yours, this repo only (sandbox URL, test data) | `./CLAUDE.local.md`, gitignored |
| Yours, this repo, in every worktree | a file in `~/.claude/`, imported with `@~/.claude/<file>.md` (a gitignored `CLAUDE.local.md` exists only in the worktree that created it) |
| Shared with other coding agents | `AGENTS.md` (§5) |
| A multi-step procedure, needed sometimes | a skill, not memory |
| Must happen every time | a hook, not memory |

Add a line when Claude makes the same mistake twice, review catches something Claude should have known, you type the correction you typed last session, or a new teammate would need it.

## 2. Load order

```
claude launched in repo/app/
  at launch, broadest first:
    managed CLAUDE.md
    ~/.claude/CLAUDE.md, ~/.claude/rules/        user rules load before project rules
    repo/CLAUDE.md          → repo/CLAUDE.local.md
    repo/app/CLAUDE.md      → repo/app/CLAUDE.local.md      read last = closest to cwd
    .claude/rules/*.md without paths:              same priority as .claude/CLAUDE.md
  later, on demand:
    repo/app/sub/CLAUDE.md                         when Claude reads a file in sub/
    rule with paths:                               when Read, Write or Edit touches a match
```

* Files concatenate; none overrides another. Two conflicting lines → Claude may follow either, so delete one.
* Block-level `<!-- notes -->` are stripped before injection: free notes for maintainers. Comments inside code blocks stay.
* Directories added with `--add-dir` load their CLAUDE.md only when `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1`.
* After `/compact`: root CLAUDE.md is re-read from disk. Nested CLAUDE.md and `paths:` rules return only when a matching file is touched again. Chat-only instructions are gone.
* Edits to CLAUDE.md apply after `/clear`, `/compact` or a restart, not mid-session.

## 3. Writing instructions

```
✗ "Format code properly"        ✓ "Use 2-space indentation"
✗ "Test your changes"           ✓ "Run `dotnet test` before committing"
✗ "Keep files organized"        ✓ "Request DTOs live in <module>/_dto/ and are validated there"
```

* Group under headers and bullets; dense paragraphs are followed less reliably.
* Size: Claude Code warns above 200 lines per file and when all files together pass a combined limit. In this repo **value decides, not length** (CLAUDE.md, "Value per token"): keep every line Claude can't derive, move lines needed only for some files into `paths:` rules and procedures into skills. Imports organize a file but don't cut its cost: imported files load at launch too.
* Audit for conflicts, dead file references and outdated instructions: `/doctor prompt-audit` (or `/doctor prompt-audit <path>`). It reports only; nothing changes until you apply it.
* Starting point: `/init` drafts a CLAUDE.md (or suggests improvements to an existing one) and folds in `.cursorrules`, `.cursor/rules/` and `.github/copilot-instructions.md`. With `CLAUDE_CODE_NEW_INIT=1` it asks which of CLAUDE.md, skills and hooks to set up and shows a proposal before writing.

## 4. Imports and rules

**Imports** work in CLAUDE.md, CLAUDE.local.md, AGENTS.md and rules:

```text
- git workflow @docs/git-instructions.md     path is relative to THIS file, not the cwd
- @~/.claude/my-project-instructions.md      home dir: outside the repo → external import
- api spec @Design\ Docs/api.md              escape each space with a backslash
- "@Design Docs/api.md"                      quoted → NOT imported
- `@README`                                  inside backticks or a code fence → literal text
```

* Imports nest at most 4 hops deep.
* An import in a project file that resolves outside the working directory shows a one-time approval dialog. Declining disables external imports for that project for good. Imports in `~/.claude/` files load without the dialog.

**Rules:** `.claude/rules/**/*.md`, found recursively, one topic per file (`testing.md`, `api/validation.md`).

```markdown
---
paths:
  - "src/features/**/api/**/*.cs"
  - "src/**/*.{cs,csproj}"
---
# API rules
- Validate every request DTO before it reaches the domain
```

* `paths` is the only frontmatter field read; any other field is ignored without an error. A YAML list or a comma-separated string.
* No `paths` → loads at launch. With `paths` → loads when Read, Write or Edit touches a matching file; Grep, Glob and Bash don't trigger it.
* YAML that doesn't parse → frontmatter ignored, rule loads **unconditionally**. `claude --debug` shows the parse error.
* Globs: `**/*.cs` any directory, `src/**/*` everything under `src/`, `*.md` repo root only. Brace groups multiply (`{a,b}/{c,d}/*.{ts,tsx}` = 8 patterns); one rule's whole list may expand to 1,000 patterns, past that the pattern is used unexpanded and matches nothing. Match a literal `[` with `\[`.
* Check every pattern against real files: `paths: API/Backend/**` in a repo laid out as `src/features/**` never loads.
* Shared rules across projects: put them in `~/.claude/rules/` (every project, no approval). A symlink in `.claude/rules/` pointing outside the repo counts as an external import, and even after approval only its rules without `paths` load. Network targets (`\\server\share`, `/net`) are never followed. Symlinks on Windows need Administrator or Developer Mode.

## 5. AGENTS.md

Default setting (`claude-md-or-agents-md`):

| Repo has | Claude reads |
|---|---|
| `AGENTS.md`, and no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` in the cwd or above | `AGENTS.md` (and `.claude/AGENTS.md`) |
| `AGENTS.md` plus any of those three | the CLAUDE.md files only |
| a `CLAUDE.md` containing `@AGENTS.md` | both, AGENTS.md through the import (never twice) |

* `~/.claude/CLAUDE.md`, the managed CLAUDE.md and `.claude/rules/` don't count; they load alongside AGENTS.md.
* Trap: creating a personal `CLAUDE.local.md` silently stops AGENTS.md from loading.
* One file for every agent, working on every version and on Windows:

```markdown
@AGENTS.md

## Claude Code
Use plan mode for changes under `src/billing/`.
```

* Avoid `ln -s AGENTS.md CLAUDE.md` when anyone clones on Windows: without `core.symlinks`, git checks it out as a one-line text file.
* Never read: `AGENTS.local.md`, `AGENTS.override.md`, anything under `.agents/`.
* To read both files, only CLAUDE.md, or only managed instructions: `/config` → **Project instructions** ([reference §3](reference.md#3-agentsmd-details)).

## 6. Auto memory

```
~/.claude/projects/<project>/memory/     <project> derived from the git repo: worktrees share it
├── MEMORY.md            index, one line per memory → loads at start (first 200 lines / 25KB)
├── user_role.md         one memory per file, read on demand
└── feedback_testing.md
```

* Frontmatter `type`: `user` (role, expertise, preferences), `feedback` (corrections, confirmed approaches), `project` (ongoing work, decisions not in code or git), `reference` (where outside info lives). Anything derivable from the code, or already in CLAUDE.md, is skipped.
* Claude Code stamps a `modified` ISO 8601 timestamp into the frontmatter on every write to a file that has frontmatter.
* `MEMORY.md` over its limit: the write succeeds, an error tells Claude to rewrite the index, and lines past the limit drop on the next load. Fix: one line per entry, detail into topic files, merge or delete stale entries.
* "Remember to use pnpm" → auto memory. "Add this to CLAUDE.md" → CLAUDE.md.
* Off: the `/memory` toggle (writes `autoMemoryEnabled` to `~/.claude/settings.json`), `"autoMemoryEnabled": false` in a project's settings, or `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`. Move it: `autoMemoryDirectory` ([reference §4](reference.md#4-auto-memory-settings)).
* Subagents don't get the main auto memory (a fork does, it inherits the conversation). A subagent keeps its own with the `memory` field.
* Machine-local: not synced across machines or cloud sessions. Survives the transcript cleanup.

## 7. Troubleshooting

```
instruction not followed?
  /context → is the file under "Memory files"?
    no  → wrong location (§1, §2) · matched by claudeMdExcludes (reference §2)
          · AGENTS.md shadowed by a CLAUDE.md (§5) · paths: never matched a touched file (§4)
    yes → vague?                          rewrite it to be verifiable (§3)
          conflicts with another file?    delete one (/doctor prompt-audit finds them)
          conflicts with built-in git or PR guidance?  includeGitInstructions: false, attribution setting
          must happen at a fixed point?   hook
          gone after /compact?            it was chat-only, nested or path-scoped (§2)
```

* An `InstructionsLoaded` hook logs which files loaded, when and why: useful for `paths:` rules and nested CLAUDE.md.
* System-prompt-level instructions for scripted runs: `--append-system-prompt`.
* What auto memory saved: `/memory` → open the auto memory folder; everything is plain markdown.

## Verify every change

1. Start a fresh session (`/clear` or restart); edits don't apply mid-session.
2. `/context` → the file appears under **Memory files**. For a `paths:` rule or nested CLAUDE.md, first read a file it should match.
3. Ask a question whose answer depends on the new line, and check the answer uses it.
