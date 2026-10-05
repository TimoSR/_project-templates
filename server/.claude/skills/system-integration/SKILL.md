---
name: system-integration
description: Connects systems over the wire - picks the transport (REST, GraphQL, gRPC, polling, SSE, WebSockets, webhooks, TCP vs UDP), the queue or broker (Redis Pub/Sub and Streams, RabbitMQ, Kafka, Azure Service Bus), data formats and encodings (JSON, CSV, XML, Protobuf, Base64, ISO 8601), and vendor adapters (Stripe, Twilio, HubSpot, AIIA, KYC), plus Redis caching, scheduled jobs and blob storage. Use when wiring a feature to another system or vendor, pushing live updates to clients, receiving or verifying webhooks, picking a broker, parsing or serializing data, handling uploads, dates or time zones, scheduling jobs, or fixing CORS errors. Covers a module's integration/ folder (Hubspot, Twilio), infrastructure/ cache and _tools/docker. Not for service boundaries, sagas, the outbox or CQRS (microservices-patterns), or for designing our own REST endpoints (api-design).
---

# System Integration

Source: the user's KEA *System Integration* course notes, corrected against current docs and mapped to this repo.

Boundaries:
* This skill: the wire. Transports, broker choice and delivery mechanics, formats, vendor adapters and their webhooks (inbox dedupe).
* `microservices-patterns`: consistency between our own services or modules. Sagas, the transactional outbox, idempotent consumers of our events, CQRS views, gateways.
* `api-design`: the shape of our own REST endpoints once REST is chosen (routes, status codes, pagination, versioning, OpenAPI contract).

## The one idea

Every integration couples two systems in time, in format, or both. Pick the loosest coupling the requirement needs, and name what it costs.

```
Tight ───────────────────────────────────────────────────────────────────────▶ Loose
sync HTTP call         webhook               queue                  event stream
caller waits;          receiver must be up;  message waits for      message kept; any number of
both must be up        sender retries        ONE consumer           consumer groups; replay
```

* Integration is mostly waiting: who waits (caller, broker, receiver), where the message waits, and for how long.
* Before picking anything, ask: *how stale may the receiver's copy be?*

| Freshness | Delay | Example | Default |
|---|---|---|---|
| Real-time | < 2 s | chat, multiplayer, live cursors | WebSockets (SignalR), SSE, WebRTC |
| Near real-time | 2–10 s | order status, notifications | SSE, webhook, long polling |
| Periodic | minutes | office dashboard with the subscriber count | short polling every few minutes |
| Batch | hours | nightly export, reports | cron or timer → queue |

## Defaults: take the left side until a named force pushes you right

| Decision | Default | Step up to | Only when |
|---|---|---|---|
| Client ↔ our API | REST + JSON + OpenAPI | GraphQL | many clients need different shapes of the same data and keep waiting on new endpoints |
| Our service → internal service | REST + JSON | gRPC + Protobuf | high call volume or streaming between typed services; no browser involved |
| Server → browser updates | polling | SSE | seconds matter |
| | SSE | WebSockets via SignalR | the client also streams messages: chat, game, collaborative editing |
| Browser ↔ browser audio/video | — | WebRTC | sub-second media; needs STUN/TURN servers |
| Vendor → us | the vendor's webhooks | + a reconciliation poll | events can be lost, or the vendor has no webhooks |
| Work that can finish later | `BackgroundService` in process | durable queue | it must survive restarts, spread over instances, or absorb spikes |
| One event, many consumers | topic with one subscription per consumer | event stream (Kafka, Redis Streams) | consumers join later and need replay, or volume is high |
| Payload | JSON, UTF-8 | Protobuf or MessagePack | measured size or parse time hurts |
| Time | UTC instant, ISO 8601 | local time + IANA zone id | a future local appointment ("09:00 in Copenhagen") |
| Transport | TCP (through HTTP) | UDP | a late packet is worthless: game state, voice, video |
| Scheduled job | in-process scheduler on one elected instance (repo: Quartz + `ActiveAppInstanceCoordinator`) | — | never ungated in-process cron on a scaled-out app |
| Auth | managed provider + JWT validation | — | never roll your own |

* On every recommendation, name the side of the trade-off you took: Speed vs Simplicity, Latency vs Coupling, Lossless vs Lossy, Compression vs Time.

## Workflow

1. **Data.** What crosses the boundary: shape, size, format, owner. Is it a command (do this), a query (tell me) or an event (this happened)?
2. **Freshness.** Place it in the table above.
3. **Direction and fan-out.** Who starts the exchange, how many receivers there are, and whether a receiver needs history.
4. **Pick** from the defaults. Write down what you rejected and why.
5. **Failure.** The other side is down, slow, or sends the same thing twice: timeout, retry with backoff, idempotency key, dead-letter queue, reconciliation.
6. **Contract.** OpenAPI for HTTP, a versioned envelope for events, real sample payloads as test fixtures.
7. **Place it** in the repo (below).

Depth: [transports.md](references/transports.md) (HTTP API styles, polling, SSE, WebSockets, WebRTC, TCP/UDP, CORS, API coupling) · [messaging.md](references/messaging.md) (queues, streams, brokers, delivery guarantees, event-driven architecture) · [data-formats.md](references/data-formats.md) (formats, encoding, dates, hashing vs encryption, uploads, media) · [third-parties.md](references/third-parties.md) (vendor adapters, webhooks, auth, SMS, email, payments, scraping, Redis, scheduling, Azure, documentation, local config).

## Symptom → fix

Sections: **T** = transports, **M** = messaging, **D** = data-formats, **V** = third-parties.

| Symptom | Fix | Depth |
|---|---|---|
| Client calls `GET /orders/9` every second | SSE stream for that order; a webhook if the client is a server | T §3 |
| SSE works, but after a deploy clients never reconnect | a non-200 response or wrong `Content-Type` stops `EventSource` for good | T §3 |
| WebSocket clients go silent after a Wi-Fi drop | heartbeat + reconnect with backoff, or SignalR | T §3 |
| Pushes only reach clients connected to one instance | backplane: Redis Pub/Sub, Azure SignalR Service, or Hot Chocolate Redis subscriptions | T §3 |
| CORS error in the browser, Postman works | allow the origin in the API's CORS policy; CORS is enforced by browsers only | T §6 |
| A vendor API change breaks the domain | one adapter per vendor (`FF.App/Twilio/`, a feature's `Integration/`) maps their types to ours | V §1 |
| Webhook handler charged a card twice | dedupe on the event id, in the same transaction as the effect | V §2 |
| Vendor marks our webhook endpoint as failing | return 2xx within seconds, process from a queue | V §2 |
| Anyone can POST to our webhook URL | verify the HMAC signature over the raw body | V §2 |
| Subscriber missed Redis Pub/Sub messages during a deploy | Redis Streams or a durable queue | M §4 |
| Redis memory grows although every entry gets `XACK` | `XACK` doesn't delete entries; trim with `MAXLEN` | M §5 |
| Nightly job ran three times | three instances each ran their in-process cron: one scheduler or a lock | V §7 |
| Times shift by an hour twice a year | store UTC instants; convert at the edge with an IANA zone | D §5 |
| `æøå` shows as `Ã¦Ã¸Ã¥` | UTF-8 bytes decoded as Latin-1: declare `charset=utf-8` | D §3 |
| Upload saved as `..\..\appsettings.json` | never use the client's file name; generate one and check magic bytes | D §7 |
| Large integer ids change in the browser | JavaScript numbers lose precision above 2⁵³: send ids as strings | D §1 |
| Scraper returns 0 items after a site redesign | selectors in config, fixture HTML in tests, alert on an empty result | V §5 |

## Proposal format

```
Interaction    Billing → customer browser: invoice status changes
Freshness      near real-time (< 5 s)
Choice         SSE  GET /v1/invoices/{invoiceId}/events
Rejected       WebSockets: the client never sends; polling every 5 s × 2,000 open tabs = 400 req/s
Failure        on reconnect the browser sends Last-Event-ID; the server replays from the invoice_events table
Trade-off      latency over simplicity: one open connection per tab
```

* Close with what you deliberately left out, for example "no broker yet, `BackgroundService` is enough".

## This repo (C#)

```
API/FF-API/
├── FF.Api/Controllers/{Vendor}/            webhook receivers: Aiia/, Stripe/, Kyc/ (GetId, ZingSec); HubSpot/ (OAuth callback)
├── FF.Api/Subscriptions/                   GraphQL subscriptions (Hot Chocolate)
├── FF.App/{Vendor}/, FF.App/Services/{Vendor}/   outbound adapters: Twilio/, Bank/ (AIIA), Kyc/, Services/HubSpot/, Services/DanskeBank/, Services/Biq/
├── FF.App/Services/ProcessingQueue/        DB-backed work queue: ProcessingQueueEntry rows, polled by QueueProcessorService<T>
├── FF.App/Services/Coordination/           ActiveAppInstanceCoordinator: only one instance runs hosted services
├── FF.Api/Features/{Name}Feature/Integration/   a feature module's own vendor adapters (FactoringHubSpot*)
└── FF.Api/appsettings.json + ConfigSettings.cs  config classes per vendor (TwilioConfig, AiiaConfig); secrets from Key Vault
```

* House rules win over the notes: explicit namespace aliases (`using http = System.Net.Http;`), config objects at the top, units in names (`timeoutSeconds`), guard clauses, and no exceptions in the domain. The adapter catches vendor exceptions and returns a result.
* What the repo uses, and what to add only when the defaults table says so:

| Need | Repo today | Add when needed |
|---|---|---|
| Client ↔ our API | GraphQL, Hot Chocolate 15 (`HotChocolate.Fetching` for DataLoader); REST controllers for webhooks and feature modules | — |
| Server → browser updates | GraphQL subscriptions over WebSocket (`graphql-ws`), `AddInMemorySubscriptions()`: a push reaches only clients on the instance that raised it | Redis subscription backplane before scaling out; SSE: `TypedResults.ServerSentEvents` |
| Outbound HTTP | RestSharp `*ServiceAgent` classes (AIIA, Biq, Danske Bank, GetId, ZingSec); typed `AddHttpClient<T>` (Twilio); no retry or circuit-breaker package | `Microsoft.Extensions.Http.Resilience` |
| Work that can finish later | MediatR notification → `ProcessingQueueEntry` row → `QueueProcessorService<T>` polls every 10 s; no broker | `Azure.Messaging.ServiceBus`, `RabbitMQ.Client` or `Confluent.Kafka`; MassTransit on top |
| Redis | `IDistributedCache` via `AddStackExchangeRedisCache` (in-memory fallback without a `Redis` connection string); `IConnectionMultiplexer` for coordination | — |
| Scheduling | Quartz (`Ftb/Batch/BatchRunnerHostedService`), on the active instance only | — |
| Auth | Firebase, Criipto and Signicat sign in; the API issues its own JWT and validates it with `AddJwtBearer` | — |
| SMS, email, payments | Twilio (`FF.App/Twilio/`); email through HubSpot (`HubSpotEmailClient : IEmailSender`); Stripe.net | — |
| Files | Azure Blob Storage (`FF.App/Services/Files/`); SFTP via SSH.NET | — |
| Formats | `System.Text.Json` and Newtonsoft.Json, `CsvHelper` | `System.Xml.Linq`, `YamlDotNet`, `Google.Protobuf`, `Grpc.AspNetCore` |
| OpenAPI | NSwag: `AddOpenApiDocument()`, `UseOpenApi()`, `UseSwaggerUi()` | — |
| Scraping | none | `AngleSharp` (static HTML), `Microsoft.Playwright` (JavaScript-rendered pages) |
