# Coupling, cohesion and connascence

How to judge whether the SOLID refactoring paid off. Low coupling and high cohesion *correlate* with good code. The stronger claim runs the other way: high coupling and low cohesion make projects fail.

## Coupling

The **strength of interdependence** between elements (methods, classes, packages, subsystems).

* Low: elements change independently.
* High: one change cascades. Aim for low coupling everywhere.

## Cohesion

The **strength of the contextual relationship** between elements in the same container: variables in a method, methods in a class, classes in a module, and so on up (it's fractal).

Two classes belong in the same module only when they share:

* **an architectural layer:** same layer *can* share a module; different layers *must* be split by at least a module boundary.
* **a bounded context:** the same rule.

```
✓ cohesive      UserReader + UserCache
               → both deal with user data, same layer

✗ not cohesive  UserController + UserRepository + InvoiceMapper in one module
               → several layers and contexts together; harder to extend over time
```

## Connascence: grading a dependency

Two components are **connascent** when changing one requires changing the other. Connascence says *what kind* of dependency it is. Weaker (better) first:

| # | Kind | ✗ Example | Fix |
|---|---|---|---|
| **Static:** visible in the code, easier to fix | | | |
| 1 | Name | Client calls a static method by name; renaming breaks it | Usually acceptable |
| 2 | Type | Client knows the concrete type; the compiler catches mismatches | Usual minimum in OO |
| 1–2 | *Interface* (unofficial) | Client knows only the message shape (`IDataRecord.Save()`) | What dependency inversion buys |
| 3 | Meaning | `GetName()` returns `"N/A"` when unset and clients compare against it; changing it breaks clients with no compiler error | Nullable/option type, enum, Null Object, dedicated method or type |
| 4 | Algorithm | A test recomputes the production checksum formula, so any algorithm change breaks the test | Assert against known values or properties |
| 5 | Position | `new Person(int age, int weight)` called as `new Person(185, 33)`; the compiler catches neither the mistake nor a reorder | Value types (`Age`, `Weight`), named arguments, parameter objects |
| **Dynamic:** visible only at run time, stronger | | | |
| 6 | Execution order | Set property X before calling Y; `Init()` before `Use()` | Constructor injection, immutable construction |
| 7 | Timing | Temporal dependencies from threading | Synchronization design |
| 8 | Value | Two places must hold the same constant at run time | One source of truth |
| 9 | Identity | Components depend on the *same instance* | Make the sharing explicit |

## Weigh it by locality

The farther apart the two sides, the more it matters:

* **Inside one class or project:** strong connascence is tolerable.
* **Across package, process or service boundaries:** reduce it aggressively. The argument *order* of a remote operation is connascence of position that forces every remote client to update.

## Using it in a review

* Classify each problem precisely: "connascence of meaning across a service boundary".
* Prefer refactors that move a dependency **up** the table, toward weaker kinds: meaning → type, position → name, execution order → type (via constructor injection).
* Pair it with cohesion:
   * strong connascence + different modules → maybe they belong together
   * weak cohesion + same module → maybe they belong apart

## Closing principle

Test-first, write the simplest code that passes, and improve the design only under green tests. A solution should never be more complicated than the problem it solves.
