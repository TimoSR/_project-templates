# API Design: Reference

## Contents
1. Standard methods
2. Custom methods
3. Errors: ProblemDetails setup
4. Filtering, sorting, partial responses, embedding
5. Concurrency: ETags
6. Idempotency keys
7. Long-running operations
8. Compatibility and deprecation
9. Hypermedia: HATEOAS and HAL
10. The OpenAPI contract (NSwag)
11. Sources

---

## 1. Standard methods

Google AIP-130 to 135, mapped to HTTP. Five methods cover most of an API. Each new custom method is a sign the resource model may be missing a noun.

| Method | HTTP | Request | Response | Notes |
|---|---|---|---|---|
| List (AIP-132) | `GET /{parent}/loans` | `pageSize`, `pageToken`, filters, `sort` | `{ items, nextPageToken }` | summary view; never unbounded |
| Get (AIP-131) | `GET /loans/{loanNumber}` | — | the resource | detail view |
| Create (AIP-133) | `POST /{parent}/loans` | the resource without server fields | `201` + `Location` + resource | server generates the id unless the business key comes from the client |
| Update (AIP-134) | `PATCH /loans/{loanNumber}` | the fields to change | the full resource | Google uses an `update_mask`; we use "absent = unchanged" |
| Delete (AIP-135) | `DELETE /loans/{loanNumber}` | — | `204` | soft delete (AIP-164): `200` + the resource with `deletedAtUtc` set |

* Read-only fields (`id`, `createdAtUtc`, `status` set by the domain) are ignored or rejected on input. Never trust them from the client.
* A resource uses one schema for reading and writing where possible (Zalando #252). Mark server-only fields `readOnly` in OpenAPI.
* `PUT` replaces the whole resource. Use it only for small resources the client fully owns (settings, preferences). Otherwise `PATCH`.

## 2. Custom methods

For operations that don't fit the five methods (AIP-136). Always `POST` (or `GET` if the operation is safe), on the resource or the collection:

```
POST /loans/{loanNumber}/cancel        an action with its own rules and side effects
POST /loans/{loanNumber}/payouts       ✓ better when the action leaves a record: model it as a sub-resource
POST /loans/search                     a filter too complex or too long for the query string
```

* Decision order:
   1. A field the client may edit freely → `PATCH` the field.
   2. The action creates something that has its own life (a payout, a lock, a transfer) → a sub-resource you `POST` to.
   3. A status transition, or any other action on one resource → `POST /{id}/{verb}`: `POST /factorings/{loanNumber}/fund`. The status field itself stays read-only (AIP-216).
   4. An action on the whole collection → `POST /{collection}/{verb}`: `POST /factorings/copy-legacy`.
* Google writes `:cancel`. We use `/cancel`: in ASP.NET route templates `:` introduces a constraint (`{id:int}`), and proxies and NSwag treat `/` segments uniformly.
* Batch operations return `207 Multi-Status` with one result per item (Zalando #152). Avoid them until a client needs them.

## 3. Errors: ProblemDetails setup

`Startup.cs` doesn't register `AddProblemDetails()` yet. Without it, unhandled exceptions and status-only responses outside `[ApiController]` return an empty body. When touching error handling, register it:

```csharp
services.AddProblemDetails();     // IProblemDetailsService for exceptions and status codes

app.UseExceptionHandler();        // unhandled exception → 500 ProblemDetails, no stack trace outside Development
app.UseStatusCodePages();         // empty 4xx/5xx bodies → ProblemDetails
```

* `[ApiController]` already turns `NotFound()`, `Conflict()` and model-validation failures into ProblemDetails, but with a generic `type` (an RFC link) and no `detail`. Return `Problem(...)` with a specific `type` whenever the client can act on the difference.

```csharp
// ✗ custom error shape: a second contract clients have to parse
return BadRequest(new { error });

// ✓ one shape everywhere
return Problem(
    statusCode: 409,
    type: "/problems/illegal-status-transition",
    title: "Status change not allowed",
    detail: $"Factoring {loanNumber} cannot go from {current} to {requested}.");
```

* Keep the `type` values in one config or constants class, so the list of problem kinds is visible and documented in OpenAPI.
* The domain returns a result (`null`, a tuple, a result type), not an exception. The controller maps it to a status code. Exceptions reach `UseExceptionHandler` only for bugs.

## 4. Filtering, sorting, partial responses, embedding

| Need | Form | Default |
|---|---|---|
| Filter | one query parameter per field: `?status=Funded&createdAfterUtc=2026-01-01T00:00:00Z` | yes |
| Sort | `?sort=-createdAtUtc,loanNumber` (`-` = descending) | only the indexed columns; the server rejects others with `400` |
| Free-text search | `?q=acme` | when a screen has a search box |
| Partial response | `?fields=loanNumber,status` | no: build two views (summary and detail) first |
| Embed related resources | `?expand=borrower` → `"borrower": { ... }` inline | no: only when measured round trips hurt |

* Unknown query parameters are ignored (tolerant reader), but a known parameter with a bad value is `400`.
* Every filter and sort field needs an index (`database-design`). A filter nobody indexed is a slow-query bug waiting.

## 5. Concurrency: ETags

Prevents lost updates when two users edit the same resource:

```
GET   /factorings/10432            → 200   ETag: "AAAAAAAAB9E="
PATCH /factorings/10432            If-Match: "AAAAAAAAB9E="   → 200   ETag: "AAAAAAAAB9I="
PATCH /factorings/10432            If-Match: "AAAAAAAAB9E="   → 412   someone changed it in between
```

* ETag = the EF Core `rowversion` column (`[System.ComponentModel.DataAnnotations.Timestamp]`), base64-encoded. EF raises `DbUpdateConcurrencyException`, which the controller maps to `412`.
* `GET` with `If-None-Match` and an unchanged ETag → `304`, with no body. Cheap caching for polling clients.
* Use only where concurrent edits of the same resource happen (back-office screens). Not by default.

## 6. Idempotency keys

A network timeout on `POST /payouts` leaves the client unsure whether the payout was made. A retry must not pay twice.

```
POST /loans/10432/payouts
Idempotency-Key: 6f1c2a9e-4b7d-4e0a-9c55-2d8f3e1b7a40
{ "amount": 50000.00, "currency": "DKK" }
```

| Case | Server response |
|---|---|
| New key | process, store `(key, userId, requestHash, status, body)`, return the result |
| Same key, same body, finished | replay the stored status and body; do nothing |
| Same key, still processing | `409` |
| Same key, different body | `422` (IETF idempotency-key draft; the one exception to the status list in SKILL.md) |
| Missing key on an endpoint that requires it | `400` |

* Required on every `POST` that moves money or creates something a duplicate would harm. Optional elsewhere.
* Store the key in the same transaction as the effect, with a unique index on `(userId, key)`. Expire keys after 24 hours, from a config value.
* Consuming events or webhooks twice is a different problem: dedupe on the event id (`system-integration`).

## 7. Long-running operations

Work that takes longer than a request should wait (more than a few seconds: reports, bulk imports, external payouts):

```
POST /tax-reports            { "year": 2025 }
202  Location: /tax-reports/7f3a
GET  /tax-reports/7f3a       → { "id": "7f3a", "status": "Running" }
GET  /tax-reports/7f3a       → { "id": "7f3a", "status": "Succeeded", "downloadUrl": "https://…" }
GET  /tax-reports/7f3a       → { "id": "7f3a", "status": "Failed", "problem": { "type": "/problems/...", ... } }
```

* Default: the resource itself carries the `status`. Use a generic `/operations/{id}` resource (Google's LRO pattern) only when many unrelated endpoints share the same async mechanism.
* The client polls with backoff. Pushing the result (SSE, webhook) is `system-integration`.

## 8. Compatibility and deprecation

* Specification version in OpenAPI `info.version` uses semantic versioning (Zalando #116): MAJOR for breaking, MINOR for added endpoints or fields, PATCH for doc fixes. Only MAJOR appears in a URL.
* Retiring a route, in order:
   1. Ship the new route. Both work.
   2. Mark the old action `[System.Obsolete("Use GET /external-api/loans")]` (NSwag marks it `deprecated: true`) and send the headers:

```
Deprecation: @1767225600                          (RFC 9745: deprecated since this Unix time)
Sunset: Thu, 01 Jul 2027 00:00:00 GMT             (RFC 8594: stops working after)
Link: </external-api/loans>; rel="successor-version"
```

   3. Tell partners and watch request logs for the old route.
   4. Remove it after the sunset date, once the logs show no callers.

* A clean break with many changes → `/v2/...` next to `/v1/...` (or next to the unversioned original). Both run until the sunset.

## 9. Hypermedia: HATEOAS and HAL

HATEOAS: the response tells the client what it can do next, as links, so the client follows links instead of building URLs. HAL is the simplest format for it (`application/hal+json`): plain properties plus `_links` and optional `_embedded`.

```json
{
  "loanNumber": "10432",
  "status": "Pending",
  "_links": {
    "self":     { "href": "https://api.flexfunding.com/external-api/loans/10432" },
    "payments": { "href": "https://api.flexfunding.com/external-api/loans/10432/payments" },
    "cancel":   { "href": "https://api.flexfunding.com/external-api/loans/10432/cancel" }
  }
}
```

* Where it earns its cost: links that appear only when the action is allowed. Above, `cancel` is present only while `status` is `Pending`, so the client shows a Cancel button without copying the server's state rules.
* Costs: a bigger payload, every response computes links, and most clients ignore them and hardcode URLs anyway.
* House default: no HAL. Use it for a public API with unknown clients, or a workflow whose allowed actions change with state.
* If used: absolute URIs, links in the JSON body, never in `Link` headers (Zalando #166, #217); standard relation names `self`, `next`, `prev`, `first`, `last`.
* Alternatives with richer controls (JSON-LD, Siren) only if a consumer requires them.

## 10. The OpenAPI contract (NSwag)

* This repo generates the spec with NSwag: `services.AddOpenApiDocument(...)` in `FF.Api/Startup.cs` publishes the `"external"` group, served through Swagger UI and ReDoc (`/redoc`). A snapshot is committed at `FF.Api/Controllers/ExternalApi/api.spec.json`.
* An action appears in the external spec only with `[ApiExplorerSettings(GroupName = "external")]` on the controller.
* The spec is only as good as the attributes:

| Attribute | Publishes |
|---|---|
| `[ProducesResponseType<T>(201)]`, one per status code | every success and error response with its schema |
| `[Required]` and `required` on DTO properties | required vs optional fields |
| `/// <summary>` XML comments | operation and field descriptions |
| `[System.Obsolete]` | `deprecated: true` |
| `ExternalApiSwaggerExamplesOperationProcessor` (`FF.Api/Infrastructure/`) | request/response examples |

* Review the generated spec, not just the code. A route without its error codes in the spec isn't finished.

## 11. Sources

* Google API Design Guide / AIP: https://docs.cloud.google.com/apis/design and https://google.aip.dev/general (AIP-121 resources, 122 names, 131–136 methods, 158 pagination, 180 compatibility, 185 versioning, 193 errors).
* Zalando RESTful API Guidelines: https://opensource.zalando.com/restful-api-guidelines/ (rule numbers cited as `#NNN`).
* Google Cloud blog, RESTful web API design best practices: https://cloud.google.com/blog/products/api-management/restful-web-api-design-best-practices (outside-in design: design for the client's use case first, and break a REST rule when it makes the API simpler to use).
* RFC 9457 Problem Details, RFC 9745 Deprecation header, RFC 8594 Sunset header, IETF draft `draft-ietf-httpapi-idempotency-key-header`.
