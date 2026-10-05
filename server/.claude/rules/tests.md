---
paths:
  - "API/FF-API/FF.Tests/**/*"
  - "Web/test/**/*"
  - "Web/**/*.{test,spec}.{js,ts}"
---

# Tests as documentation

- Names state behavior in domain language; arrange/act show calls a real consumer can make; asserts pin the contract and relevant state changes.
- Use AAA, one behavior per test, realistic objects/values, and helpers that expose every behavior-driving input. Expected values are literal or independently derived, not recalculated with production logic.
- Assert stable values/codes/state, not error wording, log text, or display formatting unless exact formatting is the contract.
- Use the cheapest test type that proves the behavior. Run our components for real; hand-written third-party stubs isolate external services. Unit tests need no database/filesystem.
- New persistence tests use Testcontainers SQL Server and MsSqlContainerFixture/MsSqlCollection, not legacy SQLite/InMemDbFixture or EF in-memory. Assert committed state through a fresh context.
- Guid-suffix unique keys because reused containers retain data across runs. Add shared lookup rows only if absent.
- Tests own time via parameters, TimeProvider, or the existing clock abstraction. No real third-party network calls or fixed sleeps; await operations or poll with a bounded timeout.
- Keep behavior tests current in the same change. A new implementation/base contract needs meaningful conformance coverage where applicable.
- A regression test asserts intended behavior. Characterization tests deliberately pin current behavior, including documented bugs, during extraction.
- Do not weaken assertions or silently skip failures. For a bug-fix request, fix the related production bug; for tests-only/review work, report it and seek scope for production changes.
- Focused runs verify selected tests only. For backend behavior changes, follow the test-runner agent's focused/full-suite policy; repeat runs when investigating flakes/shared state.

Example: `Invests_the_low_risk_amount_when_the_loan_is_low_risk` with the rating visible in arrange and the expected amount literal in assert.
Harnesses, matrices, calendar edges, and API/E2E setup: `.claude/skills/tests-as-documentation/SKILL.md`.
