# Build settings: compiler flags, profiles, native compilation

Flags are rule 7 of [the_optimizer_between_your_ears.md](the_optimizer_between_your_ears.md): free speed or size once the design is right, and never a fix for a bad design. Measure every flag change with the same harness (measuring.md). Measurements below were taken on Windows 11, x86_64, Rust 1.97 and .NET SDK 10.0.302.

## Contents
1. Rust: Cargo profiles and RUSTFLAGS
2. .NET: Release, tiered JIT, ReadyToRun, Native AOT
3. C and C++: GCC, Clang, MSVC, CMake
4. Which knob for which goal

## 1. Rust: Cargo profiles and RUSTFLAGS

```toml
# Cargo.toml
[profile.release]
debug = "line-tables-only"  # function names + lines for profilers and .s files; code unchanged

[profile.dist]              # cargo build --profile dist: the shipped binary
inherits = "release"
lto = "fat"                 # optimize across crates; slower link
codegen-units = 1           # one unit = more inlining; slower build (release default: 16)
panic = "abort"             # no unwinding tables; a panic kills the process, catch_unwind stops working
strip = true                # drop symbols from the binary
```

| Setting | Values | Effect |
|---|---|---|
| `opt-level` | `0` dev, `3` release, `"s"` / `"z"` size | `"z"` for size-bound targets (WASM, embedded); measure, it is sometimes faster too |
| `lto` | `false` (default, local only), `"thin"`, `"fat"` | cross-crate inlining; biggest effect when hot code calls into dependencies |
| `codegen-units` | `16` (release), `1` | `1` lets LLVM see all code at once |
| `panic` | `"unwind"`, `"abort"` | smaller binary |
| `debug` | `0`, `"line-tables-only"`, `1`, `2` | profiler readability; doesn't change the generated code |
| `overflow-checks` | off in release by default | turn on in release only for money or index arithmetic that must never wrap silently |

CPU features through `RUSTFLAGS` or `.cargo/config.toml`:

```toml
# .cargo/config.toml
[target.x86_64-pc-windows-msvc]
rustflags = ["-C", "target-cpu=x86-64-v3"] # AVX2 baseline: CPUs from about 2015 on
```

* `-C target-cpu=native` uses every feature of **this** machine. The binary can crash with an illegal instruction on an older CPU, so use it only for code that runs where it was built. To ship, pick a level (`x86-64-v2`, `x86-64-v3`), or keep the baseline and check at runtime with `is_x86_feature_detected!("avx2")`.
* PGO: build instrumented, run a realistic workload, rebuild with the profile. `cargo install cargo-pgo`, then `cargo pgo build`, run the binary, then `cargo pgo optimize`.

Measured on the sum loop from measuring.md (4 MB `u32` array, memory-bound):

| Build | Binary | Generated loop | Median time |
|---|---|---|---|
| `release` | 145,408 B | SSE2: `paddq xmm`, 4 values per step | 129–186 µs |
| `dist` (fat LTO, 1 CGU, abort, strip) | 131,584 B (−9.5 %) | same | 129–139 µs: no change |
| `release` + `target-cpu=native` | 147,456 B | AVX2: `vpaddq ymm`, 8 values per step | 122–140 µs (best run 98 vs 125 µs) |

* Wider vectors made the best case about 20 % faster, but memory bandwidth limits the median. The data layout matters more than the flag (rule 3).

## 2. .NET: Release, tiered JIT, ReadyToRun, Native AOT

| Mode | csproj / CLI | What runs | Use for |
|---|---|---|---|
| Debug | `-c Debug` | JIT with optimizations off | never measure this |
| Release + tiered JIT (default) | `-c Release` | quick JIT first, hot methods recompiled with Dynamic PGO (on by default since .NET 8) | servers: best peak speed after warm-up |
| ReadyToRun | `<PublishReadyToRun>true</PublishReadyToRun>` | precompiled code + IL; hot methods still re-JIT with PGO | large apps that need faster startup and must keep the JIT, reflection and full framework |
| Native AOT | `<PublishAot>true</PublishAot>` | one native executable, no JIT, no runtime installed | CLIs, serverless, containers: fastest startup and lowest memory |

Measured on a small console app (`win-x64`, median of 15 starts):

| Mode | Files | Startup |
|---|---|---|
| JIT, framework-dependent | 166,400 B, plus the installed runtime | 77.7 ms |
| ReadyToRun | 178,688 B, plus the installed runtime | 74.0 ms: no gain for a tiny app, since R2R pays off with lots of startup code |
| Native AOT | 935,424 B, self-contained | **14.4 ms** (5.4× faster) |

Native AOT rules:
* Needs the platform linker: on Windows the "Desktop development with C++" workload. If publishing fails with `'vswhere.exe' is not recognized`, add `C:/Program Files (x86)/Microsoft Visual Studio/Installer` to `PATH`.
* No runtime code generation: `Reflection.Emit`, runtime-compiled expression trees and unannotated reflection break. Treat every `IL2xxx` (trimming) and `IL3xxx` (AOT) publish warning as an error. Set `<IsAotCompatible>true</IsAotCompatible>` on libraries to see them at build time.
* No JIT means no Dynamic PGO: long-running servers can be **slower** at peak than tiered JIT. Measure throughput, not just startup.
* Tuning: `<OptimizationPreference>Speed</OptimizationPreference>` (or `Size`), `<IlcInstructionSet>x86-x64-v3</IlcInstructionSet>` for an AVX2 baseline.
* Check the framework stack before choosing it: an app built on reflection-heavy libraries (an ORM with runtime queries, GraphQL schema discovery) usually can't go AOT. ReadyToRun is the safe startup option there.

Other .NET switches:

| Switch | Effect | Caution |
|---|---|---|
| `<InvariantGlobalization>true</InvariantGlobalization>` | drops ICU culture data: smaller, faster startup | breaks culture-specific formatting and sorting (Danish dates, currency) |
| `<PublishTrimmed>true</PublishTrimmed>` | removes unused framework code (self-contained only) | same reflection warnings as AOT |
| `<ServerGarbageCollector>` / `<ConcurrentGarbageCollection>` | GC per core / background GC | ASP.NET Core already uses server GC |
| `<TieredPGO>false</TieredPGO>` | disables Dynamic PGO | only to compare; the default is on |
| `[MethodImpl(MethodImplOptions.AggressiveInlining)]`, `[SkipLocalsInit]` | force inlining / skip zeroing stack locals | measure each; `SkipLocalsInit` needs `<AllowUnsafeBlocks>` |

See the JIT's asm without tools, like `--emit asm` in Rust:

```bash
DOTNET_JitDisasm="*Main*" DOTNET_TieredCompilation=0 dotnet run -c Release
```

* `TieredCompilation=0` shows the fully optimized code at once; otherwise the first listing is the quick unoptimized tier.
* Measured: the JIT kept the 1,000-iteration sum loop (`add rcx, rdx` / `cmp eax, 0x3E8` / `jl`) where LLVM folds such loops to a constant. Don't assume one compiler's optimizations in another.
* For benchmarks use BenchmarkDotNet; `[DisassemblyDiagnoser]` adds the asm of each benchmark to the report.

## 3. C and C++: GCC, Clang, MSVC, CMake

| Goal | GCC / Clang | MSVC |
|---|---|---|
| Release optimization | `-O2` (`-O3` more aggressive, `-Os` size) | `/O2` (`/O1` size) |
| Link-time optimization | `-flto` | `/GL` + linker `/LTCG` |
| CPU features | `-march=native`, `-march=x86-64-v3` | `/arch:AVX2` |
| Profile-guided | `-fprofile-generate`, run, `-fprofile-use` | `/GENPROFILE`, run, `/USEPROFILE` |
| Debug info in release | `-g` | `/Zi` |
| Emit asm | `-S -masm=intel` | `/FA` |

```cmake
set(CMAKE_BUILD_TYPE Release)                      # -O3 -DNDEBUG (GCC/Clang), /O2 /DNDEBUG (MSVC)
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION ON)         # LTO on every compiler CMake supports
```

## 4. Which knob for which goal

| Goal | First | Then |
|---|---|---|
| Faster hot loop | design and data layout (rule 3) | `target-cpu` level, LTO + 1 codegen unit, PGO |
| Faster startup | do less at startup (lazy init) | .NET: Native AOT, else ReadyToRun |
| Smaller binary | drop dependencies | `opt-level = "z"`, `panic = "abort"`, `strip`; .NET: trimming |
| Faster peak throughput of a server | fix N+1 round trips, allocations, locks | keep tiered JIT + Dynamic PGO; Rust: PGO |
