# The optimizer between your ears

Principles from chapter 1 of Michael Abrash's *Graphics Programming Black Book* ([online](https://www.jagregory.com/abrash-black-book/#chapter-1-the-best-optimizer-is-between-your-ears)), paraphrased, with his measurements and a 2026 reproduction. Main point: **design decides speed; compilers and assembly only polish a good design.**

## Contents
1. The seven rules
2. The evidence: Abrash's checksum, 1990s
3. The evidence: the same experiment, 2026
4. What the numbers teach

## 1. The seven rules

| # | Rule (paraphrased) | In practice |
|---|---|---|
| 1 | Know the objective | Write down what "fast enough" means before touching code: `startup < 50 ms`, `1 GB in < 2 s` |
| 2 | Design the whole program first | Data structures and the parts that pass data between them are chosen together, not one function at a time |
| 3 | Design an algorithm per part | Pick each part's algorithm and data layout on purpose: O(n) vs O(n²), block vs byte |
| 4 | Know how the machine does each task | Know what a library call costs underneath: a system call, an allocation, a lock, a cache miss. Read the asm and the library source; don't guess |
| 5 | Know where it matters | Profile to find the time-critical part and leave the rest readable |
| 6 | Always consider alternatives | The first working design is rarely the fastest; ask "what if I didn't do this per item?" |
| 7 | Then optimize hard | Only once 1–6 are done: compiler flags (build-settings.md), intrinsics, assembly |

## 2. The evidence: Abrash's checksum, 1990s

16-bit checksum of a 362,293-byte file on a 10 MHz AT, disk cache off. Seconds:

| Design | C, no opt | C, opt | Assembly | Optimization gain |
|---|---|---|---|---|
| Listing 1.1: `read()` one byte per call (a DOS call per byte) | 166.8 | 165.8 | 155.1 | 1.08× |
| Listing 1.4: `getc()`, the C library buffers | 13.6 | 13.5 | — | 1.01× |
| Listing 1.5: own 32 KB block, loop over it | 5.5 | 3.4 | 2.7 | 2.04× |

* Better design: 166.8 → 2.7 s, **62×**. Assembly on the bad design: **8 %**.
* Compiler optimization only mattered once the design stopped wasting time in DOS (row 3).
* Abrash notes that with the file already in the disk cache, the assembly version ran three times as fast as the C one: polish pays only when nothing bigger is in the way.

## 3. The evidence: the same experiment, 2026

The same three designs in Rust, 4 MiB file, `--release`, Windows 11, x86_64. Three runs:

| Design | Code | Time |
|---|---|---|
| One system call per byte | `file.read(&mut [0u8; 1])` in a loop | 7,489–8,201 ms |
| The library buffers, we ask per byte | `BufReader::new(file).bytes()` | 3.8–5.3 ms |
| Own 32 KB block, plain loop | `file.read(&mut block)`, then `for index in 0..read_count` | 1.27–1.57 ms |

```rust
// Design 3: one system call per 32 KB, then pure CPU work on bytes already in memory
loop {
    let read_count = file.read(&mut block).ok()?;
    if read_count == 0 { break; }
    for index in 0..read_count {
        checksum = checksum.wrapping_add(block[index] as u16);
    }
}
```

* The gap grew: per-byte system calls are now about **5,500×** slower than block reads (Abrash: 62×), because CPUs got much faster and system calls didn't.
* The same lesson applies to anything with a fixed cost per call: database round trips (N+1 queries), HTTP requests, allocations, locks, `extern "C"` calls (measuring.md §5 example 2).

## 4. What the numbers teach

* **Find the per-item fixed cost and batch it away.** That is design, and it is where the 100–1,000× gains are.
* **Measure, don't assume.** Abrash found the DOS-per-byte cost by stepping through the library in a debugger. Today: the profiler and the generated asm (measuring.md).
* **"The library is already optimized" is a hypothesis.** Libraries are written to be general and portable. Here the library buffer was still 3× slower than a plain block loop.
* **Assembly is the finishing touch.** It gave 8 % on the bad design and about 25 % on the good one (3.4 → 2.7 s).
* **Stop when the objective from rule 1 is met.** Fast enough is a number, not a feeling.
