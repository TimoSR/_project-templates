---
name: low-level-optimizations
description: Makes code faster and smaller, measured, close to the machine - design before tuning (Abrash's rules), cut waiting (latency, round trips, batching, caching, precomputation, memory vs persistence), measure with benchmarks, profilers and generated assembly (--emit asm, cargo asm, DOTNET_JitDisasm), set build flags (Cargo profiles, LTO, target-cpu, PGO, .NET ReadyToRun and Native AOT, -O flags), design binary file formats (header, endianness, RLE), measure type sizes and padding, and hide per-platform assembly (MASM / GAS, calling conventions) behind one safe signature. Use when code is slow or big, when benchmarking or profiling, when asking whether a flag or abstraction costs anything, when choosing release, AOT or compiler settings, when reducing round trips or I/O, when writing a binary or save file, asking how many bytes a type takes, or when the user mentions extern "C", .asm / .s files, registers or assembly linker errors. Not for picking a wire format between services (system-integration).
---

# Low-Level Optimizations

Known up front beats discovered at runtime, and measured beats guessed. A binary format is a spec written into the code, so the reader jumps to fixed offsets instead of parsing text; an assembly routine hands the CPU the exact instructions. Only a small subset of each field enables the implementation; this skill is that subset.

## Principles for the whole task

1. **Design first, tune last.** Better design took Abrash's checksum from 166.8 s to 2.7 s (62×); assembly on the bad design gained 8 %. Rules and evidence: [the_optimizer_between_your_ears.md](the_optimizer_between_your_ears.md).
2. **Remove waiting before speeding up work.** Find the per-item fixed cost (system call, round trip, allocation, sync, `extern` call) and batch, overlap, cache or precompute it away. Per-byte reads are about 5,500× slower than 32 KB blocks; a RAM miss costs 95× a cache hit. The latency scale and ten techniques (metadata first, idle time, round trips, latency, precalculation, units, memory for speed, in memory, persistence, batching): [waiting-and-data-movement.md](waiting-and-data-movement.md).
3. **No optimization without numbers.** Measure → read the asm or profile → change one thing → measure again with the same harness → keep it only if it beats the run-to-run spread. Tools and how to read the asm: [measuring.md](measuring.md).
4. **Write the hypothesis down first.** In measuring.md §5 the "obvious" bounds-check cost turned out not to exist.
5. **Report `before → after` with the spread.**
6. **Name the trade-off** every design takes, with its number:

   | Trade-off | Example from this skill (measured) |
   |---|---|
   | Speed vs simplicity | own 32 KB block loop instead of `BufReader`: 3× faster, more code to own |
   | Speed vs memory vs accuracy | precomputed CRC table: 1 KB of binary for one lookup per byte; `f32` instead of `f64`: half the memory, about 7 significant digits instead of about 16 |
   | Lossless vs lossy | RLE gives back every byte; dropping vowels or rounding floats doesn't |
   | Compression vs time | RLE / zstd shrink the file but cost CPU time on every read; raw bytes load in 1.4 ms |
7. **Every precalculated value carries a comment** naming its source (formula, inputs or generator) and how to regenerate or check it (§9). An unexplained constant is an answer nobody can verify.

Write all code in the `c-like-coding-style` skill: explicit `return`, guard clauses, no `unwrap` in the reader.

## 1. Decide: is binary worth it?

| Pick binary when | Stay with text (JSON, CSV) when |
|---|---|
| Size or load time is measured and matters (game saves, telemetry, caches, large arrays of numbers) | People read or hand-edit the file |
| The data is mostly numbers, fixed-size records or repeated values | Another team or vendor consumes it |
| One program writes it and the same program reads it | The schema changes often and nobody owns versioning |

* Binary is smaller and faster because the reader already knows the layout: `42` as text is 2 bytes plus a delimiter, plus parsing; as `u8` it is 1 byte at a known offset.
* Trade-off: speed and size over simplicity and readability. State that when you propose it.

## 2. Layout: header, then payload

```
offset  bytes  field          example (hex)   why
0       4      magic          53 43 4F 52     "SCOR": reject the wrong file before reading more
4       2      version u16    01 00           old readers refuse new files instead of misreading them
6       4      record_count   02 00 00 00     metadata: the reader preallocates and knows when to stop
10      …      records        …               player_id u32 | name_length u16 | name UTF-8 | points i32
```

Rules:
* **Magic first, version second.** Magic is 4 ASCII bytes readable in a hex dump. The version is checked before any field it governs.
* **Fixed endianness: little-endian.** `to_le_bytes` / `from_le_bytes` on both sides. Never write native order.
* **Explicit widths.** `u16`, `u32`, `i64`, never `usize`, `int` or `long`: their size depends on the platform.
* **Variable data is length-prefixed.** Write the length in bytes, then the bytes. No terminators to scan for.
* **Counts and sizes in the header.** The reader bounds every loop by them and preallocates, capped by what the remaining bytes can hold: a forged `record_count = 0xFFFFFFFF` must not allocate gigabytes.
* **Never cast a struct's memory to bytes** (`transmute`, `memcpy` of a `struct`): padding and field order are compiler choices. Write each field explicitly.
* **The reader distrusts every byte.** Bounds-check each read, cap lengths against the remaining bytes, cap decompressed output at the size the header promises, reject trailing bytes. A bad file returns `None`, never panics.

## 3. Text inside binary: encodings

| Encoding | Bytes per character | Use |
|---|---|---|
| ASCII | 1 (values `0x00`–`0x7F`; `G` = `0x47`) | magic numbers, tags, fixed identifiers |
| UTF-8 | 1–4 (ASCII is unchanged) | default for all stored text |
| UTF-16 | 2 or 4, needs a byte order (BOM `FF FE` = LE) | only to match Windows APIs or an existing format |

* The length prefix counts **bytes, not characters**: `"Søren"` is 5 characters and 6 UTF-8 bytes.
* Validate on read: `String::from_utf8(...)` returns an error for invalid bytes. Map it to `None`.

## 4. Make it smaller: cheapest step first

Measure the file size after every step and keep a step only if it pays.

1. **Precompute.** Store the answer, not the inputs to compute it. A lookup table baked into the file or code replaces work at load time (§9).
2. **Smaller representation.** Repeated strings become an enum or an index into a string table stored once in the header: `"warrior"` × 10,000 → one table entry + 10,000 × `u8`.
3. **Narrower types.** A value that fits in `u8` is not stored as `u32`. Small counts can use a varint.
4. **Run-length encoding** for long runs of one byte (tiles, masks, sparse arrays). Pairs of `(count, byte)`, count `1..=255`.
   * RLE **doubles** data without runs (`ABCD` → 8 bytes). Test it on real data.
5. **General compression** (deflate, zstd) over the whole payload, flagged in the header so the reader knows to decompress.

* Lossless is the default. Lossy tricks (dropping vowels, rounding floats, stripping whitespace and comments from text) are valid only when the reader never needs the original back. Say which one you chose.

## 5. Memory sizes: measure, don't guess

Smaller values mean more of them fit in a cache line (64 bytes), which is often a bigger speed win than fewer instructions. Print sizes with `std::mem::size_of::<T>()` and `std::mem::align_of::<T>()`. Measured on 64-bit (`x86_64-pc-windows-msvc`):

| Type | Bytes | Why |
|---|---|---|
| `u8` / `bool` | 1 | `bool` is guaranteed 1 byte in Rust, values `0x00` / `0x01` only |
| `i32` / `char` | 4 | `char` is a Unicode scalar, not a byte |
| `f64` / `usize` / `*const T` / `&T` / `Box<T>` | 8 | pointer-sized: 4 on 32-bit targets, so never write `usize` to a file |
| `&str` / `&[T]` | 16 | pointer + length |
| `String` / `Vec<T>` | 24 | pointer + capacity + length; the contents live on the heap |
| `Option<u32>` | 8 | tag + padding to `u32` alignment |
| `Option<&T>` / `Option<Box<T>>` | 8 | free: null is the `None` value |

Padding: each field sits at a multiple of its own alignment.

```rust
#[repr(C)] struct Unordered { flag: u8, id: u64, kind: u8 } // 1 + 7 pad + 8 + 1 + 7 pad = 24
#[repr(C)] struct Ordered { id: u64, flag: u8, kind: u8 }   // 8 + 1 + 1 + 6 pad = 16
```

* Plain Rust structs (no `repr`) are reordered by the compiler: `Unordered` without `#[repr(C)]` is 16. Only `#[repr(C)]` (needed for FFI, §7) fixes field order, so order its fields largest first.
* Padding bytes hold garbage, which is one more reason §2 bans casting a struct to bytes.
* Pin a size the code depends on at compile time: `const _: () = assert!(std::mem::size_of::<Ordered>() == 16);`

## 6. Proof: tests that pin the bytes

Every format gets three tests, written per the `tests-as-documentation` skill:

| Test | Proves |
|---|---|
| Round trip: `read(write(x)) == x`, including non-ASCII text | writer and reader agree |
| Golden bytes: the header equals a literal byte array | the layout table in §2 is true, so the file stays readable by other versions |
| Rejection: wrong magic, truncated file, trailing bytes → `None` | the reader survives corrupt input |

The tested reference implementation (writer, reader, RLE and these tests) is [format-example.md](format-example.md).

## 7. Low-level abstractions and assembly per platform

One safe signature, a per-platform implementation chosen at build time, and a plain-Rust reference that defines correct behaviour and runs where no assembly exists:

```
add(first, second) ──► platform::add ──┬── asm_add  MASM  x86_64-windows-msvc  (rcx, rdx → rax)
                                       ├── asm_add  GAS   x86_64 System V      (rdi, rsi → rax)
                                       ├── asm_add  GAS   aarch64              (x0, x1 → x0)
                                       └── Rust reference: every other target
```

* The calling convention picks the file, never the OS name alone: Windows GNU and MSVC share one ABI.
* Abstractions cost something: an `extern "C"` call can't be inlined. `add(7, 35)` is `call asm_add` through assembly and the constant `42` through Rust. Prefer the cheapest layer: plain Rust → `core::arch` intrinsics → inline `asm!` → assembly file.
* Layout, `build.rs`, calling-convention table, CMake, pitfalls: [assembly-subroutines.md](assembly-subroutines.md). Read it before writing any assembly file.

## 8. Build settings

Cargo profiles (`lto`, `codegen-units`, `panic`, `opt-level`), `target-cpu` levels, PGO, .NET Release / ReadyToRun / Native AOT, and GCC / Clang / MSVC flags, each with measured effects: [build-settings.md](build-settings.md).

* Measured here: fat LTO + 1 codegen unit cut the binary 9.5 % with no speed change; `target-cpu=native` switched to AVX2 but a memory-bound loop barely moved; Native AOT cut .NET startup from 77.7 to 14.4 ms.
* `target-cpu=native` only for code that runs where it was built; ship a fixed level such as `x86-64-v3`.

## 9. Precalculate: put the answer in the code

Removing the need to compute something, by giving the answer up front, saves the work at every run. Convert at write time or compile time, never at every read.

| Form | ✗ computed at runtime | ✓ predefined |
|---|---|---|
| Byte literal | parse `"53 43 4F 52"` or build the magic at startup | `*b"SCOR"`, `[0x53, 0x43, 0x4F, 0x52]` |
| Compile-time table | fill a `Vec` on first use | `const CRC_TABLE: [u32; 256] = build_crc_table();` (a `const fn`): stored as data in the binary |
| Converted data | store `"4294967295\n"` as text and parse on load | store `u32` little-endian bytes (§2) |
| Generated asset | compute a large table in `main` | `build.rs` writes it to `OUT_DIR`, the code reads it with `include_bytes!` |

The comment rule: what it is, where it comes from, how to check it.

```rust
// ✗ a magic answer: nobody can check it or regenerate it
const SECONDS_PER_YEAR: u64 = 31_556_952;

// ✓ source + check
// Gregorian mean year: 365.2425 days × 86,400 seconds per day.
// Checked by the test seconds_per_year_matches_formula.
const SECONDS_PER_YEAR: u64 = 31_556_952;

// CRC-32 (IEEE 802.3), reflected polynomial 0xEDB8_8320, one entry per byte value.
// Generated by build_crc_table() at compile time; entry 1 = 0x7707_3096.
const CRC_TABLE: [u32; 256] = build_crc_table();
```

* Add a test that recomputes the value from its formula whenever that is cheap: the comment says what it should be, the test proves it.

Measured:
* **Text vs bytes (1,000,000 `u32`):** text 10.7 MB, 28–45 ms to parse; bytes 4.0 MB, 1.4–1.7 ms to load. About 20× faster and 2.7× smaller, with identical values.
* **The compiler precalculates too.** A bitwise CRC-32 loop (8 shifts per byte) compiled to the **same instructions** as the hand-written table version: LLVM recognized the loop and generated its own `.crctable`. Read the asm (measuring.md §4) before precomputing by hand. What the compiler can't do is convert data it never sees, such as files or inputs. That part is yours.
