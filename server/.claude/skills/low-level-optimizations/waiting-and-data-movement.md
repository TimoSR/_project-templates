# Waiting and data movement

Data doesn't just move; it waits to move, and most of a slow program's time is that waiting. Before making the CPU work faster, remove the time where it does no work: fewer trips, shorter trips, trips that overlap, answers prepared before they're asked for.

Measured rows: Windows 11, x86_64, Rust 1.97 `--release`. Rows marked *typical* are order-of-magnitude figures for comparison, not measured here.

## Contents
1. Latency and units: the scale
2. The ten techniques
3. Choosing where data lives: memory vs persistence

## 1. Latency and units: the scale

Compare costs in one unit and per item (`ns per read`, `bytes per record`), and name the unit in the variable (`elapsedNanoseconds`). The human column multiplies time by 10⁹: one nanosecond becomes one second.

| Operation | Measured | If 1 ns were 1 s |
|---|---|---|
| Sequential read of a `u32` (prefetcher streams it) | 0.33 ns | 0.3 s |
| Dependent read, data in cache (16 KB) | 1.7 ns | 1.7 s |
| Dependent read, data in RAM (256 MB, cache miss) | 155–164 ns | 2.7 min |
| One system call (`read` of 1 byte) | ≈ 1.9 µs | 32 min |
| Durable write: `sync_all` per record | 0.24–0.41 ms | 3–5 days |
| *Typical:* network round trip inside a data centre | ≈ 0.5 ms | ≈ 6 days |
| *Typical:* network round trip across regions | 50–150 ms | 1.5–5 years |

* **Dependent vs independent loads.** Random reads whose addresses don't depend on each other took 13–16 ns in RAM, not 160 ns: the CPU overlaps independent misses. Linked lists and trees (pointer chasing) pay full latency on every step; arrays of indices don't.
* Moving one level down the table costs 10–1,000×. An optimization that removes one trip down the table beats any instruction-level tuning.

## 2. The ten techniques

| # | Technique | Do | ✗ → ✓ | Measured / where in this skill |
|---|---|---|---|---|
| 1 | **Metadata first: set the expectation** | Send sizes, counts, versions and schema in the first bytes or the first request, so the receiver can prepare (preallocate, pick a parser, reject early) | read until EOF and grow the buffer → header says `record_count = 2`, reader allocates once and bounds its loop | SKILL.md §2 header; HTTP `Content-Length`, page counts, ETags |
| 2 | **Lower the time where no work is done** | Overlap waiting with work: start I/O early, prefetch the next block while processing this one, run independent requests concurrently, keep connections and pools warm. Never sleep-poll | `await a; await b;` (sum of latencies) → start both, then await both (max of latencies) | idle CPU in a profiler = waiting; measuring.md §2 |
| 3 | **Fewer round trips** | One request that carries everything instead of one per item; fetch related data with the parent | N+1: 1 query + 1 per row → 1 query with a join or `WHERE id IN (…)` | each trip costs the full latency row above, regardless of payload size |
| 4 | **Shorter latency** | Move data closer to where it's used: register → cache → RAM → disk → network | linked list → contiguous array; remote lookup → local cache | dependent read 1.7 ns (cache) vs 160 ns (RAM): 95× |
| 5 | **Precalculate / convert once** | Do the conversion at write or build time, not at every read: store bytes not text, sorted not unsorted, the answer not the inputs | parse `"42"` on every load → store `u8` 42; compute a rate per request → lookup table built once | SKILL.md §9 (forms, the comment rule, text vs bytes 20×); constant folding in measuring.md §5 example 2 |
| 6 | **Units and scale** | Put the unit in the name, normalize per item, and compare on one scale (§1) before deciding what matters | `timeout = 30` → `timeoutSeconds = 30`; "it's fast" → `0.33 ns per read` | `codemath` skill for unit types |
| 7 | **Trade memory for speed** | Spend RAM on caches, lookup tables, indexes, precomputed results and preallocated buffers when a read repeats; trade back when memory pressure causes cache misses | recompute a hash per call → memoize in a `HashMap`; `Vec::new()` + grow → `Vec::with_capacity(count)` | trade-off: speed vs memory; measure the cache-hit ratio |
| 8 | **Keep hot data in memory** | Load once, serve from RAM; keep the working set small and contiguous so it stays in cache | read the config file per request → read at startup | 256 MB random reads: 13–16 ns; 16 KB: 3.3 ns |
| 9 | **Persist deliberately** | Choose durability per data: what must survive a crash is flushed (`sync_all`, transaction commit); the rest is written lazily or not at all | `sync_all` after every log line → append in memory, sync at a commit point | 200 × 64 B records: sync each 50–84 ms vs sync once 1.8–2.5 ms (≈ 30×) |
| 10 | **Batch** | Pay a fixed per-call cost once per batch: block reads, bulk inserts, one commit per batch, vectorized loops | 1 byte per `read` → 32 KB blocks | 7.5–8.2 s → 1.3–1.6 ms (the_optimizer_between_your_ears.md §3) |

* Batching and fewer round trips trade **latency of the first item** for **throughput**: a batch of 1,000 makes the first result wait for the other 999. Set a maximum batch size and a maximum wait (flush every 1,000 items or 50 ms, whichever comes first).
* Every cache (7, 8) needs an invalidation rule written next to it: when does this copy stop being true?

## 3. Choosing where data lives: memory vs persistence

| Data | Lives in | Survives a restart | Cost to read |
|---|---|---|---|
| Per-request scratch | stack / local `Vec` | no | cache |
| Hot shared lookups (config, rates, lookup tables) | process memory, loaded at startup | rebuilt from persistence | cache / RAM |
| Shared across processes, short-lived | external cache (Redis) | optional | network round trip |
| Must not be lost (money, orders, audit) | database or file with sync at commit | yes | disk or network round trip |

* Write path: memory first, persist at a commit point (batch of writes, one sync). Read path: memory first, persistence on a miss.
* Lossless vs lossy applies here too: a cache may drop entries (lossy, rebuildable); the persisted record may not.
