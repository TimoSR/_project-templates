---
name: building-skills
description: Designs, writes, and tests Claude Code skills (SKILL.md plus supporting files) following Anthropic's skill-authoring best practices. Use when the user wants to create a new skill, turn a repeated workflow or a body of domain knowledge into a skill, improve or shrink an existing skill, fix a skill that triggers too often or never triggers, or asks how skills, SKILL.md frontmatter, or slash-command skills work. Not for rendering a skill as a page (generate-skill-artifact) or benchmarked evals (skill-creator).
argument-hint: "[what the skill should do]"
---

# Building Skills

A skill is instructions that load on demand. Its `description` sits in every session's context; the body loads only when the skill is invoked. Every line must earn its place. Fields, templates, patterns and the full checklist are in [reference.md](reference.md).

## 1. Decide that it should be a skill

| Need | Use |
|---|---|
| Rule for every session | `CLAUDE.md` line |
| Must happen every time, no exceptions | Hook in `.claude/settings.json` |
| Isolated task with its own tools or context | Subagent in `.claude/agents/` (or a skill with `context: fork`) |
| Knowledge or a workflow needed only sometimes | **Skill** |

If Claude already handles the task well without help, don't write a skill.

## 2. Find the gap before writing

1. Collect 2–3 real tasks the skill should handle (ask, or reconstruct them from the conversation). Note what Claude got wrong or what the user had to explain. That gap is the skill's content.
2. Write three test prompts now: two that should trigger the skill and one near-miss that shouldn't.

```
✓ trigger    "turn our release checklist into a skill"
✓ trigger    "my api-conventions skill never fires"
✗ near-miss  "add a hook that runs eslint after every edit"   (a hook, not a skill)
```

3. Scope unclear? Ask with `AskUserQuestion` about the hard parts: who invokes it, side effects, required inputs, what a correct output looks like.

## 3. Pick the shape

* **Location:** project `.claude/skills/<name>/` (shared via git) or personal `~/.claude/skills/<name>/`. The directory name is the command name.
* **Type:**

| Type | Example | Frontmatter |
|---|---|---|
| Knowledge: conventions or domain facts, applied automatically | API conventions | default |
| Workflow with side effects | deploy, commit, send | `disable-model-invocation: true`, so it only runs as `/name` |
| Background-only knowledge | notes on a legacy system | `user-invocable: false` |

* **Degree of freedom:** fragile or order-sensitive steps get exact commands or a script (low freedom). Judgment calls get heuristics (high freedom).

## 4. Write it

* **`name`:** lowercase letters, digits and hyphens; at most 64 characters; no `anthropic` or `claude` if it may be uploaded to claude.ai or the API (Claude Code loads such names). Prefer a gerund (`processing-pdfs`) or a noun phrase, matching sibling skills.
* **`description`:** triggering depends on it.
   * Third person. What it does, then "Use when …" with concrete triggers: user phrasings, file types, tool names, symptoms.
   * At most 1,024 characters. Slightly assertive triggers better than timid.

```yaml
# ✗ vague, no trigger
description: Helps with documents

# ✓ what it does + when + concrete triggers
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
```

* **Body:** write it per the `high-quality-tokens` skill (bullets, an example per rule, nothing Claude already knows). Specific to skills:
   * An orienting line first, then the workflow or rules.
   * One default with an escape hatch, not a menu of options.
   * One term per concept.
   * No dates or time-sensitive statements; forward-slash paths.
* **Size:** SKILL.md under ~500 lines, ideally far less. Move detail into supporting files linked directly from SKILL.md, one level deep. Files over 100 lines get a `## Contents` section.
* **Scripts:** for deterministic work such as validation and transformations.
   * Say whether to *run* or *read* each one.
   * Scripts handle their own errors and have no unexplained constants.
   * Reference them as `${CLAUDE_SKILL_DIR}/scripts/x.py`.
* **Workflows:** numbered steps. Long ones get a copyable checklist and a validate → fix → repeat loop before any irreversible step.
* **Standing instructions:** Claude doesn't re-read SKILL.md on later turns, so word guidance for the whole task ("Run the tests after every edit", not "Run the tests").
* **Rules that must hold all session go at the top:** after compaction only the first ~5,000 tokens of a skill are re-attached, from a 25,000-token budget shared by all skills (older ones can drop). Rules with no exceptions belong in a hook (the skill's `hooks` frontmatter keeps it with the skill).

## 5. Verify (required)

1. Lint and fix every `ERROR`:
   ```bash
   python "${CLAUDE_SKILL_DIR}/scripts/validate_skill.py" .claude/skills/<name>
   ```
   Also run `claude plugin validate .claude/skills` (YAML parse errors). No Python (on Windows, `python` may be only the Store stub)? That command alone still catches YAML errors, but not the size, link or description checks.
2. **Trigger test** in a fresh context: one subagent per test prompt, with no hint about the skill. Report which prompts loaded it. Adjust the `description` until both should-trigger prompts fire and the near-miss doesn't.
3. **Behavior test:** a fresh subagent runs one real task with the skill. Compare the result against the gap from step 2 and fix what it missed. Don't add rules for problems that never showed up.
4. **Show the evidence:** linter output, trigger results, behavior result. Never just "done".

For measured evals (with-skill vs baseline, trigger accuracy, benchmarks), hand off to the `anthropic-skills:skill-creator` skill.

## 6. Review before finishing

* For every line: *would removing this make Claude get the task wrong?* If not, cut it.
* Run the [checklist](reference.md#checklist).
