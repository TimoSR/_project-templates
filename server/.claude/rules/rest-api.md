---
paths:
  - "src/features/**/api/REST/**"
  - "src/features/**/_dto/**"
  - "**/*openapi*.{json,yaml,yml}"
---

# REST contracts

Applies to REST endpoints in a module's `api/REST/` and their request/response types in `_dto/`, not GraphQL operations or event handlers. New contracts follow the standard; published routes retain compatibility. Detailed choices/examples: `.claude/skills/api-design/SKILL.md` and `reference.md` (their `external-api`, NSwag and `Web/` specifics are FlexFunding's).

- Plural resource nouns, kebab-case paths, business IDs as strings, camelCase JSON/query fields. Nest only dependent resources, at most three levels.
- GET reads; POST creates; PUT replaces; PATCH updates editable fields; DELETE removes. Status transitions use named POST actions (`POST /invoices/{invoiceNumber}/cancel`).
- Create: 201 + Location + created resource. Read/update: 200 + resource. Delete: 204. Work finishing later: 202 + operation.
- Validate the `_dto/` request before it reaches `application/`: 400. Unauthenticated: 401; forbidden: 403; missing/non-owned: 404; state conflict: 409; stale ETag: 412; throttled: 429 + Retry-After; unexpected bug: generic 500.
- Use RFC 9457 ProblemDetails, never 200 with `success: false` or leaked stack/exception details. Declare every response code so the OpenAPI spec publishes it.
- Bound/paginate lists: default `pageSize` + `pageToken` → `nextPageToken`. Filters/sorts are query parameters.
- Creation/money-moving POSTs use idempotency keys. PATCH: absent/null means unchanged; clearing must be explicit.
- Published means a client outside the module calls it (another service, a frontend, a partner). Find its consumers and check the OpenAPI spec before changing an existing contract.
- Do not rename/remove/reshape published fields or routes in place. Breaking changes need a new route/major version within the requested scope; deprecation is deliberate.
- Default REST level 2, no HAL. Add hypermedia only for a demonstrated client requirement.

Example: new `POST /invoices` → 201 + Location; an existing published `/invoices/new` is flagged, not silently renamed.
