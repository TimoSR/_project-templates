---
name: building-skills
description: Designs, writes, and tests Claude Code skills (SKILL.md plus supporting files) following Anthropic's skill-authoring best practices. Use when the user wants to create a new skill, turn a repeated workflow or a body of domain knowledge into a skill, improve or shrink an existing skill, fix a skill that triggers too often or never triggers, or asks how skills, SKILL.md frontmatter, or slash-command skills work.
argument-hint: "[what the skill should do]"
---

# Building Skills

A skill is a set of instructions that loads on demand. Its `description` sits in every session's context, and the body loads only when the skill is invoked. Every line has to earn its place. Field tables, templates, patterns and the full checklist are in [reference.md](reference.md).

## 1. Decide that it should be a skill

| Need | Use instead |
|---|---|
| Rule that applies to every session | `CLAUDE.md` line |
| Must happen every time, no exceptions | Hook in `.claude/settings.json` |
| Isolated task with its own tools or context | Subagent in `.claude/agents/` (or a skill with `context: fork`) |
| Knowledge or a workflow needed only sometimes | **Skill** |

If Claude already handles the task well without help, don't write a skill.

## 2. Find the gap before writing

1. Ask for, or reconstruct from the conversation, 2–3 real tasks the skill should handle. Note what Claude got wrong or what the user had to explain without the skill. That gap is the skill's content.
2. Write down three concrete test prompts now: two that should trigger the skill and one near-miss that should not.
3. If the scope is unclear, use `AskUserQuestion` to ask about the hard parts: who invokes it, any side effects, required inputs, and what a correct output looks like.

## 3. Pick the shape

- **Location:** project `.claude/skills/<name>/` (shared via git) or personal `~/.claude/skills/<name>/`. The directory name is the command name.
- **Type:**
  - *Knowledge skill:* conventions or domain facts. Claude applies it automatically.
  - *Workflow skill:* steps with side effects (deploy, commit, send). Add `disable-model-invocation: true` so it only runs as `/name`.
  - *Background-only knowledge:* add `user-invocable: false`.
- **Degree of freedom:** fragile or order-sensitive steps get exact commands or a script (low freedom). Judgment calls get heuristics (high freedom).

## 4. Write it

- **`name`:** lowercase letters, digits and hyphens, at most 64 characters, and no `anthropic` or `claude`. Prefer a gerund (`processing-pdfs`) or a noun phrase, and match the naming of sibling skills.
- **`description`:** this is what triggering depends on. Write it in the third person. Say *what it does* and then *"Use when …"* with the concrete triggers: user phrasings, file types, tool names, symptoms. Keep it under 1,024 characters. A slightly assertive description triggers better than a timid one.
- **Body:**
  - Assume Claude is already smart. Cut explanations of things it knows.
  - Put a short orienting line first, then the workflow or rules.
  - Give one default with an escape hatch, not a menu of options.
  - Use one term per concept throughout.
  - Prefer concrete examples (input → output) over abstract description.
  - Avoid dates and anything time-sensitive. Use forward-slash paths.
- **Size:** keep SKILL.md under ~500 lines (ideally far less). Move detail into supporting files that SKILL.md links to directly, one level deep. Give any file over 100 lines a contents list at the top.
- **Scripts:** use them for deterministic work such as validation and transformations. Say whether to *run* the script or *read* it. Scripts should handle their own errors and avoid unexplained constants. Reference them as `${CLAUDE_SKILL_DIR}/scripts/x.py`.
- **Workflows:** use numbered steps. For long ones, add a copyable checklist and a validate → fix → repeat loop before any irreversible step.
- **Rules that must hold for a whole session** go at the top, because after compaction only the first ~5,000 tokens of a skill are re-attached. Consider making them a hook instead.

## 5. Verify (required)

1. Run the linter and fix every `ERROR`:
   ```bash
   python "${CLAUDE_SKILL_DIR}/scripts/validate_skill.py" .claude/skills/<name>
   ```
   If the CLI supports it (v2.1.233+), also run `claude plugin validate .claude/skills`.
2. Test triggering in a **fresh context** by spawning a subagent with each of the three test prompts and no hint about the skill. Report which prompts loaded it. Adjust the `description` until the two should-trigger prompts fire and the near-miss does not.
3. Test behavior by having a fresh subagent run one real task with the skill. Compare the result against the gap from step 2. Fix what it missed. Don't add rules for problems that never showed up.
4. Show the evidence: the linter output and the trigger and behavior results. Don't just say "done".

For measured evals (with-skill vs. baseline, trigger accuracy, benchmarks), hand off to the `skill-creator` plugin.

## 6. Review before finishing

Ask the same question about every line: *"Would removing this make Claude get the task wrong?"* If not, cut it. Then run the checklist in [reference.md](reference.md#checklist).
