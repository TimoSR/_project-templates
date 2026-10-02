# Data Consistency and Queries

Book chapters 4–7. Running example: FTGO's Create Order saga and the Order History view.

## Contents

1. Organizing business logic
2. Aggregates
3. Domain events
4. Sagas
5. Countermeasures for the lack of isolation
6. Event sourcing
7. Queries: API composition vs CQRS

## 1. Organizing business logic

* Each service is hexagonal. Business logic sits in the middle, inbound adapters (REST, command handlers, event handlers) call it, and it calls outbound adapters (database, event publisher, proxies to other services).
* Choose the organization deliberately:
   * **Transaction script:** one procedure per request, plus data classes without behavior. Right for simple logic. It grows the way a monolith does.
   * **Domain model:** classes with state and behavior. Right for complex logic.
* DDD building blocks:
   * Entity: has an identity.
   * Value object: equal by value, such as `Money`.
   * Factory, repository and domain service.
   * Aggregate: the block that matters most for microservices.

## 2. Aggregates

* An aggregate is a cluster of objects treated as one unit, reached through its root. The Order aggregate is `Order` (the root) plus the `OrderLineItem`, `DeliveryInfo` and `PaymentInfo` value objects.
* Without explicit boundaries, invariants break:

```
✗ Sam and Mary edit different line items of order X at the same time.
  Each checks "total ≥ minimum" against what it loaded, and each updates only its own row (row-level version check).
  Both commit. The total is now below the minimum.
✓ Both go through order.ReviseLineItems(...). The root checks the minimum,
  and a version check on the root serializes the two updates.
```

* **Rules:**
   1. Outside code references only the root and changes the aggregate only through root methods.
   2. Aggregates reference each other by id (`consumerId`, `restaurantId`), never by object reference. This gives loose coupling and no references across services, makes the aggregate the unit of storage, and makes sharding straightforward.
   3. One transaction creates or updates one aggregate. To change several, use a saga: each step changes one aggregate. Updating two aggregates of the same service in one RDBMS transaction is allowed, but it's a shortcut, not the rule.
* **Granularity:** prefer small aggregates. They mean more concurrency, fewer conflicting edits and easier decomposition. Grow one only when an update must be atomic.
   * ✗ A `Consumer` aggregate that contains its `Order`s: every order of one consumer is serialized, and consumers and orders can never be split into separate services.
* Inside a service:
   * Aggregates hold most of the logic.
   * A domain service is the entry point: it loads and saves through a repository and publishes the events.
   * Sagas cover commands that span services.

## 3. Domain events

* A domain event is named in the past tense (`OrderCreated`, `TicketAccepted`).
   * Its properties are primitives or value objects.
   * Its metadata is the event id, a timestamp, the user (for audit), and the aggregate type and id (often in an envelope).
* Uses: choreographed sagas, updating replicas and CQRS views, webhooks, WebSocket and email notifications, monitoring, analytics.
* **Finding events:**
   * Look for "when X happens, do Y" in the requirements.
   * Or run event storming: events on a timeline, then their triggers (a user command, an external system, another event, the passing of time), then the aggregate that handles each command.
* **Enrichment:** include what consumers usually need (line items, restaurant name) to save them a call back. The cost is that the event changes whenever its consumers' needs change.
* **Generate in the aggregate, publish in the service.** The aggregate can't get infrastructure injected, and shouldn't.

```csharp
// domain/aggregates/ticket.cs: the root guards the transition and returns what happened; it never publishes
public TicketResult Accept(System.DateTimeOffset readyBy)
{
    if (State != TicketState.AwaitingAcceptance) return new TicketResult(Accepted: false, Events: []);

    State = TicketState.Accepted;
    ReadyBy = readyBy;
    return new TicketResult(Accepted: true, Events: [new TicketAccepted(Id, readyBy)]);
}

// application/accept-ticket.cs: load → decide → save state and events in one transaction
var ticket = await ticketRepository.FindById(ticketId);
if (ticket is null) return AcceptTicketOutcome.NotFound;

var result = ticket.Accept(readyBy);
if (!result.Accepted) return AcceptTicketOutcome.WrongState;

await ticketRepository.Save(ticket, result.Events); // inserts outbox rows in the same transaction
return AcceptTicketOutcome.Accepted;
```

* The alternative is for the root to collect events in a field (`RegisterDomainEvent`), and for the service to read them afterwards. The book prefers returning them, because collecting requires a base class and is awkward for non-root classes.
* Publish only through the outbox (decomposition-and-communication.md §4). Use one typed publisher per aggregate, so Kitchen can only publish `ITicketEvent`s.

## 4. Sagas

* A saga is a sequence of local transactions, each in one service, coordinated by async messages. Write one per system command that updates several services. Messaging guarantees the saga completes even when a participant is temporarily down.
* A saga is ACD without the I:
   * Atomicity comes from compensations.
   * Consistency is enforced inside each service.
   * Durability comes from each local database.
* Rollback is explicit. If T1…Tn commit and Tn+1 fails, run the compensations Cn…C1 in reverse order.

**Create Order saga**

| Step | Service | Transaction | Compensation | Type |
|---|---|---|---|---|
| 1 | Order | `createOrder()` → `APPROVAL_PENDING` | `rejectOrder()` | compensatable |
| 2 | Consumer | `verifyConsumerDetails()` | none (read-only) | compensatable |
| 3 | Kitchen | `createTicket()` → `CREATE_PENDING` | `rejectTicket()` | compensatable |
| 4 | Accounting | `authorizeCreditCard()` | none | **pivot** |
| 5 | Kitchen | `approveTicket()` | none | retriable |
| 6 | Order | `approveOrder()` | none | retriable |

* **Pivot:** the go/no-go point. Once it commits, the saga runs to completion.
* **Retriable:** comes after the pivot and must succeed, so retry it until it does.
* Design rule: put every step that can fail before the pivot.

**Coordination**

| | Choreography | Orchestration |
|---|---|---|
| How | Participants react to each other's events | An orchestrator sends commands and handles the replies |
| For | Simple, loosely coupled | The flow lives in one place. No cycles: the orchestrator calls the participants, never the reverse. Domain objects don't know about sagas. |
| Against | The flow is scattered. Cyclic dependencies (Order ↔ Accounting). Each participant must subscribe to every event that affects it. | Risk of a smart orchestrator with dumb services. Keep it to sequencing only. |
| Use for | The simplest sagas | Everything else |

* Choreography needs two things:
   * An atomic update-and-publish (outbox).
   * A correlation id (`orderId`) in every event, so participants can find their own data.
* **Orchestrator = state machine.** It covers every scenario, not just the happy path, and it's easy to test:

```
VerifyingConsumer ─ConsumerVerified→ CreatingTicket ─TicketCreated→ AuthorizingCard ─CardAuthorized→ ApprovingTicket → ApprovingOrder → OrderApproved
   │ failed                             │ failed                       │ failed
   └──────────→ RejectingOrder ←────────┘                              └→ RejectingTicket → RejectingOrder → OrderRejected
```

```csharp
// application/create-order-saga.cs: (state, reply) → (next state, command to send). Pure: unit-test it without a broker.
public static (CreateOrderSagaState Next, ISagaCommand? Command) Handle(CreateOrderSagaState state, ISagaReply reply, long orderId) =>
    (state, reply) switch
    {
        (CreateOrderSagaState.VerifyingConsumer, ConsumerVerified)           => (CreateOrderSagaState.CreatingTicket, new CreateTicket(orderId)),
        (CreateOrderSagaState.VerifyingConsumer, ConsumerVerificationFailed) => (CreateOrderSagaState.RejectingOrder, new RejectOrder(orderId)),
        (CreateOrderSagaState.CreatingTicket, TicketCreated)                 => (CreateOrderSagaState.AuthorizingCard, new AuthorizeCard(orderId)),
        (CreateOrderSagaState.AuthorizingCard, CardAuthorizationFailed)      => (CreateOrderSagaState.RejectingTicket, new RejectTicket(orderId)),
        // ...one row per transition in the diagram
        _ => (state, null), // unexpected reply: stay in this state and log it
    };
```

* Atomicity at each step:
   * The orchestrator saves its new state and the outgoing command in one transaction (outbox).
   * A participant consumes the command, discards duplicates, updates its aggregate and sends the reply, all atomically.
* The orchestrator treats its own service as just another participant: it sends `ApproveOrder` to Order Service as a command.

## 5. Countermeasures for the lack of isolation

* **Anomalies:**
   * **Lost update:** the Cancel Order saga cancels an order, then the Create Order saga's last step approves it, so a cancelled order ships.
   * **Dirty read:** the Cancel saga raises available credit, the Create saga spends it, then the Cancel saga is compensated. The consumer is now over their limit.
   * **Fuzzy read:** two steps of one saga read the same data and get different values.

| Countermeasure | How | Prevents | FTGO example |
|---|---|---|---|
| Semantic lock | A compensatable step sets a `*_PENDING` flag. A retriable or compensating step clears it. Others fail and retry, or block. | lost updates, dirty reads | `APPROVAL_PENDING`, `REVISION_PENDING`; `cancelOrder()` on a pending order answers "try again later" |
| Commutative updates | Operations work in any order | lost updates | `debit()` / `credit()`; the compensation is the opposite operation |
| Pessimistic view | Reorder steps so risky updates happen in retriable steps | dirty reads | Cancel saga: cancel the order, cancel the delivery, *then* raise the credit |
| Reread value | Reread before writing and verify it's unchanged; otherwise abort the saga | lost updates | `approveOrder()` checks the order is still `APPROVAL_PENDING` |
| Version file | Record operations as they arrive and apply them in the right order | out-of-order requests | Accounting receives `CancelAuthorization` before `AuthorizeCard`, so it skips the authorization |
| By value | Choose the mechanism per request by business risk | high-risk anomalies | low value: a saga; very high value: a distributed transaction |

* A semantic lock that blocks instead of failing recreates isolation, but then you need deadlock detection.
* When a monolith takes part in a saga, it's cheapest if its steps are pivot or retriable, so it never needs compensation code (testing-and-production.md §7).

## 6. Event sourcing

* Persist each aggregate as its events. Loading means folding the events onto an empty aggregate.

```
EVENTS (event_id, event_type,     entity_type, entity_id, event_data)
        102       OrderCreated    Order        101        {...line items, delivery, payment}
        103       OrderApproved   Order        101        {}
load: Order.Empty → Apply(OrderCreated) → Apply(OrderApproved) → current state     (a fold)
```

* Every state change is an event, including creation. Each event carries the data needed to apply it, so `OrderCreated` holds all the line items, not just the id.
* Each command method splits in two:

```csharp
// Process: decide, don't mutate. Apply: mutate, can't fail (the event already happened).
public OrderRevisionResult Process(ReviseOrder command)
{
    if (State != OrderState.Approved) return OrderRevisionResult.Rejected;

    var newTotal = LineItems.TotalAfter(command.Revision);
    if (newTotal < OrderMinimum) return OrderRevisionResult.Rejected;

    return OrderRevisionResult.Proposed(new OrderRevisionProposed(command.Revision, Total, newTotal));
}

public Order Apply(OrderRevisionProposed revisionProposed) => this with { State = OrderState.RevisionPending };
```

* **Concurrency:** optimistic locking on the aggregate version, where the version is the event count.
* **Publishing:** the events table is the outbox, kept forever.
   * ✗ Polling with `WHERE event_id > lastSeen` skips events whose transaction commits late.
   * ✓ Poll a `published` flag, or tail the transaction log.
* **Snapshots:** for long-lived aggregates (`Account`), store a snapshot periodically, then load it plus the events that came after it.
* **Idempotency:**
   * With an RDBMS event store: a processed-messages table in the same transaction.
   * With a NoSQL store: put the message id in the emitted events. If handling a message emits nothing, save a pseudo-event that just records the id.
* **Evolving events:**
   * Backward compatible: adding an aggregate, an event type or a field.
   * Breaking: removing or renaming any of them, or changing a field's type.
   * Upcasters convert old events on load, so the aggregate only knows the latest version.
* **Deleting (GDPR):**
   * Soft delete with a `Deleted` event.
   * Encrypt each user's personal data with a per-user key, and delete the key on an erasure request.
   * Ids derived from personal data (an email) get pseudonymized: a UUID plus a mapping table, whose row is deleted on erasure.
* **Benefits:** reliable event publishing, an accurate audit log, temporal queries, and a "time machine" for requirements nobody anticipated (who added an item to their cart and then removed it?). It also mostly avoids the object-relational mismatch.
* **Drawbacks:** an unfamiliar model, messaging complexity (at-least-once delivery), event evolution, deletion, and queries that need CQRS.
* **With sagas:** choreography fits naturally. But aggregates must then emit events even for failures, and they can't when creating the aggregate is what failed. Prefer orchestration for complex sagas.

## 7. Queries: API composition vs CQRS

**API composition:** a composer calls the provider services, ideally in parallel, and joins the results in memory.

* Who composes:
   * A client inside the LAN.
   * The API gateway, for an external query.
   * A standalone service, for a query several services use.
* Costs:
   * Overhead: more calls and more database queries.
   * Availability is a product: four providers plus the composer at 99.5% gives about 97.5%. Mitigate with cached data or partial results.
   * No transactional consistency: the Order can say `CANCELLED` while the Ticket isn't cancelled yet.
* It fails for `findOrderHistory(consumerId, keyword, sortBy date)`. Delivery and Accounting don't store menu items or order dates, so the composer would fetch every order and join large sets in memory.

**CQRS:** the command side (domain model and its database) publishes events. The query side keeps a read-optimized view, updated by event handlers. Use API composition when it works, and CQRS when you must.

```
Order Service     ─OrderCreated─────┐
Kitchen Service   ─TicketPrepared───┼→ Order History Service → order_history view → findOrderHistory()
Delivery Service  ─DeliveryPickedUp─┘
```

* Reach for it when:
   * The composition needs large in-memory joins.
   * The owner's database can't serve the query, like the geospatial `findAvailableRestaurants()`.
   * A different team should own a critical, high-volume query.
* A query-only service has only query operations and owns views built from other services' events.

| The view needs | Store |
|---|---|
| Lookup of JSON objects by key | Document or key-value store (MongoDB, DynamoDB, Redis) |
| Text search | Elasticsearch |
| Graph queries (fraud detection) | Neo4j |
| SQL reporting and BI | RDBMS |

* A view module has three parts: event handlers, a query API, and a data access object that both use.
* The data access object must handle three things:
   * **Concurrency.** Events from different aggregate types (Order, Delivery) can update the same row at once. Update without reading first, or use optimistic locking.
   * **Idempotency.** Store `max(eventId)` per source aggregate on the row and ignore anything older. Non-idempotent updates (`balance += amount`) must also record event ids.
   * **Foreign-key updates.** `DeliveryPickedUp` may carry only `deliveryId`, so the view needs an index from `deliveryId` to the row.
* **Replication lag:**
   * The command returns a token (the published event's id). The query takes the token and reports "not yet" until the view has processed that event.
   * Or the UI updates its local model from the command's result.
* **Building and rebuilding views:**
   * Brokers don't keep events forever, so archive them (S3) and replay from the archive.
   * Snapshot incrementally, so a rebuild doesn't reprocess every event ever published.
