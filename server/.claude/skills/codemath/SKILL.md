---
name: codemath
description: Translates compact math notation (Σ, ∏, ∫, ∀, ∃, P(A|B), matrix and vector notation) into readable, runnable code with full names, gives every quantity a unit type so the compiler rejects dimensionally wrong formulas, and backs every claim with an executable check - an exhaustive check, a property test with a stated failure margin, or a tolerance-bounded numeric comparison. Use when implementing a formula from a paper, spec or textbook (finance, statistics, probability, physics, AI, quantitative models), modelling quantities with units (length, time, mass, money, interest rates, durations) or mixing units such as annual and monthly rates or percent and fraction, explaining what a formula means, checking that a formula or its implementation is correct, writing formula tests test-first and trying to break them with edge inputs, choosing between an exact and an approximate (good-enough) solution, or writing CodeMath book and teaching material. Not for performance tuning (low-level-optimizations).
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
): number | null => {
  if (paymentCount <= 0) return null
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
| `∫ₐᵇ f(x) dx` | area under f from a to b | sum `f(x) · width` over small slices (see §4) |
| `∀x ∈ S: P(x)` | P holds for every x in S | `for (const x of set) { if (!holds(x)) return false } return true` |
| `∃x ∈ S: P(x)` | P holds for at least one x | `for (const x of set) { if (holds(x)) return true } return false` |
| `⟨u, v⟩` | dot product | `for (let i = 0; i < u.length; i += 1) { total += u[i] * v[i] }` |
| `P(A ∩ B) = P(A∣B)·P(B)` | chance of both | `probabilityBoth = probabilityAGivenB * probabilityB` |
| `x ∈ ℝ, x > 0` | positive real | guard clause: `if (!(x > 0)) return null` |

## 2. Type the units: the compiler checks the dimensions

Source: the `physics` Rust crate in [TimoSR/2026 › Defining/Physics](https://github.com/TimoSR/2026/tree/main/Best_Research/%23Done/Rust/%23Defining/Physics).

* A unit is a type, not a comment. `// meters` can lie; a `Length` cannot be passed where a `Time` is expected.
* One base unit inside, every other unit at the edges.
   * `Length(f64)` holds meters (SI). Constructors convert in (`kilometers(5.0)`), readers convert out (`to_kilometers()`). Each conversion factor is written once.
* Operators are the laws: one operator per formula, plus its inverses. Anything without a law does not compile.

| Formula | Law | Inverses |
|---|---|---|
| v = d / t | `Length / Time → Velocity` | `Velocity × Time → Length`, `Length / Velocity → Time` |
| a = v / t | `Velocity / Time → Acceleration` | `Acceleration × Time → Velocity`, `Velocity / Acceleration → Time` |
| F = m · a | `Mass × Acceleration → Force` | `Force / Mass → Acceleration`, `Force / Acceleration → Mass` |
| same unit | `Length ± Length → Length`, `Length × f64 → Length` | `Length / Length → f64` (dimensionless ratio) |
| no law | `Length + Time` | compile error |

* Generate the same-unit arithmetic once (macro, generic base); write each cross-unit law by hand, so every law is one visible, tested line.
* Name each formula as a function that reads like the notation: `velocity(distance, time)` is `v = d / t`.
* Partial operations get two entry points (speed vs safety):
   * `calculate(distance, time)`: unchecked and `const`; the caller guarantees `t ≠ 0`.
   * `checked_calculate(distance, time)` → `Err(DivisionByZero { operation: "velocity::calculate" })`. The error names the operation.
   * `try_meters(value)` rejects NaN and ∞ at the boundary, so the domain only ever holds finite values.
* Full precision in storage, rounding only in display (lossless store, lossy view). `display_kilometers_per_hour_precision(2)` formats; the stored value never changes.
* Constants carry their unit: `STANDARD_GRAVITY_METERS_PER_SECOND_SQUARED = 9.80665`.
* Equality is tolerance-based on the type: `approximately_equals(other, epsilon)`.
* One test per law, named as the sentence it proves: `length_divided_by_time_returns_velocity`, `checked_div_time_rejects_zero_time`.

```rust
// ✗ every value is f64: swapping the arguments compiles and returns nonsense
fn velocity(distance: f64, time: f64) -> f64 {
    return distance / time;
}

// ✓ unit types: the derivation reads like the physics
impl Div<Time> for Length {
    type Output = Velocity;
    fn div(self, time: Time) -> Velocity {
        return Velocity::meters_per_second(self.to_meters() / time.to_seconds());
    }
}

let distance = length::kilometers(5.0);
let time = time::milliseconds(9_580.0);
let mass = mass::grams(80_000.0);

let velocity = velocity(distance, time);         // Length / Time → Velocity
let acceleration = acceleration(velocity, time); // Velocity / Time → Acceleration
let force = force(mass, acceleration);           // Mass × Acceleration → Force
// let wrong = distance + time;                  // compile error: no Add<Time> for Length

println!("{}", velocity.display_kilometers_per_hour_precision(2)); // 1878.91 km/h
```

Applied to money in this repo:

* Same pattern: `Money × MonthlyRate → Money` is one month's interest. With no `Money × AnnualRate`, using an annual rate as a monthly one does not compile. Converting between them is a named function that states its convention (`ToMonthlyNominal`: ÷ 12, not the effective `(1+r)^(1/12) − 1`), which is a §5 model assumption.
* TypeScript has no operator overloading. Branded parameter types (`number & { readonly unit: 'months' }`) stop swapped arguments, but arithmetic drops the brand, so money formulas belong in C#.
* Full C# version (types, annuity, compile errors, xUnit test, all verified): [units-as-types.md](units-as-types.md).

## 3. Prove: make the claim executable

A formula is a claim. Code turns it into a check that fails loudly. Pick the strongest check the domain allows.

| Proof type | What it shows | Code form |
|---|---|---|
| Exhaustion | Holds for **every** case of a finite domain: a real proof | Loop over all cases, assert each |
| Counterexample | Claim is **false**: one case suffices | A single failing test |
| Induction | Holds for n = 1 and for n + 1 given n | Loop invariant: assert it before and after each step |
| Construction | Something exists | Return the object and check it |
| Type check | Units are consistent in **every** formula, for all inputs. It proves units, not values: `distance / time` with the wrong distance still compiles | Unit types with one operator per law (§2) |
| Sampling | Evidence, **not** proof, with a stated failure margin (see §4) | Property test over random inputs |
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

## 4. A 90 % solution is still a solution, if the margin is stated

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

## 5. A model is not reality

* A passing check proves the code matches the formula, not that the formula matches the world.
   * The annuity check passes; it says nothing about borrowers who pay late.
* Put every model assumption in a named config object so it is visible and testable.
* Validate against observed data separately from the internal-consistency checks.

## 6. Show change as a graph

* When a value evolves (balance over months, error over slice count, loss over epochs), plot it. A curve shows convergence, divergence or a kink that a final number hides.
* Plot error on a log axis: the slope shows the convergence order (midpoint rule: error falls 100× per 10× slices).

## 7. Test first, then try to break it

A formula works on the textbook example and fails at the edges the notation never mentions. Write the tests before the code, then attack the code.

* Order: claim → failing test → code → green → break attempts → green again.
* Tests follow the `tests-as-documentation` skill: names are sentences, expected values are stated literals or hand-derived (never the formula re-run), variants in one `[Theory]` with named states, out-of-domain returns `null`/`false`, not an exception.

**Break it with 0, 1, ∞ and their neighbours.** Each row is a test. Found on the C# `Annuity.CalculateMonthlyPayment` ([units-as-types.md](units-as-types.md)) and the TS version (§1):

| Attack | Input | Expected (hand-derived) | Found |
|---|---|---|---|
| Zero | `paymentCount = 0` | `null` | ✓ guarded |
| Zero | `monthlyRate = 0` | `P / n` = 277.78 for 100 000 / 360 | ✓ guarded |
| One | `paymentCount = 1` | `P(1 + r)` = 100 500 at 0.5 % | ✓ |
| Near zero | `monthlyRate = 1e-12` (TS `number`) | ≈ `P / n` = 277.78 | ✗ 277.75: `(1+r)ⁿ − 1` cancels, 2.5 cents off |
| Infinity / huge | `paymentCount = 20 000` at 0.5 % (C# `decimal`) | a payment ≈ `P · r` = 500 | ✗ `OverflowException` from month 13 342 (`decimal` max ≈ 7.9e28) |
| Negative | `monthlyRate = −1` | `null` (rate ≤ −100 % is outside the domain) | ✗ returns 0, silently |
| Not a number | `NaN`, `±∞` (TS) | `NaN` / rejected at the boundary | depends on the guard |
| Boundary ± 1 | last month, first month, month 13 342 vs 13 343 | off-by-one shows here | |
| Empty | empty list into a Σ | 0 (Π: 1) | |

**Checks that need no second formula:**

| Check | Annuity example |
|---|---|
| Known answer | 100 000 at 0.5 % for 360 months → 599.55 (published table) |
| Limit / reduction | r → 0 tends to `P / n`; n = 1 gives `P(1 + r)` |
| Round trip | `kilometers(5).to_kilometers() == 5`; amortize with the payment → balance 0 (§3) |
| Scaling (metamorphic) | 2 × principal → 2 × payment |
| Monotonic | more months → lower payment; higher rate → higher payment |
| Invariant | balance never grows during amortization (§3 loop) |

**Then break the code, not only the input.** Flip `+` to `−`, drop a guard, change `<=` to `<`: at least one test must go red. A mutation every test survives is an untested line.

```csharp
public static TheoryData<int, decimal> EdgePaymentCounts
{
    get
    {
        return new TheoryData<int, decimal>
        {
            { OneMonth(), 100_500m },       // P(1 + r)
            { ThirtyYears(), 599.55m },     // published table
            { BeyondDecimalRange(), 500m }, // ≈ P · r, interest-only limit
        };
    }
}

[Xunit.Theory]
[Xunit.MemberData(nameof(EdgePaymentCounts))]
public void Monthly_payment_holds_from_one_month_to_beyond_decimal_range(int paymentCount, decimal expectedPayment) { ... }
```

* A failing edge test is a finding: report it, don't loosen the assert (`tests-as-documentation` › When a test exposes a bug). The fix (a domain guard, `r ≤ −1 → null`, an overflow-safe `(1+r)ⁿ`) is a separate change.

## Rules for this repo

* Follow the house style from `.claude/CLAUDE.md`: full names, units in names or comments, guard clauses, config objects, no magic numbers.
* Money in production code is `decimal` (C#), not `number`/`double`. Examples above use `number` only for readability.
* A money or eligibility formula gets a test (`tests-as-documentation` skill), written before the code: the check from §3 is the test body, the §7 edge rows are the `[Theory]`.
* New C# formula code that mixes units (money × rate, annual vs monthly, percent vs fraction) gets unit types (§2), not bare `decimal`s with unit comments.
