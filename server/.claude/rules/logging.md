---
paths:
  - "API/**/*.cs"
---

# Logging

- Match the class's existing Serilog or `ILogger<T>` logger. Use constant message templates with named PascalCase placeholders, never interpolation/concatenation.
- Keep property names consistent and include useful lookup/correlation IDs and units.
- Pass exceptions as exception arguments, preserving stack/type; log each failure once at the boundary that handles it.
- Levels reflect action: Debug/Verbose for diagnosis, Information for meaningful business events, Warning for actionable handled problems, Error for failed operations, Fatal for process failure. Expected validation/domain rejection is not an Error.
- Summarize loops with counts and elapsed time. Avoid per-item Information noise.
- No PII, tokens, secrets, raw webhook bodies, or whole entity destructuring. Use safe internal IDs.
- Guard expensive arguments and hot-path/below-Information allocation costs with `IsEnabled` or MEL source-generated logging. Serilog's generic overloads cover 1–3 arguments; MEL `params` calls and Serilog 4+ arguments may allocate even when disabled.

Example: `_logger.Error(exception, "Payout failed for {LoanId}", loanId)`.
Implementation and level examples: `.claude/skills/logging/guide.md`.
