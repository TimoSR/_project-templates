# Dependency Inversion Principle and abstraction design

## Definition

> High-level modules should not depend on low-level modules. Both should depend on abstractions.
> Abstractions should not depend on details. Details should depend on abstractions.

In practice, an interface sits between client and implementation, and **both** depend on it. The principle has to hold at the class level *and* at the package (assembly/project/module) level. Most violations happen at the package level.

## Why `new` is a code smell

Interfaces describe *what*, classes describe *how*, and constructors belong to the *how*. So apart from a few exceptions (value types, DTOs, framework primitives, and the composition root), `new SomeService()` inside a client is inappropriate intimacy. It causes four problems:

1. **The dependency is permanent.** Swapping the implementation means editing the client or growing the existing service.
2. **Hidden transitive dependencies.** A parameterless `SecurityService()` may quietly open an ORM session, so `AccountController` now depends on the ORM too. If that constructor's signature changes (it starts needing a connection string), every client breaks.
3. **Untestable.** The real dependency can't be replaced with a fake without heavy tools that intercept constructors.
4. **Leaky method design.** Clients end up building things (`new UserRepository().GetByID(id)`) only to satisfy a badly shaped API. Move that work behind the service: `ChangeUsersPassword(Guid userId, string newPassword)`.

The fix: extract the interface, depend on it, inject it through the constructor, and guard against null.

```csharp
public AccountController(ISecurityService securityService)
{
    this.securityService = securityService ?? throw new ArgumentNullException(nameof(securityService));
}
```

Statics such as `ConfigurationManager`, `DateTime.Now`, and global singletons are "skyhooks", the same smell in a different form. Put them behind an adapter interface (`ISettings`, `IClock`).

## Package structure: Entourage vs. Stairway

### The Entourage anti-pattern

The interface and its implementation share a package. `Controllers → Services` (which holds `ISecurityService` *and* `SecurityService`) → `Domain` → NHibernate. You ask for one interface and its whole entourage follows: build `Controllers` alone and NHibernate still shows up in `bin/`. This causes two problems:

- **Discipline.** The implementations must be public so they can be constructed somewhere, so nothing stops a developer from `new`ing one directly.
- **Bloat.** Adding an alternative implementation (say, one using a message bus) adds *its* dependencies to the shared package, and every client picks them up.

### The Stairway pattern

Put interfaces and implementations in **separate packages**:

```
Controllers ──► Services.Interfaces ◄── Services.Impl ──► Domain.Interfaces ◄── Domain.Impl ──► Data.Interfaces ◄── Data.NHibernate
```

- Clients reference only interface packages.
- Implementations reference their own interface package plus the *interface* packages of whatever they depend on, never another implementation package.
- **Interface packages have no external dependencies.** Their signatures expose only your own types, other interface packages' types, and core framework types. They never expose third-party types (ORM sessions, driver/document types, logger types). Third-party libraries usually ship in Entourage form (interface and implementation in one package), so depending on their interfaces still ties you to their implementation. Wrap them behind your own interface with an adapter.
- This adds only a few projects, and it often *reduces* the count in a badly arranged solution.
- **Pragmatic limit:** when wrapping a large framework would cost too much, accept that it becomes omnipresent, and acknowledge that replacing it later will be expensive.

In layered architectures, each layer is an interface package plus an implementation package. A higher layer that references a lower layer's *implementation* is a **leaky abstraction**: the lower layer's dependencies seep upward. A domain model should not reference the ORM. Put ORM mapping in a separate, implementation-specific package.

## Designing good abstractions

Interfaces are not automatically abstractions. The book's example is a measurement app with `Camera`, `Laser`, and `TouchProbe` sensors under an abstract `Sensor` base that has a virtual `Move`, plus a command switchboard that type-sniffs (`CurrentSensor as Camera`) for every command. It has three problems:

- **Premature abstraction.** `Sensor` assumes every sensor moves. A static `HeatDetector` would have to throw from `Move()`, which is an LSP violation.
- **Concretion coupling.** The switchboard knows every concrete sensor class.
- **Type-sniffing everywhere.**

### The trouble with "extract interface"

Running a refactoring tool's "extract interface" on each class gives `ICamera`, `ILaser`, `ITouchProbe`, each 1:1 with its class. That adds indirection, costs comprehensibility, and buys nothing.

### Abstract capabilities instead

Look for shared *behavior* hiding behind different names. Camera `Zoom` and probe `Raise`/`Lower` are both z-axis adjustment, and every sensor moves in x/y. Name the capabilities as **-able adjectives**, which come from verbs:

```csharp
public interface ISensor            { string GetName(); }                     // the only universal trait
public interface IMovable           { void Move(float x, float y); }
public interface IHeightAdjustable  { void Raise(float h); void Lower(float h); }
public interface IRotatable         { void Pitch(float p); void Roll(float r); }
public interface IMeasurable        { void WriteMeasurement(TextWriter writer); }

public class Camera     : ISensor, IMovable, IHeightAdjustable { ... }   // Raise/Lower drive the zoom level
public class Laser      : ISensor, IMovable { ... }
public class TouchProbe : ISensor, IMovable, IRotatable, IHeightAdjustable { ... }
```

- Each class **opts in** to the capabilities it has. That is an intersection of capabilities, not a union of every method on one fat `ISensor`.
- The client sniffs for **capabilities**, not concretions (`CurrentSensor as IHeightAdjustable`). One command per capability means the switchboard shrinks and becomes self-documenting. A new sensor that implements the right interfaces works with **no client change**. A natural next step is to make each command an `ICommand` so the switchboard itself is closed for modification.
- **Reuse is the test of an abstraction.** `IMovable` and `IHeightAdjustable` are reused. `IRotatable` is used once, which is a warning sign (and it is missing yaw, which nobody needs, so don't add it).
- **Unify disparate queries by turning them into a command.** `Capture()` returns `Image`, `Measure()` returns `float`, and `GetPressure()` returns `PoundsPerSquareInch`, so there is no common return type. Look at what the client actually *wants*, which is to output the measurement, and invert it: `IMeasurable.WriteMeasurement(TextWriter)`. Choose the most reusable sink: `TextWriter` (console, file, HTTP response) rather than `Console`.
- **Sealed or third-party classes** can still join the abstraction through **adapters** that implement your capability interfaces.

## Summary checklist

- Does any business class `new` a service or call infrastructure statics? Then inject an interface.
- Does any interface package reference an implementation package or a third-party library? Then restructure into a Stairway and add an adapter.
- Does any interface have exactly one non-test implementation and mirror its class 1:1? Then reconsider: model capabilities, or drop the interface.
- Are clients casting to concrete types? Then introduce capability interfaces.
- Does an abstraction force some implementers to throw? Then the abstraction is premature; split it.
