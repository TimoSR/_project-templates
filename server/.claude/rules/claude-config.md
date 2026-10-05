---
paths:
  - ".claude/**"
  - "**/CLAUDE.md"
  - "**/CLAUDE.local.md"
  - "**/AGENTS.md"
---

# Claude config: `.claude/`, CLAUDE.md, AGENTS.md

Project rules live in `.claude/CLAUDE.md`. This file covers changing the Claude setup itself, and loads when Claude reads or edits one of the files above.

## Skills per file

`hooks/require-claude-skills.mjs` blocks a write to these files until the session has invoked their skills.

| Changing | Skills |
|---|---|
| Any `.claude/` file, CLAUDE.md, AGENTS.md | `claude-core-concepts`, `claude-best-practices` |
| CLAUDE.md, CLAUDE.local.md, AGENTS.md, `.claude/rules/` | + `claude-memory` |
| `.claude/skills/` | + `building-skills` |
| `settings*.json`, `.claude/hooks/` | + `update-config` |
| Any `.md` | + `high-quality-tokens` |

## IMPORTANT: Value per token, not fewer tokens

Judge context by the **value each token carries**, never by the token count. Every "cut" in these files (High-Quality Tokens in CLAUDE.md, the skills) means "cut what carries no value". It never means "cut to save tokens".

* Test for every line: does it give the reader something they need and can't derive themselves (a rule, a reason, a fact, an example)?
   * Yes → it stays, however long it is and however often it loads.
   * No → it goes, however short it is.
* Context that is missing or wrong is worse than extra tokens: Claude then guesses.
* Never propose removing or shrinking valuable content because of its size or load cost.

| Content | Value | Decision |
|---|---|---|
| Approach / Data / Building Blocks sections that shape every design | high | keep |
| Valuable content needed only for some tasks (code style, `.claude/` know-how like this file) | high | keep, in a skill or `paths:` rule, not CLAUDE.md or an `@` import: it loads when relevant, and every always-loaded line dilutes adherence to the rest |
| A concrete example that makes a rule unambiguous | high | keep, even if long |
| Preamble, filler, a sentence that repeats the one above | none | cut |
| A rule whose `paths:` match no file here (`API/Backend/**` vs `src/features/**`) | none: it never loads | fix the paths |
| A link to a missing file (`skills/security/guide.md`, only `SKILL.md` exists) | negative: misleads | fix the link |
| Config written for another repo (`dotnet test API/Backend/...`, `yarn` in `web/`) | negative: misleads | match this repo |
| Copies of a rule that disagree (CLAUDE.md vs `rules/code-style.md` vs `c-like-coding-style`) | negative: Claude has to pick one | make them consistent |
