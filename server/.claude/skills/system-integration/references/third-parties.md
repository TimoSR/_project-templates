# Third Parties and Operations

Integrating vendors, plus the infrastructure around integrations: Redis, scheduling, Azure, documentation and local config.

## Contents

1. The adapter: one per vendor
2. Receiving webhooks
3. Sending webhooks
4. Auth, SMS, email, payments
5. Scraping and crawling
6. Redis beyond messaging
7. Scheduling: cron, timers, Azure Functions
8. Azure and hosted building blocks
9. Documenting APIs, databases and architecture
10. Local development and config

## 1. The adapter: one per vendor

```
features/billing/payment/
├── application/charge-invoice.cs        calls the gateway with OUR types: invoiceId, amountCents, currency
└── integration/Stripe/
    ├── stripe-payment-gateway.cs        the only code that references Stripe.net
    └── stripe-webhook-verifier.cs       signature check for incoming events
src/_config/infrastructure/stripe.json   base URL, API version, timeouts, secret names
```

* Vendor SDK types never leave `integration/<Vendor>/`. The adapter maps them to our DTOs and value objects (an anti-corruption layer), catches vendor exceptions and returns a result.
* Every outbound call gets a timeout and a circuit breaker: `services.AddHttpClient<HubspotClient>().AddStandardResilienceHandler()`.
* Retry only what is safe to repeat: GETs, or writes carrying an idempotency key (Stripe's `Idempotency-Key` header).
* Respect rate limits: on `429`, wait for `Retry-After`.
* Pin the vendor's API version (`Stripe-Version`, `X-GitHub-Api-Version`) and upgrade on purpose.
* Secrets: config holds the setting's name; the value comes from env vars, user secrets or Key Vault, never git.
* Tests: application tests fake the adapter; adapter tests replay recorded vendor responses (fixtures); one manual run against the vendor's sandbox (Stripe test mode, Twilio test credentials).
* Several features need the same vendor → move the adapter to `src/_libs/`. An API gateway is for inbound traffic, not for wrapping vendors.

## 2. Receiving webhooks

```
Vendor ──POST /v1/webhooks/stripe (raw body + signature header)──▶ api/REST
  1. read the raw body: verify these exact bytes; re-serialized JSON won't match
  2. verify the HMAC signature; reject old timestamps (replay)     → 400/401 on failure
  3. insert the event id into the inbox table; duplicate → 200, stop
  4. return 200 within a few seconds; the vendor retries on timeouts and 5xx
  5. a worker in api/EventHandlers processes the inbox: fetch the current object from the
     vendor API when order matters, then call the use case
```

* Delivery is at-least-once with no ordering guarantee: expect duplicates and `invoice.paid` before `invoice.created`.
* A webhook is often a notification, not the data: treat the payload as a hint and read the current state from the vendor's API.
* Back it up with a periodic reconciliation (list objects changed since the last sync), because deliveries do get lost.

Signature check in house style (GitHub's `X-Hub-Signature-256: sha256=<hex>`):

```csharp
using aspnet = Microsoft.AspNetCore.Http;
using crypto = System.Security.Cryptography;
using io = System.IO;
using text = System.Text;

var githubWebhookConfig = new {
    signatureHeader = "X-Hub-Signature-256",
    signaturePrefix = "sha256=",
    deliveryIdHeader = "X-GitHub-Delivery",
};

var webhookSecret = app.Configuration["Integration:Github:WebhookSecret"]!; // value from env var or Key Vault

bool isValidSignature(byte[] rawBody, string? signature) {
    if (string.IsNullOrEmpty(signature)) return false;

    var hash = crypto.HMACSHA256.HashData(text.Encoding.UTF8.GetBytes(webhookSecret), rawBody);
    var expected = githubWebhookConfig.signaturePrefix + System.Convert.ToHexString(hash).ToLowerInvariant();
    return crypto.CryptographicOperations.FixedTimeEquals( // constant time: no timing leak
        text.Encoding.ASCII.GetBytes(expected),
        text.Encoding.ASCII.GetBytes(signature));
}

app.MapPost("/v1/webhooks/github", async (aspnet.HttpRequest request, WebhookInbox inbox) => {
    using var buffer = new io.MemoryStream();
    await request.Body.CopyToAsync(buffer);
    var rawBody = buffer.ToArray();

    if (!isValidSignature(rawBody, request.Headers[githubWebhookConfig.signatureHeader])) return aspnet.Results.Unauthorized();

    await inbox.addOnce(request.Headers[githubWebhookConfig.deliveryIdHeader].ToString(), rawBody); // INSERT … ON CONFLICT DO NOTHING
    return aspnet.Results.Ok(); // 200 for duplicates too, or the sender keeps retrying
});
```

* Stripe: `Stripe.EventUtility.ConstructEvent(json, signatureHeader, endpointSecret)` checks the signature and a 5-minute timestamp tolerance. It throws on failure, so call it inside the adapter and return a result.
* Local testing: expose localhost with ngrok (§10), or replay events with the vendor's CLI (`stripe listen --forward-to localhost:5000/v1/webhooks/stripe`).

## 3. Sending webhooks

When we are the provider:

```
POST   /v1/webhooks              { "url": "https://partner.example/hooks", "events": ["invoice.paid"] }  → { "id": "wh_3", "secret": "…" }
GET    /v1/webhooks              list the caller's registrations
DELETE /v1/webhooks/{id}         unregister
POST   /v1/webhooks/{id}/ping    send a test event now
```

* Flow: domain event → outbox row → worker POSTs to each matching registration.
* Each delivery carries `X-Event-Id`, `X-Event-Type`, a timestamp and `X-Signature: sha256=<HMAC of timestamp + body>`.
* Timeout 5–10 s; any non-2xx counts as a failure.
* Retry with exponential backoff (1 min, 5 min, 30 min, 2 h, …) for a bounded number of attempts. After repeated failures, disable the registration and notify its owner.
* Log every attempt with status code and duration; let subscribers see their delivery log.
* Accept only HTTPS URLs and block private IP ranges (`10.0.0.0/8`, `127.0.0.1`, `169.254.169.254`): otherwise a registered URL makes our server call internal services (SSRF).
* Document the payloads and the signature scheme in OpenAPI (`webhooks:` section in OpenAPI 3.1).

## 4. Auth, SMS, email, payments

**Auth**

```
browser ──sign in──▶ provider (Supabase, Auth0, Entra ID, Firebase) ──▶ JWT access token
browser ──Authorization: Bearer <jwt>──▶ our API: verify signature (provider's JWKS), iss, aud, exp → read claims
```

* Don't build auth yourself: password storage, resets, MFA, lockout and token rotation are each a security project. Config lives in `src/_config/infrastructure/authentication.json`.
* .NET: `AddAuthentication().AddJwtBearer(options => { options.Authority = …; options.Audience = …; })`.
* Short-lived access tokens + refresh tokens. Don't put data in a token that must take effect immediately (roles revoked now).
* Price at scale differs a lot between providers (per monthly active user vs free tiers): check before committing.
* SSO (OIDC, SAML): one identity across many apps. Cloud IAM (Entra ID, Google Cloud IAM): who may touch infrastructure. These are different from app user auth.
* MFA: use the provider's feature (Auth0 + Twilio for SMS codes) instead of sending codes yourself.

**SMS** (Twilio, Azure Communication Services)

* Phone numbers in E.164: `+4512345678`.
* Send through the REST API; the delivery status arrives later through a status-callback webhook.
* Costs per message and sender-id rules differ per country; add a rate limit per user against abuse.
* One-time codes: prefer the vendor's verify API, or store the code in Redis with an expiry (§6).

**Email** (SendGrid, Azure Communication Services Email, Postmark; or SMTP via MailKit)

* SMTP: port 587 with STARTTLS.
* Deliverability needs SPF, DKIM and DMARC DNS records on the sending domain.
* Bounces and spam complaints arrive by webhook: stop sending to those addresses.
* Send from a queue, never inside the request thread.

**Payments** (Stripe)

* Create the payment server-side with the amount from our database, never from the client.
* Fulfil the order on the `payment_intent.succeeded` webhook, not on the client's redirect: the user may close the tab.
* Idempotency key on every create call; amounts in minor units (`4900` = 49.00 DKK).
* Test mode keys and test card numbers in development.

## 5. Scraping and crawling

* Prefer, in order: an official API → the JSON API the page itself calls (browser DevTools → Network) → RSS or sitemap → scraping HTML.
* Data scraping extracts fields from known pages. Crawling follows links to discover pages:

```
queue = [seedUrl]; visited = HashSet<string>
while queue not empty and pages < maxPages:
    url = dequeue; if visited contains url → skip; add url to visited
    html = fetch(url)   # rate-limited, cached
    extract data; enqueue same-domain <a href> links up to maxDepth
```

* Politeness: honour `robots.txt` and the terms of service (not technically enforced, still legally relevant), about 1 request per second per host, an honest `User-Agent`.
* During development, download pages once and scrape the saved HTML instead of hitting the site on every run.
* Tools:
   * Static HTML: AngleSharp or HtmlAgilityPack (C#), cheerio (Node), BeautifulSoup with the lxml parser (Python).
   * JavaScript-rendered pages: Playwright (`Microsoft.Playwright`), Puppeteer.
* Selectors: target the closest stable class, id or `data-` attribute around the values. Keep selectors in config, keep a fixture HTML file in tests, and alert when a run extracts 0 items: sites change markup without notice.
* Search engines find pages through crawling links, sitemaps, backlinks, direct submission and new domain registrations.
* Proxy services (Bright Data and similar) rotate IP addresses; using them to get around a site's blocks is a legal question, not a technical one.

## 6. Redis beyond messaging

| Use | Commands | Note |
|---|---|---|
| Cache-aside | `GET k` → miss → load from DB → `SET k v EX 300` | `DEL k` on every write to the source |
| Session, one-time code | `SET otp:42 913204 EX 300` | expires by itself |
| Rate limit (fixed window) | `INCR rate:42:202610020945`, then `EXPIRE rate:42:202610020945 60` | count > limit → `429` |
| Distributed lock | `SET lock:nightly-report <token> NX PX 60000` | release only when the value is still your token (Lua: `if GET == token then DEL`) |
| Counter, leaderboard | `INCR`, `ZADD board 1500 ada`, `ZREVRANGE board 0 9 WITHSCORES` | sorted sets keep the order |
| Unique count | `PFADD visitors 10.0.0.7`, `PFCOUNT visitors` | HyperLogLog: ~0.81% error in 12 KB |
| Optimistic transaction | `WATCH k`, `MULTI`, … , `EXEC` | `EXEC` returns nil if `k` changed; no rollback of executed commands |
| Location | `GEOADD shops 12.57 55.68 shop_1` | longitude first |

* Key names: `<feature>:<entity>:<id>` (`billing:invoice:inv_9`). `SELECT <n>` switches between numbered databases.
* `KEYS *` blocks the server while it scans: use `SCAN` outside a laptop. `UNLINK` deletes in the background.
* Persistence: RDB snapshots (compact, may lose minutes) + AOF (logs every write, small overhead). Use both for data you care about.
* Replication: one primary, read replicas, manual failover with `REPLICAOF NO ONE` (Sentinel or a managed service automates it).
* Redis is RAM: keep only data you can rebuild, or that also lives in the database. It sits between the app and the database, shared by all app instances.
* Rate limiting in Redis or at the gateway? The gateway, when the limit spans many services; Redis, when the rule needs app data (per plan, per tenant).
* `redis-cli -h <host> -p <port> -a <password>` connects to a hosted instance; `redis-benchmark` measures throughput.

## 7. Scheduling

```
┌───────── minute (0–59)
│ ┌─────── hour (0–23)
│ │ ┌───── day of month (1–31)
│ │ │ ┌─── month (1–12)
│ │ │ │ ┌─ day of week (0–6, Sunday = 0)
* * * * *     command
*/5 * * * *   every 5 minutes
0 3 * * *     03:00 every day, in the server's zone: run servers in UTC
0 8 * * 1     08:00 every Monday
```

* Azure Functions timers use six fields, seconds first: `0 */5 * * * *` = every 5 minutes.
* Cron is one host's scheduler: time-based only, and adding servers adds no capacity. The trap: an app scaled to 3 instances with an in-process cron runs every job 3 times.

| Option | Runs | Fits |
|---|---|---|
| `crontab` on a VM | once, on that VM | scripts in `_tools/scripts/`: backups, cleanups |
| `BackgroundService` + `PeriodicTimer` | once per instance | in-app work on a single instance |
| Hangfire, Quartz.NET (clustered, DB-backed) | once across instances | self-hosted, needs retries and a dashboard |
| Azure Functions timer trigger, Kubernetes CronJob | once, managed | cloud default |

* Every job must be idempotent and safe to rerun: it will run twice eventually.
* For heavy jobs, the timer only enqueues work; workers do it (messaging.md §6).

## 8. Azure and hosted building blocks

| Need | Service | Note |
|---|---|---|
| Run code on events or a timer without managing servers | Azure Functions | triggers (HTTP, Timer, Blob, Queue, Service Bus) start a function; bindings read and write data without SDK code; use the isolated worker model |
| Files, images, backups | Storage account → Blob | containers; hot, cool and archive tiers; give clients SAS URLs, never the account key |
| SMB file share | Storage account → Files | mount from Windows, Linux, macOS |
| Simple key-value table | Storage account → Table | cheap NoSQL |
| Simple queue | Storage account → Queue | 64 KB messages; Service Bus for topics, sessions, dead-letters |
| Container images | Container Registry (ACR) | `docker build -t myregistry.azurecr.io/billing:1.4.0 .`, `docker push …`; Container Apps or AKS pull with a managed identity |
| A full machine | Virtual Machines | you patch the OS and secure the network (network security groups); prefer managed services |
| Hosted databases | Azure Database for PostgreSQL, Supabase, Redis Cloud | connection string from config, TLS on, network allow-list, backups and point-in-time restore depend on the tier |

```csharp
// Isolated worker model: a function that runs when a blob lands in "uploads"
[Microsoft.Azure.Functions.Worker.Function("resizeUploadedImage")]
public static void resizeUploadedImage(
    [Microsoft.Azure.Functions.Worker.BlobTrigger("uploads/{name}")] System.IO.Stream image,
    string name) { … }
```

* Infrastructure as code lives in `_tools/terraform/`.
* Cheap static hosting for frontends: Azure Storage static website, S3, GitHub Pages, behind a CDN.

## 9. Documenting APIs, databases and architecture

**OpenAPI**

* Describes paths, parameters, request and response schemas, status codes and auth, in YAML or JSON. From it come docs, generated clients (NSwag, Kiota, openapi-generator) and contract tests.
* .NET 9+: `builder.Services.AddOpenApi(); app.MapOpenApi();` serves `/openapi/v1.json`. Add Scalar or Swagger UI to browse it. Express: swagger-jsdoc; FastAPI: built in at `/docs`.
* Commit the generated document and diff it in CI: a removed field is a breaking change.

**Databases**

* A data dictionary per table: column, type, meaning, example, owner. Keep it next to the data:

```sql
COMMENT ON COLUMN invoice.amount_cents IS 'Total including VAT, in minor units of invoice.currency';
```

* An ER diagram generated from the schema, and migrations in git as the schema's history.
* Access per consumer: one role per consumer with least privilege (`GRANT SELECT ON invoice TO reporting;`), and views or column grants to hide personal data.
* Backups:
   * `pg_dump -Fc billing > billing.dump` (Postgres), `mysqldump --single-transaction billing > billing.sql` (MySQL).
   * Full, incremental (changes since the last backup) or differential (changes since the last full), chosen by how much data you can afford to lose.
   * Scheduled (cron, §7), stored off-site: 3 copies, 2 media, 1 off-site.
   * A backup counts only after a test restore.

**Architecture diagrams**

* Keep the source in the repo so it diffs: draw.io (`.drawio`), Excalidraw (`.excalidraw`) or Mermaid in Markdown. Lucidchart and Visio when the team already uses them.
* One diagram per question: system context, containers, one flow. Label every arrow with the transport and whether it's sync or async: `Billing ──(Service Bus topic, async)──▶ Email`.

## 10. Local development and config

* Environment variables have levels:
   * OS (machine or user): visible to every process.
   * Process: `export Billing__Stripe__ApiKey=…` (bash) or `$env:Billing__Stripe__ApiKey='…'` (PowerShell) lives in that shell and its children only.
   * Runtime config: .NET layers `appsettings.json` → `appsettings.{Environment}.json` → user secrets (Development) → environment variables → command line; the later source wins. `Billing__Stripe__ApiKey` maps to `Billing:Stripe:ApiKey`.
   * Node reads `process.env` (dotenv for `.env` files); Python reads `os.environ` (python-dotenv).
* Defaults first, overridden per environment (`src/_config/config_guidelines.md`). Secrets: `dotnet user-secrets set "Billing:Stripe:ApiKey" "…"` locally, Key Vault in Azure.
* Receive webhooks on a laptop: `ngrok http 5000` (or `devtunnel host -p 5000`) gives a public HTTPS URL that forwards to localhost. Free ngrok URLs change per session, so re-register the webhook each time.
* Local dependencies (Redis, RabbitMQ, Postgres) run from `_tools/docker/` with Docker Compose.
