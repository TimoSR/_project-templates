# Open/Closed and protected variation

## Definition

* **Treat working code as append-only:** new behavior arrives as new classes plugged into extension points, not as edits to the module's source or binary.

## Edits that are still allowed

1. **Bug fixes**, in two steps:
   1. Write a failing test that reproduces the defect. For legacy code with no tests, add a golden-master characterization test first.
   2. Change the code until it passes, with no other test breaking.
2. **Changes no client notices.** This is why loose coupling matters at every level (class, package, subsystem).
   * A signature or interface change always forces client changes, so it never counts.

## Extension points, weakest to strongest

| Mechanism | Extend without modifying by | Drawback |
|---|---|---|
| **None** (client uses a concrete class, nothing virtual) | Nothing: write `TradeProcessorV2` and **edit the client** | Every requirement touches the client |
| **Virtual method** | Subclass and override: call `base` and add before or after it, or replace it | All or nothing: no single lines, no private members |
| **Abstract methods** (Template Method) | Base fixes the algorithm; subclasses fill the protected steps | Still implementation inheritance: subclasses couple to the base |
| **Interface** | New implementations, decorators, adapters, composites, strategies | You must design a stable interface |

* **Prefer interface inheritance over implementation inheritance.** With implementation inheritance, every subclass is a client of the base implementation, so almost any change to the base is client-visible.
   * Prefer composition and shallow hierarchies. A member added at the top touches the whole tree.
* **Design for inheritance or prohibit it (Bloch).** A class not marked `sealed` (Java: `final`) implicitly claims to support inheritance, even with no virtual members.

```csharp
// ✗ open by default: someone subclasses it and new-hides a member, which defeats polymorphism
public class TradeParser { public IEnumerable<TradeRecord> Parse(IEnumerable<string> lines) { ... } }

// ✓ intent is explicit: extend through ITradeParser and composition, not inheritance
public sealed class SimpleTradeParser : ITradeParser { ... }
```

* Choose sealed, abstract, virtual, interface or concrete dependency deliberately, never by default.

## Protected (predicted) variation

> Identify points of predicted variation and create a stable interface around them. (Alistair Cockburn)

* **Predicted variation:** trace each class to a real business requirement. During backlog refinement, ask the product owner about likely *related* future requirements. Their answers say where extension points belong.
* **Stable interface:** if the interface changes, every client changes. Interfaces change far less than implementations, but only if designed to. Keep the interface in a separate package so each side varies alone.

### The Goldilocks zone

| Amount | Looks like | Cost |
|---|---|---|
| Too little | Procedural code in classes; a god object that knows everything | Every change edits it |
| Too much | The "new hammer" phase: everything behind an interface | Unused extension points; logic scattered across files and packages; slow progress |
| Just enough | Extension points only where requirements are unclear, changeable or hard | — |

* Sometimes the god class *is* correct. For a small tool with near-zero predicted variation, the original or the clarity-refactored version is enough.

### Predicted variation vs speculative generality

Two sides of one decision:

* If you predicted a specific variation, the generality isn't speculative.
* If you can't name one, it is: you are generalizing for an imagined problem, which produces leaky, unused abstractions.

| | Example | Why |
|---|---|---|
| ✓ Interface pays off | Data access by identifier | Could be backed by a relational DB, document store, cache, file, in-memory dictionary, test double or remote service |
| ✗ Interface doesn't | Mapper between one data-access implementation's DTOs and the domain | Only ever one per implementation; it belongs *with* that implementation. This is "predicting a lack of variation" |

## When a new requirement arrives

```
new requirement
├─ extension point already here?   → add an implementation or decorator; don't edit
├─ area likely to vary again?
│     yes → refactor once to a stable interface, then extend
│     no  → edit directly (bug fix or client-invisible change) and move on
└─ public signature changes?       → client-visible: prefer a new interface or an adapter
```
