---
name: best-practices
description: Use when starting a multi-file or non-trivial change, when setting up or auditing CLAUDE.md or .claude/ (skills, agents, hooks, settings), when planning headless, parallel or unattended Claude Code runs, or when the user asks how to use Claude Code effectively.
---

# Claude Code Best Practices

Context is the scarcest resource; performance degrades as it fills. For commands, shortcuts, example prompts and config recipes, read [reference.md](reference.md).

## Verify
- Before finishing, run a check that returns pass/fail: tests, build, linter, a fixture diff, or a screenshot compared against a design.
- For UI changes, screenshot the result, compare it to the target, list the differences and fix them.
- Address the root cause. Don't suppress the error.
- Show evidence: the command you ran and its output, or the screenshot. Don't just assert success.
- For unattended work, suggest a stronger gate: a `/goal` condition, a Stop hook, or a verification subagent.

## Plan
- Uncertain approach, multi-file change, or unfamiliar code: explore (read only), then plan, then implement against the plan, then commit.
- If the diff fits in one sentence, skip the plan and do it.
- For large features, interview the user with `AskUserQuestion` about the hard parts, edge cases and tradeoffs. Then write a self-contained `SPEC.md` that names files and interfaces, states what is out of scope, and ends with an end-to-end verification step.

## Context
- Scope investigations narrowly. Send broad research to a subagent and keep only its summary.
- Prefer CLI tools (`gh`, `aws`, `gcloud`) for external services. Learn unknown ones with `--help`.
- For bugs, reproduce the symptom with a failing test, then fix it.
- After two failed corrections on the same issue, suggest `/clear` and a sharper prompt that includes what was learned.
- Checkpoints track only Claude's file-tool edits, not Bash or external changes. Git is the safety net.

## Review
- For non-trivial or unattended work, review the diff in a fresh subagent (or `/code-review`) against the plan: every requirement implemented, edge cases tested, nothing out of scope changed.
- Reviewers usually report gaps even when the work is sound. Act only on findings that affect correctness or the stated requirements.

## Configuring `.claude/`
Read the "Choosing a mechanism" and "CLAUDE.md" sections of [reference.md](reference.md) first. The core test for every `CLAUDE.md` line: *"Would removing this cause Claude to make mistakes?"* If not, cut it.
