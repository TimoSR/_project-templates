---
name: tests-as-documentation
description: >-
  Writes tests of every type (unit, integration, infrastructure, API,
  E2E) as the documentation of our in-house APIs, plus standards tests for
  architecture rules (interfaces, base classes, generic constraints), and sets up
  the test database (PostgreSQL via Testcontainers). Use when adding tests for a
  new feature, raising coverage, updating tests after a behavior change, choosing
  a test type, or when the user says "write tests", "add a test", "integration
  test", "API test", "e2e test", "architecture test", "check it implements the
  interface", "test this handler/service/command/endpoint", "cover this with
  tests", or "the tests are flaky / failing". Covers a module's test/ folder.
---

# tests-as-documentation

One strategy for all five test types. Load on demand: [standards-tests.md](standards-tests.md)
(architecture rules as tests), [test-matrices.md](test-matrices.md) (`[Theory]` rows),
[api-and-e2e-tests.md](api-and-e2e-tests.md) (API contract and browser journey tests),
[dates-and-time.md](dates-and-time.md) (controlling the clock, calendar edges).

## The first principle: tests are the documentation

We keep no external docs for our in-house APIs: code is the source of truth, and the tests are the
part of the code that shows **what each feature does and how it is meant to be used**. A new
developer opens `InvoiceTotalCalculatorTests.cs`, not a wiki page. Every other rule in this skill
serves this one; speed, no flake and production-like data come after.

Write each test as the example a newcomer would copy:

* **The test list is the feature list.** Names are sentences stating behavior in domain language,
  so the test explorer reads as a spec:

  ```
  InvoiceTotalCalculatorTests
  ├── Adds_vat_to_the_net_amount_for_a_domestic_customer
  ├── Charges_no_vat_to_a_business_in_another_eu_country
  └── Prorates_the_first_month_when_the_subscription_starts_mid_month
  ```

  ✗ `Calculate_OneInvoice`, `Test1`, `Calculate_Works` (the `Method_Case` form)
* **Arrange + Act show real usage.** Go through the entry point a real caller uses (the public
  method, the command, the endpoint) with the setup a real caller needs. The arrange
  section *is* the answer to "what do I need before I can call this?"
* **No usage a caller can't do.** Reflection, poking private fields, `null!` for a required
  dependency: each documents a call that's impossible in production. If the test needs one, the
  API is the problem: report it.
* **Helpers hide noise, never the point.** A `Build…()` helper fills fields the behavior doesn't
  care about; every input the behavior depends on is a named argument, visible at the call site.

  ```csharp
  // ✗ which customer? the reader has to open the helper to learn the rule
  var invoice = BuildInvoice();

  // ✓ the input that drives the result is on the page
  var invoice = BuildInvoice(customerCountry: "DK", netAmount: 300000);
  ```

* **Realistic values.** Amounts, dates and names a real caller would send (an invoice of 300000,
  not `1`; a VAT number in the real format), so the test also documents the expected data.
* **Assert shows the contract.** What the caller gets back and which state changed: the result a
  newcomer can rely on, not implementation details.
* **Comments say why, as business rules.** `// Invoices under 50 DKK roll into next month
  (billing policy)`. Never restate what the code does.
* **Coverage goal: every in-house API has at least one happy-path test that shows how to use it.**
  An API with no test is an undocumented API. Not a percentage, not 100%: cover the main behaviors
  and the edges that would silently break a feature.

## Two parts of the suite

| Part | Answers | Example |
| --- | --- | --- |
| **Documentation of the implementation** | What does this feature do, how do I call it? | `Adds_vat_to_the_net_amount_for_a_domestic_customer` |
| **Validation of set standards** | Does the code follow the rules we set for it? | `Every_dunning_policy_implements_IDunningPolicy` |

Both are documentation: the first documents behavior, the second documents our architecture rules
as executable checks. A rule with no test is a rule the next class can silently break. How to write
standards tests: [standards-tests.md](standards-tests.md).

## The five types

Pick the **cheapest type that can prove the behavior**. Each step up buys confidence and pays in
speed and flake risk.

| Type | Proves | Documents | Real | Faked | Speed | Where |
| --- | --- | --- | --- | --- | --- | --- |
| **Unit** | One function / class does the right thing | How to call a class and what each input does | Everything (plain objects) | Nothing | ms | the module's `test/` |
| **Integration** | Our components work together | How a flow is composed: which components cooperate, which side effects happen | All our code, wired as in production | Only third parties, with hand-rolled stubs | ms–s | the module's `test/` (a processor + a `…Stub` that records published events) |
| **Infrastructure** | Our code works against real infrastructure | What the database / cache guarantees (constraints, concurrency) | PostgreSQL, Redis, … in Docker via Testcontainers | Third parties | s | the module's `test/`, joining `PostgreSqlCollection` |
| **API** | The HTTP or GraphQL contract a client sees | How a client calls the endpoint: the request itself is the example | HTTP pipeline, auth, controllers/resolvers, DB | Third parties | s | No harness: [api-and-e2e-tests.md](api-and-e2e-tests.md) |
| **E2E** | A user journey works through the real UI | How a user moves through a feature | Browser → frontend → API → DB | Third parties (sandbox / test mode) | s–min | No harness: [api-and-e2e-tests.md](api-and-e2e-tests.md) |

```
            E2E          few: critical journeys only (sign up, subscribe, pay)
           API           one per endpoint contract
      Infrastructure     persistence, raw SQL, concurrency, caching
       Integration       handlers, processors, orchestration
          Unit           most tests: calculators, rules, mappers
```

Trade-off: **speed and simplicity at the bottom, confidence in the wiring at the top.** A rule that
a unit test can prove never gets an E2E test.

## Shared rules (every type)

* **Real objects, not fake data.** When the SUT takes an `Invoice`, construct an `Invoice`.
   * ✗ a mocked `Invoice`, an anonymous object, a half-filled DTO the SUT never sees in production
   * ✓ `new Invoice(customerId, netAmount: 300000, customerCountry: "DK")`
* **Fake only what we don't own.** Our code, our database and our cache run for real (in a
  container if needed). Third parties (HubSpot, Twilio, Stripe, the identity provider) get a
  hand-rolled `…Stub` implementing the module's `integration/` interface. Reuse an existing stub
  first; a stub records what it received (`EventsPublished`, `SentMessages`) so the test can
  assert the side effect.
* **Expected values are stated, not computed.** Write the literal or a hand-derived value; never
  re-run the production formula in the assert. That's a tautology that passes whatever the code does.

  ```csharp
  // ✗ the same formula on both sides: passes even when the formula is wrong
  Xunit.Assert.Equal(calculator.Calculate(invoice), result);

  // ✓ the number a reader can check by hand: 300000 + 25 % VAT
  Xunit.Assert.Equal(375000, result);
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
  var invoice = BuildInvoice(customerCountry: "DK", netAmount: 300000);

  // Act
  var result = calculator.Calculate(invoice);

  // Assert
  Xunit.Assert.Equal(375000, result);
  ```

* **No hardcoded keys that collide.** Every field that must be unique (email, VAT number, code,
  partner code) gets a readable prefix plus `Guid.NewGuid():N` (32 hex chars, no dashes, safe in
  emails and codes). The prefix keeps failures diagnosable. Non-key values (a display name, an
  amount) stay literal.
   * ✗ `Email = "customer@test.dk"`: the second run, or a parallel test, hits the unique index
   * ✓ `Email = $"customer-{System.Guid.NewGuid():N}@test.dk"`
* **The test owns "now".** Date-dependent code gets its time from outside: a `now` / `today`
  parameter or `System.TimeProvider`. Never from `DateTime.UtcNow`. The test sets a fixed instant,
  writes the expected dates as literals, and moves the clock forward instead of sleeping. Cover the
  calendar edges the rule depends on: month end, leap day, year change, the exact boundary, DST.
  Full rules: [dates-and-time.md](dates-and-time.md).
* **No real third-party network call, ever.** No `Thread.Sleep` / `Task.Delay` for timing: await the
  actual operation, or poll for the condition with a timeout.

## What to cover

* **Happy path:** intended usage, the call a real caller makes.
* **Unhappy path:** misuse the feature guarantees to handle (missing input, wrong partner,
  amount ≤ 0). It documents the API's limits: what it refuses and how it says no. Assert the
  returned `false` / `null` / validation result / error code, not an exception: the domain doesn't
  throw.
* **State:** the object's fields before → after the call (`PaidAmount` 0 → 375000), not only
  the return value.
* **Variants of one behavior:** one `[Theory]`, an expected value per row, each input state named
  by a function: [test-matrices.md](test-matrices.md).
* **Orchestrating functions:** the method that coordinates other methods (a processor calling
  calculator → repository → event publisher). Pin the combined result.
* **Internal helpers:** test the helper directly when its logic is hard to reach through the public
  method. Make it `internal` and expose internals to the test project once per assembly:

  ```csharp
  // AssemblyInfo.cs of the assembly under test
  [assembly: System.Runtime.CompilerServices.InternalsVisibleTo("Billing.Tests")]
  ```

  If the assembly has no `InternalsVisibleTo` yet, adding it is a production change: say so in the
  summary. A truly `private` method stays covered through its public caller.
* **Skip:** generated CRUD, thin pass-through resolvers, framework glue, trivial getters,
  impossible states. Spend the budget on calculators, processors, eligibility and money rules.

## Per type

### Unit

* Target: calculator, service, mapper, domain rule whose collaborators can be built for real.
* No stubs, no database, no file system. If the test needs any of them, it's an integration or
  infrastructure test.

### Integration

* Target: a handler or processor and the real components it coordinates.
* Wire our classes for real. A stub that captures what it received (published events, sent emails)
  lets you assert the side effect.
* Needs persistence → use the real database (infrastructure setup below), never SQLite or the EF
  in-memory provider: they skip PostgreSQL's constraints, collation and concurrency, so a test can
  pass there and fail in production.

### Infrastructure

* Target: behavior that only exists in the real engine: migrations, raw SQL, concurrency tokens,
  constraints, transactions, Redis caching.
* One shared container per test run: a `PostgreSqlContainerFixture` (`Testcontainers.PostgreSql`)
  exposed as the xUnit collection `PostgreSqlCollection`. Tests join it with
  `[Collection(nameof(PostgreSqlCollection))]` and take the fixture in the ctor. The first module
  that needs it builds it; later modules reuse it, never a second one.
* Configure the context with `UseNpgsql(fixture.ConnectionString)` and apply the real migrations
  (`MigrateAsync`), so the schema is production's.
* Other infrastructure (Redis, …): the matching Testcontainers module (`Testcontainers.Redis`), same
  fixture pattern.
* Build the container `WithReuse(true)`: it survives across tests **and across runs**. Rows
  persist, so every key a test owns is Guid-suffixed, and shared lookup rows (countries,
  currencies, VAT rates) are added only when absent.
* Handlers commit their own unit of work. **Assert through a separate fresh context** (or clear the
  change tracker) so you read committed state, not tracked entities that give a false green.
* Requires Docker running locally.

## Organization

Tests live in the module's `test/` folder, so a module extracts together with its tests. The file
name names the component under test: `<Sut>Tests.cs`.

```
src/features/billing-feature-example/
├── invoicing-module/test/InvoiceTotalCalculatorTests.cs     unit
├── invoicing-module/test/InvoiceIssuingProcessorTests.cs    integration + infrastructure
├── payment-module/test/DunningPolicyStandardsTests.cs       standards: lives with the code whose rules it guards
└── subscription-module/test/SubscriptionRenewalTests.cs
```

One test class per SUT and type. A class that grows too large splits by behavior
(`IssueInvoiceCommandValidationTests`, `IssueInvoiceCommandVatTests`).

## Process

1. **Locate the SUT and its collaborators.** Read the class; list its ctor deps. State what the
   code is *for* before writing asserts. Pick the cheapest type that proves it. Verify: you can
   name the one behavior each test pins.
2. **Find the nearest existing test of that type** (same `test/` folder first) and match its
   layout; don't invent a harness. Database tests always join `PostgreSqlCollection`, never
   SQLite. API or E2E with no harness: stop and propose the setup
   ([api-and-e2e-tests.md](api-and-e2e-tests.md)).
3. **Arrange production-like data** via small `Build…()` / `Seed…()` helpers with Guid-suffixed
   keys, so intent stays visible and a signature change touches one place.
4. **Cover** per [What to cover](#what-to-cover), matrices per [test-matrices.md](test-matrices.md).
5. **Verify green, then verify it can go red.** Run the class several times, then the full test
   project. A filtered run isn't verification: tests sharing a database can break each other; a
   result that changes between runs is shared state leaking. Re-read each assert: would it fail if
   the behavior regressed? Finish with the checklist.

## When a test exposes a bug

The test asserts the *intended* behavior and fails: that failing test is the finding.
* Report it: file, line, expected vs actual.
* Never rewrite the test to match the broken behavior, and never silently fix production code; the
  fix is a separate, user-approved change that turns the test green.
* Don't pre-emptively `Skip` it; that's the outcome of the discussion with the user, not its start.
* Exception: characterization tests (written before moving or extracting code) pin *current* behavior, known-wrong
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
- [ ] Only third parties are faked; the database is the Testcontainers PostgreSQL, never SQLite.
- [ ] Database tests assert through a fresh context.
- [ ] No real third-party call; no fixed sleeps.
- [ ] Tests don't depend on execution order: running the class repeatedly gives the same result.
