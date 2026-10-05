---
name: microservices-patterns
description: Chooses and reviews service boundaries with the pattern language from Chris Richardson's "Microservices Patterns" - decomposition, sagas, transactional outbox, idempotent consumers, domain events, event sourcing, API composition vs CQRS, API gateway, strangler fig. Use when deciding whether or how to split a system into services or modules, keeping data consistent across services without 2PC, publishing events reliably, handling duplicate messages, or querying data owned by several services, or when the user mentions microservices, saga, outbox, CQRS, bounded context or eventual consistency. Covers deciding whether a feature is a folder, a module or a separate library, and what a feature exposes in _contracts/. Not for the concrete extraction of a FlexFunding feature module (soft-extract-feature) or for picking a transport, broker or vendor (system-integration).
---

# Microservices Patterns

Source: Chris Richardson, *Microservices Patterns* (Manning, 2018). The book's code is Java/Spring. This skill keeps its running example, **FTGO** (food delivery: Order, Consumer, Kitchen, Accounting and Delivery services), and maps it to C# and this repo at the end.

Each pattern comes with three things: the forces it resolves, its drawbacks, and the new problems it creates (the successor patterns). Recommend a pattern only with all three.

Boundaries:
* This skill picks the architecture and the pattern: module or service, saga or not, outbox, composition or CQRS view.
* `soft-extract-feature`: the in-repo procedure that moves monolith code into `FF.Api/Features/{Name}Feature/`.
* `system-integration`: the wire under a pattern: transport, broker choice, webhooks, vendor adapters, formats.

## The one idea

Every pattern solves a problem created by one rule: **each service owns its data, and others reach it only through its API** (commands, queries, events).

```
Database per service
├── no JOIN across services             → API composition; CQRS view when composition is too slow
├── no ACID transaction across services → saga (+ countermeasures, because sagas lack isolation)
│   └── "update DB and send message" must be atomic → transactional outbox
│       └── the broker delivers at least once       → idempotent consumer
├── each sync call multiplies failure   → async messaging; timeout + circuit breaker
└── many fine-grained APIs              → API gateway / backends for frontends
```

## The counterweight: start smaller

* New applications start as a monolith. Decompose when complexity and team size slow delivery, not because of load. Load alone is solved by cloning instances (X-axis) or partitioning by key (Z-axis).
* Rule out process causes first: manual testing, no CI, waterfall. Fixing those can be enough.
* A modular monolith with service-shaped boundaries (own tables, references by id, events through an outbox) makes a later extraction a deployment change, not a rewrite. In this repo that is a `Features/{Name}Feature/` module (below); it can stay a module.
* Size is not the measure. A service fits when one small team can change, test and deploy it without coordinating. If one requirement change touches several services, the split is wrong: a distributed monolith has the costs of both styles.
* Take the simple side of each pair until a named force pushes you over:

| Problem | Default | Step up to | Only when |
|---|---|---|---|
| Architecture | Monolith | Microservices | teams block each other on one codebase and one deploy |
| Business logic | Transaction script | Aggregates (domain model) | the rules are complex |
| Cross-service query | API composition | CQRS view | large in-memory joins, the owner's DB can't serve the query, or another team must own it |
| Saga coordination | Choreography | Orchestration | anything beyond the simplest flow (the book's default) |
| Outbox relay | Polling publisher | Transaction log tailing | polling load or scale hurts |
| Persistence | Current-state tables | Event sourcing | history or audit is a requirement and the team accepts the learning curve |
| External API | One API gateway | Backends for frontends | client teams queue on the gateway team |
| Deployment | Whatever deploys the monolith | Containers + orchestrator, serverless | a few services already run in production |

* When you recommend a pattern, name the force it resolves here and what it costs. When you decline one, say why.

## Workflow

1. **System operations.** From the stories, the nouns give a rough domain model and the verbs give operations. Commands change data (`createOrder()`, `acceptOrder()`). Queries read it (`findOrderHistory()`).
2. **Services.** Decompose by business capability or by DDD subdomain. Both give business-shaped, stable boundaries; never split by technical layer. Then apply SRP and the Common Closure Principle: code that changes together for one reason lives together.
3. **APIs.** Give each operation an entry service, then list what it needs from other services. Those needs become collaboration operations and events.
4. **Obstacles per operation:** chatty round-trips (batch API, or merge the services), sync calls in the request path (messaging, replicas), multi-service updates (saga), god classes (one model per bounded context).
5. **Communication per interaction.** Pick the style first (one-to-one or one-to-many, sync or async), then the technology. Default: async messaging between services, with REST or gRPC at the edge behind a gateway. Between modules of one deployable: in-process MediatR notifications, no broker.
6. **Inside each service:** aggregates, domain events through an outbox, sagas for cross-service commands, views for cross-service queries.
7. **Tests and production:** a contract test per interaction, a component test per service, and few end-to-end journeys. Plus a health check, logs, tracing, metrics, an access token and externalized config.

Depth: [decomposition-and-communication.md](references/decomposition-and-communication.md) (steps 1–5, gateway) · [data-consistency-and-queries.md](references/data-consistency-and-queries.md) (step 6) · [testing-and-production.md](references/testing-and-production.md) (step 7, deployment, migrating a monolith).

## Symptom → pattern

Sections: **C** = decomposition-and-communication, **D** = data-consistency-and-queries, **T** = testing-and-production.

| Symptom in the design or code | Pattern | Depth |
|---|---|---|
| One `Order` class has fields and methods for ordering, kitchen, delivery and billing | One model per bounded context: `Order`, `Ticket`, `Delivery` | C §1 |
| A handler calls `GET /consumers/{id}` and `GET /restaurants/{id}` before replying | Replicate the data from events, or reply first (`APPROVAL_PENDING`) and finish async | C §5 |
| A slow dependency exhausts the caller's threads | Timeout + concurrency cap + circuit breaker + a fallback per call | C §3 |
| `Save(order)` then `Publish(orderCreated)` as two steps | Transactional outbox | C §4 |
| A redelivered message charges a card twice | Idempotent consumer: record processed message ids in the same transaction | C §4 |
| Two instances handle events for the same order out of order | Partitioned channel, shard key = aggregate id | C §4 |
| One command must update several services, and someone proposes 2PC | Saga with compensating transactions | D §4 |
| Concurrent sagas overwrite each other or read half-done data | Countermeasures: semantic lock, commutative updates, pessimistic view, reread value | D §5 |
| Code changes `OrderLineItem` directly and breaks the order minimum | Aggregate: change only through the root, one aggregate per transaction | D §2 |
| An `order.Restaurant` object reference crosses a service boundary | Reference by id (`restaurantId`) | D §2 |
| History or audit of every change is a requirement | Event sourcing, or audit logging | D §6, T §4 |
| A query filters or sorts on data spread over several services | API composition; a CQRS view when it needs large in-memory joins | D §7 |
| A mobile client makes many calls per screen | API gateway with API composition | C §6 |
| Client teams wait on one gateway team | Backends for frontends | C §6 |
| Integration is only verified by running every service | Consumer-driven contract tests + component tests | T §1 |
| A request can't be followed across services | Distributed tracing + log aggregation | T §4 |
| Someone proposes a big-bang rewrite | Strangler application + anti-corruption layer | T §7 |

## Reporting a review or proposal

One entry per finding:

```
Where          application/create-order.cs:40  CreateOrder
Problem        calls Consumer and Restaurant services over REST before replying: 99.5%³ ≈ 98.5% availability
Pattern        validate locally, save Order as APPROVAL_PENDING + outbox row, reply; the Create Order saga finishes async
Trade-off      availability over immediate consistency; the client polls GET /orders/{id} or gets a notification
Worth it now?  yes: Restaurant Service deploys daily, and every deploy blocks ordering
```

* **Trade-off** names the side taken: availability vs consistency, speed vs simplicity, latency vs coupling.
* If you can't name the force the pattern resolves here, drop the finding.
* Close with the patterns you deliberately did not recommend, for example "API composition is enough" or "keep it a module, no service yet".

## This repo (C#)

One deployable (`FF.Api`) on SQL Server. A bounded context is a feature module; reference module `FactoringFeature`:

```
API/FF-API/
├── FF.Api/Features/{Name}Feature/    a bounded context: a module today, a service if it must deploy alone
│   ├── _DTO/                         requests; rejects malformed commands before the domain
│   ├── _CRITICAL/                    business-critical enums and constants
│   ├── API/REST/                     controller, partial by Commands / Queries
│   ├── Application/                  use cases (+ saga orchestrators, only when a saga exists)
│   ├── Domain/                       aggregates, value objects
│   ├── Infrastructure/               own DbContext + schema, migrations, outbox table + dispatcher
│   ├── Integration/                  anti-corruption layer to the monolith and vendors (HubSpot mapper, lifecycle events)
│   └── {Name}ServiceExtensions.cs    DI registration + its own migrate call
├── _CONTRACTS/                       FF.Contracts: interfaces shared by features and the monolith (IHubSpotDataMapper<T>)
└── FF.Tests/Features/{Name}Feature/
```

What the repo uses today:

| Pattern | In the repo |
|---|---|
| Domain events | `IDomainEventPublisher` → MediatR `IMediator.Publish`, in process |
| Transactional outbox, monolith | `AddProcessingQueueEntry<T>` writes a `ProcessingQueueEntry` row in the same unit of work; a `QueueProcessorService<T>` per type polls it every 10 s |
| Transactional outbox, feature | `FactoringOutboxMessage` table; `FactoringOutboxDispatcher` polls (batch 20, 10 s idle delay, 5-min lease) and publishes through MediatR |
| One worker across instances | `ActiveAppInstanceCoordinator` (Redis set `ff:app:instances`): the newest instance runs the hosted services, older ones stop theirs and keep serving HTTP |
| Health check | `/health`, `/health/details`: SQL Server plus account-balance and client-funds consistency checks |
| Logs, tracing, exceptions | Serilog → Application Insights |

* Both outboxes are polling publishers. Log tailing on SQL Server would mean CDC; only when polling load hurts.
* Not in the repo; add one only when a named force needs it: Polly or `Microsoft.Extensions.Http.Resilience` (circuit breakers), a broker plus MassTransit (cross-process outbox, idempotent consumers), YARP (a composing gateway), PactNet (contract tests), OpenTelemetry.
* Where the house rules differ from the book, the house rules win. The book's aggregate `process()` throws on an invalid command. Here the domain returns the object or `null`, or a `bool` (no exceptions in the domain), and `_DTO` has already rejected malformed input.
* Use `solid-principles` and `design-patterns` for the classes inside one service. Use this skill for the boundaries between services.
