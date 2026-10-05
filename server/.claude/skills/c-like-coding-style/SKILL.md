---
name: c-like-coding-style
description: Enforces the user's C-like, C#-manner coding style in every language (Rust, C#, TypeScript, JavaScript, Vue and others) - braces and explicit returns, plain loops instead of lambda chains, delegates / arrow functions / closures only as named local rules at the top of a function, and Rust APIs that own the ownership so callers just pass plain values like "hello world" or [73, 67] with no &, .clone(), .to_string() or lifetimes. Use whenever writing, refactoring, generating or reviewing code in any language, even if style is never mentioned - snippets, examples, katas, tests and full features. Not for explaining a concept with no code to write.
---

# C-Like Style

Code reads like C written by a C# developer: explicit, imperative, top to bottom. These rules apply in every language; the per-language sections only add what differs. A project's `CLAUDE.md` or formatter config overrides this skill where they disagree.

## Rules for every language

`.claude/CLAUDE.md` § Code Style already defines these, with examples; apply them in every language, not only TS/Vue: guard clauses (fail first, return early, no nesting), full verb + noun names, config at the top with no magic numbers, units in names, explicit namespaces, types at boundaries with inferred locals, every create paired with its release in the same scope, one linear file. This skill adds:

| Rule | ✗ | ✓ |
|---|---|---|
| Braces even on one-line bodies; brace placement follows the language's formatter. TS/Vue exception: a one-statement guard (§ TypeScript) | `if (x) return;` | `if (x) { return; }` |
| Explicit `return` at the end of every function body | tail expression `result` | `return result;` |
| Plain loops and `if`/`switch` statements for logic | `.filter().map().reduce()`, ternary chains | `for` + `if` + `push` |
| Delegates, arrow functions, closures: only as named local rules (next section) | `items.filter(x => …)`, `Func<T,bool>` params | rules declared at the top, used by `if` |
| Duplicate ten explicit lines rather than share them through a function parameter | `process(items, x => x.Total)` | two readable functions |
| Return the object itself; null/`None` when absent; `bool` for "applied or not" | `Result { IsSuccess, Errors }` wrappers | `return loan;` / `return null;` / `return false;` |
| No exceptions or panics in the domain | `throw` / `panic!` on bad input | validate at the boundary, return null/`false` |
| Domain type aliases name the concept | `Vec<i32>` everywhere | `type Grade = i32;` |
| A static class (C#) / unit struct + `impl` (Rust) is the namespace for a feature | loose free functions | `GradingStudents::round_grades(…)` |

* Don't add decoration: no `// region` comment pairs, no banner comments, no demo functions the task didn't ask for.

## Delegates, arrow functions and closures

Your own code uses one form: **named local rules**. These are small named closures declared at the top of a function body; the function's statements below use them.

| Use | Allowed | Instead |
|---|---|---|
| Named local rule at the top of a function | ✓ | — |
| Callback a framework requires: event handler, `vue.onMounted`, `vue.computed`, EF/LINQ predicate, DI `options => …`, Moq `Setup(x => …)` | ✓ unavoidable. Keep the body short and call a named function for real work | — |
| Closure as a local helper with statements (C#, Rust; TS/Vue allows it, § TypeScript) | ✗ | a named function that takes what it needs as parameters |
| Your own function taking a delegate: `Func<T, bool>`, `impl Fn(T) -> bool`, `callback: (x) => …` | ✗ | two explicit functions |
| Stored or module-level delegate: `const IS_FAILING: fn(i32) -> bool = …`, a `static Func<…>` field (TS/Vue exception: the teardown handle, § TypeScript) | ✗ | a plain function |
| Returning a closure, currying, function factories | ✗ | a plain function |
| Passing a rule to a chain: `.filter(isPassing)`, `.Where(isPassing)` | ✗ | `for` + `if (isPassing(x))` |

A named local rule:
* is declared before any logic, smallest rule first, composed rules after it.
* is named like a predicate or a value: `isPassing`, `shouldRound`, `deltaToNextMultiple`.
* is one pure expression. It reads only its parameters and config constants: no mutation, no I/O, no `throw` / `panic!`.
* has its parameter types written out.
* has a positive form only. Negate at the call site with `!`; don't define both `isPassing` and `isFailing`.
* stays inside its function: it is never passed, stored or returned. If a second function needs the rule, promote it to a plain function.

The Rust form is `round_grade` in [rust.md](rust.md) §6.

```csharp
public static class GradingStudents
{
    private const int MinimumPassingGrade = 38;
    private const int RoundingBase = 5;
    private const int RoundingDeltaLimit = 3; // round only when the gap is below this

    public static int RoundGrade(int grade)
    {
        System.Func<int, bool> isPassing = (int grade) => grade >= MinimumPassingGrade;
        System.Func<int, int> deltaToNextMultiple = (int grade) => RoundingBase - grade % RoundingBase;
        System.Func<int, bool> shouldRound = (int grade) => isPassing(grade) && deltaToNextMultiple(grade) < RoundingDeltaLimit;

        if (!shouldRound(grade))
        {
            return grade;
        }

        return grade + deltaToNextMultiple(grade);
    }
}
```

```ts
function roundGrade(grade: number): number {
  const isPassing = (grade: number): boolean => grade >= gradingConfig.minimumPassingGrade
  const deltaToNextMultiple = (grade: number): number => gradingConfig.roundingBase - (grade % gradingConfig.roundingBase)
  const shouldRound = (grade: number): boolean => isPassing(grade) && deltaToNextMultiple(grade) < gradingConfig.roundingDeltaLimit

  if (!shouldRound(grade)) {
    return grade
  }

  return grade + deltaToNextMultiple(grade)
}
```

## Rust

* The API owns the ownership: the caller passes literals and values (`"hello"`, `73`, `[73, 67]`) and never writes `String::from`, `.to_string()`, `&`, `.clone()` or a lifetime.
* **Never `.unwrap()`**, nor `.expect()` or `panic!`, anywhere: library code, `main` or tests.
* Before writing Rust, read [rust.md](rust.md): signatures that take `impl Into<…>`, owned returns, no-unwrap patterns, crate and module layout, imports, lint and rustfmt config, a full example, tests.

## C#

* Block bodies for methods and properties: `{ return x; }`, never `=> x`. Named local rules are the only `=>` you write yourself.
* `switch` statement with `case X: return …;` and `default:`, not switch expressions.
* Explicit constructor assigning `private readonly` fields; no primary constructors.
* Write the type: `new LoanResponse(…)`, not target-typed `new()`. No range tricks (`[..20]`): use `Substring(0, 20)`.

## TypeScript / JavaScript / Vue

`.claude/CLAUDE.md`'s reference example sets three exceptions to the rules above:

* Local helpers inside a setup scope are arrow-function constants: `const resizeScene = () => { … }`. They may read that scope's handles (`camera`, `renderer`, `element`) instead of taking them as parameters.
* A guard clause that is one statement stays unbraced: `if (!element) return`. Any other `if` body gets braces.
* The teardown handle is the one stored closure: `let destroyScene: (() => void) | undefined`, assigned at the end of setup and called in `vue.onBeforeUnmount`.
