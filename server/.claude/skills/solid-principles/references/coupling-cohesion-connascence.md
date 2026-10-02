# Coupling, cohesion, and connascence

These are how you judge whether the SOLID refactoring paid off. Low coupling and high cohesion *correlate* with good code. The stronger causal claim runs the other way: high coupling and low cohesion make projects fail.

## Coupling

Coupling is the **strength of interdependence** between software elements: methods, classes, packages, components, subsystems. When it's low, elements change independently. When it's high, one change cascades into others. Aim for low coupling everywhere.

## Cohesion

Cohesion is the **strength of the contextual relationship** between elements in the same container: variables in a method, methods in a class, classes in a module, modules in a solution, and so on up (it's fractal). Low cohesion at any scope is a problem. Two classes have a *valid* relationship when they share:

- **the same architectural layer.** Classes from the same layer *can* share a module. Classes from different layers *must* be separated by at least a module boundary.
- **the same bounded context.** The same rule applies: same context *can* share, different contexts *must* be separated.

For example, a class that reads user data and a class that caches user data are cohesive, because both deal with user data. A module that lumps several layers or bounded contexts together is a common smell, and it gets harder to extend over time.

## Connascence: grading how bad a dependency is

Two components are **connascent** when a change to one requires a change to the other. Knowing that a dependency exists isn't enough; connascence tells you what *kind* it is. Levels run from weaker (better) to stronger (worse).

### Static (visible by reading the code; easier to find and fix)

1. **Name.** The client must know a name (a static method, a global function). Renaming it breaks callers.
2. **Type.** The client must know a concrete type. This is the usual minimum in strictly OO languages, and the compiler catches mismatches.
   - *Unofficial level between Name and Type:* **Interface.** The client knows only the name and shape of messages (`IDataRecord.Save()`), not the concrete type. This is what dependency inversion buys you.
3. **Meaning.** Special values carry implied meaning (`GetName()` returns `"N/A"` when unset, and clients compare against that exact string). Changing the sentinel breaks clients *with no compiler error*. Fix it with nullable/option types, enums, a Null Object, or a dedicated method or type.
4. **Algorithm.** Both sides must agree on the steps. A common example is a test that recomputes the production hash or checksum formula, so any change to the algorithm breaks the test. Assert against known values or properties instead.
5. **Position.** Order matters, typically several same-typed parameters (`new Person(int age, int weight)` called as `new Person(185, 33)`). Neither a mistake nor a reordering of the definition is caught by the compiler. Fix it with distinct value types (`Age`, `Weight`), named arguments, or parameter objects.

### Dynamic (only visible at run time; stronger, harder to remove)

6. **Execution order.** Calls must happen in a particular sequence (set property X before calling Y; `Init()` before `Use()`). A well-designed class makes it easy to do things right and hard to do them wrong. Constructor injection and immutable construction remove most of these.
7. **Timing.** Temporal dependencies, usually from threading or concurrency.
8. **Value.** Several components must agree on a value at run time (e.g. two places that must hold the same constant).
9. **Identity.** Components depend on the *same instance* of an entity.

## Weigh connascence by locality

The same connascence matters more the farther apart the two sides are:

- **Inside one class or project:** strong connascence is tolerable.
- **Across package, process, or service boundaries:** reduce it aggressively. For example, the argument *order* of a remote service operation is connascence of position that forces every remote client to update if it changes, regardless of types.

## How to use this in a review

- Classify each problematic dependency (e.g. "connascence of meaning across a service boundary"). This gives a precise, non-subjective vocabulary.
- Prefer refactors that move a dependency **down** the list (meaning → type, position → name, execution order → type via constructor injection).
- Pair it with cohesion: if two things have strong connascence *and* live in different modules, maybe they belong together. If they have weak cohesion *and* share a module, maybe they belong apart.

## Closing principle from the book

Test-first, write the simplest code that passes, and improve the design only with green tests as a safety net. A solution should never be more complicated than the problem it solves. Good design means low coupling between methods, classes, and modules, and high cohesion inside each.
