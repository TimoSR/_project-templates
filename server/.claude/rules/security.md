---
paths:
  - "API/**/*.cs"
---

# Backend security

New code meets these standards. Preserve existing protection schemes when narrowly editing legacy code; flag gaps and do not silently migrate stored data. Recipe and framework details: `.claude/skills/security/guide.md`.

- Validate and bound request fields before executing services/commands: type, requiredness, length, range, format, enum, list count, and request cost. Parse raw values into valid domain types. Reject unknown REST request fields.
- Inputs contain only caller-owned choices. Ownership, partner, audit fields, and server-controlled transitions come from trusted context or server logic.
- Authenticate, name an appropriate authorization policy, and fail closed without context. Anonymous endpoints require an explicit reason. Do not put a secured action under a controller marked `[AllowAnonymous]`.
- Scope every row read/write inside the query to the caller's trusted owner/partner context. Check the stored row on writes. Non-owned rows get the same response as missing rows.
- Protect new sensitive values at entry: hash for verification, keyed lookup hash for searching, authenticated encryption for values that must be recovered, and masks for display. Plaintext exists only at the input boundary and the outbound adapter that needs it.
- No plaintext PII/tokens/secrets in commands, events, outbox payloads, logs, exceptions, cache keys, or URLs. Keys come from the existing key-vault abstraction; compare secrets in constant time.
- Output is an audience-specific allowlist, projected in the query; do not expose whole entities. Apply the same restriction to exports, caches, and third-party syncs.
- For sensitive GraphQL properties, hide output, filter, and sort exposure explicitly. `[FtbDoNotExpose]` and field authorization alone are insufficient; prove absence with a schema test.
- Write policies admit writer roles only. `ReadOnly` and `Viewer` cannot write. Ordinary GET/GraphQL reads have no business writes or emitted business events; privileged full-value reads may write their required access audit.
- Facts are append-only; corrections are new records referencing originals. Do not introduce public setters or generated update/delete paths for immutable facts. Preserve documented processing-state exceptions.
- Test owner/partner isolation and read-only denial for affected endpoints. Do not weaken existing protection to make a test pass.
- Current isolation is application-level. Tenant columns, RLS, and database roles are target architecture; introducing them requires explicit task scope.

Example: caller A requests B's loan → no row returned, no sensitive fields, no state change.
