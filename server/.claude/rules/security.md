---
paths:
  - "src/**/*.cs"
  - "src/_config/**"
---

# Backend security

New code meets these standards. Preserve existing protection schemes when narrowly editing code; flag gaps and do not silently migrate stored data. Recipes: `.claude/skills/security/SKILL.md` and `sensitive-data-protector.md` (their `FF.*` paths and Ftb/Hot Chocolate traps are FlexFunding's).

- Validate and bound `_dto/` request fields before `application/` runs: type, requiredness, length, range, format, enum, list count, and request cost. Parse raw values into `domain/value-objects/` types. Reject unknown REST request fields.
- Inputs contain only caller-owned choices. Ownership, tenant, audit fields, and server-controlled transitions come from trusted context or server logic.
- Authenticate, name an appropriate authorization policy, and fail closed without context. Anonymous endpoints require an explicit reason. Do not put a secured action under a controller marked `[AllowAnonymous]`.
- Scope every row read/write inside the query to the caller's trusted owner context. Check the stored row on writes. Non-owned rows get the same response as missing rows.
- Protect new sensitive values at entry: hash for verification, keyed lookup hash for searching, authenticated encryption for values that must be recovered, and masks for display. Plaintext exists only at the input boundary and the `integration/` adapter that needs it.
- No plaintext PII/tokens/secrets in commands, `domain/events/`, outbox payloads, logs, exceptions, cache keys, or URLs. Secrets come from a secret store or git-ignored local config, never tracked files under `src/_config/`; compare secrets in constant time.
- Output is an audience-specific allowlist, projected in the query; do not expose whole entities. Apply the same restriction to exports, caches, and third-party syncs.
- For sensitive GraphQL properties in `api/GraphQL/`, hide output, filter, and sort exposure explicitly; field authorization alone is insufficient. Prove absence with a schema test.
- Write policies admit writer roles only; read-only roles cannot write. Ordinary GET/GraphQL reads have no business writes or emitted business events; privileged full-value reads may write their required access audit.
- Facts are append-only; corrections are new records referencing originals. Do not introduce public setters or update/delete paths for immutable facts.
- Test owner isolation and read-only denial for affected endpoints. Do not weaken existing protection to make a test pass.
- Isolation is application-level by default. Tenant columns, RLS, and database roles are target architecture; introducing them requires explicit task scope.

Example: caller A requests B's invoice → no row returned, no sensitive fields, no state change.
