---
paths:
  - "**/*{Test,Tests,_test,-test}.*"
  - "**/*.{test,spec}.*"
  - "**/test_*.*"
---

# Tests as documentation

Each module's tests live in its own `test/` folder, so the module stays extractable together with them.

- Names state behavior in domain language; arrange/act show calls a real consumer can make; asserts pin the contract and relevant state changes.
- Use AAA, one behavior per test, realistic objects/values, and helpers that expose every behavior-driving input. Expected values are literal or independently derived, not recalculated with production logic.
- Assert stable values/codes/state, not error wording, log text, or display formatting unless exact formatting is the contract.
- Use the cheapest test type that proves the behavior. Run our components for real; hand-written stubs replace only `integration/` adapters to third parties. Unit tests need no database/filesystem.
- Persistence tests run against PostgreSQL in Testcontainers (`Testcontainers.PostgreSql`) through one shared container fixture, never SQLite or EF in-memory. Assert committed state through a fresh context.
- Guid-suffix unique keys because reused containers retain data across runs. Add shared lookup rows only if absent.
- Tests own time via parameters or `TimeProvider`. No real third-party network calls or fixed sleeps; await operations or poll with a bounded timeout.
- Keep behavior tests current in the same change. A new implementation/base contract needs meaningful conformance coverage where applicable.
- A regression test asserts intended behavior. Characterization tests deliberately pin current behavior, including documented bugs, during extraction.
- Do not weaken assertions or silently skip failures. For a bug-fix request, fix the related production bug; for tests-only/review work, report it and seek scope for production changes.
- Focused runs verify selected tests only. Before finishing a behavior change, run the full test project; repeat runs when investigating flakes/shared state.

Example: `Issues_the_invoice_when_the_subscription_renews` with the renewal date visible in arrange and the expected amount literal in assert.

## Full standard: `tests-as-documentation` skill

Imported so the whole skill applies whenever this rule loads. The lines above narrow it for this repo and win where they differ. Links inside it resolve under `.claude/skills/tests-as-documentation/`.

@../skills/tests-as-documentation/SKILL.md
