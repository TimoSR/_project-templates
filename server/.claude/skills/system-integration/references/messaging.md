# Messaging

Brokers, queues, streams and event-driven architecture: what happens when the receiver isn't waiting.

## Contents

1. Does the message wait?
2. Queue vs stream vs pub/sub
3. Delivery guarantees, ordering, envelopes
4. Picking a broker
5. Redis Pub/Sub and Streams in practice
6. Task queues
7. Event-driven architecture

## 1. Does the message wait?

* Synchronous: the sender blocks until the receiver answers (an HTTP call). Asynchronous: the sender hands the message off and continues; the receiver processes it when it can.
* What decides the tool is retention: can the receiver be offline (deploy, crash, overload) without losing messages?

| | Receiver must be connected now | Message waits for the receiver |
|---|---|---|
| No broker | sockets, ZeroMQ: peers connect directly (LAN, a few devices talking to one server) | — |
| Broker | Redis Pub/Sub: routes live, keeps nothing | queues (RabbitMQ, Service Bus, Redis lists, SQS); streams (Kafka, Redis Streams, Event Hubs) |

## 2. Queue vs stream vs pub/sub

```
Queue: push, competing consumers                   Stream: append-only log, pull by offset
producer → [m3 m2 m1] ─┬─▶ worker A gets m1         producer → [m1 m2 m3 m4 m5]   (kept)
                       └─▶ worker B gets m2                         ▲           ▲
each message goes to ONE consumer                      group "billing"   group "email"
and is deleted on ack                                  at offset 2       at offset 5
                                                       a new group may start at m1 (replay)
```

| | Queue | Stream |
|---|---|---|
| A message goes to | one consumer | every consumer group, each at its own offset |
| After processing | deleted | kept until retention ends |
| Fan-out to 3 services | 3 queues, 3 copies (an exchange or topic makes the copies) | 3 consumer groups on one log |
| Messages | may change (retry count) | immutable |
| A new consumer sees | only new messages | history (replay) |
| Fits | jobs: encode a video, send an email, build a report | facts many systems react to; audit; analytics; IoT; logs |

* Pub/sub is a delivery pattern, not a product: a publisher sends to a topic, every subscriber gets a copy, and neither knows the other. It runs on:
   * a queue broker: RabbitMQ fanout/topic exchange, Service Bus topic (each subscription is its own queue);
   * a stream: Kafka topic + one consumer group per subscriber;
   * nothing durable: Redis Pub/Sub.
* Example: an order is placed, and the mailing, delivery and CRM services each need it → publish `order-placed` once to a topic, with one subscription per service.
* Choose a queue when routing is fixed and point-to-point. Choose a stream when subscribers come and go and must catch up on what they missed.

## 3. Delivery guarantees, ordering, envelopes

| Guarantee | How | Failure mode |
|---|---|---|
| At-most-once | ack before processing, or no acks at all (Redis Pub/Sub) | a crash mid-processing loses the message |
| At-least-once | ack after processing | a crash after the effect but before the ack → redelivery, duplicate |
| Effectively once | at-least-once + idempotent consumer | — |

* Every durable broker and every webhook provider is at-least-once. "Exactly-once" in a broker's docs means inside the broker (Kafka transactions between Kafka topics), not your database.
* Idempotent consumer: record the message id in the same transaction as the effect.

```sql
INSERT INTO processed_messages (message_id) VALUES ('evt_01J9ZK3') ON CONFLICT DO NOTHING;
-- 0 rows inserted → already handled → ack and skip
```

* Saving and publishing atomically (transactional outbox): `microservices-patterns`.
* Ordering exists only inside a partition (Kafka), a session (Service Bus) or a queue with one consumer. Use the entity id (`invoiceId`) as the partition or session key so one invoice's events stay in order.
* Poison message: one that always fails. After N attempts (3–10) move it to a dead-letter queue and alert. Retrying forever blocks everything behind it.
* Every event carries an envelope. CloudEvents is the standard shape:

```json
{ "id": "evt_01J9ZK3", "type": "invoice-paid", "version": 1, "occurredAt": "2026-10-02T09:45:12.123Z",
  "correlationId": "req_7f3a", "data": { "invoiceId": "inv_9", "amountCents": 4900, "currency": "DKK" } }
```

   * Evolve by adding fields. Removing or renaming a field means a new `version`. Consumers ignore fields they don't know.
   * Thin event (`{ "invoiceId": "inv_9" }`): consumers call back for details. A small contract, but it couples consumers to your API and its uptime.
   * Fat event (full state): no callback, but a bigger contract. Default: enough data for the known consumers to act.

## 4. Picking a broker

| | Redis Pub/Sub | Redis Streams | RabbitMQ | Azure Service Bus | Kafka |
|---|---|---|---|---|---|
| Model | live fan-out | log in RAM + consumer groups | queues + exchanges (routing rules) | managed queues + topics | partitioned log on disk |
| Retention | none | until trimmed; bounded by RAM | until acked | until acked or TTL | by time or size: days to forever |
| Delivery | at-most-once | at-least-once (`XACK`) | at-least-once | at-least-once; duplicate detection | at-least-once |
| Replay | no | yes | no | no | yes |
| Ordering | per channel | per stream | per queue with one consumer | per session | per partition |
| Dead-letter | no | manual (`XPENDING`, `XAUTOCLAIM`) | yes | built in | manual (a DLQ topic) |
| Large messages | slow above ~1 MB | slow above ~1 MB | fine | up to 256 KB–100 MB by tier | 1 MB default |
| Operations | Redis you already run | Redis you already run | a broker to run and patch | managed | heavy; managed via Confluent or Event Hubs' Kafka endpoint |
| Fits | cache invalidation, live notifications, SignalR backplane | small or medium event log, task queue | task queues with routing | business messaging on Azure | high volume, many consumers, replay, analytics |

* Escalate in this order: in process (`System.Threading.Channels`, `BackgroundService`) → the broker you already run (Redis Streams if Redis exists, Service Bus on Azure) → Kafka when volume and replay demand it.
* Azure Storage Queues: the cheapest option, 64 KB messages, no topics or sessions. Fine for a single worker queue.
* Google Pub/Sub and Amazon SNS + SQS fill the same slots on other clouds.

## 5. Redis Pub/Sub and Streams in practice

Pub/Sub:

```
SUBSCRIBE invoices            # this connection can now only (P)SUBSCRIBE, (P)UNSUBSCRIBE, PING, QUIT
PSUBSCRIBE invoice.*          # pattern: matches invoice.paid, invoice.voided
PUBLISH invoices "inv_9 paid" # returns the number of receivers; 0 = the message is gone
PUBSUB NUMSUB invoices        # subscriber count
```

Streams:

```
XGROUP CREATE invoices billing $ MKSTREAM                              # group reads entries added from now ($); 0 = from the start
XADD invoices MAXLEN ~ 100000 * type invoice-paid invoiceId inv_9      # * = auto id (1727860000000-0); ~ = cheap approximate trim
XREADGROUP GROUP billing worker-1 COUNT 10 BLOCK 5000 STREAMS invoices >   # > = entries never delivered to this group
XACK invoices billing 1727860000000-0                                  # removes it from the group's pending list, NOT from the stream
XPENDING invoices billing                                              # delivered but not acked
XAUTOCLAIM invoices billing worker-2 60000 0                           # take over entries idle > 60 s (worker-1 crashed)
XRANGE invoices - + COUNT 10                                           # read history
```

* On restart a consumer first re-reads its own pending entries (`STREAMS invoices 0` instead of `>`), then new ones.
* Pub/Sub vs Streams: push vs pull; fire-and-forget vs acked; a subscriber's connection is blocked vs consumers that block or poll; plain strings vs field/value entries with time-based ids and range queries.

## 6. Task queues

A queue between "submit" and "do" gives three things:

| Use | Example |
|---|---|
| Smooth a bottleneck | reports generated one at a time, so 50 requests don't run 50 heavy queries at once |
| Spread work | a pool of workers resizing images; add workers to go faster |
| Run later | promotional emails scheduled for 08:00, off the request path |

* Peak clipping, valley filling: a spike fills the queue, and workers drain it at their steady rate.
* The request returns `202 Accepted` with a status URL (`/v1/reports/r_17`). The client polls it, or the result arrives by SSE or webhook.

## 7. Event-driven architecture

* Terms:
   * **Event:** a fact in the past tense (`InvoicePaid`).
   * **Producer:** emits it, doesn't wait, doesn't know who listens.
   * **Consumer:** reacts to it.
   * **Broker / channel:** carries it.
* What it solves:
   * Loose coupling: add a consumer without touching the producer.
   * Asymmetric availability: the consumer can be down; events wait.
   * Spikes: consumers work at their own pace.
   * Multicast: one event, many reactions (invoice paid → email receipt, update CRM, start delivery).
   * Scaling: add consumers per partition.
* What it costs:
   * Eventual consistency: the CRM shows "unpaid" for a few seconds.
   * Debugging: one action spans several processes → a correlation id in every envelope + distributed tracing (OpenTelemetry).
   * Duplicates and ordering (§3), schema evolution, a broker to run, harder end-to-end tests.
* Default for one deployable: in-process domain events and handlers. A broker enters when a consumer must run in another process or survive restarts.
* Event sourcing (state rebuilt by replaying stored events) and CQRS views: `microservices-patterns`.
* Good pub/sub fits: IoT telemetry (devices come and go), monitoring and centralized logging, replication, notifications, game matchmaking, lobbies and telemetry. Not media streaming, which needs smooth, ordered delivery (HLS/DASH, WebRTC).
