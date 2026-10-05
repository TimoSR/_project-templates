# API and E2E tests

Neither type has a harness until the user approves one. Check first: an API host in `FF.Tests`
(a `WebApplicationFactory` or `TestServer`), an E2E runner in `Web/package.json`. None found → the
first test is a setup decision for the user: propose it; don't build the harness or install tooling
unasked.

## API

* Target: the GraphQL contract: query/mutation in → response data, `errors` and authorization out.
  One test per contract, not per business rule (rules are proven lower down).
* Proposed setup: host `FF.Api` in-process (`FF.Tests` already references it) against the
  Testcontainers database, with third parties stubbed in DI.
* Assert what a client depends on: field values, error codes, an unauthorized caller being refused.
  Not response key order or incidental fields.

## E2E

* Target: a critical user journey through the real UI (sign up, KYC, invest, repay). A handful,
  not one per feature.
* The setup decision covers the browser driver, which environment, and how third parties run in
  sandbox / test mode.
* Select elements by role or visible text, not CSS classes. Wait for a condition, never a fixed
  delay. Each test creates its own Guid-suffixed user; never share accounts between tests.
