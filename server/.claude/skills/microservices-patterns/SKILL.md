---
name: microservices-patterns
description: Designs, reviews, and refactors service-based systems with the microservice pattern language from Chris Richardson's "Microservices Patterns" (Manning, 2018) - monolith vs microservices, decomposition by business capability or subdomain, sync vs async communication, circuit breakers, transactional outbox, idempotent consumers, sagas, DDD aggregates and domain events, event sourcing, API composition vs CQRS, API gateway and backends for frontends, contract and component tests, observability, and strangling a monolith. Use when the user splits a monolith or feature into services or modules, designs how services talk, needs consistency across databases without distributed transactions, publishes events reliably, handles duplicate or out-of-order messages, queries data owned by several services, designs an external API or gateway, or tests service interactions, or mentions microservices, saga, outbox, CQRS, event sourcing, aggregate, bounded context, API gateway, eventual consistency, 2PC, or strangler fig.
---

# Microservices Patterns

Source: Chris Richardson, *Microservices Patterns* (Manning, 2018). The book's code is Java/Spring. This skill keeps its running example, **FTGO** (food delivery: Order, Consumer, Kitchen, Accounting and Delivery services), and maps it to C# and this repo at the end.

Each pattern comes with three things: the forces it resolves, its drawbacks, and the new problems it creates (the successor patterns). Recommend a pattern only with all three.

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
* A modular monolith with service-shaped boundaries (own tables, references by id, events through an outbox) makes a later extraction a deployment change, not a rewrite. In this repo a feature can stay a module.
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
5. **Communication per interaction.** Pick the style first (one-to-one or one-to-many, sync or async), then the technology. Default: async messaging between services, with REST or gRPC at the edge behind a gateway.
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

```
features/<feature>/                  a bounded context: a module today, a service if it must deploy alone
├── _contracts/                      commands, replies and events other features use: the async API
└── <module>/
    ├── _dto/                        rejects malformed commands before they reach the domain
    ├── api/REST, api/GraphQL/       inbound adapters, API composition endpoints
    ├── api/EventHandlers/           event, command and reply handlers (idempotent)
    ├── application/                 use cases, saga orchestrators (state machines)
    ├── domain/                      aggregates/, events/, policies/, value-objects/
    ├── infrastructure/postgress/    repositories, outbox, processed_messages, CQRS view tables
    ├── integration/                 proxies to other services, anti-corruption layer, Hubspot/, Twillio/
    └── test/                        aggregate, saga and handler unit tests; contract tests
src/_contracts/                      contracts shared by several features
src/_config/                         timeouts, circuit breaker thresholds, broker and DB locations: defaults, overridden per environment
```

* Where the house rules differ from the book, the house rules win. The book's aggregate `process()` throws on an invalid command. Here the domain returns a result (no exceptions in the domain), and `_dto` has already rejected malformed input.
* .NET equivalents (the book names only Polly):
   * Polly or `Microsoft.Extensions.Http.Resilience`: timeouts and circuit breakers.
   * MassTransit or NServiceBus: outbox and idempotent consumers.
   * Debezium: tails the Postgres WAL.
   * YARP: a custom gateway.
   * PactNet: contract tests.
   * OpenTelemetry: tracing.
   * ASP.NET Core health checks.
* Use `solid-principles` and `design-patterns` for the classes inside one service. Use this skill for the boundaries between services.
