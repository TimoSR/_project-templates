# Extending Claude Code

Source: code.claude.com/docs/en/features-overview. Built-in tools cover most coding; this is the layer you add on top.

## Contents

* What each extension is
* When to add each one
* Comparing look-alikes
* Layering across levels
* Combining features
* Context cost and load timing

## What each extension is

| Feature | What it does | Use when | Example |
|---|---|---|---|
| **CLAUDE.md** | Persistent context, every conversation | Project conventions, "always do X" | "Use pnpm, not npm. Run tests before committing." |
| **Output style** | Role, tone, response format for the session | A voice, length or format wanted in every response, or a non-engineer role | Built-in Concise style; custom "diagram first" style |
| **Skill** | Instructions, knowledge, workflows | Reusable content, reference docs, repeatable tasks | `/deploy` checklist; API docs skill |
| **Subagent** | Isolated context, returns a summary | Context isolation, parallel tasks, specialized workers | Research that reads many files, returns key findings |
| **Dynamic workflow** | Script Claude writes, runs many subagents in background | Work beyond a handful of subagents, or findings to cross-check | Codebase audit with a second agent set verifying each finding |
| **Cross-session messaging** | Claude passes a message from one of your sessions to another | Your parallel sessions need each other's findings | One session warns another its change breaks the other's work |
| **Code intelligence** | Language-server navigation and diagnostics | Typed languages, large codebases where grep is slow | Jump to a definition instead of reading the whole file |
| **MCP** | Connects external services | External data or actions | Query a DB, post to Slack, drive a browser |
| **Hook** | Script, HTTP request, MCP tool call, prompt or subagent on a lifecycle event | Must run on every matching event | ESLint after every edit |
| **Artifact** | Publishes output as a private interactive page | Output better seen than read in a terminal | Incident timeline that updates live |
| **Plugin** | Packaging: bundles skills, hooks, subagents, MCP | Reuse across repos, distribute via a marketplace | Namespaced skills like `/my-plugin:review` |

Skills are the most flexible: invoked as `/name` or loaded automatically when relevant, run inline or in a subagent (`context: fork`). Two kinds:

| Kind | Does | Example |
|---|---|---|
| Reference skill | Knowledge Claude uses throughout the session | API style guide |
| Action skill | Tells Claude to do something specific | `/deploy` runs the deployment workflow |

Extensions plug into different parts of the agentic loop: CLAUDE.md and output styles shape every turn, skills and MCP add knowledge and tools on demand, subagents and workflows run separate loops, hooks fire at lifecycle events, plugins package all of it.

## When to add each one

Start with CLAUDE.md; add the rest when its trigger appears. The same triggers say when to revise what exists.

| Trigger | Add |
|---|---|
| A convention or command is wrong twice | CLAUDE.md line |
| You keep asking for shorter, longer, or the same format | Output style |
| You keep typing the same prompt to start a task | User-invocable skill |
| You paste the same playbook a third time | Skill |
| You keep copying data from a tab Claude can't see | MCP server |
| Claude reads many files to locate a symbol | Code intelligence plugin |
| A side task floods the conversation | Subagent |
| Something must happen every time without asking | Hook |
| A second repo needs the same setup | Plugin |

A repeated mistake or recurring review comment → edit CLAUDE.md, not a one-off chat correction. A workflow you keep hand-tweaking → revise the skill.

## Comparing look-alikes

| Pair | Left | Right | Pick right when |
|---|---|---|---|
| Skill vs Subagent | Content loaded into *your* window; reference or action | Isolated worker, own window, only a summary returns | Many files read, parallel work, or your window is filling. Combine: subagent `skills:` preloads skills; skill `context: fork` runs isolated |
| CLAUDE.md vs Skill | Every session; `@path` imports; no `/name` | On demand; `@path` imports; `/name` workflows | Content needed only sometimes (API docs, deploy, release). Keep CLAUDE.md under 200 lines |
| CLAUDE.md vs Output style | Facts about the project, always loaded | How Claude responds; one active, switchable | It's about the response itself and you may want it off. Both are instructions, neither is enforced |
| CLAUDE.md vs Rules vs Skill | Every session, whole project | Every session, or when matching files are opened (`paths:`) | Skill: task-specific content on demand. Rules: language- or directory-specific guidance that keeps CLAUDE.md focused |
| Subagent vs Dynamic workflow | Claude decides turn by turn; quick focused worker | A script decides; many agents, one result | Codebase-wide audit, large migration, plan from several angles. Ask for a workflow in the prompt |
| MCP vs Skill | Tools and data access, connection and auth handled | Knowledge of how to use them, plus `/name` workflows | Use together: MCP to the DB, skill with schema and query patterns |
| Hook vs Skill | Runs on lifecycle events (`PostToolUse`, `SessionStart`); trigger guaranteed; zero cost unless it returns output | Claude reads and follows; outcome varies; description every request | Skill when reasoning is needed or the content is knowledge. Hook for format-on-save, rejecting `rm -rf /`, Slack on session end |

* **Subagents** suit tasks whose intermediate work you don't need to see. Custom subagents have their own instructions and can preload skills. Subagents Claude named when spawning them can message each other.
* **Several Claudes at once**: subagents, dynamic workflows, cross-session messaging (ask one session's Claude to send a finding to another), and hand-off sessions you check back on later (docs `agents` compares them).
* **Guardrails go in hooks.** "Never edit `.env`" in CLAUDE.md is a request; a `PreToolUse` hook that blocks the edit is enforcement.
* **Hook output lands in context.** A `PostToolUse` linter hook feeds results back as text; a `/fix-lint` skill says how to resolve them.

## Layering across levels

Levels: user, project, plugin, managed policy; CLAUDE.md can nest in subdirectories, skills can live in monorepo packages.

| Feature | Same name at several levels |
|---|---|
| CLAUDE.md | Additive: all levels load. Working dir and above at launch, subdirectories as Claude works in them. Conflicts resolved by Claude's judgment |
| Skills | One wins: managed > user > project. Plugin skills are namespaced |
| Subagents | managed > CLI flag > project > user > plugin |
| MCP servers | local > project > user |
| Hooks | Merge: every registered hook fires |

## Combining features

| Pattern | How | Example |
|---|---|---|
| Skill + MCP | MCP connects, skill teaches use | DB server + schema/query-pattern skill |
| Skill + Subagent | Skill spawns parallel subagents | `/audit` → security, performance, style subagents |
| CLAUDE.md + Skills | Always-on rule points to on-demand detail | "Follow our API conventions" + full style-guide skill |
| Hook + MCP | Hook triggers external action | Post-edit hook posts to Slack when critical files change |

## Context cost and load timing

Too much loaded context fills the window and adds noise: skills misfire, conventions get lost.

| Feature | Loads | What loads | Cost |
|---|---|---|---|
| CLAUDE.md | Session start | Full content, all levels (managed, user, project) | Every request |
| Output style | Start and on switch | Active style's full text; nothing for Default | Every request |
| Skills | Start + on use | Names + descriptions at start; full body on use | Low; zero with `disable-model-invocation: true` (or `skillOverrides` in settings for skills you didn't write) |
| MCP | Session start | Tool names + server instructions; schemas on demand (tool search) | Low until used. `/mcp` for status, `/context all` for per-tool tokens |
| Code intelligence | After edits, on lookup | Diagnostics; symbol locations | Low; often reduces file reads. Inactive until an LSP plugin is installed |
| Subagents | When spawned | Own system prompt, `skills:` preloaded in full, CLAUDE.md + git status (not Explore/Plan, not with `omitClaudeMd`), the lead's prompt. A fork gets the parent conversation instead | Isolated from main |
| Hooks | On trigger | Nothing by default | Zero unless it returns context |

* CLAUDE.md inheritance: read from the working directory up to the filesystem root at launch; nested ones in subdirectories are discovered as Claude accesses files there.
* MCP: `/mcp` shows connection status; remote servers reconnect automatically if they drop; disconnect servers you aren't using.
* Hook lifecycle events include tool execution, session boundaries, prompt submission, permission requests and compaction (full list: docs `hooks`). Ideal for side effects (linting, logging) that needn't touch context.
* `disable-model-invocation: true` belongs on skills with side effects: saves context and guarantees they run only when named.
* Claude picks skills by matching the task to descriptions; vague or overlapping descriptions → wrong skill or none. `/name` forces one.
* In subagents, listed `skills:` are preloaded, not on demand; unlisted skills stay invocable via the Skill tool.
* Bundled skills include `/code-review`, `/batch`, `/debug`.
* `/doctor` proposes trims for an oversized checked-in CLAUDE.md.
