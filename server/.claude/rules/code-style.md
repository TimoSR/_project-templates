# House code style

Apply this style to new code. Preserve existing conventions in narrowly edited legacy code and follow formatter configuration for whitespace. Do not restyle unrelated lines.

- Write explicit, imperative flow: guard clauses, plain loops, and `if`/`switch` statements rather than lambda chains or nested ternaries.
- Use full names; functions are verb + noun. Put units in names or comments (`deltaSeconds`, radians per second).
- Put existing tunable values in named config objects/constants at the top. This organizes required values; it does not authorize new configurable behavior. Avoid unexplained inline numbers.
- Use explicit library namespaces: `import * as vue from 'vue'`, then `vue.ref`; C#: namespace aliases such as `using io = System.IO;`, then `io.File.ReadAllText`. Language globals and framework macros stay bare.
- Annotate boundary types; infer local types. TS/JS: `const` by default, `let` for reassignment.
- Keep setup, processing, and teardown in dependency order. Pair each owned resource with its release in the same scope.
- Use braces and explicit returns where the language requires/allows a value return. Void functions need no redundant return. TS/Vue allows a single-statement unbraced guard.
- Return the object created, `null`/`None` when absent, or `bool` for applied/not applied. Expected domain outcomes do not throw or panic; validate at the boundary and enforce invariants in the domain. Do not introduce `Result<T>`/success wrappers for new domain APIs.
- Prefer plain named functions to custom delegate parameters, currying, stored delegates, or function factories. A few explicit functions are preferable to callback-driven indirection.
- Named local rules may be pure expressions at the top of a function: typed parameters, positive predicate/value names, no I/O/mutation, and no passing/storing/returning them. Promote shared rules to plain functions.
- Framework-required callbacks are allowed: Vue lifecycle/computed, EF/LINQ predicates, DI options, Moq setup. Keep bodies small; extract substantive work into named functions. EF compiled-query delegates are also allowed for measured hot paths.
- Avoid banner/region comments and unsolicited demonstration functions.

## C#

- Block-bodied methods/properties, statement `switch`, explicit constructors assigning readonly fields; no primary constructors.
- Explicit `new LoanResponse(...)`, not target-typed `new()`; ordinary APIs such as `Substring`, not range tricks.
- Static classes can serve as feature namespaces.

## TypeScript / JavaScript / Vue

- No semicolons, single quotes, trailing commas, 2-space indentation, one argument per line when a call wraps, subject to the project's formatter.
- Setup-local arrow helpers may capture handles. A teardown function handle may be stored for `onBeforeUnmount`.
- Existing framework composables/hooks and callback contracts remain intact.

## Rust

- Design public APIs so callers can pass ordinary values/literals; handle conversions and ownership internally where practical. Use meaningful domain type aliases.
- No `unwrap`, `expect`, or `panic!` in library code, main, or tests. Use a unit struct plus `impl` as a feature namespace when appropriate.
- Before writing Rust, read `.claude/skills/c-like-coding-style/rust.md` for signatures, error handling, crate layout, and lint setup.

Examples: `for` + `if` + `push` instead of `.filter().map()` for local logic; `.Where(...).Select(...)` remains appropriate when EF must translate the query into SQL.

## Full standard: `c-like-coding-style` skill

Imported so the whole skill applies whenever this rule loads. The lines above narrow it for this repo and win where they differ. Links inside it resolve under `.claude/skills/c-like-coding-style/`.

@../skills/c-like-coding-style/SKILL.md
