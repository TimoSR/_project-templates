---
name: solid-principles
description: Reviews and refactors object-oriented code, once a simple working version exists, with the SOLID principles (SRP, OCP, LSP, ISP, DIP), dependency injection and coupling/cohesion/connascence, as taught in Gary McLean Hall's "Adaptive Code". Use when the user asks for a design or architecture review, refactors a god class, long method or tangled service, introduces interfaces or abstractions, reshapes a class hierarchy, wires up DI or a composition root, asks whether an abstraction is worth it, or fights code that is hard to test or change. Also when they mention SOLID, single responsibility, open/closed, Liskov, interface segregation, dependency inversion, service locator, coupling, cohesion or connascence, even if they never say "SOLID". Covers reviewing domain/ and application/ code and the *-serviceServiceExtensions.cs DI registration. Not for up-front design before the simple version exists, or for choosing or comparing named GoF patterns (design-patterns).
---

# SOLID: Adaptive Code

Source: Gary McLean Hall, *Adaptive Code*, 2nd ed. (Microsoft Press, 2017). The examples are C#; the ideas map to any language with interfaces.

## The one idea

Adaptive code absorbs new requirements without rewriting code that works. It gets there with one move: **delegate to abstractions, and have them handed to you.**

```
SRP  decides what to split out    one reason to change per class
ISP  shapes the abstraction       small, client-shaped interfaces
LSP  keeps it honest              any implementation stands in for any other
DIP  points dependencies at it    at class level and package level
DI   hands it over                built at one composition root
───
OCP  is the result                new behavior = a new class at an extension point
```

Coupling, cohesion and connascence measure whether the result is any good.

## The counterweight: just enough

Over-abstraction fails as surely as under-abstraction.

* Add an extension point only where variation is predicted: a stakeholder said so, or the area is volatile or hard to get right.
   * If you can't name the change, it's speculative generality: indirection that costs readability and buys nothing.
* An interface with one implementation is a smell (test mocks don't count). Good abstractions get reused by decorators, adapters and strategies.
* "Extract interface" is not abstraction:

```csharp
// ✗ a 1:1 mirror: indirection, no second implementation
interface ICamera { void Zoom(float level); }
class Camera : ICamera { ... }

// ✓ a capability several types share
interface IHeightAdjustable { void Raise(float height); void Lower(float height); }
class Camera     : IHeightAdjustable { ... }   // drives the zoom
class TouchProbe : IHeightAdjustable { ... }   // drives the probe height
```

* A small tool that won't change can stay a god class. At most, refactor it for clarity (extract methods) and stop.
* Some third-party dependencies can stay unwrapped, such as a ubiquitous framework or logging. Skip the wrapper on purpose and say so.
* When you recommend an abstraction, name the change it protects against. When you decline one, say why.

## Workflow: refactoring toward SOLID

1. **Safety net first.** Behavior must not change while structure does. No tests? Add characterization tests (a golden master recording current output for representative input). Write new code test-first.
2. **List the reasons to change.** Each concrete future change is a responsibility: a new input source, format, validation rule, log destination or storage engine.
3. **Refactor for clarity.** Extract one method per responsibility so the top method reads as the process (`Read → Parse → Store`). Readable, not yet adaptive.
4. **Refactor for abstraction.** Move each responsibility behind an interface and inject it through the constructor. Pass context (stream, connection string, path) into the *implementation's* constructor, never into interface methods. Repeat until each class has one reason to change.
5. **Apply patterns where they fit:** Decorator for cross-cutting behavior, Adapter for third-party types, Composite for one-to-many, Strategy for interchangeable algorithms. See [srp-and-decorators.md](references/srp-and-decorators.md); choosing between look-alike patterns is the `design-patterns` skill.
6. **Wire everything at the composition root**, at the entry point only. See [dependency-injection.md](references/dependency-injection.md).
7. **Verify.**
   * Tests are still green.
   * Each change from step 2 is now "add or replace a class", with no client edits.
   * No interface was created that will never get a second implementation.

## Diagnosis: smell → principle → remedy

Start here when reviewing.

| Smell in the code | Principle | Remedy |
|---|---|---|
| One method or class reads, parses, validates, logs and persists | SRP | Split into collaborators behind interfaces; the original becomes the process blueprint |
| Logging, caching, timing, transactions or auth tangled into business methods | SRP | A decorator per concern (AOP when it's truly everywhere) |
| Client wraps a call in `if (condition) dependency.Do()` and depends on the condition's source | SRP | Predicate or branching decorator around the dependency |
| Every new feature edits the same class and its clients | OCP | Extension point (interface + new implementation or decorator) at the predicted variation |
| `switch` on type, or `is`/`as` checks against concrete classes | OCP / LSP / DIP | Polymorphism, or check for *capability interfaces* |
| Override throws `NotImplementedException` / `NotSupportedException` | LSP (+ ISP) | The base promises too much; split into capability interfaces |
| Subclass adds guard clauses rejecting inputs the base accepted | LSP: precondition strengthened | Keep the base precondition or redesign the hierarchy |
| Subclass returns values the base ruled out (0, null, negative) | LSP: postcondition weakened | Honor the base postcondition or don't subtype |
| Subclass exposes a setter or field that bypasses a base invariant | LSP: invariant broken | Private field + guarded protected property in the base |
| Implementations throw unrelated exception types for the same failure | LSP: new exceptions | One base exception per interface; implementations derive from it |
| Decorator full of pass-through methods | ISP | Segregate so the decorator targets only what it changes |
| Clients each use a different slice of an interface (read vs write) | ISP: client need | Split by client; one class may still implement every slice |
| One implementation drags in two unrelated heavy dependencies | ISP: architectural need | Split (commands vs queries) into separate packages |
| `IEverything : IRead, ISave, IDelete` re-merges segregated interfaces | ISP: Interface Soup | Delete the aggregate; inject the parts, even the same instance three times |
| `new SomeService()` in business classes; static calls to config, clock or DB | DIP / DI ("skyhooks") | Depend on an interface, inject it, adapt statics behind interfaces |
| Interface shares a package with its implementation, or exposes ORM/driver/vendor types | DIP: Entourage | Stairway: separate interface and implementation packages; adapters for third-party types |
| 1:1 interfaces created by "extract interface" | DIP: poor abstraction | Capability interfaces (`IMovable`, `IMeasurable`); commands instead of disparate queries |
| `ServiceLocator.Current.Get<T>()`, or the container injected into classes | DI: Service Locator | Constructor injection; only the composition root knows the container |
| Second convenience constructor that `new`s default implementations | DI: Illegitimate Injection | Delete it; tests pass doubles through the real constructor |
| Property or method injection that must happen before another call works | DI / connascence of execution order | Constructor injection, or make the dependency a method parameter |
| A class disposes a dependency it was handed | DI: lifetime ownership | Only the creator disposes; inject a factory for short-lived instances |
| Magic values (`"N/A"`, -1), same-typed positional parameters, tests recomputing the algorithm | Connascence of meaning / position / algorithm | Types, enums, null objects, value types, named parameters; test against known values |

## The principles and their references

| Principle | Rule | Depth |
|---|---|---|
| SRP | One reason to change. Find reasons by listing the changes that force an edit. Adapter and Decorator split concerns that look inseparable. | [srp-and-decorators.md](references/srp-and-decorators.md) |
| OCP | Closed for modification except bug fixes (failing test first) and changes no client can observe. Extension points, weakest to strongest: none, virtual, abstract (Template Method), interface. Seal what isn't designed for inheritance. | [ocp-and-protected-variation.md](references/ocp-and-protected-variation.md) |
| LSP | Preconditions can't be strengthened, postconditions can't be weakened, invariants hold. Parameters contravariant, returns covariant, no new exception types. Don't catch contract violations; unit-test the contracts. | [lsp-contracts-and-variance.md](references/lsp-contracts-and-variance.md) |
| ISP | Split when decorators would pass through, when clients need different slices, or when the architecture demands it (CQRS). Single-method interfaces compose best. | [isp-interface-design.md](references/isp-interface-design.md) |
| DIP | Client and implementation both depend on the interface, also at package level (Stairway, not Entourage). Interfaces never expose third-party types. Model capabilities, not classes. | [dip-and-abstraction-design.md](references/dip-and-abstraction-design.md) |
| DI | Constructor injection with null guards. One composition root; resolve only resolution roots. No Service Locator, no Illegitimate Injection. | [dependency-injection.md](references/dependency-injection.md) |
| Measure | Low coupling, high cohesion. Rank coupling by connascence and weigh it by distance: strong connascence across a service boundary hurts far more than inside a class. | [coupling-cohesion-connascence.md](references/coupling-cohesion-connascence.md) |

## Reporting a review

One entry per finding:

```
UserService.cs:42  UserService.Register
Smell → principle  sends the welcome email inline → SRP
Why here           moving to the queue-based mailer means editing registration logic and its tests
Refactor           extract IWelcomeNotifier and inject it; SmtpWelcomeNotifier keeps today's code
Worth it now?      yes: the queue migration is planned
```

* **Why here** names the concrete change or test the design makes painful. Can't name one? Drop the finding.
* **Worth it now?** weighs predicted variation and distance (same class vs separate services).
* Close with what you deliberately did *not* flag because abstracting it would be speculative.

## In this repo

* **No exceptions in the domain** (`.claude/CLAUDE.md`). An LSP precondition becomes DTO-boundary validation or a factory that returns null: `Weight.Create(kilograms) → Weight?`, not a throwing constructor. The guard-clause, exception-hierarchy and `NotSupportedException` advice in [lsp-contracts-and-variance.md](references/lsp-contracts-and-variance.md) applies to infrastructure and adapters only.
* **Composition root:** `FF.Api/Startup.cs`. Elsewhere, wherever the program starts: `Program.cs`/`main`, an app factory, framework startup.
* **Contract folders** (here `API/FF-API/_CONTRACTS/`) are the interface side of the Stairway. Interfaces go there; implementations stay in their feature or module.
