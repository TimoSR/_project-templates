---
name: generate-skill-artifact
description: Converts a Claude Code skill (SKILL.md plus its supporting files) into a published HTML Artifact page in one fixed visual standard, written to the high-quality-tokens rules - purpose and triggers first, a load profile of what sits in context and when, every rule with its ✗/✓ example, workflows as numbered steps. Use when the user asks to turn, convert, render, publish, share or present a skill as an artifact, page or HTML doc, wants a readable or shareable version of a skill for teammates, or wants skill pages to look consistent. Not for writing, fixing or testing a skill (building-skills), or for artifacts about anything other than a skill.
argument-hint: "[skill name or path]"
---

# Skill Artifact

One skill in, one Artifact page out, every page in the same standard, modelled on rustdoc and the Rust book: a sidebar of sections and rules beside one reading column, every rule collapsible, a Summary button that collapses them all. [template.html](template.html) is the standard: its `<style>`, font `<link>`s and `<script>`s are fixed; only the content changes. The content follows `high-quality-tokens`: each idea once, as a bullet or component with its example, no preamble, recap or decoration.

## Rules for every page

* **The skill is the source of truth.** The page says nothing the skill doesn't.
   * Lossless on ideas, lossy on wording: every idea that changes understanding or action appears once, in tighter words.
   * A rule with no example in the skill or its files keeps none and goes in the gap report. Never invent one.
   * Fixes go into the skill, then the page is regenerated. Never hand-edit a published page.
* **The frame is fixed.** Copy the template; replace only `<title>` and what's inside `<div class="page">`. Only the template's classes; no inline style except `--fill` on a load bar. The check script enforces both.
* **The idea's shape picks the component, not its markdown syntax.**

```
✗ markdown table | Rule | ✗ | ✓ |   → copied as a plain table
✓                                  → one .rule per row, its ✗/✓ cells as a .compare
                                     (or a table with .bad / .good columns when rows are one-liners)
```

* **Sections follow the skill's order.** One `section.block` per skill section. Merge sections that hold one line; drop sections that only point to files, since the sidebar lists files.
   * Text before the first `##` becomes the first block, a `.thesis`. Its `h2` is the skill's own label for it ("The one idea", "The test"), else "Core idea". Drop what the masthead or load profile already says.
* **A rule is a directive:** a line telling the reader what to do or not do ("Fail early"). It gets a `details.rule`. Facts, definitions and options stay `.points` bullets, and only rules count toward the gap report.
   * Keep a heading's number ("1. Decide …") only when the sections are a real sequence.
* Changing the standard means editing template.html's `<style>`, then regenerating every page: the check compares it byte for byte.

## Source → component

| Idea in the skill | Component | Classes |
|---|---|---|
| H1, `name`, `argument-hint`, invocation | page name after the word Skill; `/command` and invocation pill top of the sidebar | `.skill-name` › `.skill-kind`, `.command` `.argument-hint` `.pill` |
| description: what it does | lede, one sentence | `.lede` |
| "Source:" line (book, course, docs), in any file of the skill | source line | `.source` |
| description: "Use when …" | chips; phrases the user types go in `<mark>` on a `.chip-said` | `.trigger-row` › `.chips` › `.chip` |
| description: "Not for …" | second trigger row | `.trigger-row.not` |
| sizes and files from `stats` | load profile; a `/command only` skill's first stage reads "Not in context", no bar | `.load-profile` |
| orienting line, "the one idea", "the test" | thesis, key phrase in `<mark>` | `.thesis` |
| rule + why + example | collapsible rule, open; listed in the sidebar's Rules by a 2–5 word name | `details.rule[id][open]` › `summary.rule-statement`, `.rule-body` › `.rule-why` + example |
| what an example shows, when the skill says it | caption under the example | `.caption` |
| constraint, caveat, side note | gray aside | `.note` |
| ✗/✓ pair, before → after | diff block, ✗ row above ✓ row | `.compare` › `.compare-row.bad` `.compare-row.good` |
| items on shared attributes, decision table | table; ✗/✓ columns take `.bad` / `.good` | `.table-wrap` › `table` |
| tree, straight flow | ASCII diagram | `pre.diagram` |
| loops, participants, states | Mermaid, rendered by the Artifact viewer | `pre.mermaid` |
| code | code with a language label | `pre.code[data-language]` › `code.language-…` |
| numbered workflow | steps; numbers only for a real order | `ol.steps` › `li.step` |
| copyable checklist | checklist | `ul.checklist` |
| bullets, notes | bullet list | `ul.points` |
| supporting files | sidebar file list: name, lines and when it loads ("runs, never loaded" for a script), what it holds; the on-demand stage uses stats' total, which leaves scripts out | `.file-list` |

template.html renders `high-quality-tokens` with one of each component. Components it doesn't use (checklist, "Not for" row, source line, argument hint, standalone code block) sit in HTML comments where they go.

```
div.page
├── aside.sidebar           /command + pill · Sections · Rules · Files   (phones: command + sections only)
└── main.main
    ├── header.masthead     breadcrumb (path) + Summary button · Skill name · lede · source · triggers
    ├── section.load-profile  always in context → on invoke → on demand
    └── div.content         section.block per skill section: thesis, rules, tables, steps
```

## Cut from the page

* Raw frontmatter, and the description restated as prose: the masthead already says it.
* `See [file](…)` links inside rules: the sidebar names each file once.
* Reference material from supporting files: one line in the file list. Pull a piece in only as a rule's missing example, or as a checklist SKILL.md tells Claude to run.
* Intros ("This skill helps…"), closing summaries, related-skill lists that repeat the contents.
* Emoji and icons: ✗ ✓ → are the only symbols.

## Workflow

1. **Read** SKILL.md and every file in the skill folder, fully.
2. **Numbers:** run `node ${CLAUDE_SKILL_DIR}/scripts/skill_page.mjs stats <skill-dir>`. Use its title, command, invocation, sizes and `--fill` values as printed; don't count by hand.
3. **Extract** the ideas, one line each, in the skill's order (`high-quality-tokens`, "Condensing existing text", steps 1–3). Tag each with its component from the table.
4. **Quickstart:** `Artifact` with `action: "quickstart"`, `intent: "other"`, `design_systems: false`. The tool requires one per new artifact; template.html replaces the design pass. Skip it on an update.
5. **Write:** copy template.html to `<scratchpad>/<skill-name>.html` and replace the content.
   * Escape `<` `>` `&` in code, diagrams and Mermaid as `&lt;` `&gt;` `&amp;`.
   * Code inside a `.compare` is a plain `<pre><code class="language-csharp">`; elsewhere it is `<pre class="code" data-language="csharp">`.
   * Every `section.block` and `details.rule` gets an `id` (on the element, not its heading: the scroll offset is there). The sidebar's Sections and Rules link to each; the check fails a link without a target.
6. **Check:** run `node ${CLAUDE_SKILL_DIR}/scripts/skill_page.mjs check <page.html>`. Fix every ERROR and rerun until none is left. A `rule without example` WARN goes in the gap report.
7. **Look once** if the session offers a preview (`ArtifactCheck`, or a screenshot); fix what it shows, no second look. Mermaid renders only once published.
8. **Publish:** `Artifact` with `file_path`, `icon: "book"` and `description` set to the lede.
   * The skill already has a page: `action: "list"`, match the title, `read` it, then publish to its `url` without `icon`, so the link stays the same.
9. **Report:** the link, then the gap report: rules without examples, contradictions, stale facts. Each gap names the `file:line` to fix.
