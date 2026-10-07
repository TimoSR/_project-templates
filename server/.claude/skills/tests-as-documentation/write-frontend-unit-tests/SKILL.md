---
name: write-frontend-unit-tests
description: >-
  Writes Vitest unit tests for the Web/ frontend the FlexFunding way — plain-node
  only (no DOM, no Nuxt runtime, no mocks), real objects constructed inline, dates
  relative to now. Use when adding tests for frontend logic, raising coverage on a
  Web/ module, or updating tests after changing frontend behavior, or when the user
  says "write frontend tests", "test this util/composable/store", "add a unit test
  for <Web file>", or "cover this with tests" in Web/.
---

# write-frontend-unit-tests

Unit suite only. The backend equivalent is `tests-as-documentation`; this skill is its
frontend sibling and shares the same philosophy: tests are documentation, real
objects over fakes, pragmatic coverage over percentages.

Conventions live in `Web/test/README.md` — read it before writing; its "Unit
scope" section is this suite's boundary. This skill is the process; that file is
the style. On top of it: **don't refactor production code to make it testable.**
The team's source guidelines (the intent behind both) are in
`references/testing-guidelines.md`.

## Phase 1 — Classify the target

Answer: is the logic pure (deps arrive as arguments, no browser/Nuxt globals)?
Vue's `ref`/`reactive`/`computed` don't count against it — they run in plain
node.
- **Pure** → Phase 2.
- **Entangled** (needs a component instance — inside a component `setup()`,
  lifecycle hooks, `inject` — or touches browser globals, Nuxt auto-imports or
  `#app`) → wrong suite: runtime-entangled code is
  `write-frontend-integration-tests`, a `.vue` component is
  `testing-vue-components`. Don't restructure the production code to pull it
  into this suite. Say so and stop.
  The trap: a module that looks pure is entangled too if anything in its
  import chain loads a `.vue` file at top level (often via an extensionless
  import) — it then fails to import in plain node. Follow the chain before
  writing, not after the failure.
- **No real logic** (constants, GraphQL documents, declarative field metadata,
  thin wrappers, generated CRUD glue) → don't test it. Say so and stop.

New code the user asks to have tested should be written in the testable shape
from the start — deps as arguments (model: `useOnboardingMutations` in
`Web/state/useOnboardingMutations.js`, and its unit test).

## Phase 2 — Place and name the file

Place and name it the way `Web/test/README.md` and the existing unit tests do
(the path mirrors the source). Only the aliases the unit project declares in
`Web/vitest.config.mjs` resolve.

## Phase 3 — Write the tests

**Test the intended behavior, not the implementation.** Before writing asserts,
state what the function is *for*; the expected value must be stated
independently (a literal, or a hand-derived value), never computed by re-running
the production algorithm — that's a tautology that passes no matter what the
code does. Don't assert incidental implementation details (key order, internal
shapes, formatting accidents) unless that detail *is* the contract (e.g. the
exact GraphQL clause a server consumes). If the current behavior contradicts the
evident intent, that's a bug finding — surface it (Phase 4), don't enshrine it
as the expectation.

Follow `Web/test/README.md` for layout, naming, real-object construction and
test matrices. On top of it:
- **No dates or amounts that age out** — build times relative to `Date.now()`
  (model: `nowInSeconds` in `Web/test/unit/packages/ftb/util/jwt.test.js`).
- Cover what the README lists plus orchestrating functions (the ones
  coordinating other functions). Private helpers are covered through the public
  export that calls them; if logic is unreachable that way, it is out of
  scope — note it, don't restructure.
- **Never test framework or language features** (Vue reactivity working,
  JS number limits, lodash behaving) — only this module's own contract. The
  flip side: **do test the design's boundaries** — the magnitudes and sizes the
  feature was planned for (a loan amount in the millions, a hundred rows, a
  0–100 percentage) — not the language's limits (`Number.MAX_SAFE_INTEGER` is
  not a test case; "the largest loan we sell" is).
- Module-level singleton state: whatever a test mutates, it puts back.

## Phase 4 — Run and verify

Run the unit project on its own, as the README's "Running" section shows.

Green is not done: re-read each test and check the assert would actually fail if
the behavior regressed (no tautologies, no asserting the arrange). A test that
cannot fail when it should is worth nothing.

**If a test exposes a live bug:** the test asserts the INTENDED behavior and
therefore fails — that failing test IS the finding. Report the bug (file, line,
what the test expects vs what happens); never rewrite the test to match the
broken behavior, and never silently fix production code — the fix is a
separate, user-approved change that turns the test green. Do NOT mark such tests
as expected-to-fail (`it.fails`/`it.skip`/`it.todo`) as a first step — an early
marker can hide unintended failures; the failing test is the basis for a
discussion with the user, and any expected-failure marking is that discussion's
outcome, not its start.
