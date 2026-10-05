# CodeMath: Background

Load for CodeMath book, teaching or positioning work. Not needed to translate a formula.

## Thesis

* Most frustration with math comes from notation, not from the ideas.
   * `Σᵢ₌₁ⁿ i²` and a 3-line loop hold the same idea; only one is readable without training.
* Code is unambiguous, runnable and checkable. If you can't run it, it's suspect.
* Code shows the steps (intuition) and is precise (rigor) at once.
* Readable beats compact. Abstract only when the name reads better than the expansion: `dotProduct(u, v)` over `⟨u, v⟩`.

## Two positionings

| | Teaching framework | Formal alternative to notation |
|---|---|---|
| Goal | Math easier for coders and students | Code is the canonical form of definitions, theorems, proofs |
| Artifact | Book, courses, example library | Language spec + standard library + proof checker |
| Bar | Readable, runnable | Machine-verified: "if it doesn't run, it's not proven" |
| Effort | Small: start now | Large: competes with Lean |

* Teaching is the realistic entry point; formal is the long-term direction.

## Audience

* Programmers: already think in loops, not Σ and ∫.
* Engineers / applied scientists: want clarity and reproducibility.
* Educators and students: lower barrier; students learn Python faster than algebraic notation.
* Industry (finance, AI, physics, quant): reproducible results, no misread formulas.
* Resistance: mathematicians (invested in notation, see code as "dumbing down") and publishers (LaTeX infrastructure).

## Predecessors and the gap

| Tool | Does | Why it didn't replace notation |
|---|---|---|
| Lean (mathlib), Coq, Agda, Isabelle | Machine-checked proofs | Hard to learn, alien to most coders |
| Mathematica, Maple, SymPy | Symbolic calculation | Still notation in code syntax (`Sum[x^2, {x, 1, n}]`); calculates, doesn't explain |
| LaTeX | Typesets symbols | No execution, no verification |
| Jupyter, Wolfram Alpha | Interactive teaching aid | Helps read notation, doesn't replace it |
| Univalent foundations (HoTT) | Code-like foundations of math | Too abstract outside academia |

* Gap: a readable, coder-first form positioned as a replacement, not an assistant, with a manifesto and community.

## Adoption path

```
education (book, videos, MOOCs) → tools (library replacing textbook exercises)
  → research supplements (papers with runnable CodeMath appendices) → accepted medium
```

## Book plan

* Short, to the point, one subject per part: math foundations, statistics, physics, AI, quantitative finance.
* Every chapter: notation → CodeMath → runnable check → graph of the behavior.
* Must cover: types of proof, automating proofs, graphs to show change, approximation with failure margins, model vs reality.

## Sources to follow

* Lean community (leanprover-community.github.io)
* Computerphile: "Programming with Proofs"
* "When Computers Write Proofs, What's the Point of Mathematicians?"
* "Why Einstein Couldn't Get a Job for 9 Years"
