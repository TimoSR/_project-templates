---
name: codemath
description: Translates compact math notation (Σ, ∏, ∫, ∀, ∃, P(A|B), matrix and vector notation) into readable, runnable code with full names, and backs every claim with an executable check - an exhaustive check, a property test with a stated failure margin, or a tolerance-bounded numeric comparison. Use when implementing a formula from a paper, spec or textbook (finance, statistics, probability, physics, AI, quantitative models), explaining what a formula means, checking that a formula or its implementation is correct, choosing between an exact and an approximate (good-enough) solution, or writing CodeMath book and teaching material.
---

# CodeMath

Math written as code a programmer can read, run and check. Notation compresses an idea; code unfolds it into steps with names.

Running example used below: the loan annuity payment.

```
M = P · r(1+r)ⁿ / ((1+r)ⁿ − 1)
```

## 1. Translate: unfold the notation

* Every symbol gets a full name and a unit.
   * `P` → `principal` (currency), `r` → `monthlyRate` (fraction per month), `n` → `paymentCount` (months).
* Prefer the explicit loop over the operator when the loop is clearer. A one-line `reduce` is notation again.
* Name intermediate values. They are the steps the formula hid.
* Write the domain as guard clauses. Notation leaves it implicit; code must not.
   * `r = 0` divides by zero in the formula above. The guard is the math's missing case.

```ts
// ✗ notation in code syntax: one-letter names, hidden domain, crashes at r = 0
const m = (p: number, r: number, n: number) => p * r * (1 + r) ** n / ((1 + r) ** n - 1)

// ✓ CodeMath
const calculateMonthlyPayment = (
  principal: number,    // currency
  monthlyRate: number,  // fraction per month, 0.005 = 0.5 %
  paymentCount: number, // months
): number => {
  if (paymentCount <= 0) return Number.NaN
  if (monthlyRate === 0) return principal / paymentCount

  const growthFactor = (1 + monthlyRate) ** paymentCount
  return principal * monthlyRate * growthFactor / (growthFactor - 1)
}
```

Notation → code:

| Notation | Read as | Code |
|---|---|---|
| `Σᵢ₌₁ⁿ f(i)` | add f(i) for i from 1 to n | `let total = 0; for (let i = 1; i <= n; i += 1) { total += f(i) }` |
| `Πᵢ₌₁ⁿ f(i)` | multiply f(i) for i from 1 to n | same loop, `product *= f(i)`, start at 1 |
| `∫ₐᵇ f(x) dx` | area under f from a to b | sum `f(x) · width` over small slices (see §3) |
| `∀x ∈ S: P(x)` | P holds for every x in S | `for (const x of set) { if (!holds(x)) return false } return true` |
| `∃x ∈ S: P(x)` | P holds for at least one x | `for (const x of set) { if (holds(x)) return true } return false` |
| `⟨u, v⟩` | dot product | `for (let i = 0; i < u.length; i += 1) { total += u[i] * v[i] }` |
| `P(A ∩ B) = P(A∣B)·P(B)` | chance of both | `probabilityBoth = probabilityAGivenB * probabilityB` |
| `x ∈ ℝ, x > 0` | positive real | guard clause: `if (!(x > 0)) return Number.NaN` |

## 2. Prove: make the claim executable

A formula is a claim. Code turns it into a check that fails loudly. Pick the strongest check the domain allows.

| Proof type | What it shows | Code form |
|---|---|---|
| Exhaustion | Holds for **every** case of a finite domain: a real proof | Loop over all cases, assert each |
| Counterexample | Claim is **false**: one case suffices | A single failing test |
| Induction | Holds for n = 1 and for n + 1 given n | Loop invariant: assert it before and after each step |
| Construction | Something exists | Return the object and check it |
| Sampling | Evidence, **not** proof, with a stated failure margin (see §3) | Property test over random inputs |
| Machine-checked | Proof over an infinite domain | Proof assistant (Lean); tests cannot reach this |

Running example: amortizing the loan with the computed payment must leave a zero balance. The loop is the invariant; the end state is the claim.

```ts
const checkPaymentRepaysLoan = (principal: number, monthlyRate: number, paymentCount: number): boolean => {
  const toleranceCurrency = 0.01 // one cent
  const payment = calculateMonthlyPayment(principal, monthlyRate, paymentCount)

  let balance = principal
  for (let month = 1; month <= paymentCount; month += 1) {
    const interest = balance * monthlyRate
    balance = balance + interest - payment
    if (balance > principal) return false // invariant: balance never grows
  }
  return Math.abs(balance) <= toleranceCurrency
}

checkPaymentRepaysLoan(100_000, 0.005, 360) // payment ≈ 599.55, balance ends ≈ 0 → true
```

## 3. A 90 % solution is still a solution, if the margin is stated

* An approximation is valid when its error bound is known and smaller than what matters.
   * ✗ "it's approximately right"
   * ✓ "midpoint rule, 1 000 slices, error < 1e-6; we need cents"
* Zero failures in `n` random trials → the true failure rate is below `3 / n` with 95 % confidence (rule of three).
   * 10 000 passing samples → failure rate < 0.03 %. Say that, not "it works".
* Numeric code compares with a tolerance, never `===`.

```ts
const integrateMidpoint = (
  integrand: (x: number) => number,
  lowerBound: number,
  upperBound: number,
  sliceCount: number,
): number => {
  const sliceWidth = (upperBound - lowerBound) / sliceCount
  let area = 0
  for (let slice = 0; slice < sliceCount; slice += 1) {
    area += integrand(lowerBound + (slice + 0.5) * sliceWidth) * sliceWidth
  }
  return area
}

// Fundamental theorem of calculus, checked: ∫₀² f = F(2) − F(0)
const integrand = (x: number) => x ** 2 + 3 * x + 2
const antiderivative = (x: number) => x ** 3 / 3 + 1.5 * x ** 2 + 2 * x
const difference = integrateMidpoint(integrand, 0, 2, 1_000) - (antiderivative(2) - antiderivative(0))
Math.abs(difference) < 1e-6 // true: midpoint error here ≈ 6.7e-7
```

## 4. A model is not reality

* A passing check proves the code matches the formula, not that the formula matches the world.
   * The annuity check passes; it says nothing about borrowers who pay late.
* Put every model assumption in a named config object so it is visible and testable.
* Validate against observed data separately from the internal-consistency checks.

## 5. Show change as a graph

* When a value evolves (balance over months, error over slice count, loss over epochs), plot it. A curve shows convergence, divergence or a kink that a final number hides.
* Plot error on a log axis: the slope shows the convergence order (midpoint rule: error falls 100× per 10× slices).

## Rules for this repo

* Follow the house style from `.claude/CLAUDE.md`: full names, units in names or comments, guard clauses, config objects, no magic numbers.
* Money in production code is `decimal` (C#), not `number`/`double`. Examples above use `number` only for readability.
* A money or eligibility formula gets a test (`tests-as-documentation` skill): the check from §2 is the test body.
