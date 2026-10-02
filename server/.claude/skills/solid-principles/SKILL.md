---
name: solid-principles
description: Design, review, and refactor object-oriented code with the SOLID principles (SRP, OCP, LSP, ISP, DIP) plus dependency injection and coupling/cohesion/connascence, as taught in Gary McLean Hall's "Adaptive Code" (2nd ed.). Use whenever the user asks for a design or architecture review, wants to refactor a god class / long method / tangled service, is introducing interfaces or abstractions, designing a class hierarchy or an interface, wiring up DI or a composition root, deciding whether an abstraction is worth it, or fighting code that is hard to test or hard to change — and whenever they mention SOLID, single responsibility, open/closed, Liskov, interface segregation, dependency inversion, decorator/adapter/composite/strategy patterns, service locator, coupling, cohesion, or connascence, even if they never say "SOLID".
---

# SOLID — Adaptive Code

Source: Gary McLean Hall, *Adaptive Code: Agile coding with design patterns and SOLID principles*, 2nd ed. (Microsoft Press, 2017). The book's examples are C#; the ideas carry over to any language with interfaces/protocols/traits.

## The one idea underneath everything

**Adaptive code** is code that can absorb new requirements without existing, working code being rewritten. The book gets there through one move, applied again and again:

> Delegate to abstractions, and have those abstractions handed to you.

- **SRP** decides *what* to split out (each reason to change becomes its own class).
- **ISP** decides the *shape* of the abstraction (small, client-shaped interfaces).
- **LSP** keeps the abstraction *honest* (any implementation can stand in for any other).
- **OCP** is the result: new behavior arrives as *new* classes plugged into extension points.
- **DIP** points dependencies *at abstractions*, and the package structure keeps them pointed that way.
- **Dependency injection** is the glue that builds the object graph at a single composition root.

Coupling, cohesion, and connascence are how you *measure* whether the result is any good.

## The counterweight: just enough adaptability

The book is explicit that over-abstraction is as much a failure as under-abstraction. Keep these checks in mind before you add any interface:

- **Predicted variation.** Put an extension point where change is *likely* (because a stakeholder said so, or because that area is volatile or hard to get right) and keep a *stable* interface around it. If you can't name a plausible change, you're adding speculative generality: indirection that costs readability and buys nothing.
- **An interface with one implementation is a smell** (test mocks don't count). Good abstractions get reused: decorators, adapters, and alternative strategies all implement the same interface.
- **"Extract interface" is not abstraction.** A 1:1 `ICamera` for `Camera` adds indirection with no payoff. Look for shared *capabilities* across types instead.
- **Small tools that won't change can stay simple.** A god-class prototype that will never grow is fine. If anything, refactor it for clarity (extract methods), and stop there.
- **Some third-party dependencies can stay.** Wrapping a ubiquitous framework or a cross-cutting library (logging, say) in your own interface can cost more than it's worth. If you skip the wrapper, do it on purpose and say so.

When you recommend an abstraction, name the concrete change it protects against. When you decline to add one, say why.

## Workflow: refactoring toward SOLID

1. **Put a safety net in place first.** Behavior must not change while structure does. If tests are missing, add characterization tests (a "golden master" that records current output for representative input) before you touch anything. Write new code test-first.
2. **List the reasons to change.** For the class or method in question, write down each concrete future change: a new input source, a new format, new validation rules, a new log destination, a new storage engine. Each distinct reason is a responsibility.
3. **Refactor for clarity.** Extract one method per responsibility so the top-level method reads as the process (`Read → Parse → Store`). This is readable but not yet adaptive, because changing any step still means editing this class.
4. **Refactor for abstraction.** Move each responsibility into its own class behind an interface, and inject the interfaces through the constructor. Pass context such as a stream, a connection string, or a file path into the *implementation's* constructor, not into the interface's method signatures. That keeps the interface free of technology. Repeat recursively until each class has one reason to change.
5. **Apply patterns where they fit.** Use a Decorator for cross-cutting behavior, an Adapter to turn third-party types into your own interfaces, Composite for one-to-many, and Strategy for interchangeable algorithms. See [references/srp-and-decorators.md](references/srp-and-decorators.md).
6. **Wire everything at the composition root.** Do this at the entry point only. See [references/dependency-injection.md](references/dependency-injection.md).
7. **Verify.** Tests must still be green. Check each original change scenario: can it now be handled by adding or replacing a class, without editing the client? Then check the other direction: did you create interfaces that will never get a second implementation?

## Diagnosis table: smell → principle → remedy

Start here when reviewing code. Open the linked reference for depth.

| Smell in the code | Principle | Typical remedy |
|---|---|---|
| One method/class reads input, parses, validates, logs, and persists | SRP | Split into collaborators behind interfaces; the original becomes the "blueprint" of the process |
| Logging/caching/timing/transactions/auth tangled into business methods | SRP | Decorator per concern (or AOP when it's truly everywhere) |
| A client wraps a call in `if (someCondition) dep.Do()` and depends on the condition's source | SRP | Predicate / branching decorator around the dependency |
| Every new feature edits the same class and its clients | OCP | Add an extension point (interface + new implementation / decorator) at the point of predicted variation |
| `switch` on type, or `is`/`as` checks against concrete classes | OCP / LSP / DIP | Polymorphism, or check for *capability interfaces*, not concrete types |
| Override throws `NotImplementedException`/`NotSupportedException` | LSP (+ ISP) | The base type promises too much; split into capability interfaces |
| Subclass adds guard clauses rejecting inputs the base accepted | LSP: precondition strengthened | Keep the base precondition or redesign the hierarchy |
| Subclass returns values the base contract ruled out (0, null, negative) | LSP: postcondition weakened | Honor the base postcondition or don't subtype |
| Subclass exposes a setter or field that bypasses a base invariant | LSP: invariant broken | Private field + guarded protected/public property in the base |
| Implementations throw unrelated exception types for the same failure | LSP: new exceptions | Common base exception per interface; implementations derive from it |
| Decorator full of pass-through methods | ISP | Segregate the interface so the decorator targets only what it changes |
| Clients each use a different slice of an interface (e.g. read vs. write) | ISP: client need | Split by client; one class may still implement all the slices |
| One implementation drags in two unrelated heavy dependencies | ISP: architectural need | Split interface (e.g. commands vs. queries) so implementations live in separate packages |
| Segregated interfaces re-merged into `IEverything : IRead, ISave, IDelete` | ISP: "Interface Soup" anti-pattern | Delete the aggregate; inject the parts (even the same instance three times) |
| `new SomeService()` inside business classes; static calls to config/clock/DB | DIP / DI ("new is a code smell", static "skyhooks") | Depend on an interface, inject via constructor, adapt statics behind interfaces |
| Interface lives in the same package as its implementation; interface signatures expose ORM/driver/vendor types | DIP: "Entourage" anti-pattern | "Stairway" pattern: separate interface and implementation packages; adapters for third-party types |
| 1:1 interfaces created by "extract interface" | DIP: poor abstraction | Capability interfaces (`IMovable`, `IMeasurable`); commands instead of disparate queries |
| `ServiceLocator.Current.Get<T>()` or a container injected into classes | DI: Service Locator anti-pattern | Constructor injection; only the composition root knows the container |
| Second "convenience" constructor that `new`s default implementations | DI: Illegitimate Injection | Delete it; tests pass doubles through the real constructor |
| Property/method injection that must happen before another call works | DI / connascence of execution order | Constructor injection, or make the dependency a method parameter |
| A class disposes a dependency it was handed | DI: lifetime ownership | Only the creator disposes; inject a factory if the class needs short-lived instances |
| Magic return values ("N/A", -1), same-typed positional params, tests that recompute the algorithm | Connascence of meaning/position/algorithm | Types/enums/null-objects, value types or named params, test against known values |

## The five principles in brief

**Single Responsibility (SRP).** A class should have one reason to change. Find responsibilities by listing the changes that could force an edit. Achieve SRP by delegating to abstractions, then use Adapter and Decorator to split out concerns that look inseparable. → [references/srp-and-decorators.md](references/srp-and-decorators.md)

**Open/Closed (OCP).** A class should be open for extension and closed for modification. Two edits remain legitimate: bug fixes (write the failing test first), and changes no client can observe. Extension points, from weakest to strongest: none, virtual method, abstract method (Template Method), interface. Prefer interfaces over implementation inheritance. Design for inheritance or seal the class. Put extension points only where you predict variation. → [references/ocp-and-protected-variation.md](references/ocp-and-protected-variation.md)

**Liskov Substitution (LSP).** Clients must be able to use any subtype through the base type without knowing which one they have. Contract rules: preconditions can't be strengthened, postconditions can't be weakened, invariants must be preserved. Type rules: parameters are contravariant, return types are covariant, and no new exceptions outside the existing hierarchy. Contract violations are bugs: don't catch them, fail fast and log. Unit-test the contracts. → [references/lsp-contracts-and-variance.md](references/lsp-contracts-and-variance.md)

**Interface Segregation (ISP).** Keep interfaces small and shaped by what clients need. Split an interface when decorators would otherwise pass through, when clients need different slices (reader vs. writer, anonymous vs. authorized), or when the architecture demands it (CQRS). Single-method interfaces (`ITask`, `IAction<T>`, `IFunction<T>`, `IPredicate`) are the most composable. → [references/isp-interface-design.md](references/isp-interface-design.md)

**Dependency Inversion (DIP).** High-level and low-level modules both depend on abstractions, and abstractions don't depend on details. At package level, use the Stairway pattern (client → interface package ← implementation package) instead of the Entourage anti-pattern. Interfaces must not expose third-party types. Abstractions should model *capabilities*, not mirror classes. → [references/dip-and-abstraction-design.md](references/dip-and-abstraction-design.md)

**Dependency injection** is the glue. Prefer constructor injection with null-guard preconditions. Keep one composition root at the entry point and resolve only the resolution roots (controllers, views, handlers). Choose Poor Man's DI for small graphs and conventions plus a few manual registrations for large ones. Avoid Service Locator and Illegitimate Injection. → [references/dependency-injection.md](references/dependency-injection.md)

**Measuring the result**: aim for low coupling and high cohesion. Use connascence to rank how bad a coupling is, and weigh it against locality: strong connascence across a service boundary hurts much more than inside one class. → [references/coupling-cohesion-connascence.md](references/coupling-cohesion-connascence.md)

## When reviewing code, report like this

For each finding, give:

- **Where**: `file:line` and the class or method.
- **Smell → principle**: use the vocabulary from the table above.
- **Why it matters here**: the *concrete* change or test that this design makes painful. If you can't name one, the finding probably isn't worth raising.
- **Suggested refactor**: the smallest step that helps. Show a short code sketch when it clarifies.
- **Worth it now?** Yes, or later, or no, based on predicted variation and on how far apart the coupled pieces are (same class vs. separate services).

Close with the things you deliberately *didn't* flag because abstracting them would be speculative. That keeps the review from reading as an exhaustive checklist and shows the trade-offs you made.

## Language mapping

The book writes C#, but the vocabulary maps directly onto other languages:

- **Interface** means a Java/Kotlin/TS interface, a Python `Protocol`/ABC, a Rust trait, or a Go interface.
- **`sealed`** corresponds to `final`.
- **Generic `in`/`out` variance** exists in Kotlin, and in Java as `? super`/`? extends`.
- **Composition root** is wherever the program starts: `Program.cs`/`main`, an app factory, or framework startup.

In a codebase that already has dedicated contract folders or packages (for example `_contracts/`), treat those as the interface side of the Stairway. Interfaces go there, and implementations stay in their feature or module.
