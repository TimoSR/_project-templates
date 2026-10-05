---
paths:
  - "API/FF-API/FF.Api/Controllers/**/*.cs"
  - "API/FF-API/FF.Api/Features/**/API/REST/**/*.cs"
  - "API/FF-API/FF.Api/Features/**/_DTO/**/*.cs"
  - "**/*openapi*.{json,yaml,yml}"
  - "**/api.spec.json"
---

# REST contracts

Applies to REST endpoints and their DTOs, not GraphQL operations. New contracts follow the standard; published routes retain compatibility. Detailed choices/examples: `.claude/skills/api-design/guide.md` and `reference.md`.

- Plural resource nouns, kebab-case paths, business IDs as strings, camelCase JSON/query fields. Nest only dependent resources, at most three levels.
- GET reads; POST creates; PUT replaces; PATCH updates editable fields; DELETE removes. Read-only status transitions use named POST actions (`POST /factorings/{loanNumber}/cancel`).
- Create: 201 + Location + created resource. Read/update: 200 + resource. Delete: 204. Work finishing later: 202 + operation.
- Validation: 400; unauthenticated: 401; forbidden: 403; missing/non-owned: 404; state conflict: 409; stale ETag: 412; throttled: 429 + Retry-After; unexpected bug: generic 500.
- Use RFC 9457 ProblemDetails, never 200 with `success: false` or leaked stack/exception details. Declare response codes for NSwag.
- Bound/paginate lists: default `pageSize` + `pageToken` → `nextPageToken`; preserve published offset contracts. Filters/sorts are query parameters.
- Creation/money-moving POSTs use idempotency keys. Under the existing house PATCH convention, absent/null means unchanged; clearing must be explicit.
- Published means under `external-api`, in the external NSwag group, or consumed by Web. Inspect Web and the API specification before changing an existing contract.
- Do not rename/remove/reshape published fields or routes in place. Breaking changes need a new route/major version within the requested scope; deprecation is deliberate.
- Default REST level 2, no HAL. Add hypermedia only for a demonstrated client requirement.

Example: new `POST /investments` → 201 + Location; existing published `/investments/new` is flagged, not silently renamed.
