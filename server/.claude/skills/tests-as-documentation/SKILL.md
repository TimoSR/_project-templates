---
name: tests-as-documentation
description: >-
  The FlexFunding test strategy for every test type (unit, integration,
  infrastructure, API, E2E). Tests are the documentation of our in-house APIs: a
  new developer learns what each feature does and how to call it by reading its
  tests, and standards tests verify the architecture rules (interfaces, base
  classes, generic constraints). Picks the cheapest type that proves the behavior, then writes it the
  house way: AAA layout, real objects
  instead of mocks, real SQL Server via Testcontainers, named test matrices, and
  collision-free production-like data (no hardcoded strings/dates that age out).
  Use when adding tests for a new feature, raising coverage, updating tests after
  changing behavior, deciding what kind of test something needs, or when the user
  says "write tests", "add a test", "integration test", "API test", "e2e test",
  "architecture test", "check it implements the interface",
  "test this handler/service/command/endpoint", "cover this with tests", or "the
  tests are flaky / failing".
---

# tests-as-documentation

One strategy for all five test types.

## The first principle: tests are the documentation

We keep no external docs for our in-house APIs: code is the source of truth, and the tests are the
part of the code that shows **what each feature does and how it is meant to be used**. A new
developer opens `AutoInvestCalculatorTests.cs`, not a wiki page. Every other rule in this skill
serves this one, then speed and reliability.

Write each test as the example a newcomer would copy:

* **The test list is the feature list.** Names state behavior in domain language, so the test
  explorer reads as a spec:

  ```
  AutoInvestCalculatorTests
  ├── Invests_the_low_risk_amount_when_the_loan_is_low_risk
  ├── Never_invests_more_than_the_loan_has_left_to_fill
  └── Monthly_strategy_invests_less_as_the_month_runs_out
  ```

  ✗ `Calculate_OneAccount`, `Test1`, `Calculate_Works`
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
* **Unhappy paths document the API's limits.** What it refuses and how it says no
  (`false`, a validation result, a GraphQL error code).
* **Comments say why, as business rules.** `// Loans under 6 months can't be auto-invested
  (risk policy)`. Never restate what the code does.
* **Coverage goal: every in-house API has at least one happy-path test that shows how to use it.**
  Not a percentage. An API with no test is an undocumented API.
* **A behavior change updates the test in the same change.** The test is the doc; a stale test is
  a lie the next developer will copy.

Each type documents something different:

| Type | Documents |
| --- | --- |
| Unit | How to call a class and what each input does |
| Integration | How a flow is composed: which components cooperate, which side effects happen |
| Infrastructure | What the database / cache guarantees (constraints, concurrency) |
| API | How a client calls the endpoint: the query or mutation text itself is the example |
| E2E | How a user moves through a feature |

## Two parts of the suite

| Part | Answers | Example |
| --- | --- | --- |
| **Documentation of the implementation** | What does this feature do, how do I call it? | `Invests_the_low_risk_amount_when_the_loan_is_low_risk` |
| **Validation of set standards** | Does the code follow the rules we set for it? | `Every_alarm_policy_implements_IAlarmPolicy` |

Both are documentation: the first documents behavior, the second documents our architecture rules
as executable checks. A rule with no test is a rule the next class can silently break. Standards
tests: [below](#standards-tests).

Other goals, after documentation: speed, no flake, production-like data. Not 100% coverage: cover
the main behaviors and the edges that would silently break a feature.

## The five types

Pick the **cheapest type that can prove the behavior**. Each step up buys confidence and pays in
speed and flake risk.

| Type | Proves | Real | Faked | Speed | In the repo |
| --- | --- | --- | --- | --- | --- |
| **Unit** | One function / class does the right thing | Everything (plain objects) | Nothing | ms | Backend `FF.Tests`; Web `test/unit/` |
| **Integration** | Our components work together | All our code, wired as in production | Only third parties, with hand-rolled stubs | ms–s | Backend `FF.Tests` (e.g. `AutoInvestProcessorTests` + `MediatorStub`); Web `test/integration/`, `test/component/` |
| **Infrastructure** | Our code works against real infrastructure | SQL Server, Redis, … in Docker via Testcontainers | Third parties | s | `MsSqlContainerFixture` |
| **API** | The GraphQL contract a client sees | HTTP pipeline, auth, resolvers, DB | Third parties | s | **Not set up yet** |
| **E2E** | A user journey works through the real UI | Browser → Web → API → DB | Third parties (sandbox / test mode) | s–min | **Not set up yet** |

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
  `…Stub` implementing the interface; reuse an existing one in `FF.Tests` first.
* **Expected values are stated, not computed.** Write the literal or a hand-derived value; never
  re-run the production formula in the assert. That's a tautology that passes whatever the code does.
* **AAA, one behavior per test.** Mark the sections:

  ```csharp
  // Arrange
  var loan = BuildLoan(amount: 300000);

  // Act
  var result = calculator.Calculate(loan, accounts);

  // Assert
  Xunit.Assert.Equal(10000, result);
  ```

  Name the test as a sentence describing the behavior
  (`Invests_the_low_risk_amount_when_the_loan_is_low_risk`), not the `Method_Case` form.
* **No hardcoded keys that collide.** Every field that must be unique (email, reg number, code,
  partner code) gets a readable prefix plus `Guid.NewGuid():N` (32 hex chars, no dashes, safe in
  emails and codes). The prefix keeps failures diagnosable. Non-key values (a display name, an
  amount) stay literal.
* **No absolute "now"/year literals.** Express time relative to `DateTime.UtcNow`:

  | Intent | Write |
  | --- | --- |
  | In the past | `DateTime.UtcNow.AddDays(-25)` |
  | In the future | `DateTime.UtcNow + TimeSpan.FromHours(1)` |
  | Just expired | `DateTime.UtcNow - TimeSpan.FromMinutes(1)` |

  Exception: fixed dates are fine when the test builds the calendar or clock the SUT reads; both
  live in the test, so nothing external drifts. If the SUT reads `DateTime.UtcNow` itself, assert
  with a tolerance.
* **No real third-party network call, ever.** No `Thread.Sleep` / `Task.Delay` for timing: await the
  actual operation, or poll for the condition with a timeout.

## What to cover

* **Happy path:** intended usage, the call a real caller makes.
* **Unhappy path:** misuse the feature guarantees to handle (missing input, wrong partner,
  amount ≤ 0). Assert the returned `false` / validation result, not an exception: the domain
  doesn't throw.
* **State:** the object's fields before → after the call (`FilledAmount` 10000 → 20000), not only
  the return value.
* **Orchestrating functions:** the method that coordinates other methods (a processor calling
  calculator → repository → event publisher). Pin the combined result.
* **Internal helpers:** test the helper directly when its logic is hard to reach through the public
  method. Make it `internal` and expose internals to the test project once per assembly:

  ```csharp
  // FF.App/Properties/AssemblyInfo.cs
  [assembly: System.Runtime.CompilerServices.InternalsVisibleTo("FF.Tests")]
  ```

  No assembly does this yet: adding it is a production change, so say so in the summary. A truly
  `private` method stays covered through its public caller.
* **Skip:** source-generated CRUD, thin pass-through resolvers, framework glue, trivial getters,
  impossible states. Spend the budget on calculators, processors, eligibility and money rules.

## Test matrices

Fold variants of one behavior into a `[Theory]`, expected value in each row. Name the input state
with a function, so the row says what it's aiming for without a comment.

```csharp
// ✗ the intent lives in a comment; -15 means nothing on its own
[InlineData(100000, 40000, 10000, AutoInvestStrategyEnum.Monthly, -15)] // Days 15-21: factor = 4

// ✓ the state has a name
public static TheoryData<System.DateTime, int> MonthlyWeeks => new()
{
    { FirstWeekOfMonth(), 2500 },
    { ThirdWeekOfMonth(), 10000 },
    { AfterThirdWeek(),   5000 },
};
private static System.DateTime ThirdWeekOfMonth() { return System.DateTime.UtcNow.AddDays(-15); }

[Theory]
[MemberData(nameof(MonthlyWeeks))]
public void Monthly_strategy_invests_less_as_the_month_runs_out(System.DateTime startedAt, int expectedAmount) { ... }
```

* `[InlineData]` takes only compile-time constants: a `DateTime` as a string (xUnit converts it),
  anything else via `[MemberData]` / `TheoryData`.
* Rows that need different assertions are different tests.

## Per type

### Unit

* Target: calculator, service, mapper, domain rule whose collaborators can be built for real.
* No stubs, no database, no file system. If the test needs any of them, it's an integration or
  infrastructure test.
* Web: `write-frontend-unit-tests` skill.

### Integration

* Target: a handler or processor and the real components it coordinates.
* Wire our classes for real; only third-party interfaces get a `…Stub`. A stub that captures what
  it received (published events, sent emails) lets you assert the side effect.
* Needs persistence → use the real database (infrastructure setup below), never SQLite or the EF
  in-memory provider: they skip SQL Server's constraints, collation and concurrency, so a test can
  pass there and fail in production.
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
* The container is built `WithReuse(true)`: it survives across tests **and across runs**. Rows
  persist, so every key a test owns is Guid-suffixed, and shared lookup rows (countries,
  currencies, product types) are added only when absent.
* Handlers commit their own unit of work. **Assert through a separate fresh context** (or clear the
  change tracker) so you read committed state, not tracked entities that give a false green.
* Requires Docker running locally.

### API

* Target: the GraphQL contract: query/mutation in → response data, `errors` and authorization out.
  One test per contract, not per business rule (rules are proven lower down).
* Not set up yet. The first API test is a setup decision for the user: host `FF.Api` in-process
  (`FF.Tests` already references it) against the Testcontainers database, with third parties
  stubbed in DI. Propose it; don't build the harness unasked.
* Assert what a client depends on: field values, error codes, an unauthorized caller being refused.
  Not response key order or incidental fields.

### E2E

* Target: a critical user journey through the real UI (sign up, KYC, invest, repay). A handful,
  not one per feature.
* Not set up yet. The first E2E test is a tooling decision for the user (browser driver, which
  environment, how third parties run in sandbox / test mode). Propose it; don't install tooling
  unasked.
* Select elements by role or visible text, not CSS classes. Wait for a condition, never a fixed
  delay. Each test creates its own Guid-suffixed user; never share accounts between tests.

## Standards tests

Checks that the code follows the rules we set: interfaces, base classes, generic constraints, DI
registration. Plain reflection over the compiled assemblies: no I/O, unit speed. Existing example:
`FF.Tests/HubSpot/HubSpotMapperRegistrationTests.cs` (every legacy mapper is also registered
through the shared contract).

### Domain conformance

When we implement a domain, check every implementation satisfies its contract: the right interfaces
and abstract classes.

```csharp
[Fact]
public void Every_alarm_policy_implements_IAlarmPolicy()
{
    // Arrange
    var policyTypes = typeof(FF.App.Alarms.Policies.IAlarmPolicy).Assembly.GetTypes()
        .Where(type => type.Namespace == "FF.App.Alarms.Policies" && type.IsClass && !type.IsAbstract)
        .ToArray();

    // Act
    var violations = policyTypes
        .Where(type => !typeof(FF.App.Alarms.Policies.IAlarmPolicy).IsAssignableFrom(type))
        .ToArray();

    // Assert
    Xunit.Assert.NotEmpty(policyTypes); // a scan that finds nothing passes every rule
    Xunit.Assert.Empty(violations);     // the failure message lists the offending types
}
```

* Find the types by a stable marker (namespace, base type, attribute), and assert the scan found
  some. A renamed namespace would otherwise make the rule pass vacuously.
* Assert on the list of violations, so one run names every offender.

### Generic architecture rules

A generic building block (`PolicyBase<TEntity> where TEntity : IEntity`,
`ObjectTypeBase<T> where T : EntityBase`) encodes an inheritance rule. The compiler enforces the
`where` only while it exists; deleting it compiles fine and drops the rule. So the generic owns
tests for both halves:

1. **The rule is in place:** the constraint is declared.

   ```csharp
   [Fact]
   public void PolicyBase_only_accepts_entities()
   {
       // Arrange
       var entityParameter = typeof(FF.App.Alarms.Policies.PolicyBase<>).GetGenericArguments()[0];

       // Act
       var constraints = entityParameter.GetGenericParameterConstraints();

       // Assert
       Xunit.Assert.Contains(typeof(Ftb.Core.IEntity), constraints);
   }
   ```

2. **The rule behaves correctly:** a type that satisfies the constraint runs through the generic
   and gets the behavior the base class promises (e.g. a `PolicyBase<Account>` subclass resolves
   alarms against the `Account` entity name). Use a real implementation; it doubles as the usage
   example for the next developer who builds on the generic.

* Name the test as the rule (`PolicyBase_only_accepts_entities`), so the test list reads as the
  architecture's rulebook.
* Every new generic base, marker interface or registration convention ships with its standards
  test in the same change.

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
   invent a harness. API and E2E have none yet: stop and propose the setup.
3. **Arrange production-like data** via small `Build…()` / `Seed…()` helpers with Guid-suffixed
   keys, so intent stays visible and a signature change touches one place.
4. **Cover** per [What to cover](#what-to-cover), matrices per [Test matrices](#test-matrices).
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

## Updating tests when a feature changes

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
- [ ] Every unique key is Guid-suffixed: no shared literal keys.
- [ ] No hardcoded "now"/year; time is relative to `DateTime.UtcNow` (or the test builds the clock).
- [ ] Only third parties are faked; the database is the Testcontainers SQL Server, never SQLite.
- [ ] Database tests assert through a fresh context.
- [ ] No real third-party call; no fixed sleeps.
- [ ] Tests don't depend on execution order: running the class repeatedly gives the same result.
