---
name: logging
description: Applies the house logging standard for a .NET API (Serilog or Microsoft.Extensions.Logging, to console, file and a structured sink such as Application Insights) - picking the level (Verbose, Debug, Information, Warning, Error, Fatal), deciding what an entry must carry, and writing message templates with named placeholders ("Loan {LoanId} repaid", loanId) instead of string interpolation ($"..."), so values stay queryable properties, the template stays constant, and the generic overloads skip boxing and formatting when the level is off. Use when adding, changing or reviewing any _logger (Serilog or Microsoft.Extensions.Logging) / Serilog.Log / ForContext call, a catch block, a retry, a webhook or background job, or when the user mentions logging, log levels, tracing, structured logging, message templates, Application Insights queries, log noise, or boxing and allocations in logs. Not for which fields are sensitive or how to protect them (security).
---

# Logging

A log entry is a query row, not a sentence. Every rule holds for the whole task. Two loggers are in use, both writing to Serilog: `Serilog.ILogger` via `Serilog.Log.ForContext<T>()` (`_logger.Warning(...)`), and injected `Microsoft.Extensions.Logging.ILogger<T>` (MEL, `_logger.LogWarning(...)`). Match the logger the class already has; the template rules are the same for both, the cost rules differ (§1). Default config: minimum level `Information`, `Microsoft`/`System` at `Warning` (appsettings in `src/_config/`), `Enrich.FromLogContext()` on (`src/program.cs`).

## 1. Message templates, never interpolation

```csharp
// ✗ interpolation
_logger.Warning($"Negative balance for: {_accountNumber}. Balance={_balance}, Change={balanceDelta}");

// ✓ template + arguments
_logger.Warning(
    "Negative balance for {AccountNumber}: balance {Balance}, change {BalanceDelta}",
    _accountNumber,
    _balance,
    balanceDelta);
```

| | `$"..."` | `"... {Name}", value` |
|---|---|---|
| String built when level is off | yes, always | no |
| Properties in App Insights | none, one opaque string | `AccountNumber`, `Balance`, ... filterable |
| `MessageTemplate` | unique per call → can't group, fills Serilog's template cache | one constant → `summarize count() by MessageTemplate` |
| Cost when level is off (1–3 args) | every value formatted, a new string allocated | none - generic overloads `Warning<T0, T1, T2>` return before boxing or formatting |

* **Placeholders are named, PascalCase, and describe the value:** `{LoanId}`, not `{}`, `{0}` or `{id}`. The name is the property key in App Insights, so the same value gets the same name everywhere (`{LoanId}` in every file, never `{Loan}` in one and `{LoanID}` in another).
* **Template is a compile-time constant.** No `+` concatenation, no `string.Format`, no `nameof` spliced in at runtime.
* **Boxing, precisely:** Serilog has generic overloads for 1, 2 and 3 arguments only. At 4+ arguments the `params object[]` overload runs: array allocated and value types boxed on every call, even when the level is off. When the level is *on*, Serilog captures values as properties and boxes them anyway - templates save the cost only for entries that get filtered out. That is why it matters most on `Debug`/`Verbose` in hot paths.
* **4+ arguments on a hot path or below `Information`:** guard it.
  ```csharp
  if (_logger.IsEnabled(Serilog.Events.LogEventLevel.Debug))
  {
      _logger.Debug("Allocated {Amount} from {SourceAccount} to {TargetAccount} for {LoanId}", amount, source, target, loanId);
  }
  ```
* **MEL (`ILogger<T>`) has no generic overloads:** every `LogWarning("…", args)` call allocates the `params object[]` and boxes value types, even when the level is off. Level names differ: `Trace` / `Critical` instead of `Verbose` / `Fatal`. On a hot path or below `Information`, use a `[LoggerMessage]` source-generated method (zero allocation when off), or guard with `_logger.IsEnabled(Microsoft.Extensions.Logging.LogLevel.Debug)`.
  ```csharp
  [Microsoft.Extensions.Logging.LoggerMessage(Level = Microsoft.Extensions.Logging.LogLevel.Debug, Message = "Chose payout route {Route} for {LoanId}")]
  private static partial void LogPayoutRouteChosen(Microsoft.Extensions.Logging.ILogger logger, string route, System.Guid loanId);
  ```
* **Expensive arguments** (serialization, `.ToList()`, `string.Join`) also go behind `IsEnabled` - arguments are evaluated before the call.
* **Destructuring:** `{Value}` stores `ToString()`/scalar. `{@Value}` serializes the whole object - only for small DTOs you own, never entities (lazy-loaded graphs, PII). `{$Value}` forces `ToString()`.

## 2. Pick the level

Ask: *who must act, and how fast?*

| Level | Meaning | Who acts | Example |
|---|---|---|---|
| `Verbose` | Step-by-step trace inside an algorithm | nobody - local debugging only | each installment in a repayment schedule calculation |
| `Debug` | Internal decision useful when diagnosing | developer, on demand (off in prod) | "Chose payout route {Route} for {LoanId}" |
| `Information` | A business event happened - one per meaningful state change | nobody; it's the audit/flow trail | "Loan {LoanId} disbursed {Amount}", webhook received, job started/finished with counts |
| `Warning` | Unexpected but handled; system continues correctly | someone, eventually, if it repeats | retry attempt, duplicate webhook ignored, negative balance allowed by config, fallback used |
| `Error` | An operation failed; a user or process did not get its result | someone, today | payout to the bank failed, HubSpot sync threw, invalid webhook signature |
| `Fatal` | The process cannot continue | someone, now | startup config missing, DB unreachable at boot |

* **Not an `Error`:** validation failures and expected domain rejections (insufficient funds, KYC declined) - the system worked. `Information` if the event matters to the flow, otherwise nothing; the response already tells the caller.
* **Not `Information`:** per-item lines inside loops. Log once with a count: `"Synced {DealCount} deals in {ElapsedMilliseconds} ms"`.
* **A `Warning` nobody will act on** is `Information` or nothing. A `Warning` that fires every request is noise that hides real warnings.
* **Log an exception once,** at the boundary that handles it (catch that swallows, controller/job top level). A catch that rethrows doesn't log - the handler above does.

## 3. What every entry carries

* **The id that lets you find the row:** `{LoanId}`, `{AccountId}`, `{CorrelationId}`, `{HubSpotDealId}`. "Payout failed" without an id is useless.
* **The exception as the first argument, not its message:**
  ```csharp
  // ✗ loses stack trace and exception type
  _logger.Error("Payout failed: {Message}", exception.Message);
  // ✓
  _logger.Error(exception, "Payout to bank failed for {LoanId}", loanId);
  ```
* **Units in the name:** `{ElapsedMilliseconds}`, `{AmountDkk}`, not `{Elapsed}`, `{Amount}` when the unit is ambiguous.
* **Source context:** `Serilog.Log.ForContext<T>()` per class, or the `T` of an injected `ILogger<T>`, so `SourceContext` filters by class.
* **Scope-wide ids** (one webhook, one job run) go in once via `Serilog.Context.LogContext.PushProperty("CorrelationId", correlationId)` in a `using` block, instead of repeating them in every template.
* **Never** CPR, IBAN, bank account numbers, tokens, secrets, raw webhook payloads or whole request bodies - log the id instead. Rules and the hash/mask options: `security` skill.

## 4. Review checklist

```
- [ ] no $"..." or concatenation in any log call
- [ ] placeholders named, PascalCase, same name as elsewhere for the same value
- [ ] 4+ args (Serilog), any args on a hot path (MEL), or expensive args below Information are behind IsEnabled or [LoggerMessage]
- [ ] level matches the table; no Error for expected domain outcomes
- [ ] exception passed as first argument, logged once
- [ ] entry carries the lookup id; no sensitive data or raw payloads
```
