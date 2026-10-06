# Dependency Inversion and abstraction design

## Contents
- Definition
- Why `new` is a code smell
- Package structure: Entourage vs Stairway
- Designing good abstractions

## Definition

> High-level modules should not depend on low-level modules. Both should depend on abstractions.
> Abstractions should not depend on details. Details should depend on abstractions.

* An interface sits between client and implementation, and **both** depend on it.
* It must hold at class level *and* at package level (assembly, project, module). Most violations are at package level.

## Why `new` is a code smell

Interfaces describe *what*, classes describe *how*, and constructors belong to the *how*. Outside value types, DTOs, framework primitives and the composition root, `new SomeService()` in a client is inappropriate intimacy:

```csharp
// ✗ the controller builds its own service
public class AccountController
{
    private readonly SecurityService securityService = new SecurityService();   // quietly opens an ORM session
}

// ✓ depend on the interface, inject it, guard it
public class AccountController
{
    private readonly ISecurityService securityService;
    public AccountController(ISecurityService securityService)
    {
        if (securityService == null) { throw new System.ArgumentNullException(nameof(securityService)); }
        this.securityService = securityService;
    }
}
```

What the ✗ version costs:

1. **Permanent dependency.** Swapping the implementation means editing the client or growing the service.
2. **Hidden transitive dependencies.** The controller now depends on the ORM too. If `SecurityService`'s constructor starts needing a connection string, every client breaks.
3. **Untestable.** No fake without tools that intercept constructors.
4. **Leaky method design.** Clients build things only to satisfy a badly shaped API (`new UserRepository().GetByID(id)`). Move that work behind the service: `ChangeUsersPassword(Guid userId, string newPassword)`.

Statics are the same smell in another form ("skyhooks"): `ConfigurationManager`, `DateTime.Now`, global singletons. Put them behind an adapter interface:

```csharp
// ✗ untestable: the test can't control the time
if (System.DateTime.Now.Hour >= 17) { CloseTrading(); }

// ✓ IClock is injected; a test passes a fixed clock
if (clock.Now.Hour >= 17) { CloseTrading(); }
```

## Package structure: Entourage vs Stairway

```
✗ Entourage — the interface ships with its implementation

  Controllers ──► Services { ISecurityService, SecurityService } ──► Domain ──► NHibernate

  → build Controllers alone and NHibernate still lands in bin/

✓ Stairway — interfaces and implementations in separate packages

  Controllers    ──►  Services.Interfaces  ◄──  Services.Impl
  Services.Impl  ──►  Domain.Interfaces    ◄──  Domain.Impl
  Domain.Impl    ──►  Data.Interfaces      ◄──  Data.NHibernate

  → every arrow points at an interface package; no implementation is ever referenced
```

What Entourage costs:

* **Discipline:** implementations must be public to be constructed anywhere, so nothing stops a developer `new`ing one.
* **Bloat:** an alternative implementation (say, over a message bus) adds *its* dependencies to the shared package, and every client picks them up.

Stairway rules:

* Clients reference only interface packages.
* An implementation references its own interface package plus the *interface* packages of its dependencies, never another implementation package.
* **Interface packages have no external dependencies.** Signatures expose only your own types, other interface packages' types and core framework types.
   * Never third-party types (ORM sessions, driver or document types, logger types).
   * Third-party libraries usually ship as an Entourage, so depending on their interfaces still ties you to their implementation. Wrap them behind your own interface with an adapter.
* It adds a few projects, and often *reduces* the count in a badly arranged solution.
* **Pragmatic limit:** when wrapping a large framework costs too much, accept that it's omnipresent and that replacing it later will be expensive.
* **Layers:** each layer is an interface package plus an implementation package.
   * A higher layer referencing a lower layer's *implementation* is a leaky abstraction: the lower layer's dependencies seep upward.
   * A domain model must not reference the ORM. Put ORM mapping in a separate, implementation-specific package.

## Designing good abstractions

Interfaces are not automatically abstractions. The book's example is a measurement app:

* Sensors `Camera`, `Laser` and `TouchProbe` share an abstract `Sensor` base with a virtual `Move`.
* A command switchboard type-sniffs (`CurrentSensor as Camera`) for every command.

Three problems:

* **Premature abstraction:** `Sensor` assumes every sensor moves, so a static `HeatDetector` would throw from `Move()`, which violates LSP.
* **Concretion coupling:** the switchboard knows every concrete sensor.
* **Type-sniffing everywhere.**

Running "extract interface" on each class gives `ICamera`, `ILaser`, `ITouchProbe`, each 1:1 with its class: indirection for nothing.

### Abstract capabilities instead

Look for shared *behavior* behind different names. Camera `Zoom` and probe `Raise`/`Lower` are both z-axis adjustment, and every sensor moves in x/y. Name capabilities as **-able adjectives**:

```csharp
public interface ISensor            { string GetName(); }                       // the only universal trait
public interface IMovable           { void Move(float x, float y); }
public interface IHeightAdjustable  { void Raise(float height); void Lower(float height); }
public interface IRotatable         { void Pitch(float pitch); void Roll(float roll); }
public interface IMeasurable        { void WriteMeasurement(TextWriter writer); }

public class Camera     : ISensor, IMovable, IHeightAdjustable { ... }      // Raise/Lower drive the zoom
public class Laser      : ISensor, IMovable { ... }
public class TouchProbe : ISensor, IMovable, IRotatable, IHeightAdjustable { ... }
```

* Each class **opts in** to its capabilities: an intersection, not a union of every method on one fat `ISensor`.
* The client sniffs **capabilities**, not concretions:

```csharp
// ✗ every new sensor edits the switchboard
if (CurrentSensor is Camera camera) { camera.Zoom(level); }

// ✓ a new sensor that implements IHeightAdjustable works with no client change
if (CurrentSensor is IHeightAdjustable adjustable) { adjustable.Raise(height); }
```

   * One command per capability shrinks the switchboard and documents it. Next step: make each command an `ICommand`, so the switchboard is closed for modification.
* **Reuse is the test of an abstraction.** `IMovable` and `IHeightAdjustable` are reused. `IRotatable` is used once, which is a warning sign. It also lacks yaw, which nobody needs, so don't add it.
* **Turn disparate queries into one command.** `Capture()` returns `Image`, `Measure()` returns `float`, `GetPressure()` returns `PoundsPerSquareInch`: no common return type. The client actually wants to *output* the measurement, so invert it into `IMeasurable.WriteMeasurement(TextWriter)`.
   * Pick the most reusable sink: `TextWriter` (console, file, HTTP response), not `Console`.
* **Sealed or third-party classes** join the abstraction through adapters that implement your capability interfaces.
