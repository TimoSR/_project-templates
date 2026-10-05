# Data-driven optimization: tools, metrics, generated assembly

Every number and assembly excerpt below was measured on `x86_64-pc-windows-msvc`, Rust 1.97, `--release`.

## Contents
1. The loop
2. CLI tools
3. In-code metrics: the benchmark harness
4. Reading the generated assembly
5. Worked examples

## 1. The loop

```mermaid
flowchart LR
    A[Measure: baseline numbers] --> B[Read the asm / profile: find the cause]
    B --> C[Change one thing]
    C --> D[Measure again, same harness]
    D -->|faster beyond the noise| E[Keep, record before → after]
    D -->|within the noise| F[Revert]
    F --> B
```

* Write the hypothesis down before measuring ("the bounds check costs time"). §5 example 1 shows why: the obvious hypothesis was wrong.
* Report `before → after` with the spread, not one number: `212.7 µs (172–290) → 212.8 µs (174–301)` = no change.

## 2. CLI tools

| Question | Tool | Command |
|---|---|---|
| What did the compiler emit? | rustc | `cargo rustc --release -- --emit asm -C "llvm-args=-x86-asm-syntax=intel"` → `target/release/deps/<crate>.s` |
| | cargo-show-asm | `cargo install cargo-show-asm`, then `cargo asm <crate>::<function>`: one function, demangled |
| | Compiler Explorer | godbolt.org with `-C opt-level=3`: share a snippet's asm |
| | disassemble a binary | `objdump -d -M intel` (Linux), `llvm-objdump -d`, `otool -tv` (macOS), `dumpbin /disasm` (MSVC) |
| Which symbols exist? | | `nm` (Linux / macOS), `dumpbin /symbols` (MSVC) |
| How long does the whole program take? | hyperfine | `hyperfine --warmup 3 'target/release/app'`: mean, spread, comparison of two commands |
| How long does one function take? | criterion crate | `cargo bench` with `criterion` in `[dev-dependencies]`: statistics and regression detection |
| Where does the time go? | sampling profiler | `samply record target/release/app` (all OS), `perf record` + `perf report` (Linux), Instruments (macOS), Windows Performance Analyzer (Windows) |
| Is it cache misses or branches? | hardware counters | `perf stat -e cycles,instructions,cache-misses,branch-misses target/release/app` (Linux) |
| | cache simulation | `valgrind --tool=cachegrind target/release/app` (Linux) |
| What makes the binary big? | cargo-bloat | `cargo bloat --release -n 20`: largest functions |

* Always measure `--release`. Debug builds are often 10× or more slower, in different places, so their profile points at the wrong code.
* Add `debug = 1` under `[profile.release]` so profilers and `.s` files show function names and source lines. It doesn't change the generated code.

## 3. In-code metrics: the benchmark harness

Use criterion when the crate allows dependencies. Without them, this harness is enough to compare variants:

```rust
const BENCHMARK: BenchmarkConfig = BenchmarkConfig {
    value_count: 1_000_000,
    warmup_runs: 5,
    measured_runs: 31, // odd, so the median is one real run
};

pub struct Timing {
    pub minimum_nanoseconds: u128,
    pub median_nanoseconds: u128,
    pub maximum_nanoseconds: u128,
}

pub fn summarize(samples: impl Into<Vec<u128>>) -> Option<Timing> {
    let mut samples: Vec<u128> = samples.into();
    if samples.is_empty() { return None; }
    samples.sort();
    return Some(Timing {
        minimum_nanoseconds: samples[0],
        median_nanoseconds: samples[samples.len() / 2],
        maximum_nanoseconds: samples[samples.len() - 1],
    });
}

// In main: interleave the variants so CPU clock and cache changes hit both equally.
for run in 0..(BENCHMARK.warmup_runs + BENCHMARK.measured_runs) {
    let start = std::time::Instant::now();
    std::hint::black_box(sum_first(std::hint::black_box(&values), std::hint::black_box(values.len())));
    let sum_first_nanoseconds = start.elapsed().as_nanos();

    let start = std::time::Instant::now();
    std::hint::black_box(sum_all(std::hint::black_box(&values)));
    let sum_all_nanoseconds = start.elapsed().as_nanos();

    if run < BENCHMARK.warmup_runs { continue; }
    sum_first_samples.push(sum_first_nanoseconds);
    sum_all_samples.push(sum_all_nanoseconds);
}
```

| Rule | Why (measured) |
|---|---|
| `std::hint::black_box` on inputs and on the result | without it the optimizer may compute the answer at compile time or delete the call (§5 example 2 shows the folding) |
| `#[inline(never)]` on each variant | keeps it a separate function, so it shows up by name in the asm and the profiler |
| Warm-up runs, then the **median** of an odd count | the first runs pay for page faults and cold caches; the maximum was nearly 3× the median |
| Interleave variants in one process | separate processes gave medians from 133 to 280 µs for the same binary; interleaved, the two variants matched within 0.2 % |
| Print min, median and max | a difference smaller than the min–max spread is noise |
| Metrics beyond time: bytes written, items per second, `size_of`, allocation count | file size and memory layout are measured, not assumed (SKILL.md §4, §5) |

## 4. Reading the generated assembly

Find the function by name in the `.s` file (mangled: `_RNvCs…2dd7sum_all`), and skip the `.cv_` / `.cfi_` / `.seh_` debug lines.

| Look for | Means | Usually good or bad |
|---|---|---|
| `call …panic_bounds_check` | an index check that can fail | bad **inside** the loop body; harmless when it runs once before the loop |
| `xmm` / `ymm` registers with `paddq`, `paddd`, `movdqu` | vectorized: several elements per instruction | good for bulk loops |
| loop body processing 16 bytes per step (`add r9, 16`) | vectorized or unrolled | good |
| `call` to a small function inside a hot loop | not inlined | bad: check `#[inline]`, generics, crate boundaries |
| `call asm_add` / any `extern "C"` call | opaque: the optimizer can't inline or fold it | cost per call (§5 example 2) |
| a constant (`mov …, 42`) where you expected a computation | constant-folded | good in real code; in a benchmark it means the input needs `black_box` |
| `sub rsp, N` / `push` / `pop` | stack frame, saved registers | fine once; a cost in tiny hot functions |
| `div` / `idiv` | integer division, tens of cycles | the divisor is only known at runtime (compilers already turn constant divisors into shifts or a multiply); make it a compile-time constant, ideally a power of two |

## 5. Worked examples

**Example 1: the bounds check that wasn't there.** Hypothesis: `values[index]` with an unrelated `count` keeps a bounds check per element, so it is slower than looping to `values.len()`.

```rust
pub fn sum_first(values: &[u32], count: usize) -> u64 { /* for index in 0..count { total += values[index] as u64; } */ }
pub fn sum_all(values: &[u32]) -> u64 { /* for index in 0..values.len() { … } */ }
```

```asm
; sum_first: one check BEFORE the loop, then the same vector loop as sum_all
    lea  rax, [r8 - 1]          ; last index = count - 1
    cmp  rdx, rax               ; values.len() <= last index?
    jbe  .LBB12_11              ; → call panic_bounds_check (cold path)
.LBB12_7:                       ; hot loop: 4 u32 per step, no checks
    movq xmm3, qword ptr [rcx + 4*rax]
    paddq ...
```

Result: LLVM hoisted the check out of the loop and vectorized both. Interleaved median `212.7 µs` vs `212.8 µs`. **No change: don't "optimize" it.**

**Example 2: the abstraction that stopped the optimizer.** `add(7, 35)` through the assembly subroutine vs the Rust fallback (assembly-subroutines.md §1):

```asm
; assembly path: an opaque call, executed at runtime
    mov  ecx, 7
    mov  edx, 35
    call asm_add
; Rust fallback: computed at compile time, no call at all
    mov  qword ptr [rsp + 32], 42
```

Result: for a tiny operation, the hand-written assembly is **slower** than plain Rust, because a call across the language boundary can't be inlined, folded or vectorized. Assembly pays off only for a whole routine with real work per call.
