---
name: write-tests
description: >-
  Writes fast, reliable, non-flaky unit tests for the .NET backend the FlexFunding
  way — AAA layout, collision-free production-like data (no hardcoded strings/dates
  that age out).
  Use when adding tests for a new feature, raising coverage on an existing feature,
  or updating tests after changing behavior, or when the user says "write tests",
  "add a test", "test this handler/service/command", "cover this with tests", or
  "the tests are flaky / failing".
---

# write-tests

Write backend tests in `FF.Tests` that match how this repo already tests, optimized for
**speed, reliability (no flake), and production-like data**. We are **not** chasing 100%
coverage — cover the main behaviors and the edges that would silently break a feature.

## Pick the test shape first
- **Pure unit (preferred — fastest, zero flake):** the SUT is a calculator/service/mapper with
  no DB. Construct it in the test constructor and pass it stubs/Moq mocks.
- **DB-touching (only when the behavior is the persistence):** handlers/commands that query or
  save. Use the shared SQLite in-memory fixture.

Default to pure unit. Reach for the DB only if mocking the persistence would test nothing real.

## Non-negotiables (these are what keep tests reliable)
- **AAA, one behavior per test.** Arrange / Act / Assert, blank-line separated. Name the test as
  a sentence describing the behavior (`Creates_a_new_opted_in_person_when_no_match_exists`),
  not the `Method_Case` form.
- **No hardcoded keys that collide or age out.** Every field that must be unique (email, reg
  number, code, partner code) gets a per-test value: a readable prefix plus `Guid.NewGuid():N`
  (32 hex chars, no dashes — safe inside emails and codes). Unique values mean tests can't
  collide whatever order they run in; the prefix keeps failures diagnosable. Non-key values
  (a display name, an amount) can stay literal.
- **No absolute "now"/year literals.** Express time relative to `DateTime.UtcNow` so the test
  means the same thing forever:

  | Intent | Write |
  | --- | --- |
  | In the past | `DateTime.UtcNow.AddDays(-25)` |
  | In the future | `DateTime.UtcNow + TimeSpan.FromHours(1)` |
  | Just expired | `DateTime.UtcNow - TimeSpan.FromMinutes(1)` |

  Exception: fixed absolute dates are fine when a stub owns the calendar or clock the SUT reads
  — the dates and what interprets them live together in the test, so nothing external can
  drift. If the SUT takes a clock, pass it a fixed one; if it reads `DateTime.UtcNow` itself,
  assert with a tolerance, not exact equality.
- **No real network or randomness in the SUT path.** Use the existing stubs and null loggers
  in `FF.Tests`; never mock a logger, and never call a real HTTP/Hub client.
- **Assert with FluentAssertions** and give a reason on the non-obvious ones.

## Real, Moq, or stub
- **Real** when the collaborator is cheap and deterministic (unit-of-work plumbing, pure
  calculators) — mocking it would test nothing.
- **Moq** for one-off behavior of an external collaborator.
- **A small hand-rolled `…Stub` class** implementing the interface when the fake is shared
  across tests or needs real logic (e.g. capturing published events). Reuse an existing one in
  `FF.Tests` before writing a new one.

## Process
1. **Locate the SUT and its real collaborators.** Read the class under test; list its ctor deps.
   Decide shape (above). Verify: you can name the one behavior each test will pin.
2. **Find the nearest existing test** to copy structure from (same folder/area first). Match its
   layout — don't invent a new harness. Don't mirror a test that reaches a live service; the
   no-network rule wins.
3. **Arrange production-like data** via small `Build…()` / `Seed…()` helpers with Guid-suffixed
   keys, so intent stays visible and a signature change touches one place. For DB tests, seed
   only the reference rows the SUT actually needs, idempotently: rows this test owns get
   Guid-suffixed keys and are added unconditionally; shared lookup rows (countries, currencies,
   product types) are added only when absent, so a sibling test that already seeded them can't
   cause a duplicate-key failure. Save once at the end of seeding.
4. **For DB tests, wire the unit of work correctly.** Handlers commit their own unit of work —
   give them a factory that returns a fresh context per `Create()`, and **assert through a
   separate fresh context** (or clear the change tracker first) so you read committed state,
   not tracked entities that give a false green. Clean up in `Dispose` — remove the rows you
   added (and dispose any contexts you created) — so nothing leaks into the next test.
5. **Cover main + edge, not everything.** Happy path, the one or two failure modes the feature
   guarantees (missing input, not-found, wrong partner), and any branch with money/eligibility
   logic. Skip trivial getters and impossible states. Fold variants of one behavior into a
   `[Theory]`, keeping the expected value in each data row. `[InlineData]` takes only
   compile-time constants — pass a `DateTime` as a string (xUnit converts it); use
   `[MemberData]` for anything else. If cases need different assertions, they're different tests.
6. **Verify green.** Run the new test class several times, then the full `FF.Tests` suite (the
   `test-runner` agent does this). A filtered run doesn't count as verified: tests that share a
   database can break each other. If a result changes between runs you have shared-state
   leakage (back to unique keys and `Dispose` cleanup). Finish with the flake checklist below.

## Updating tests when a feature changes
- Change the **test's expectation**, not the assertion's meaning, to match new intended behavior;
  if the old test encoded a now-wrong rule, rewrite it and say so.
- If a signature changed, update the `Build…()` helper in one place rather than every test.
- A test that now needs a new seeded dependency means the SUT took a new dependency — add it to
  the ctor wiring, not via reflection or `null!` shortcuts.

## When NOT to add a test
Source-generated CRUD, thin pass-through resolvers, and
framework glue rarely earn a test. Spend the budget on calculators, processors, eligibility/
money rules, and anything with branching the next change could silently break.

## Flake checklist (before declaring done)
- [ ] Every unique DB key is Guid-suffixed — no shared literal keys.
- [ ] No hardcoded "now"/year; time is relative to `DateTime.UtcNow` (or a stub owns the clock).
- [ ] DB tests assert through a fresh context and clean up in `Dispose`.
- [ ] No real HTTP/network/file call escapes a mock or stub.
- [ ] Tests don't depend on execution order — running the class repeatedly gives the same result.
- [ ] No `Thread.Sleep` / `Task.Delay` for timing — await the actual operation.
