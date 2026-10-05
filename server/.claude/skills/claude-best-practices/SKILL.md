---
name: claude-best-practices
description: Applies Claude Code working practices - verification, planning, context management, review, and configuring CLAUDE.md and .claude/. Use when starting a multi-file or non-trivial change, when setting up or auditing CLAUDE.md or .claude/ (skills, agents, hooks, settings), when planning headless, parallel or unattended Claude Code runs, or when the user asks how to use Claude Code effectively. Not for writing or fixing one skill (building-skills).
---

# Claude Code Best Practices

Context is the scarcest resource: the window holds every message, file read and command output, and performance degrades as it fills. Most rules below follow from that. Commands, prompts and config recipes are in [reference.md](reference.md).

## Verify

* Before finishing, run a check that returns pass/fail: tests, build, linter, a fixture diff, or a screenshot compared against a design.

```
✗ "implement a function that validates email addresses"
✓ "write validateEmail. test cases: user@example.com → true, invalid → false, user@.com → false.
   run the tests after implementing"
```

* UI changes: screenshot the result, compare it to the target, list the differences, fix them.
* Fix the root cause; don't suppress the error.
* Show evidence (the command and its output, or the screenshot), never just an assertion.
* Unattended work needs a stronger gate: a `/goal` condition, a Stop hook or a verification subagent ([reference §1](reference.md#1-verification)).

## Plan

```
uncertain approach, multi-file change, or unfamiliar code?
  yes → explore (read only) → plan → implement against the plan → commit
  no  → the diff fits in one sentence: do it
```

* Large features: interview the user with `AskUserQuestion` about the hard parts, edge cases and trade-offs. Then write a self-contained `SPEC.md` that names files and interfaces, states what's out of scope, and ends with an end-to-end verification step.

## Context

* Scope investigations narrowly. Send broad research to a subagent and keep only its summary.
* Reach external services through CLI tools (`gh`, `aws`, `gcloud`). Learn unknown ones with `--help`.
* Bugs: reproduce the symptom with a failing test, then fix it.
* After two failed corrections on the same issue, suggest `/clear` and a sharper prompt that includes what was learned.
* Checkpoints track only Claude's file-tool edits, not Bash or external changes. Git is the safety net.

## Review

* Non-trivial or unattended work: review the diff in a fresh subagent (or `/code-review`) against the plan. Every requirement implemented, edge cases tested, nothing out of scope changed.
* Reviewers usually report gaps even when the work is sound. Act only on findings that affect correctness or the stated requirements.

## Configuring `.claude/`

* Choose the mechanism first ([reference §4](reference.md#4-configuring-the-environment)): `CLAUDE.md` for every-session rules, skills for on-demand knowledge, hooks for must-happen actions, subagents for isolated tasks.
* For every `CLAUDE.md` line: *does it carry value Claude needs and can't derive itself (prevents a mistake, shapes a decision, gives a fact or example)?* If yes, keep it, whatever its length. If not, cut it. Value decides, never token count.
* Write all of it per [high-quality-tokens](../high-quality-tokens/SKILL.md) (bullets, a concrete example per concept, no filler). Every line is reloaded in every session.
