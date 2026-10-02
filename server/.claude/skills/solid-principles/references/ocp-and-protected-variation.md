# Open/Closed Principle and protected variation

## Definitions

- **Meyer (1988):** software entities should be open for extension but closed for modification.
- **Martin:** *Open for extension* means the module's behavior can be extended to meet new requirements. *Closed for modification* means extending it doesn't change the module's source or binary.

Read the principle as **treat working code as append-only**. New behavior arrives as new classes plugged into extension points.

## Legitimate modifications

The principle isn't pure. Two kinds of edits to existing code are acceptable:

1. **Bug fixes**, done in two steps: (a) write a failing unit or integration test that reproduces the defect (Arrange the failing state, Act, Assert the expected behavior), then (b) change the code until it passes, with no other tests breaking. For legacy code with no tests, add a golden-master characterization test first.
2. **Changes no client notices.** Any change that doesn't force a change in a client is tolerable. This is why **loose coupling** matters at every level (class↔class, package↔package, subsystem↔subsystem). Signature or interface changes always force client changes, so they are never "client-unaware".

## Extension points, from weakest to strongest

| Mechanism | What you can do without modifying the class | Drawbacks |
|---|---|---|
| **None** (client depends on a concrete class, nothing virtual) | Nothing. You write `TradeProcessorV2` and **edit the client** to use it | Every new requirement touches the client |
| **Virtual method** | Subclass and override. Either call `base` in full (adding before or after it) or replace it entirely | All-or-nothing: you can't change individual lines, and private members are unreachable |
| **Abstract methods** (Template Method) | Base class fixes the algorithm (`ProcessTrades`) and delegates steps to protected abstract (or virtual) methods | Still implementation inheritance, so subclasses are coupled to the base implementation |
| **Interface** (client depends on an interface) | Any new implementation, plus decorators, adapters, composites, and strategies | Need to design a stable interface |

**Prefer interface inheritance over implementation inheritance.** With implementation inheritance, every current and future subclass is a client of the base implementation, so almost any change to the base is client-visible. Prefer composition, keep hierarchies shallow, and remember that a member added at the top touches the whole tree.

### "Design and document for inheritance or else prohibit it" (Bloch)

In C#, any class not marked `sealed` (Java: not `final`) is implicitly claiming to support inheritance, even with no virtual members. `new`-hiding a member defeats polymorphism and surprises callers. Seal classes not designed for extension. That is an explicit statement of intent, and it pushes other developers toward composition. Every choice here (sealed, abstract, virtual, interface, or concrete dependency) should be made deliberately, not by default.

## Protected (predicted) variation

> Identify points of predicted variation and create a stable interface around them. (Alistair Cockburn)

"Predicted variation" is the more accurate name. It has two halves:

- **Predicted variation.** Trace each class back to a real business requirement. During backlog refinement and sprint conversations, ask the product owner about likely *related* future requirements. Those answers tell you where the extension points belong.
- **A stable interface.** Clients depend on the interface, so if *it* changes, every client changes. Interfaces change far less often than implementations, but only if you design them to. Keep the interface in a separate package from its implementations so each side can vary without the other.

### The Goldilocks zone

- **Too little:** beginner-style procedural code in classes. The class is a bag of methods (a "god object" that knows everything), and every change edits it.
- **Too much:** the "new hammer" phase, where everything goes behind an interface. You get a mass of extension points that will never be used, code that is hard to follow because it is spread across files and packages, and slow progress.
- **Just enough:** extension points only where requirements are unclear, changeable, or hard to implement.

Sometimes the god class *is* correct. If predicted variation is roughly zero for a small tool, the original (or the clarity-refactored version) is enough, and the abstraction effort would be wasted.

### Predicted variation vs. speculative generality

These look opposed but are two sides of one decision:

- *Predicted variation*: be explicit about what may and may not be extended.
- *Speculative generality*: don't generalize for problems you only imagine, because that produces leaky, unused abstractions.

If you predicted a specific variation, the generality isn't speculative. If you can't name one, it is.

**Where interfaces clearly pay off:** application edges where client and service must be decoupled. The classic case is data access by identifier, which might be backed by a relational DB, document store, cache, file, in-memory dictionary, test double, or remote service.

**Where they don't:** mapping code between a specific data-access implementation's DTOs and the domain model. That mapper belongs *with* its data-access implementation. There will only ever be one per implementation, so an `IMapper` extension point there adds indirection and nothing else. This is "predicting a lack of variation".

## Checklist when a new requirement arrives

1. Is there already an extension point here? Then add a new implementation or decorator. Don't edit.
2. If not, is this area likely to vary again? If yes, refactor once to introduce a stable interface, then extend. If no, edit the class directly (bug fix or client-invisible change) and move on.
3. Does the change alter a public signature? Then it is client-visible. Prefer a new interface or adapter over breaking existing clients.
