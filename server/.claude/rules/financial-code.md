---
paths:
  - "src/features/**/domain/**/*.cs"
  - "src/features/**/application/**/*.cs"
---

# Financial formulas

Applies when implementing money, rates, quantities, or eligibility formulas in a module's `domain/` or `application/`.

- Production money uses decimal, not double/float; keep currency, rate period, percent/fraction, and duration explicit.
- New C# formulas mixing units use unit types to reject dimensional mistakes; do not retrofit unrelated existing APIs.
- Write the money/eligibility test in the module's `test/` before implementation. Include relevant boundary inputs and independently derived expected values.
- State numeric tolerance and model assumptions for approximations; evidence about a mathematical model does not prove the model matches reality.

Example: convert an annual rate to a monthly rate explicitly before combining it with a monthly payment count.
Use `codemath` for translating, typing, and verifying the formula.
