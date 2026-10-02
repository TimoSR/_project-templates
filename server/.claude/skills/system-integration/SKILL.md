---
name: system-integration
description: Connects systems over the wire - choosing the transport (REST, GraphQL, gRPC, polling, long polling, server-sent events, WebSockets, SignalR or Socket.IO, WebRTC, webhooks, TCP vs UDP), the messaging style (sync vs async, queue vs event stream, Redis Pub/Sub and Streams, RabbitMQ, Kafka, Azure Service Bus), data formats and encodings (JSON, CSV, XML, YAML, Protobuf, UTF-8, Base64, ISO 8601 dates, multipart uploads), and third-party integrations (auth and JWT, SMS, email, payments, scraping), plus Redis caching, cron and Azure Functions, blob storage and OpenAPI docs. Use when wiring a feature to another system or vendor, pushing live updates to clients, sending or receiving webhooks, picking a broker, parsing or serializing data, handling uploads, dates or time zones, scheduling jobs, or when the user mentions CORS, low coupling, real-time updates or the update problem.
---

# System Integration

Source: the user's *System Integration* course notes (KEA), checked against current docs and mapped to this repo. Where the notes were wrong or outdated, this skill has the corrected version. Boundaries between our own services (sagas, outbox, CQRS, gateways) belong to `microservices-patterns`. This skill covers the wire: transports, brokers, formats and third parties.

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
| Scheduled job | one timer trigger in one place | — | never in-process cron on a scaled-out app |
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
| Pushes only reach clients connected to one instance | backplane: Redis Pub/Sub or Azure SignalR Service | T §3 |
| CORS error in the browser, Postman works | allow the origin in the API's CORS policy; CORS is enforced by browsers only | T §6 |
| A vendor API change breaks the domain | adapter in `integration/<Vendor>/` maps their types to ours | V §1 |
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
features/<feature>/<module>/
├── _dto/                    rejects malformed bodies, webhook payloads and upload metadata before the domain
├── api/REST/                endpoints, SSE streams, webhook receivers, uploads, OpenAPI metadata
├── api/GraphQL/             schema, resolvers, subscriptions
├── api/EventHandlers/       queue and stream consumers, webhook processors; all idempotent
├── infrastructure/cache/    Redis: cache-aside, rate limits, locks, one-time codes
└── integration/<Vendor>/    one adapter per vendor (Hubspot/, Twillio/): HTTP client, auth, signature check, mapping
src/_config/infrastructure/  base URLs, timeouts, broker and Redis connections, secret names (values in env vars or Key Vault)
_tools/docker/               local Redis, RabbitMQ, Postgres
_tools/scripts/              backups, cron entries
_tools/terraform/            Azure storage account, container registry, Functions, Service Bus
```

* House rules win over the notes: explicit namespace aliases (`using http = System.Net.Http;`), config objects at the top, units in names (`timeoutSeconds`), guard clauses, and no exceptions in the domain. The adapter catches vendor exceptions and returns a result.
* .NET picks:

| Need | Package |
|---|---|
| Outbound HTTP with timeout, retry, circuit breaker | `IHttpClientFactory` + `Microsoft.Extensions.Http.Resilience` |
| SSE | `TypedResults.ServerSentEvents` (.NET 10+) |
| WebSockets with reconnect, groups and scale-out | SignalR (+ Redis backplane or Azure SignalR Service) |
| gRPC | `Grpc.AspNetCore` |
| GraphQL | Hot Chocolate (server), StrawberryShake (client) |
| Redis | `StackExchange.Redis` |
| Brokers | `Azure.Messaging.ServiceBus`, `RabbitMQ.Client`, `Confluent.Kafka`; MassTransit on top for outbox and retries |
| Formats | `System.Text.Json`, `CsvHelper`, `System.Xml.Linq`, `YamlDotNet`, `Google.Protobuf` |
| JWT validation | `Microsoft.AspNetCore.Authentication.JwtBearer` |
| OpenAPI | `Microsoft.AspNetCore.OpenApi` (`AddOpenApi()`, `MapOpenApi()`) + Scalar or Swagger UI |
| Scraping | `AngleSharp` (static HTML), `Microsoft.Playwright` (JavaScript-rendered pages) |
| Scheduling | Azure Functions timer trigger (isolated worker model); Hangfire or Quartz.NET when self-hosted |
