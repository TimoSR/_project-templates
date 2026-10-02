# Building Skills — Reference

Sources: https://code.claude.com/docs/en/skills and https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
Companion to [SKILL.md](SKILL.md).

## Contents
1. Frontmatter fields
2. Substitutions and dynamic context
3. Invocation control
4. Locations and precedence
5. Directory layout and progressive disclosure
6. Description examples
7. Body patterns (template, examples, conditional, checklist, feedback loop)
8. Templates for new skills
9. Troubleshooting
10. Checklist

---

## 1. Frontmatter fields

The opening `---` must be the first line of the file. With malformed YAML the skill loads with empty metadata, so Claude can't match it. Unknown fields are ignored without any warning.

| Field | Purpose |
|---|---|
| `name` | The `/` command name. Defaults to the directory name. Lowercase letters, digits and hyphens, max 64 characters. Must not contain `anthropic` or `claude`. |
| `description` | What the skill does and when to use it. This is the main trigger signal. Max 1,024 characters (API spec). In Claude Code, it is capped at 1,536 characters together with `when_to_use`. |
| `when_to_use` | Extra trigger context, appended to `description`. |
| `argument-hint` | Autocomplete hint, e.g. `[issue-number]`. |
| `arguments` | Named positional args, e.g. `[issue, branch]`, used as `$issue` and `$branch`. |
| `disable-model-invocation` | `true` means only the user can run it via `/name`. The description is removed from Claude's context. |
| `user-invocable` | `false` hides it from the `/` menu. Claude can still use it. |
| `allowed-tools` | Pre-approves tools for the invoking turn, e.g. `Bash(gh *) Read`. It does not restrict other tools. |
| `disallowed-tools` | Removes tools while the skill is active. |
| `model` / `effort` | Overrides the model or effort level for the skill's turn. |
| `context: fork` + `agent` | Runs the skill as an isolated subagent (`Explore`, `Plan`, `general-purpose`, or a custom agent). The skill body becomes the subagent's whole prompt, and it sees no conversation history. Set `background: false` to wait for the result. |
| `paths` | Globs that limit when the skill auto-activates. |
| `hooks` | Hooks registered when the skill is invoked. |
| `shell` | `bash` (default) or `powershell` for `` !`cmd` `` blocks. |

## 2. Substitutions and dynamic context

| Placeholder | Expands to |
|---|---|
| `$ARGUMENTS` | The full argument string. If the body never uses it, `ARGUMENTS: <value>` is appended to the skill instead. |
| `$0`, `$1`, `$ARGUMENTS[N]` | One argument by 0-based index, with shell-style quoting. |
| `$name` | A named argument from `arguments`. |
| `${CLAUDE_SKILL_DIR}` | The directory that contains SKILL.md. Use it for script paths. |
| `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_SESSION_ID}`, `${CLAUDE_EFFORT}` | The project root, the session id, and the current effort level. |

To get a literal `$` before a digit or an argument name, write `\$`.

**Dynamic context** runs before Claude sees the skill, and the command's output replaces the placeholder:

```markdown
Current diff: !`git diff HEAD`
```

Rules for dynamic context:
- The `!` must start the line or follow whitespace.
- Each command has a 2-minute timeout.
- A non-zero exit aborts the skill. Exit 1 from `grep`, `diff`, `find` or `git diff` is allowed. Add `|| true` to anything else that may fail.
- The command is checked against the user's permission rules.

## 3. Invocation control

| Frontmatter | User `/name` | Claude auto-invokes | Description in context |
|---|---|---|---|
| (default) | yes | yes | yes |
| `disable-model-invocation: true` | yes | no | no |
| `user-invocable: false` | no | yes | yes |

Use `disable-model-invocation` for anything with side effects: deploy, commit, push, sending messages. Use `user-invocable: false` for background knowledge that would only clutter the `/` menu.

## 4. Locations and precedence

| Location | Path | Scope |
|---|---|---|
| Enterprise | managed settings dir `.claude/skills/<name>/` | Organization. Wins name clashes. |
| Personal | `~/.claude/skills/<name>/` | All projects on this machine. |
| Project | `.claude/skills/<name>/` (also loaded from parent dirs up to the repo root) | This repo, shared via git. |
| Nested | `<subdir>/.claude/skills/<name>/` | Loads when Claude works in `<subdir>`. |
| Plugin | `<plugin>/skills/<name>/` | Invoked as `/plugin:name`. |

Clash order is Enterprise > Personal > Project. Any local skill replaces a bundled skill of the same name. The names `synced` and `anthropic-skills` are reserved.

## 5. Directory layout and progressive disclosure

```
my-skill/
├── SKILL.md          # overview + workflow; loaded when invoked
├── reference.md      # loaded only when SKILL.md sends Claude there
├── examples.md
└── scripts/
    └── validate.py   # executed; only its output costs tokens
```

- Every supporting file is linked **directly from SKILL.md**. When a reference file links to another file, Claude may read the second one only partially (e.g. with `head`).
- Organize by domain (`reference/finance.md`, `reference/sales.md`) so Claude reads only what the task needs.
- Use descriptive filenames: `form_validation_rules.md`, not `doc2.md`.
- State the intent for each script: "Run `scripts/x.py` to …" (execute) vs. "See `scripts/x.py` for the algorithm" (read).
- Context lifecycle: once invoked, a skill's content stays in context for the rest of the session. After compaction, only the first ~5,000 tokens of each recent skill are re-attached.

## 6. Description examples

Good. These are third person, say what the skill does and when, and name concrete triggers:

```yaml
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
description: Generate descriptive commit messages by analyzing git diffs. Use when the user asks for help writing commit messages or reviewing staged changes.
```

Bad:

```yaml
description: Helps with documents            # vague, no trigger
description: I can help you process Excel     # first person
description: You can use this for reports     # second person
```

Trigger tuning:
- **Never triggers:** add the words users actually type, plus file extensions, tool names and symptoms. Say "even if they don't mention X" when the topic is implicit.
- **Triggers too often:** narrow the "Use when" clause, add a "Not for …" clause, or switch to `disable-model-invocation: true`.

## 7. Body patterns

**Template (strict).** Use for output formats that must not vary:

````markdown
ALWAYS use this structure:
```markdown
# [Title]
## Summary
## Findings
## Recommendations
```
````

**Examples.** Input/output pairs teach style better than prose does:

````markdown
Input: Fixed bug where dates displayed incorrectly in reports
Output:
```
fix(reports): correct date formatting in timezone conversion
```
````

**Conditional workflow:**

```markdown
1. Determine the task:
   **Creating new?** → follow "Create" below
   **Editing existing?** → follow "Edit" below
```

**Copyable checklist.** Use for long workflows so steps don't get skipped:

````markdown
Copy this checklist and tick items off as you go:
```
- [ ] 1. Analyze input (run scripts/analyze.py)
- [ ] 2. Write plan to plan.json
- [ ] 3. Validate plan (run scripts/validate.py plan.json)
- [ ] 4. Apply
- [ ] 5. Verify output
```
````

**Feedback loop.** Validate, fix, and repeat, and only move on once the check passes. For batch or destructive operations, use plan → validate plan → execute → verify. Make validator errors specific, e.g. "Field 'x' not found. Available: a, b, c".

**Old patterns.** Instead of date-based instructions, keep deprecated material in a collapsed `<details>` "Old patterns" section.

**MCP tools.** Always use fully qualified names (`ServerName:tool_name`).

**Dependencies.** State the install command. Never assume a package is present.

## 8. Templates for new skills

Knowledge skill:

```markdown
---
name: api-conventions
description: REST API design conventions for this service. Use when adding or reviewing HTTP endpoints, routes, request/response DTOs, or pagination.
---
# API Conventions
- kebab-case URL paths; camelCase JSON properties
- Every list endpoint is paginated (`?cursor=&limit=`)
- Version in the path: /v1/, /v2/
```

Workflow skill with side effects:

```markdown
---
name: fix-issue
description: Fix a GitHub issue end to end and open a PR.
argument-hint: "[issue-number]"
arguments: [issue]
disable-model-invocation: true
allowed-tools: Bash(gh *)
---
Fix GitHub issue #$issue.

Issue: !`gh issue view $issue`

1. Reproduce with a failing test.
2. Fix the root cause.
3. Run the test suite and linter; iterate until green.
4. Commit, push, open a PR that references #$issue.
```

Forked research skill:

```markdown
---
name: deep-research
description: Researches a codebase question in an isolated context and returns a summary. Use for broad "how does X work across the repo" questions.
context: fork
agent: Explore
---
Research: $ARGUMENTS
Return a summary of at most 30 lines with file:line references.
```

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| Claude never uses the skill | Check `/skills`. Reword `description` with concrete triggers. Test with `/name`. |
| Triggers too often | Make `description` more specific, or add `disable-model-invocation: true`. |
| Stops following a rule mid-session | Move the rule to the top of SKILL.md, or turn it into a hook. |
| Description truncated in listing | Too many skills are competing for the listing budget. Run `/skill-doctor` and disable unused skills. |
| YAML errors | `claude --debug`, or `claude plugin validate .claude/skills` (v2.1.233+). |
| `` !`cmd` `` aborts the skill | The command exited non-zero. Add `|| true` or fix the command. |

## Checklist

**Core**
- [ ] A real gap was observed, and there are 3 test prompts (2 trigger, 1 near-miss)
- [ ] `name` is valid and consistent with sibling skills
- [ ] `description` is third person, says what + "Use when …" with concrete triggers, and is ≤1,024 chars
- [ ] Side-effecting workflow → `disable-model-invocation: true`
- [ ] SKILL.md < 500 lines, and nothing in it Claude already knows
- [ ] Supporting files are linked directly from SKILL.md, and files over 100 lines have a contents list
- [ ] One default per decision, one term per concept, concrete examples
- [ ] No time-sensitive statements; forward-slash paths only

**Scripts** (if any)
- [ ] Each script is marked as run vs. read, and paths use `${CLAUDE_SKILL_DIR}`
- [ ] Errors are handled in the script; no unexplained constants
- [ ] Dependencies are stated with install commands
- [ ] Validation loop before any irreversible step

**Verified**
- [ ] `validate_skill.py` passes with no errors
- [ ] Trigger test in a fresh context: both should-trigger prompts fire, the near-miss does not
- [ ] One real task run with the skill in a fresh context; the result was checked against the gap
