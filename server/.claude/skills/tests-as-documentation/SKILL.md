---
name: tests-as-documentation
description: >-
  Writes FlexFunding tests of every type (unit, integration, infrastructure, API,
  E2E) as the documentation of our in-house APIs, plus standards tests for
  architecture rules (interfaces, base classes, generic constraints), and sets up
  the test database (SQL Server via Testcontainers). Use when adding tests for a
  new feature, raising coverage, updating tests after a behavior change, choosing
  a test type, or when the user says "write tests", "add a test", "integration
  test", "API test", "e2e test", "architecture test", "check it implements the
  interface", "test this handler/service/command/endpoint", "cover this with
  tests", or "the tests are flaky / failing". Covers a module's test/ folder.
  Not for tracing a production
  exception to its source (debug-exception).
---

# tests-as-documentation

One strategy for all five test types. Load on demand: [standards-tests.md](standards-tests.md)
(architecture rules as tests), [test-matrices.md](test-matrices.md) (`[Theory]` rows),
[api-and-e2e-tests.md](api-and-e2e-tests.md) (GraphQL contract and browser journey tests),
[dates-and-time.md](dates-and-time.md) (controlling the clock, calendar edges).

## The first principle: tests are the documentation

We keep no external docs for our in-house APIs: code is the source of truth, and the tests are the
part of the code that shows **what each feature does and how it is meant to be used**. A new
developer opens `AutoInvestCalculatorTests.cs`, not a wiki page. Every other rule in this skill
serves this one; speed, no flake and production-like data come after.

Write each test as the example a newcomer would copy:

* **The test list is the feature list.** Names are sentences stating behavior in domain language,
  so the test explorer reads as a spec:

  ```
  AutoInvestCalculatorTests
  ├── Invests_the_low_risk_amount_when_the_loan_is_low_risk
  ├── Never_invests_more_than_the_loan_has_left_to_fill
  └── Monthly_strategy_invests_less_as_the_month_runs_out
  ```

  ✗ `Calculate_OneAccount`, `Test1`, `Calculate_Works` (the `Method_Case` form)
* **Arrange + Act show real usage.** Go through the entry point a real caller uses (the public
  method, the command, the GraphQL mutation) with the setup a real caller needs. The arrange
  section *is* the answer to "what do I need before I can call this?"
* **No usage a caller can't do.** Reflection, poking private fields, `null!` for a required
  dependency: each documents a call that's impossible in production. If the test needs one, the
  API is the problem: report it.
* **Helpers hide noise, never the point.** A `Build…()` helper fills fields the behavior doesn't
  care about; every input the behavior depends on is a named argument, visible at the call site.

  ```csharp
  // ✗ which rating? the reader has to open the helper to learn the rule
  var loan = BuildLoan();

  // ✓ the input that drives the result is on the page
  var loan = BuildLoan(rating: LoanRatingEnum.LowRisk, amount: 300000);
  ```

* **Realistic values.** Amounts, dates and names a real caller would send (a loan of 300000, not
  `1`; a reg number in the real format), so the test also documents the expected data.
* **Assert shows the contract.** What the caller gets back and which state changed: the result a
  newcomer can rely on, not implementation details.
* **Comments say why, as business rules.** `// Loans under 6 months can't be auto-invested
  (risk policy)`. Never restate what the code does.
* **Coverage goal: every in-house API has at least one happy-path test that shows how to use it.**
  An API with no test is an undocumented API. Not a percentage, not 100%: cover the main behaviors
  and the edges that would silently break a feature.

## Two parts of the suite

| Part | Answers | Example |
| --- | --- | --- |
| **Documentation of the implementation** | What does this feature do, how do I call it? | `Invests_the_low_risk_amount_when_the_loan_is_low_risk` |
| **Validation of set standards** | Does the code follow the rules we set for it? | `Every_alarm_policy_implements_IAlarmPolicy` |

Both are documentation: the first documents behavior, the second documents our architecture rules
as executable checks. A rule with no test is a rule the next class can silently break. How to write
standards tests: [standards-tests.md](standards-tests.md).

## The five types

Pick the **cheapest type that can prove the behavior**. Each step up buys confidence and pays in
speed and flake risk.

| Type | Proves | Documents | Real | Faked | Speed | In the repo |
| --- | --- | --- | --- | --- | --- | --- |
| **Unit** | One function / class does the right thing | How to call a class and what each input does | Everything (plain objects) | Nothing | ms | Backend `FF.Tests`; Web `test/unit/` |
| **Integration** | Our components work together | How a flow is composed: which components cooperate, which side effects happen | All our code, wired as in production | Only third parties, with hand-rolled stubs | ms–s | Backend `FF.Tests` (e.g. `AutoInvestProcessorTests` + `MediatorStub`); Web `test/integration/`, `test/component/` |
| **Infrastructure** | Our code works against real infrastructure | What the database / cache guarantees (constraints, concurrency) | SQL Server, Redis, … in Docker via Testcontainers | Third parties | s | `MsSqlContainerFixture` |
| **API** | The GraphQL contract a client sees | How a client calls the endpoint: the query or mutation text itself is the example | HTTP pipeline, auth, resolvers, DB | Third parties | s | No harness: [api-and-e2e-tests.md](api-and-e2e-tests.md) |
| **E2E** | A user journey works through the real UI | How a user moves through a feature | Browser → Web → API → DB | Third parties (sandbox / test mode) | s–min | No harness: [api-and-e2e-tests.md](api-and-e2e-tests.md) |

```
            E2E          few: critical journeys only (sign up, invest, repay)
           API           one per endpoint contract
      Infrastructure     persistence, raw SQL, concurrency, caching
       Integration       handlers, processors, orchestration
          Unit           most tests: calculators, rules, mappers
```

Trade-off: **speed and simplicity at the bottom, confidence in the wiring at the top.** A rule that
a unit test can prove never gets an E2E test.

## Shared rules (every type)

* **Real objects, not fake data.** When the SUT takes a `Loan`, construct a `Loan`.
   * ✗ a mocked `Loan`, an anonymous object, a half-filled DTO the SUT never sees in production
   * ✓ `new Loan { Amount = 300000, LoanRating = LoanRatingEnum.LowRisk }`
* **Fake only what we don't own.** Our code, our database and our cache run for real (in a
  container if needed). Third parties (HubSpot, AIIA, Criipto, Firebase, Intercom) get a hand-rolled
  `…Stub` implementing the interface. Reuse an existing one in `FF.Tests` first:
  `FF.Tests/Util/MediatorStub.cs` records `EventsPublished`; the `EmailSenderStub` in
  `FF.Tests/Commands/SendUserMigrationLinkCommandTests.cs` records `SentEmails`.
* **Expected values are stated, not computed.** Write the literal or a hand-derived value; never
  re-run the production formula in the assert. That's a tautology that passes whatever the code does.

  ```csharp
  // ✗ the same formula on both sides: passes even when the formula is wrong
  Xunit.Assert.Equal(calculator.Calculate(loan, accounts), result);

  // ✓ the number a reader can check by hand
  Xunit.Assert.Equal(10000, result);
  ```

* **Assert what stays stable, not what changes often.** A test pinned to volatile output breaks on
  every cosmetic edit, so people learn to "fix" tests by copying the new output, and the test stops
  guarding anything. String formatting is the common case: error message wording, `ToString()`,
  log text, formatted amounts (`"300.000,00 kr."`), date display. Assert the value, code or state
  underneath instead.

  ```csharp
  // ✗ breaks when someone rewords the message; the rule didn't change
  Xunit.Assert.Equal("The amount must be greater than 0.", result.Errors[0].Message);

  // ✓ the contract a caller branches on
  Xunit.Assert.Equal(ValidationErrorCode.AmountNotPositive, result.Errors[0].Code);
  ```

  Exception: when the format *is* the contract (a bank file export, a CSV a partner parses, a
  formatter class), the exact text is the behavior: test it.

* **AAA, one behavior per test.** Mark the sections:

  ```csharp
  // Arrange
  var loan = BuildLoan(amount: 300000);

  // Act
  var result = calculator.Calculate(loan, accounts);

  // Assert
  Xunit.Assert.Equal(10000, result);
  ```

* **No hardcoded keys that collide.** Every field that must be unique (email, reg number, code,
  partner code) gets a readable prefix plus `Guid.NewGuid():N` (32 hex chars, no dashes, safe in
  emails and codes). The prefix keeps failures diagnosable. Non-key values (a display name, an
  amount) stay literal.
   * ✗ `Email = "investor@test.dk"`: the second run, or a parallel test, hits the unique index
   * ✓ `Email = $"investor-{System.Guid.NewGuid():N}@test.dk"`
* **The test owns "now".** Date-dependent code gets its time from outside: a `now` / `today`
  parameter, `System.TimeProvider`, or `IDateAndTimeProvider`. Never from `DateTime.UtcNow`. The
  test sets a fixed instant, writes the expected dates as literals, and moves the clock forward
  instead of sleeping. Cover the calendar edges the rule depends on: month end, leap day, year
  change, the exact boundary, DST. Full rules: [dates-and-time.md](dates-and-time.md).
* **No real third-party network call, ever.** No `Thread.Sleep` / `Task.Delay` for timing: await the
  actual operation, or poll for the condition with a timeout.

## What to cover

* **Happy path:** intended usage, the call a real caller makes.
* **Unhappy path:** misuse the feature guarantees to handle (missing input, wrong partner,
  amount ≤ 0). It documents the API's limits: what it refuses and how it says no. Assert the
  returned `false` / validation result / GraphQL error code, not an exception: the domain doesn't
  throw.
* **State:** the object's fields before → after the call (`FilledAmount` 10000 → 20000), not only
  the return value.
* **Variants of one behavior:** one `[Theory]`, an expected value per row, each input state named
  by a function: [test-matrices.md](test-matrices.md).
* **Orchestrating functions:** the method that coordinates other methods (a processor calling
  calculator → repository → event publisher). Pin the combined result.
* **Internal helpers:** test the helper directly when its logic is hard to reach through the public
  method. Make it `internal` and expose internals to the test project once per assembly:

  ```csharp
  // FF.App/Properties/AssemblyInfo.cs
  [assembly: System.Runtime.CompilerServices.InternalsVisibleTo("FF.Tests")]
  ```

  If the assembly has no `InternalsVisibleTo` yet, adding it is a production change: say so in the
  summary. A truly `private` method stays covered through its public caller.
* **Skip:** source-generated CRUD, thin pass-through resolvers, framework glue, trivial getters,
  impossible states. Spend the budget on calculators, processors, eligibility and money rules.

## Per type

### Unit

* Target: calculator, service, mapper, domain rule whose collaborators can be built for real.
* No stubs, no database, no file system. If the test needs any of them, it's an integration or
  infrastructure test.
* Web: `write-frontend-unit-tests` skill.

### Integration

* Target: a handler or processor and the real components it coordinates.
* Wire our classes for real. A stub that captures what it received (published events, sent emails)
  lets you assert the side effect.
* Needs persistence → use the real database (infrastructure setup below), never SQLite or the EF
  in-memory provider: they skip SQL Server's constraints, collation and concurrency, so a test can
  pass there and fail in production.
* Legacy: most database tests still use SQLite through `InMemDbFixture` /
  `[Collection(nameof(DatabaseCollection))]`. Don't copy that harness, even when the test next to
  yours uses it; new database tests join `MsSqlCollection`.
* Web: `write-frontend-integration-tests` (runtime-entangled code) and `testing-vue-components`
  (`.vue` contracts).

### Infrastructure

* Target: behavior that only exists in the real engine: migrations, raw SQL, concurrency tokens,
  constraints, transactions, Redis caching.
* Join the shared container: `[Collection(nameof(MsSqlCollection))]` and take the
  `MsSqlContainerFixture` (`FF.Tests/Util/MsSqlContainerFixture.cs`) in the ctor. Copy the setup
  from `FF.Tests/AutoInvest/AutoInvestProcessorTests.cs`: `UseSqlServer(fixture.ConnectionString)`
  and real migrations (`MigrateAsync`), so the schema is production's.
* Other infrastructure (Redis, …): the matching Testcontainers module, same fixture pattern.
  `FF.Tests` references only `Testcontainers.MsSql`; add the module's package
  (`dotnet add FF.Tests/FF.Tests.csproj package Testcontainers.Redis`).
* The container is built `WithReuse(true)`: it survives across tests **and across runs**. Rows
  persist, so every key a test owns is Guid-suffixed, and shared lookup rows (countries,
  currencies, product types) are added only when absent.
* Handlers commit their own unit of work. **Assert through a separate fresh context** (or clear the
  change tracker) so you read committed state, not tracked entities that give a false green.
* Requires Docker running locally.

## Organization

The file path names the component under test: `FF.Tests/<Area>/<Sut>Tests.cs`, area matching the
source.

```
FF.Tests/
├── AutoInvest/AutoInvestCalculatorTests.cs     unit
├── AutoInvest/AutoInvestProcessorTests.cs      integration + infrastructure
├── HubSpot/HubSpotMapperRegistrationTests.cs   standards: lives with the area whose rules it guards
├── LoanRepayment/LoanRepaymentCalculatorTests.cs
└── Features/FactoringFeature/FactoringServiceTests.cs
```

One test class per SUT and type. A class that grows too large splits by behavior
(`PlaceOrderCommandValidationTests`, `PlaceOrderCommandCurrencyExchangeTests`). Web paths follow
`Web/test/README.md`.

## Process

1. **Locate the SUT and its collaborators.** Read the class; list its ctor deps. State what the
   code is *for* before writing asserts. Pick the cheapest type that proves it. Verify: you can
   name the one behavior each test pins.
2. **Find the nearest existing test of that type** (same folder first) and match its layout; don't
   invent a harness. Exception: a SQLite `InMemDbFixture` test is legacy; use `MsSqlCollection`
   instead. API or E2E with no harness: stop and propose the setup
   ([api-and-e2e-tests.md](api-and-e2e-tests.md)).
3. **Arrange production-like data** via small `Build…()` / `Seed…()` helpers with Guid-suffixed
   keys, so intent stays visible and a signature change touches one place.
4. **Cover** per [What to cover](#what-to-cover), matrices per [test-matrices.md](test-matrices.md).
5. **Verify green, then verify it can go red.** Run the class several times, then the full suite
   (the `test-runner` agent does this for `FF.Tests`). A filtered run isn't verification: tests
   sharing a database can break each other; a result that changes between runs is shared state
   leaking. Re-read each assert: would it fail if the behavior regressed? Finish with the
   checklist.

## When a test exposes a bug

The test asserts the *intended* behavior and fails: that failing test is the finding.
* Report it: file, line, expected vs actual.
* Never rewrite the test to match the broken behavior, and never silently fix production code; the
  fix is a separate, user-approved change that turns the test green.
* Don't pre-emptively `Skip` it; that's the outcome of the discussion with the user, not its start.
* Exception: characterization tests (`soft-extract-feature`) pin *current* behavior, known-wrong
  parts included.

## Updating tests when a feature changes

* **A behavior change updates the test in the same change.** The test is the doc; a stale test is
  a lie the next developer will copy.
* Change the **test's expectation**, not the assertion's meaning; if the old test encoded a now-wrong
  rule, rewrite it and say so.
* A signature change updates the `Build…()` helper in one place.
* A test that now needs a new dependency means the SUT took a new dependency: add it to the ctor
  wiring, not via reflection or `null!`.

## Checklist (before declaring done)

Documentation:
- [ ] Read the class top to bottom as a newcomer: could you call the API correctly from it alone?
- [ ] Test names read as a feature list in domain language.
- [ ] Every input that drives a result is visible at the call site, not buried in a helper.
- [ ] No reflection, private-field access or `null!`: only calls a real caller can make
      (standards tests excepted: reflection is how they read the rules).

Standards:
- [ ] A new domain implementation passes the conformance test for its contract, or one exists.
- [ ] A new or changed generic base has tests for its constraint and its behavior.

Reliability:
- [ ] The test is the cheapest type that proves the behavior.
- [ ] No assert on volatile output (message wording, display formatting) unless the format is the contract.
- [ ] Every unique key is Guid-suffixed: no shared literal keys.
- [ ] Date-dependent code takes a clock the test controls; fixed dates only with a test-owned clock.
- [ ] Only third parties are faked; the database is the Testcontainers SQL Server, never SQLite.
- [ ] Database tests assert through a fresh context.
- [ ] No real third-party call; no fixed sleeps.
- [ ] Tests don't depend on execution order: running the class repeatedly gives the same result.
