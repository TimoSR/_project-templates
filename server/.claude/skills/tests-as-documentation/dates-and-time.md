# Dates and time

Code that reads the clock gives a different answer depending on when the test runs. It passes
today and fails on the 31st, at midnight, on a DST switch, or next January, after the change was
merged. **Rule: the test owns "now".** If the test can't set the time, it can't pin date behavior.

## 1. The SUT gets time from outside, never from `DateTime`

Pick the first option that fits:

| Option | When | In the repo |
| --- | --- | --- |
| `now` / `today` as a parameter | Pure calculators and rules: simplest, needs no stub | — |
| .NET `System.TimeProvider` | New code, feature modules | `FactoringService`, `FactoringOutboxDispatcher`; production registers `TimeProvider.System` |
| `FF.Core.Services.Time.IDateAndTimeProvider` | Monolith code that already uses it | `GetUtcNow()`, `GetToday(DatePurpose)`; stubbed in `PlaceOrderTestContext` |

```csharp
// ✗ the test can't choose the day, so "the last day of the month" is untestable
public decimal Calculate(Loan loan) { var today = System.DateTime.Today; ... }

// ✓ the caller (and the test) decides what today is
public decimal Calculate(Loan loan, System.DateOnly today) { ... }
```

* The SUT reads `DateTime.UtcNow` itself and you can't change it: use relative values
  (`DateTime.UtcNow.AddDays(-25)`) and assert with a tolerance. Report that the calendar edges
  stay untested. Adding a clock parameter is a production change: say so in the summary.

## 2. Fixed clock, stated dates

With the clock under control, set a fixed instant and write the expected dates as literals. Both
live in the test, so nothing drifts, and the reader can check the date by hand.

```csharp
// Arrange: a fixed instant the test owns
var start = new System.DateTimeOffset(2026, 9, 21, 12, 0, 0, System.TimeSpan.Zero);
var timeProvider = new FixedTimeProvider(start);

// Assert: a literal, not start.AddDays(30) re-derived from the production rule
Xunit.Assert.Equal(new System.DateOnly(2026, 10, 21), result.DueDate);
```

* Stub: `FixedTimeProvider` in `FF.Tests/Features/FactoringFeature/FactoringOutboxTests.cs`
  (a `TimeProvider` with a settable `UtcNow`). If a second test file needs it, move it to
  `FF.Tests/Util/` and don't copy it.
* Fixed literals are only safe with a test-owned clock. ✗ `new DateTime(2026, 1, 1)` passed to
  code that compares it with the real `DateTime.UtcNow`: it becomes "the past" once that date
  goes by.

## 3. Move time, don't wait for it

Expiry, leases, retries, grace periods, overdue checks: change the clock, don't sleep.

```csharp
// Real: Expired_worker_cannot_overwrite_the_result_of_the_new_lease_owner
timeProvider.UtcNow = start.AddMinutes(5); // the first worker's lease has expired
```

✗ `await Task.Delay(TimeSpan.FromMinutes(5))`: slow, and still flaky.

## 4. Cover the calendar edges

Date bugs live here. Make them `[Theory]` rows, each one a named function
([test-matrices.md](test-matrices.md)):

| Edge | Example input | Bug it catches |
| --- | --- | --- |
| Month end | 31 Jan + 1 month | Feb 28 vs Mar 3 |
| Leap day | 29 Feb 2028 + 1 year | Feb 28 vs Mar 1 |
| Year change | 31 Dec → 1 Jan | wrong year, interest-year split |
| Exact boundary | due at 00:00:00, checked at 00:00:00 | `<` vs `<=`: overdue one day early or late |
| DST switch (Europe/Copenhagen) | last Sunday of March / October | a 23 h or 25 h "day" |
| Business days | due on a Saturday or bank holiday | payment date not rolled forward |

Add only the edges the rule actually depends on.

## 5. UTC vs local

* `DateTime.Today` / `DateTime.Now` use the machine's time zone. A dev laptop runs CET, Azure
  and CI run UTC, so a test can pass locally and fail in CI between 00:00 and 02:00.
* Keep the clock in UTC. Convert to a named zone explicitly where the business rule is local
  (a Danish payment date), and test that conversion at the DST rows above.
