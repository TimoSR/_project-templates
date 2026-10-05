---
name: api-design
description: Applies the house HTTP/REST API design standard (Google AIP, Zalando guidelines) - resource-oriented URLs, standard and custom methods, status codes, Problem Details errors, JSON field naming, cursor pagination, filtering, idempotency keys, ETags, long-running operations, backward compatibility and versioning, HAL/HATEOAS links, and the OpenAPI contract. Use when adding, renaming or reviewing a REST controller, route, action, request or response DTO, list endpoint, error response or OpenAPI spec, when deciding PUT vs PATCH, 200 vs 201 vs 204, 400 vs 409, or whether a change breaks clients. Also when the user mentions REST, endpoints, resource naming, HATEOAS, HAL, ProblemDetails, RFC 9457, pagination tokens, Idempotency-Key, API versioning or deprecation. Covers a module's api/ folder and _dto/ request and response types. Not for picking REST vs GraphQL vs gRPC, webhooks, file uploads or media streaming (system-integration), or for authorization and input sanitizing (security).
---

# API Design

An API is a contract that outlives its code: clients are built against the URLs, fields and status codes, so a careless name costs a breaking change later. Rules come from Google's [AIP](https://google.aip.dev/general) and [Zalando's guidelines](https://opensource.zalando.com/restful-api-guidelines/). Where they disagree, the house pick below wins. Files, uploads, Base64 and media: `system-integration`. Database pagination queries: `database-design`.

## Scope: new endpoints follow the standard, published ones get flagged

* New route, action or DTO → follow this skill.
* A route is **published** if a client outside the module calls it: another service, a frontend or a partner. Check the committed OpenAPI spec and grep the callers before deciding. Unpublished routes can be fixed in place, together with their tests.
* Changing a published route → never rename or reshape it in place. That's a breaking change. Name the gap in your reply, and add the correct route next to the old one only if asked (see [Compatibility](#compatibility-dont-break-clients)).

```
Note: GET /api/invoices/all has a verb-like segment; the standard form is GET /api/invoices (api-design).
Not changed here: the route is public.
```

## House picks where the sources disagree

| Topic | Google AIP | Zalando | **House pick** | Why |
|---|---|---|---|---|
| JSON field case | `lowerCamelCase` | `snake_case` | `camelCase` | the ASP.NET default and what JavaScript clients expect |
| Query parameter case | `camelCase` | `snake_case` | `camelCase` | same case as the JSON body |
| Versioning | major version in the path `/v1/` | media type, never the URL | don't break; if you must, a new major path `/v2/...` | visible in routes, logs and OpenAPI documents; matches `system-integration` |
| Pagination | `pageToken` → `nextPageToken` | cursor + `next` link | `pageSize` + `pageToken` → `nextPageToken` | keyset speed on every page (`database-design`); no URL building |
| Actions and state | custom method `POST /books/1:archive`; state fields are output-only (AIP-216) | turn the action into a resource | an editable field = `PATCH`; a status is read-only and changes only through `POST /{resource}/{id}/{verb}` | each transition gets its own name, rules, side effects and error; `/` needs no special routing, while `:` collides with ASP.NET route syntax |
| Errors | `google.rpc.Status` | Problem JSON (RFC 9457) | RFC 9457 `ProblemDetails` | built into ASP.NET (`AddProblemDetails()`) |
| Hypermedia | none | REST level 2, links for paging | level 2, no HAL | known clients generated from OpenAPI; nobody follows links. HAL only for a public API with unknown clients ([reference](reference.md#9-hypermedia-hateoas-and-hal)) |

## URLs: nouns in a tree

```
/api/customers/{customerNumber}/invoices/{invoiceNumber}
 └ base └ collection └ id          └ sub-collection └ id
```

* Plural nouns, kebab-case: `/sales-orders`, not `/salesOrder` or `/sales_order`.
* Ids are business keys as strings (`invoiceNumber`, `customerNumber`), never the database `int` primary key: that leaks row counts and invites id guessing.
* At most 3 levels of nesting. Nest only when the child can't exist without the parent.
* No verbs, and no list modifiers in the path. Filters are query parameters.

| ✗ | ✓ |
|---|---|
| `POST /api/invoices/new` | `POST /api/invoices` |
| `GET /api/invoices/all` | `GET /api/invoices` |
| `GET /api/invoices/list/{customerNumber}` | `GET /api/customers/{customerNumber}/invoices` |
| `GET /api/invoices/currently-open` | `GET /api/invoices?status=...` |
| `PUT /invoice/{invoiceNumber}/status?status=Cancelled` | `POST /invoices/{invoiceNumber}/cancel` (the status is read-only; the domain checks the transition) |
| `POST /invoice/copy-legacy` | `POST /invoices/copy-legacy` (an action on the collection) |

## Methods and status codes

| Operation | Method + route | Success | Body |
|---|---|---|---|
| List | `GET /invoices?pageSize=50&pageToken=…` | `200` | `{ "items": [...], "nextPageToken": "…" }` |
| Get | `GET /invoices/{invoiceNumber}` | `200` | the resource |
| Create | `POST /invoices` | `201` + `Location: /invoices/{invoiceNumber}` | the created resource |
| Replace | `PUT /invoices/{invoiceNumber}` | `200` | the resource |
| Partial update | `PATCH /invoices/{invoiceNumber}` | `200` | the resource |
| Delete | `DELETE /invoices/{invoiceNumber}` | `204` | none |
| Status transition, or an action with its own rules | `POST /invoices/{invoiceNumber}/cancel` | `200`, or `202` if it finishes later | the resource, or an operation |
| Action on the whole collection | `POST /invoices/copy-legacy` | `200` or `202` | a result object |

* `GET`, `PUT` and `DELETE` are idempotent: repeating them leaves the same state. A repeated `DELETE` returns `204` again or `404`, and both are fine.
* `POST` that creates or moves money takes an `Idempotency-Key` header ([reference](reference.md#6-idempotency-keys)).
* `PATCH`: absent and `null` both mean "unchanged" (Zalando #123). Clearing a field needs an explicit value, never a meaning given to `null`.

| Failure | Code |
|---|---|
| Malformed or invalid request DTO, query parameter or path id (missing field, bad format, `invoiceNumber` that fails `InvoiceNumber.TryCreate`) | `400` + `ValidationProblemDetails` |
| No or bad credentials | `401` |
| Authenticated, but not allowed | `403` |
| Doesn't exist, **or exists but belongs to someone else** | `404`, so ids can't be probed |
| Valid request, but the current state forbids it (duplicate, illegal status transition) | `409` |
| `If-Match` ETag is stale | `412` |
| Rate limited | `429` + `Retry-After` |
| Bug | `500`: no stack trace, no exception message |

* Only the codes above (Zalando #150). No `200` with `{ "success": false }`.

## Errors: one shape, RFC 9457

```json
{
  "type": "/problems/invoice-exists",
  "title": "Invoice already exists",
  "status": 409,
  "detail": "Order 10432 already has an invoice.",
  "instance": "/invoices"
}
```

* `type` is the stable, machine-readable kind: clients branch on it, never on `title` or `detail` text.
* `detail` is for a human and differs per occurrence. Never put a stack trace, SQL or an internal id in it.
* Validation failures add `"errors": { "orderNumber": ["The OrderNumber field is required."] }`, which `[ApiController]` produces automatically.

## JSON payloads

* The top level is always an object, never a bare array: an object can gain `nextPageToken` later without breaking clients (Zalando #110).

```
✗ [ {...}, {...} ]
✓ { "items": [ {...}, {...} ], "nextPageToken": "eyJ..." }
```

* Names are full words, and dates carry the unit: `createdAtUtc`, `amountDkk` or a money object `{ "amount": 1250.00, "currency": "DKK" }` (C# `decimal`, ISO 4217 code). Never `float` for money.
* Timestamps: ISO 8601 in UTC with `Z`, e.g. `"2026-10-05T09:12:00Z"`. Dates without a time: `"2026-10-05"`.
* Enums are strings (`JsonStringEnumConverter`, registered once in `src/program.cs`), never numbers.
* Empty list = `[]`, never `null`. Booleans are never `null`: use an enum if there are three states.
* Arrays have plural names (`payments`), references to other resources end in the key name (`invoiceNumber`, `customerNumber`).
* One DTO per direction and view: `CreateInvoiceRequest`, `InvoiceSummaryResponse` (list), `InvoiceResponse` (detail). Never return an EF entity: every column becomes contract, including `int` keys and foreign keys.

## Pagination

```
GET /invoices?pageSize=50&pageToken=eyJjIjoiMjAyNi0xMC0wMVQwOToxMjowMFoiLCJpIjoiOWYzIn0
200 { "items": [ ...50 items... ], "nextPageToken": "eyJjIjoi..." }
200 { "items": [ ...12 items... ] }                                   ← last page: no nextPageToken
```

* Every list is paginated, with a server-side default (50) and maximum (100) from a config object. Larger `pageSize` values are clamped, not rejected.
* `pageToken` is opaque: base64url of the keyset (`createdAtUtc`, `id`). Clients never parse or build it.
* No total count unless a screen needs it: `COUNT(*)` on every page costs as much as the page.
* Offset paging (`pageIndex`, `pageSize`) only for page-number UIs over small tables.
* Filter and sort as query parameters: `?status=Issued&sort=-createdAtUtc` (`-` = descending).

## Compatibility: don't break clients

| Compatible (ship anytime) | Breaking (needs a new route or major version) |
|---|---|
| Add an endpoint | Remove or rename an endpoint, field or query parameter |
| Add an optional request field or query parameter | Make an optional input required, or add a required one |
| Add a response field | Change a field's type or format (`"12"` → `12`, date → timestamp) |
| Add an enum value to a request | Change a status code or the meaning of a value |
| | Add an enum value to a **response**, unless clients are known to tolerate unknown values |

* Our own clients are tolerant readers: ignore unknown fields, and map an unknown enum value to a fallback.
* Retiring a route: add the new one, mark the old one `[System.Obsolete]` plus `Deprecation` and `Sunset` response headers, and remove it after the sunset date once logs show no callers ([reference](reference.md#8-compatibility-and-deprecation)).

## Workflow

1. **Resources.** List the nouns, their business ids and their parent. Which views does each one need (list summary vs detail)?
2. **Map operations** to the standard methods above. Only what's left becomes a custom `POST /{id}/{verb}`.
3. **Write the contract before the code:** route table, request/response DTOs, every status code. Put it in the reply as below.
4. **Changing an existing route?** Check every change against the compatibility table.
5. **Implement** in house style ([example](#example-in-house-style)). Declare every status code with `[ProducesResponseType]` so the OpenAPI spec publishes it.
6. **Test** each route, including its error codes, as an API test (`tests-as-documentation`).

```
Resource   Invoice (id: invoiceNumber, parent: none)
GET    /invoices?pageSize&pageToken&status   200 { items, nextPageToken }
GET    /invoices/{invoiceNumber}             200 InvoiceResponse · 404
POST   /invoices                             201 InvoiceResponse + Location · 400 · 409 /problems/invoice-exists
POST   /invoices/{invoiceNumber}/issue       200 InvoiceResponse · 400 · 404 · 409 /problems/illegal-status-transition
POST   /invoices/{invoiceNumber}/cancel      200 InvoiceResponse · 400 · 404 · 409 /problems/illegal-status-transition
Rejected   PUT /invoice/{invoiceNumber}/status?status=X: any-to-any status writes in the query string; one route per transition names it and lets the domain check it
```

## Example in house style

```csharp
using mvc = Microsoft.AspNetCore.Mvc;
using tasks = System.Threading.Tasks;

[mvc.HttpPost]
[mvc.ProducesResponseType<InvoiceResponse>(201)]
[mvc.ProducesResponseType<mvc.ValidationProblemDetails>(400)]
[mvc.ProducesResponseType<mvc.ProblemDetails>(409)]
public async tasks.Task<mvc.IActionResult> Create([mvc.FromBody] CreateInvoiceRequest request)
{
    var invoice = await _service.Create(request);
    if (invoice == null)
    {
        return Problem(
            statusCode: 409,
            type: "/problems/invoice-exists",
            title: "Invoice already exists",
            detail: $"Order {request.OrderNumber} already has an invoice.");
    }

    return CreatedAtAction(nameof(Get), new { invoiceNumber = invoice.InvoiceNumber }, invoice);
}
```

* ✗ common mistake: `Ok(invoice)` instead of `201` + `Location`, and a bare `Conflict()` that `[ApiController]` turns into a generic ProblemDetails, with no `type` or `detail` the client can act on.

Depth, read when the task needs it: [reference.md](reference.md): standard and custom methods per AIP, ProblemDetails setup, filtering and partial responses, ETags, idempotency keys, long-running operations, deprecation headers, HAL, the OpenAPI contract, and sources.
