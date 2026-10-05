# Testing, Production Readiness, Deployment and Migration

Book chapters 9–13.

## Contents

1. Testing
2. Security
3. Externalized configuration
4. Observability
5. Microservice chassis and service mesh
6. Deployment
7. Refactoring a monolith: the strangler

## 1. Testing

* The test pyramid: the wider the scope, the slower and more brittle the test, so write fewer of them.

```
        end-to-end      user journeys only; a handful
      component         one service through its API, other services stubbed
    integration         one adapter against real infrastructure, or against a contract
  unit                  sociable: aggregates, value objects, sagas
                        solitary (with mocks): controllers, domain services, message handlers
```

* To fix a bug, first write a failing test that reproduces it.
* Test doubles: a stub returns values to the code under test; a mock verifies that the code called it correctly.
* In microservices, the complexity moves into the interactions between services. Test each interaction with a **contract**: example messages that both sides test against.

| Interaction | Contract | Provider-side test | Consumer-side test |
|---|---|---|---|
| REST request/response | an HTTP request + response | send the request to the controller, compare the response | a stub HTTP server answers from the contract |
| Publish/subscribe | one example event | trigger the publish, compare the event | feed the event to the handler |
| Async request/response | a command + a reply | send the command, compare the reply | a stub replier answers from the contract |

* **Consumer-driven:** the consumer team writes the contracts, and they run in the provider's pipeline. A failure tells the provider team it broke a client, before it deploys. Tools: Pact (many languages, including .NET), Spring Cloud Contract (JVM).
* Contract tests check the API's shape (path, headers, status, body), not the provider's business logic. Unit tests cover the logic.
* **Integration tests test adapters, not whole services:** the repository against a real database in a container (PostgreSQL via Testcontainers here: `tests-as-documentation`), the event publisher, a proxy against a contract.
* **Component tests:** acceptance tests for one service, written as Given/When/Then scenarios from the user stories.

```gherkin
Given a valid consumer
And the restaurant is accepting orders
When I place an order for Chicken Vindaloo at Ajanta
Then the order should be APPROVED
And an OrderAuthorized event should be published
```

* Two ways to run component tests:
   * In-process: in-memory infrastructure and stubs. Fast, but doesn't test the deployable artifact.
   * Out-of-process: the real container image, real database and broker, stubbed services. More realistic, slower, more brittle.
* **End-to-end:** test user journeys. One test that places, revises and cancels an order replaces three tests and shares their setup.
* **Saga unit test:** given the current state and a reply, assert the next command. In this repo's pure form (data-consistency-and-queries.md §4), that's a plain function call.
* **Deployment pipeline**, fast feedback first: pre-commit (unit) → commit (compile, unit, static analysis) → integration → component → deploy.

## 2. Security

* Two monolith habits don't carry over: an in-memory security context (thread-local) and a central session. Services share neither memory nor a session store.
* **The gateway authenticates.** That's one place to get it right, and services never deal with several login mechanisms.
* **Access token:** the gateway passes a token with the user's identity and roles to each service.
   * ✗ Opaque token: every service makes a sync call to validate it, costing latency and availability.
   * ✓ Transparent JWT: the service validates the signature locally.
   * A JWT can't be revoked, so keep its lifetime short and reissue it through OAuth 2.0 refresh tokens.
* **Authorization:**
   * Coarse, by role per path, in the gateway.
   * Per instance ("only the consumer who placed this order") in the service, which knows the domain.
   * Doing all of it in the gateway couples the gateway to every service.

## 3. Externalized configuration

* Build once, deploy to every environment. Never bake environment values, or a set of per-environment profiles, into the artifact. Secrets go in a vault.
* Two models:
   * **Push:** the platform supplies environment variables or a config file when it starts the instance.
   * **Pull:** the service reads a config server. You get centralization, decrypted secrets and reloads, but one more component to run.
* In this template: tracked defaults in `src/_config/` (`config_guidelines.md`: defaults first, override per case); local overrides in git-ignored `*.local.json`; secrets from the secret store. ASP.NET Core layers them: `appsettings.json` → `appsettings.{Environment}.json` → environment variables.

## 4. Observability

Developers make each service observable. Operations runs the servers that collect the data.

| Pattern | What the service does | .NET |
|---|---|---|
| Health check API | `GET /health` reports DB and broker connectivity. The platform sends traffic only to healthy instances and restarts unhealthy ones. | ASP.NET Core health checks (`/health`) |
| Log aggregation | Structured logs with the request id; a central server searches and alerts | Serilog → Application Insights, Seq or Elasticsearch |
| Distributed tracing | Propagates a trace id through HTTP and message headers; records a span per call, so you see where the time went | OpenTelemetry; Application Insights request/dependency correlation |
| Application metrics | Counters and gauges, technical (latency) and business (orders placed, approved, rejected) | OpenTelemetry metrics, Prometheus |
| Exception tracking | Reports exceptions to a service that deduplicates them, alerts, and tracks the fix | Application Insights; Sentry |
| Audit logging | Records user + action + business object in a table | Code in the use case, a decorator, or event sourcing (which misses queries) |

## 5. Microservice chassis and service mesh

* **Chassis:** a framework that handles cross-cutting concerns (config, health, metrics, discovery, circuit breakers, tracing), so a new service starts with business logic. Here that's ASP.NET Core plus the cross-cutting code in `src/_architecture/` and the shared libraries in `src/_libs/`.
* **Service mesh** (Istio, Linkerd): moves the network concerns out of the process: circuit breaking, tracing, discovery, load balancing, mTLS, traffic routing. It works for every language.
   * It also separates deploying from releasing: deploy v2, send it test traffic, then shift production traffic to it gradually.

## 6. Deployment

* Choose the lightest option that meets the service's needs. Evaluate them in this order:

| Option | For | Against |
|---|---|---|
| Serverless | No OS or runtime to manage, elastic, pay per request | Long-tail latency (cold starts); request/event model only, so no long-running broker consumers |
| Container + orchestrator | Encapsulates the stack, isolated, resource limits, fast deploys | You run the OS, the runtime and usually the orchestrator |
| VM | Encapsulates the stack, isolated, mature cloud tooling | Slow deploys, wasted resources, system admin overhead |
| Language-specific package | Fast deploys, efficient | No isolation or resource limits; tied to the host's tech stack |

* At the start of a migration, deploy services the way the monolith is deployed. Invest in Kubernetes and the like only after a few services run. The one thing you need from day one is an automated deployment pipeline with tests.
* Zero downtime: a rolling update, gated by a readiness check, with a recorded rollout history so you can roll back.

## 7. Refactoring a monolith: the strangler

* **Check the cause first.** Slow delivery and buggy releases often come from process, like manual testing. Fix that before changing the architecture.
* **No big-bang rewrite.** It delivers nothing until it's done, and it chases a monolith that keeps changing. Instead, build a strangler application: services grow around the monolith until it disappears or becomes just another service. Show value early, so the business keeps funding the work.
* **Three strategies:**
   1. **New features as services** (the law of holes: when in a hole, stop digging). The gateway routes the new endpoints to the service, and integration glue connects it to the monolith.
   2. **Split the presentation tier from the backend:** two smaller monoliths that deploy independently.
   3. **Extract business capabilities:** move a vertical slice (inbound adapters, domain logic, outbound adapters, tables) into a service.
* **What to extract first:** rank candidates by benefit:
   * an area with heavy upcoming development
   * a performance, scaling or reliability problem
   * an extraction that unblocks other extractions
   * Sketch the target architecture in a time-boxed effort (a couple of weeks), then revise it as you learn.
* **Splitting the domain:**
   * Replace object references that cross the new boundary with ids (aggregate rule 2).
   * Split god classes: `Order` → `Order` + `Delivery`.
   * Split tables.
* **Keep monolith changes small:** for a transition period, replicate the moved data back into the monolith's columns and make them read-only. Only the code that writes those fields has to change.
* **Integration glue:**
   * The domain sees an interface, and an adapter hides the IPC behind it. Use a repository for queries (`CustomerContactInfoRepository.FindCustomerContactInfo(customerId)`) and a service interface for commands (`DeliveryService.ScheduleDelivery(...)`).
   * An **anti-corruption layer** translates between the monolith's model and the service's model, so the monolith's concepts don't leak into the new service.
* **Sagas with the monolith:** cheapest when the monolith's steps are pivot or retriable, because then the monolith needs no compensation code. Order the extractions to keep it that way:

```
✗ extract Kitchen first: the monolith's createOrder step becomes compensatable, so it needs
  an APPROVAL_PENDING state that touches every piece of code using Order
✓ extract Order first:   Order(APPROVAL_PENDING) → monolith [verify consumer, create ticket, authorize card] = pivot → Order APPROVED
  then Consumer, Kitchen, Accounting: the monolith's step stays the pivot until it's gone
```

* **Auth during the migration:**
   * The monolith's login handler also sets a `USERINFO` cookie containing a JWT.
   * The gateway validates it and passes it to services in the `Authorization` header.
   * The monolith keeps its session, and the services get tokens.
