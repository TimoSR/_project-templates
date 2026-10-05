# Low-level abstractions and assembly per platform

Source: [TimoSR/2026 › AssemblySubroutines](https://github.com/TimoSR/2026/tree/main/claude/AssemblySubroutines) (Rust, C and C++ variants of one `asm_add`). The Rust version below fixes two target bugs in it (Windows GNU, macOS symbols), adds a Rust fallback, and was tested on `x86_64-pc-windows-msvc` with both the assembly and the fallback path.

## Contents
1. Low-level abstraction: one signature, many implementations
2. Calling conventions
3. Rust: build.rs + platform modules
4. C and C++: CMake
5. Pitfalls
6. Adding a subroutine

## 1. Low-level abstraction: one signature, many implementations

A low-level abstraction hides *where* code runs, not *what* it does. Callers see one safe function; the build picks the implementation for the target.

```
caller ──► add(first, second)                 one safe signature, the only public API
             └── platform::add                 chosen at build time by #[cfg(has_assembly)]
                   ├── asm_add  (MASM)         x86_64-windows-msvc    Microsoft x64
                   ├── asm_add  (GAS)          x86_64-windows-gnu     Microsoft x64
                   ├── asm_add  (GAS)          x86_64 Linux / macOS   System V
                   ├── asm_add  (GAS)          aarch64                AAPCS64
                   └── Rust reference          every other target     wrapping_add
```

Rules:
* **One file per ABI, never one per OS.** The calling convention decides the registers; Windows GNU and Windows MSVC share an ABI but not an assembler syntax.
* **The plain-Rust version is the reference.** It defines correct behaviour, runs on unsupported targets instead of failing the build, and every assembly version is tested against it.
* **`unsafe` lives in exactly one place:** the platform module's wrapper, with a `SAFETY` comment. Callers never see it.
* **The abstraction has a cost: measure it.** An `extern "C"` call is opaque to the optimizer. `add(7, 35)` compiles to `call asm_add` through assembly, but to the constant `42` through the Rust reference (measuring.md §5 example 2). Assembly earns its place only for a whole routine with real work per call.
* Prefer the cheapest layer that reaches the instruction you need: plain Rust → `core::arch` intrinsics (`#[cfg(target_arch = "x86_64")]`) → inline `asm!` → a separate assembly file.

## 2. Calling conventions

| ABI | Integer args, in order | Return | Callee must preserve | Stack rules |
|---|---|---|---|---|
| Microsoft x64 | `rcx rdx r8 r9`, then stack | `rax` | `rbx rbp rdi rsi rsp r12–r15 xmm6–xmm15` | caller reserves 32 bytes shadow space; `rsp` 16-byte aligned at `call` |
| System V AMD64 | `rdi rsi rdx rcx r8 r9`, then stack | `rax` | `rbx rbp rsp r12–r15` | `rsp` 16-byte aligned at `call`; 128-byte red zone below `rsp` |
| AAPCS64 | `x0`–`x7`, then stack | `x0` | `x19–x28`, `x29` (frame), `x30` (link) | `sp` 16-byte aligned; `ret` jumps to `x30` |

* A leaf routine that only uses argument and scratch registers needs no prologue: `mov rax, rcx` / `add rax, rdx` / `ret`.
* Using a callee-saved register means push it first and pop it before `ret`. Forgetting this corrupts the caller silently, often only in release builds.
* Types must match bit for bit: Rust `i64` = C `int64_t` = one 64-bit register. Pass structs, `i128` or `bool` only after checking the ABI document; prefer plain integers and pointers.

## 3. Rust: build.rs + platform modules

`Cargo.toml`: `edition = "2024"`, `[build-dependencies] cc = "1"`.

```text
├── asm/
│   ├── x86_64_windows/add.asm   MASM  Microsoft x64  (windows-msvc)
│   ├── x86_64_windows/add.s     GAS   Microsoft x64  (windows-gnu)
│   ├── x86_64_sysv/add.s        GAS   System V       (Linux, macOS, BSD)
│   └── aarch64/add.s            GAS   AAPCS64        (Linux, macOS)
├── build.rs                     picks the file for the target, or none
└── src/main.rs                  the abstraction + platform modules
```

```rust
// build.rs
fn main() {
    let architecture = std::env::var("CARGO_CFG_TARGET_ARCH").unwrap_or_default();
    let operating_system = std::env::var("CARGO_CFG_TARGET_OS").unwrap_or_default();
    let environment = std::env::var("CARGO_CFG_TARGET_ENV").unwrap_or_default();
    println!("cargo::rustc-check-cfg=cfg(has_assembly)");

    // The OS picks the ABI; the toolchain (env) only picks the assembler syntax.
    let assembly_file = match (architecture.as_str(), operating_system.as_str(), environment.as_str()) {
        ("x86_64", "windows", "msvc") => "asm/x86_64_windows/add.asm", // MASM, Microsoft x64
        ("x86_64", "windows", _) => "asm/x86_64_windows/add.s",        // GAS, Microsoft x64
        ("x86_64", _, _) => "asm/x86_64_sysv/add.s",                   // GAS, System V
        ("aarch64", _, _) => "asm/aarch64/add.s",                      // GAS, AAPCS64
        _ => {
            println!("cargo::warning=no assembly for {architecture}-{operating_system}-{environment}: using the Rust fallback");
            return;
        }
    };

    cc::Build::new().file(assembly_file).compile("subroutines");
    println!("cargo::rustc-cfg=has_assembly");
    println!("cargo::rerun-if-changed={assembly_file}");
}
```

* `cc` sends `.asm` to `ml64.exe` (MASM) and `.s` / `.S` to the C compiler (GAS via GCC or Clang). `.S` (capital) runs the C preprocessor first, so `#if defined(__linux__)` works inside it.
* The object lands in a static library (`libsubroutines.a` / `subroutines.lib`) that Cargo links automatically.
* `rustc-check-cfg` declares the custom cfg, so `#[cfg(has_assembly)]` doesn't warn as unknown.

```rust
// src/main.rs
// The abstraction: one safe signature. The platform implementation is chosen at build time.
pub fn add(first: i64, second: i64) -> i64 {
    return platform::add(first, second);
}

#[cfg(has_assembly)]
mod platform {
    unsafe extern "C" {
        fn asm_add(first: i64, second: i64) -> i64;
    }

    pub fn add(first: i64, second: i64) -> i64 {
        // SAFETY: asm_add reads two integer registers, touches no memory, and matches this signature on every target build.rs selects.
        return unsafe { asm_add(first, second) };
    }
}

#[cfg(not(has_assembly))]
mod platform {
    // Reference implementation: the behaviour every assembly version must match.
    pub fn add(first: i64, second: i64) -> i64 {
        return first.wrapping_add(second);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn add_matches_the_reference_including_overflow_wrap() {
        let cases: [(i64, i64); 4] = [(7, 35), (-1, 1), (0, 0), (i64::MAX, 1)];
        for (first, second) in cases {
            assert_eq!(add(first, second), first.wrapping_add(second));
        }
    }
}
```

* Edition 2024 requires `unsafe extern`.
* The test compares against `wrapping_add` directly, not against `platform::add`, so it checks the assembly on targets that have it.

The assembly, one file per ABI:

```asm
; asm/x86_64_windows/add.asm: MASM, Microsoft x64 (args rcx, rdx; return rax)
.CODE
asm_add PROC
    mov rax, rcx
    add rax, rdx
    ret
asm_add ENDP
END
```

```asm
/* asm/x86_64_sysv/add.s: GAS, System V (args rdi, rsi; return rax) */
.intel_syntax noprefix
.text
.global asm_add
.global _asm_add        /* macOS (Mach-O) prefixes C symbols with _ */
asm_add:
_asm_add:
    mov rax, rdi
    add rax, rsi
    ret
```

```asm
/* asm/aarch64/add.s: GAS, AAPCS64 (args x0, x1; return x0) */
.text
.global asm_add
.global _asm_add
asm_add:
_asm_add:
    add x0, x0, x1
    ret
```

`asm/x86_64_windows/add.s` is the System V file with `rcx` / `rdx` in place of `rdi` / `rsi`.

## 4. C and C++: CMake

```cmake
if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64)$")
    if(MSVC)
        enable_language(ASM_MASM)
        set(ASSEMBLY_FILE asm/x86_64_windows/add.asm)
    elseif(WIN32)
        enable_language(ASM)
        set(ASSEMBLY_FILE asm/x86_64_windows/add.s)
    else()
        enable_language(ASM)
        set(ASSEMBLY_FILE asm/x86_64_sysv/add.s)
    endif()
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64)$")
    enable_language(ASM)
    set(ASSEMBLY_FILE asm/aarch64/add.s)
else()
    message(FATAL_ERROR "Unsupported architecture: ${CMAKE_SYSTEM_PROCESSOR}")
endif()
add_executable(app src/main.c ${ASSEMBLY_FILE})
```

* C: `extern int64_t asm_add(int64_t first, int64_t second);`
* C++: `extern "C" int64_t asm_add(int64_t first, int64_t second);`. Without `extern "C"` the name is mangled and the link fails.
* `CMAKE_SYSTEM_PROCESSOR` is `AMD64` on Windows, `arm64` on macOS, `aarch64` on Linux.

## 5. Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Wrong result on `x86_64-pc-windows-gnu` only | build picked the System V file because env ≠ `msvc` | choose by OS first (§3 match, §4 `elseif(WIN32)`) |
| `Undefined symbols: _asm_add` on macOS | Mach-O expects a leading `_` | export both `asm_add` and `_asm_add` in the same file (§3); no macOS-only file |
| `unresolved external symbol asm_add` | file not assembled, or name mismatch | check `build.rs` output; list symbols with `dumpbin /symbols` (MSVC) or `nm` |
| Linux linker warning "missing .note.GNU-stack" | GAS file lacks the section | in a `.S` file: `#if defined(__linux__)` + `.section .note.GNU-stack,"",%progbits` + `#endif` |
| Crash or garbage later, only in release | clobbered a callee-saved register or misaligned the stack | §2 "Callee must preserve" column |
| `aarch64-pc-windows-msvc` fails to assemble | MSVC's `armasm64` doesn't accept GAS syntax | build with `clang`, add an `armasm64` file, or let that target use the Rust fallback |
| Edits to `.s` ignored | missing `rerun-if-changed` | one `cargo::rerun-if-changed` per assembly file |
| Linker error `LNK1104: cannot open file …build_script_build….exe` on Windows | path longer than 260 characters | set a short `CARGO_TARGET_DIR` or move the project up |

## 6. Adding a subroutine

1. Write it once per ABI under `asm/<abi>/`, registers taken from §2.
2. Pass every file to `cc`: `cc::Build::new().files(assembly_files).compile("subroutines")` and one `rerun-if-changed` each.
3. Add the Rust reference to `#[cfg(not(has_assembly))] mod platform`, the `extern` declaration and safe wrapper to `#[cfg(has_assembly)] mod platform`, and one public function that calls `platform::`.
4. Test the public function against the reference on every target you can build: `cargo test`, then `cargo build --target <triple>` for each other target.
5. Measure it against the Rust reference (measuring.md). Keep the assembly only if it is faster beyond the noise.
