---
name: high-quality-tokens
description: Writes dense, high-signal text where every token carries information the reader or a future generation needs. Bullets and concrete, visual examples (trees, flows, tables, before/after, code, Mermaid diagrams) are the standard form, and preamble, repetition, filler, decoration and closing offers are cut. Use whenever writing or editing prose that people or later sessions will read - reports, docs, READMEs, CLAUDE.md, skills, memory files, design notes, plans, PR descriptions, commit messages, code comments, explanations and summaries. Also use when the user asks to shorten, condense, tighten, compress or de-noise text, or says output is too long, verbose, padded or repetitive.
---

# High-Quality Tokens / High-Quality Density

Every token costs the reader time and costs every later generation context. Persisted text compounds: `CLAUDE.md`, skills and memory are loaded again in every session. Humans learn that less is better. An LLM has no sense of effort, so it pads. A dense 5-page report beats the same content spread over 30 pages.

## The test

For every line, ask: *would the reader understand or act differently without it?* If not, cut it.

Then check scope: match the depth to what was asked. A true, useful fact the reader didn't ask for is still noise. Point to the deeper topic in one line instead of writing a section on it.

Dense does not mean cryptic. Finally ask: *could a reader new to the topic understand it from this text alone?* If not, it's over-compressed, and that fails just like padding. Never trade away clarity, the reason behind a decision, or the example that makes it click.

## Bullets and examples are standard

* Bullets are the default form. A parent line states the idea and children refine it. One idea per line; fragments are fine.
   * Use prose only for a chain of reasoning that bullets would break.
* Every concept gets a concrete example. A rule without one is half-explained.
   * A name in backticks is not an example. Show it: the code, tree or flow.
* Prefer visual examples: a tree, flow, table, before → after, input → output, or code snippet. Pick the form that matches the shape of the idea.
   * Put ✗ next to ✓. The contrast is what teaches the rule.
* Use a Mermaid diagram for a graph ASCII can't draw cleanly: loops, branches that merge, messages between participants, states, entity relations.
   * Only where it renders as a picture (README, docs, PR descriptions on GitHub or GitLab) or a model reads it (`CLAUDE.md`, skills, memory). A person reading a terminal, code comment or commit message sees raw source: use ASCII there.
   * Straight lines and trees stay ASCII: `request → validation → domain` beats a rendered chain of boxes.
   * Types, examples and syntax traps: [examples.md](examples.md#3-mermaid-diagrams).
* Use the smallest example that shows the point. One running example reused across concepts beats a new one per concept.
* Standard examples are in [examples.md](examples.md): a full SOLID rewrite, one instance of each visual form, Mermaid diagrams, and the house style for notes and rules.

## Cut

* Preamble: restating the question, "Here's…", announcing what comes next.
* Closers: recaps of what was just said, "Let me know…", "If you want, I can…".
* Repetition: the same idea as a list, then prose, then a summary, or an intro that previews the table below it. Say it once, in the best place.
* What the reader already knows: definitions of common terms, background they gave you.
* Decoration: mnemonics, analogies, emoji, motivational framing, unless asked for.
* Filler and hedges: "basically", "it's important to note that", "in order to", "various".
* Example boilerplate: constructors, logging, usage scaffolding. Keep the lines that show the point.
* Process narration: options not pursued, how you got there, unless the reader needs the path.

## Keep

* Decisions with their reason and the trade-off taken. The *why* is what a later reader can't re-derive.
* Concrete facts: names, numbers, paths, commands, `file:line`.
* Constraints, failure cases, non-obvious behavior.

## Form

* Lead with the conclusion (the answer, recommendation or result). Evidence follows.
* Use one term per concept throughout.
* Code comments say *why*, not *what*.

## Condensing existing text

1. Extract the ideas, one line each.
2. Drop what the reader knows and what repeats.
3. Order by dependency and nest refinements under their parent.
4. Write each idea once, as a bullet with its example.
5. Check against the original: every idea that changes understanding or action survived. Fix weak or wrong content you find on the way, since padding often hides it.

## Two failure modes

The same SOLID explainer, three ways:

| | Padded | Over-compressed | Target |
|---|---|---|---|
| Length | ~200 lines | ~12 lines | ~80 lines |
| Form | Each principle stated 3× (list, mnemonic, section) | One bullet each, type names in backticks | One bullet each + a ✗/✓ code example |
| Examples | Full classes, constructors, usage, `Console.WriteLine` | None shown, only named | Only the lines that show the violation and the fix |
| Teaches a newcomer? | Slowly. The LSP example shows no violation at all. | No: it's a cheat sheet for someone who already knows | Yes |

The target version is in [examples.md](examples.md#1-full-rewrite-solid). Aim for the 5-page report, not the 30-page one, and not a 1-page index either.
