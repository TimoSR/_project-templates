# Transports

How bytes move between two systems, from HTTP API styles down to TCP and UDP.

## Contents

1. HTTP API styles: REST, GraphQL, gRPC, SOAP
2. The update problem
3. Server → client: polling, long polling, SSE, WebSockets, WebRTC
4. Server → server: webhooks, server as client, RPC
5. Below HTTP: TCP, UDP, QUIC, sockets
6. CORS
7. Low coupling with HTTP APIs

## 1. HTTP API styles

| | REST | GraphQL | gRPC | SOAP |
|---|---|---|---|---|
| Shape | a URL per resource; verbs and status codes carry meaning | one endpoint; the client names the fields it wants | typed methods generated from a `.proto` file | XML envelope described by a WSDL |
| Format | JSON (any media type) | JSON | Protobuf, binary, over HTTP/2 | XML |
| Caching | HTTP caches and CDNs work | hard: queries are POSTs to one URL | none built in | none |
| Live updates | none: polling, SSE or webhooks | subscriptions, usually over WebSockets | server and bidirectional streaming | none |
| Browser | native | native | needs a gRPC-Web proxy | rare |
| Fits | the default; public APIs | many clients needing different shapes; frontend teams waiting on new endpoints | internal, high-volume, typed service calls | legacy enterprise and government systems |

* REST gets HTTP's tooling for free: status codes (`200`, `201`, `400`, `404`, `409`, `429`), caching headers (`ETag`, `Cache-Control`), proxies, load balancers, monitoring.
* GraphQL fixes over-fetching (the endpoint returns 40 fields, the screen needs 3) and under-fetching (3 calls for one screen):

```graphql
query { invoice(id: "inv_9") { status amountCents customer { name } } }
```

   * Costs: a schema and resolvers to maintain, N+1 database queries behind nested resolvers (batch them with DataLoader), and a public endpoint needs depth and complexity limits against expensive queries.
   * Integrating with a vendor's GraphQL API ties our code to their schema: keep the queries inside the vendor adapter.
* HATEOAS / HAL: responses carry links (`"_links": { "next": { "href": "/v1/invoices?page=3" } }`) so clients follow transitions instead of building URLs. Default: only `next`/`prev` links for pagination. Full hypermedia rarely pays off.

## 2. The update problem

A client's copy goes stale the moment it's fetched. REST has no subscription, so something must tell the client.

| Approach | Who starts | Cost |
|---|---|---|
| Poll REST at an interval | client | stale between polls; most calls return "no change" |
| Webhook | server → server | receiver must be reachable and idempotent; the payload often only says "something changed" |
| SSE | server → browser | one open connection per client |
| GraphQL subscription | server → client | needs a WebSocket transport and server support |
| WebSockets | both | connection state and reconnect logic |

## 3. Server → client

| | Short polling | Long polling | SSE | WebSockets | WebRTC |
|---|---|---|---|---|---|
| Direction | client pulls | client pulls; server holds the request | server → client | both at once | peer ↔ peer |
| Connection | new request per poll | one held request per client, reopened after each response | one long-lived HTTP response | one long-lived TCP connection (`ws://`, `wss://`) | UDP between peers, set up through a signaling server |
| Payload | any | any | UTF-8 text | text and binary frames | audio, video, data channels |
| Reconnect | not needed | natural: the next request | built in; resumes with `Last-Event-ID` | write it yourself | ICE restart |
| Infrastructure | plain HTTP | plain HTTP; align timeouts with proxies | plain HTTP; proxies must not buffer | the upgrade must pass proxies and load balancers | STUN/TURN servers |
| Fits | data that may be minutes old | infrequent updates, locked-down networks | feeds, notifications, progress | chat, games, collaboration | calls, screen sharing |

* Communication modes: SSE is simplex (one direction), request/response is half duplex (one side at a time), WebSockets are full duplex (both at once).

**Long polling**

```
client: GET /v1/messages?after=41   ──▶ server holds the request for up to 30 s
server: 200 [42, 43]                ◀── as soon as data exists (204 at timeout)
client: GET /v1/messages?after=43   ──▶ immediately
```

* Each waiting client holds a connection: write the handler async.
* Still useful when firewalls or proxies block WebSockets and SSE, or updates are rare.

**Server-sent events**

```
GET /v1/invoices/inv_9/events      Accept: text/event-stream

HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache

retry: 5000

id: 41
event: invoice-paid
data: {"invoiceId":"inv_9","amountCents":4900}

: ping (a comment line; the client ignores it)
```

* A blank line ends each event. `data:` is text, so JSON travels as one line of text, not as a raw JSON stream.
* Client: `new EventSource('/v1/invoices/inv_9/events')` + `addEventListener('invoice-paid', ...)`. Events without `event:` go to `onmessage`.
* After a network drop the browser waits `retry` ms, reconnects and sends `Last-Event-ID: 41`. The server must replay everything after 41, so events need ids and a store.
* A response that isn't `200` with `Content-Type: text/event-stream` fails the `EventSource` permanently, with no more reconnects. A 500 during a deploy silently ends every stream. Return `204 No Content` on purpose to tell a client to stop.
* Error handling differs from WebSockets: a dropped SSE stream fires `error` and reconnects by itself. Track `open` and `error` events to know the real state.
* Send a comment line every 15–30 s so idle proxies don't cut the connection. Disable response buffering and compression at the proxy.
* Browsers allow about 6 HTTP/1.1 connections per origin, shared by all tabs: the 7th SSE stream waits. HTTP/2 multiplexes streams over one connection and removes the limit in practice.
* .NET 10+: return `TypedResults.ServerSentEvents(IAsyncEnumerable<SseItem<T>>)`; each `SseItem<T>` carries data, event type and id.

**WebSockets**

```
GET /chat HTTP/1.1                       HTTP/1.1 101 Switching Protocols
Upgrade: websocket                  ──▶  Upgrade: websocket
Connection: Upgrade                      then frames flow both ways on the same TCP connection
Sec-WebSocket-Key: dGhlIHNhbXBsZQ==
```

* The protocol gives you frames and nothing else: no reconnect, no heartbeat, no rooms, no acknowledgements.
   * Reconnect with exponential backoff and jitter: 1 s, 2 s, 4 s … capped at 30 s.
   * Ping/pong about every 30 s to detect dead connections.
* SignalR (.NET) and Socket.IO (Node) add reconnect, groups, acknowledgements and a long-polling fallback. Each uses its own protocol on top: a Socket.IO client can't talk to a plain WebSocket server or a SignalR server.
* Scale-out (SSE too): a client is connected to one instance, but the event may happen on another. Fan events out through a backplane (Redis Pub/Sub, Azure SignalR Service) so every instance can push to its own clients.
* Browser data transfer: HTTP (`fetch`, forms) is stateless; WebSockets and WebRTC are stateful connections.

**WebRTC**

```
peer A ──offer (SDP)──────────▶ signaling server (your WebSocket) ──▶ peer B
peer A ◀──answer + ICE candidates──────────────────────────────────── peer B
peer A ◀═══════ media and data, directly over UDP (SRTP) ═══════════▶ peer B
                or relayed through a TURN server when NAT blocks it
```

* You still run servers: signaling (any channel), STUN (tells a peer its public address), TURN (relays when a direct path fails; costs bandwidth).
* Beyond a handful of participants, peers send to a media server (SFU) instead of to each other.
* Not for server → client data feeds: use SSE or WebSockets.

## 4. Server → server

* **Webhook:** when an event happens, the source POSTs to a URL the receiver registered. One-to-one, push, no open connection. Receiving and sending: [third-parties.md](third-parties.md) §2–3.
* **Server as client:** our API calls another API while handling a request. Every such call adds its latency and its failure rate to ours.
   * Timeout on every call, through `IHttpClientFactory`; never `new HttpClient()` per request (socket exhaustion).
   * When the caller doesn't need the answer now, go async: queue or webhook. Availability math: `microservices-patterns`.
* **RPC:** call a remote function as if it were local (gRPC; JSON-RPC, which Ethereum nodes expose over HTTP). It hides the network, so the adapter must make timeouts and errors explicit.

## 5. Below HTTP: TCP, UDP, QUIC

| | TCP | UDP | QUIC |
|---|---|---|---|
| Setup | handshake, then a byte stream | none: independent datagrams | handshake (1 round trip, 0 on resume), many streams |
| Delivery | reliable, ordered, congestion control | may drop, duplicate or reorder | reliable per stream; one lost packet doesn't stall the other streams |
| Used by | HTTP/1.1, HTTP/2, WebSockets, SMTP, SSH, database drivers | DNS, VoIP and WebRTC media, game state, NTP, traceroute | HTTP/3 |

* TCP is the default. Choose UDP when a late packet is worthless: the player's position from 200 ms ago, a voice frame. Then rebuild only the reliability you need: sequence numbers to drop stale packets, and acks for the few messages that must arrive ("player died").
* Video sites stream over HTTP (HLS, DASH), on TCP or QUIC: buffering hides latency, and HTTP passes every firewall and CDN. See [data-formats.md](data-formats.md) §8.
* TCP has no message boundaries. A custom protocol must frame its messages: a length prefix (`[4-byte length][payload]`) or a delimiter (`\n`).
* Socket lifecycle:
   * Server: `socket → bind → listen → accept → receive/send → close`.
   * Client: `socket → connect → send/receive → close`.
   * Handle partial reads, timeouts and half-closed connections.
* Writing a multiplayer or blockchain protocol means designing a protocol: message types, framing, serialization, versioning, ordering, retries. Ethereum nodes speak their own protocol over TCP (port 30303).
* Text vs binary protocols:
   * Text: HTTP/1.1, SMTP, FTP, POP3 send readable commands. Easy to debug with `curl` or `telnet`.
   * Binary: HTTP/2, HTTP/3, DNS, SSH, WebSocket frames, TCP itself. Smaller and faster to parse.
* Every message is a header (addresses, type, length, metadata) plus a payload. Large payloads are split into packets that fit the network's MTU (~1,500 bytes on Ethernet).
* Delivery: unicast (one receiver), multicast (a group), broadcast (everyone on the network).

## 6. CORS

* Origin = scheme + host + port. `https://app.example.com` → `https://api.example.com` is cross-origin, and so is `http://localhost:5173` → `http://localhost:5000`.
* Browsers enforce it, servers don't: it stops other sites from using a user's browser against your API. Postman, `curl` and server-to-server calls ignore it, so it's no access control.
* Non-simple requests (JSON body, `Authorization` header, `PUT`/`DELETE`) send a preflight first:

```
OPTIONS /v1/invoices/inv_9          Origin: https://app.example.com
                                    Access-Control-Request-Method: PUT
                                    Access-Control-Request-Headers: content-type, authorization
◀ 204  Access-Control-Allow-Origin: https://app.example.com
       Access-Control-Allow-Methods: GET, PUT
       Access-Control-Allow-Headers: content-type, authorization
       Access-Control-Max-Age: 600
```

* Allowed origins come from config per environment. `*` can't be combined with credentials (cookies).
* .NET: `builder.Services.AddCors(...)` with a named policy, then `app.UseCors("frontend")`.

## 7. Low coupling with HTTP APIs

| Technique | Example | Protects against |
|---|---|---|
| Version in the URL | `/v1/invoices`, `/v2/invoices` | breaking clients when a field is removed or renamed; additive changes stay in v1 |
| Base URL and timeouts in config | `Integration:Hubspot:BaseUrl` in `src/_config/` | redeploying code to change an endpoint |
| One adapter per external API | `integration/Hubspot/` is the only code that knows Hubspot | vendor changes spreading through the app |
| Tolerant reader | ignore unknown fields (`System.Text.Json` does by default); map unknown enum values to `unknown` | breaking when the provider adds fields |
| API gateway | auth, rate limits and routing in front of many backends | duplicated cross-cutting code (`microservices-patterns`) |

* Calling an API directly is point-to-point coupling: the caller knows the callee's address, format and availability. When many systems must hear about one change (multicast), publish an event instead: [messaging.md](messaging.md).
