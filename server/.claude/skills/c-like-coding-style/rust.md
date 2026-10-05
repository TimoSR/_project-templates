# Rust in C-like style

## Contents
1. API design
2. Modules: crate and file layout
3. No unwrap
4. Lint and format config
5. Imports
6. Full example
7. Tests

## 1. API design

Design the call site first: a caller using the API writes what a C# caller would, meaning literals and values. Every ownership decision lives behind the signature.

| Caller writes | ✗ API that forces it | ✓ API |
|---|---|---|
| `Greeter::new("hello")` | `new(greeting: String)` → `Greeter::new(String::from("hello"))` | `new(greeting: impl Into<String>)` |
| `greeter.greet("world")` | `greet(&self, name: &String)` → `greeter.greet(&name)` | `greet(&self, name: impl Into<String>)` |
| `round_grades([73, 67])` | `round_grades(grades: &Vec<i32>)` → `round_grades(&vec![73, 67])` | `round_grades(grades: impl Into<Vec<Grade>>)` |
| `greet_all(["world", "Ada"])` | `greet_all(names: Vec<String>)` → `vec!["world".to_string(), …]` | `greet_all(names: impl IntoIterator<Item = impl Into<String>>)` |
| `let greeter = Greeter::new("hello");` | `struct Greeter<'a> { greeting: &'a str }`: the lifetime spreads into every caller's type | `struct Greeter { greeting: String }` |
| `parse_grade("73")` | `parse::<Grade>("73")`: the caller spells a generic | `parse_grade(text: impl Into<String>) -> Option<Grade>` |

Rules:
* **Values in.** Text is `impl Into<String>`, lists are `impl Into<Vec<T>>`, numbers and other `Copy` values go by value. Convert on the first line, with the type written out (inference needs it): `let name: String = name.into();`.
   * `impl Into<String>` is the one default for text, even when the function only reads it. This takes the simplicity side of speed vs simplicity: one allocation per call. Switch a read-only parameter to `impl AsRef<str>` only after measuring a hot path.
* **Values out.** Return `String`, `Vec<T>` or the struct itself. Never return a reference tied to an input.
* **No lifetimes and no turbofish** (`::<T>`) in anything a caller touches. `impl Trait` in argument position keeps generics out of the call site.
* **Constructors.** `pub fn new(required values) -> Greeter` takes only the values the type can't work without, and returns the concrete type name.
* **Private fields.** Callers read through getters that return an owned clone or a `Copy` value: `pub fn greeting(&self) -> String`. Simplicity over speed again: avoid the clone in a hot path only after measuring.
* **Shared or cross-thread state** lives inside the type (`Arc<Mutex<…>>`), and the type derives `Clone`, so the caller just clones a handle.
* **`&self` by default.** Use `&mut self` only when the method really changes state; the caller's `let mut` then shows that the value changes.
* **Domain names in signatures:** `grade: Grade`, not `grade: i32`. A value with a unit is a newtype, not an alias, so meters can't be passed where seconds are expected: `#[repr(transparent)] pub struct Length(pub(crate) f64);` with one constructor per unit (`Length::kilometers(5.0)`) and one `to_<unit>()` per unit.
* **Failure is a value.** Return `Option<T>` when the result may be absent, `bool` for "applied or not", and `Result<T, DomainError>` when the caller needs to know why (see section 2, rule 8). See section 3, "No unwrap".
* **Shape.** A unit struct + `impl` for stateless features (`GradingStudents::round_grades`); a struct with private fields + `new` for stateful ones (`Greeter::new("hello").greet("world")`).

## 2. Modules: crate and file layout

Folders organize the code; `pub use` re-exports decide the public API. The caller sees one short path per concept (`physics::length`), never the folder tree behind it (`physics::units::length::quantity`).

```
Physics/                          workspace root = the caller
├── Cargo.toml                    [dependencies] physics = { path = "physics" }
├── rustfmt.toml, justfile
├── src/main.rs                   uses the library like any outside user would
└── physics/                      the library = the API
    ├── Cargo.toml                [lints.rust] ambiguous_glob_reexports = "allow"
    └── src/
        ├── lib.rs                façade: private `mod`s + `pub use`
        ├── internal/             crate-wide helpers: error.rs, display.rs, macros.rs, tests/
        └── units/
            ├── mod.rs            `pub mod` per concept + renaming re-exports
            └── length/           one folder per concept
                ├── mod.rs        private `mod`s + `pub use`
                ├── quantity.rs   newtype, unit constructors, to_<unit>(), unit enum
                ├── operators.rs  std::ops impls (Length / Time → Velocity)
                ├── display.rs    fmt::Display + display_<unit>() helpers
                ├── calculations.rs  formulas: calculate, checked_calculate
                └── tests/        one file per source file + root_function.rs
```

Rules:
1. **Library and caller are separate crates.** The binary depends on the library through a path dependency, so it can only use what is `pub` and re-exported: you use your own API from the outside.
2. **Every `mod` is private; re-exports publish.**
   ```rust
   // lib.rs
   mod internal;
   mod units;

   pub use internal::*;
   pub use units::*;
   ```
   The same pattern repeats in every `mod.rs`: `mod quantity;` … then `pub use quantity::*;`. A file that only holds trait impls (`operators.rs`) is not re-exported, because impls apply wherever the type is visible.
3. **One folder per concept, one file per role:** `quantity`, `operators`, `display`, `calculations`, `tests`. Every concept folder has the same files, so you know where to look.
4. **Visibility ladder.** Choose the narrowest level that works:

   | Level | Reachable from | Use for |
   |---|---|---|
   | `pub` + re-exported up to `lib.rs` | outside users | the API |
   | `pub(crate)` | anywhere in this crate | shared helpers (`validate_finite`, `format_unit_value`), the newtype's inner field `Length(pub(crate) f64)`, crate-only macros |
   | `pub` inside a private `mod` that isn't re-exported | same as `pub(crate)` | avoid; write `pub(crate)` so the intent is visible |
   | no modifier | the file and its child modules | implementation details |

   A type that appears in a public signature must be public too: `internal/mod.rs` has `pub use error::*;` (`QuantityError` is returned by `checked_calculate`) but `pub(crate) use display::*;`.
5. **Rename at the façade.** Files use role verbs, and `units/mod.rs` gives them domain names:
   ```rust
   pub use velocity::calculate as velocity;
   pub use velocity::checked_calculate as checked_velocity;
   ```
   The caller writes `velocity(distance, time)`, not `velocity::calculate(distance, time)`. A long internal path can collapse to one word the same way: `pub use abc::deep::path::function as short_name;`.
6. **Two entry points per concept.** A module function delegates to the associated function, so both `length::kilometers(5.0)` and `Length::kilometers(5.0)` work:
   ```rust
   pub const fn kilometers(value: f64) -> Length { return Length::kilometers(value); }
   ```
7. **The caller imports modules, then calls through them:**
   ```rust
   use physics::length;
   use physics::time;
   use physics::velocity;

   fn main() {
       let distance = length::kilometers(5.0);
       let time = time::milliseconds(9_580.0);
       let velocity = velocity(distance, time);
       println!("velocity = {}", velocity.display_kilometers_per_hour_precision(2));
   }
   ```
8. **Total and checked versions.** `calculate` is a `const fn` that always returns (dividing by zero gives infinity, never a panic). `checked_calculate` returns `Result<Velocity, QuantityError>`, and `try_<unit>(value)` rejects non-finite input. The error enum lives in `internal/error.rs`, with `&'static str` context fields (`DivisionByZero { operation: "velocity::calculate" }`).
9. **Repetition becomes a macro in `internal/`.** Same-dimension arithmetic (`Add`, `Sub`, `Neg`, `Mul<f64>`, `Div`) is one `macro_rules! implement_quantity_arithmetic` exported with `pub(crate) use implement_quantity_arithmetic;`, then called once per type: `implement_quantity_arithmetic!(Length);`.
10. **Tests mirror the source.** `length/tests/quantity.rs` tests `length/quantity.rs` and starts with `use super::super::*;`. Shared helpers (`assert_close`) live in `tests/mod.rs`. `root_function.rs` tests the façade path the caller uses: `crate::velocity(…)`.

## 3. No unwrap

`.unwrap()`, `.expect()` and `panic!` are banned everywhere: library code, `main` and tests. Each one hides a crash behind a call that looks like it always works.

| Situation | ✗ | ✓ |
|---|---|---|
| Value may be missing: guard clause, then the happy path | `let grade = grades.first().unwrap();` | `let Some(grade) = grades.first() else { return None; };` |
| Parse or convert | `let grade: Grade = text.parse().unwrap();` | `let Ok(grade) = text.parse::<Grade>() else { return None; };` |
| Missing has a real default | `limits.get("delta").unwrap()` | `limits.get("delta").copied().unwrap_or(ROUNDING_DELTA_LIMIT)` |
| Both cases do work | nested `if let` chains | `match value { Some(x) => { … } None => { … } }` |
| `main` / a binary | `run().unwrap();` | `let Some(result) = run() else { eprintln!("…"); return; };` |
| Tests | `assert_eq!(parse_grade("73").unwrap(), 73);` | `assert_eq!(parse_grade("73"), Some(73));` |

* `let … else` is the default: a guard clause with the failure path written out.
* `?` is only for passing a domain error up from a function that returns `Result<T, DomainError>`: `check_nonzero(time.to_seconds(), "velocity::calculate")?;`. Guard an `Option` with `let … else`.
* `.unwrap_or(default)` is allowed: it can't crash, and the default is a named config value.
* Tests compare the whole `Option` / `Result` against the expected value instead of unwrapping it.

## 4. Lint and format config

Set once at the crate root. `allow` silences the lints this style breaks on purpose; `warn` flags every `unwrap`, `expect` and `panic!`:

```rust
#![allow(clippy::needless_return, clippy::redundant_field_names)]
#![warn(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
```

`rustfmt.toml` (`unstable_features`, `imports_granularity`, `group_imports`, `fn_single_line` and `empty_item_single_line` need nightly rustfmt):

```toml
unstable_features = true
imports_granularity = "Item"   # one item per `use` line, never `use a::{B, C}`
reorder_imports = true
group_imports = "Preserve"
edition = "2024"
max_width = 120
tab_spaces = 4
reorder_modules = true
fn_single_line = true
empty_item_single_line = true
```

`justfile`, so formatting is one command (`just format`):

```
format:
    cargo +nightly fmt --all
```

## 5. Imports

* **Callers** import the module and call through it: `use physics::length;` → `length::kilometers(5.0)`, `use std::fmt;` → `fmt::Formatter`.
* **Inside the library**, import by absolute `crate::` path, one item per line: `use crate::time::Time;`. Use `super::` only for a sibling file of the same concept (`use super::quantity::Length;`).
* Globs only for re-exporting (`pub use quantity::*;` in a `mod.rs`) and in tests (`use super::super::*;`). Never `use x::*;` just to save typing.
* Prelude types (`String`, `Vec`, `Option`, `Box`) stay bare, like language globals.

## 6. Full example

```rust
#![allow(clippy::needless_return, clippy::redundant_field_names)]

mod greeting {
    struct GreetingConfig {
        separator: &'static str,
        terminator: &'static str,
    }

    const GREETING_CONFIG: GreetingConfig = GreetingConfig {
        separator: ", ",
        terminator: "!",
    };

    pub struct Greeter {
        greeting: String,
    }

    impl Greeter {
        pub fn new(greeting: impl Into<String>) -> Greeter {
            let greeting: String = greeting.into();
            return Greeter { greeting: greeting };
        }

        pub fn greeting(&self) -> String {
            return self.greeting.clone();
        }

        pub fn greet(&self, name: impl Into<String>) -> String {
            let name: String = name.into();
            if name.is_empty() {
                return format!("{}{}", self.greeting, GREETING_CONFIG.terminator);
            }

            return format!(
                "{}{}{}{}",
                self.greeting,
                GREETING_CONFIG.separator,
                name,
                GREETING_CONFIG.terminator,
            );
        }

        pub fn greet_all(&self, names: impl IntoIterator<Item = impl Into<String>>) -> Vec<String> {
            let mut messages = Vec::new();
            for name in names {
                messages.push(self.greet(name));
            }

            return messages;
        }
    }
}

mod grading {
    type Grade = i32;

    const MIN_PASSING_GRADE: Grade = 38;
    const ROUNDING_BASE: Grade = 5;
    const ROUNDING_DELTA_LIMIT: Grade = 3; // round only when the gap to the next multiple is below this

    pub struct GradingStudents;

    impl GradingStudents {
        pub fn round_grades(grades: impl Into<Vec<Grade>>) -> Vec<Grade> {
            let grades: Vec<Grade> = grades.into();
            let mut rounded_grades = Vec::with_capacity(grades.len());
            for grade in grades {
                rounded_grades.push(Self::round_grade(grade));
            }

            return rounded_grades;
        }

        fn round_grade(grade: Grade) -> Grade {
            let is_passing = |grade: Grade| grade >= MIN_PASSING_GRADE;
            let delta_to_next_multiple = |grade: Grade| ROUNDING_BASE - grade % ROUNDING_BASE;
            let should_round = |grade: Grade| is_passing(grade) && delta_to_next_multiple(grade) < ROUNDING_DELTA_LIMIT;

            if !should_round(grade) {
                return grade;
            }

            return grade + delta_to_next_multiple(grade);
        }
    }
}

fn main() {
    let greeter = greeting::Greeter::new("hello");
    println!("{}", greeter.greet("world"));
    println!("{:?}", greeter.greet_all(["world", "Ada"]));
    println!("{:?}", grading::GradingStudents::round_grades([73, 67, 38, 33]));
}
```

## 7. Tests

* `#[cfg(test)] mod tests` inside the module reaches private items directly: no public pass-through wrappers to make them testable.
* Name tests after behavior, not implementation: `passing_grade_two_below_next_multiple_rounds_up`, not `private_internal_implementation_is_testable`.
* Tests call the API the way a caller does, with literals.
* One table-driven test covers the boundaries:

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn grades_round_up_only_when_passing_and_within_two_of_next_multiple() {
        let cases = [(73, 75), (67, 67), (38, 40), (37, 37), (33, 33), (98, 100), (99, 100), (100, 100), (0, 0)];

        for (grade, expected) in cases {
            let rounded = GradingStudents::round_grades([grade]);

            assert_eq!(rounded, vec![expected], "grade {}", grade);
        }
    }
}
```
