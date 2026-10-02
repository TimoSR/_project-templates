# Liskov Substitution: contracts and variance

## Contents
- Definition
- The rules at a glance
- Contracts: preconditions, postconditions, invariants
- Implementing contracts
- Variance
- Exceptions
- Smells

## Definition

> If S is a subtype of T, objects of type T may be replaced with objects of type S without breaking the program.

* Three ingredients: the **base type** the client holds, the **subtype** actually supplied, and the **context** of use.
* The client must stay correct whichever subtype it gets. A new subtype that forces client changes means the hierarchy is broken.
* LSP is what lets OCP and SRP work.

## The rules at a glance

The running example is a `ShippingStrategy` hierarchy:

| Rule | ✗ Violation | What breaks |
|---|---|---|
| Preconditions can't be strengthened | Base accepts a `null` destination; `WorldWideShippingStrategy` throws on `null` | Every client written against the base; no caller can satisfy both contracts |
| Postconditions can't be weakened | Base guarantees cost > 0; a subtype returns 0 for domestic | A client dividing by the cost throws `DivideByZeroException` on domestic orders |
| Invariants must be preserved | Subtype adds an unguarded public `FlatRate` setter | `-1` is accepted |
| Parameters contravariant, returns covariant | Client downcasts the returned `Entity` to `User` | Variance is worked around, not modeled |
| No new exception types | `UserRepository` throws an unrelated `UserNotFoundException` | Clients must know every implementation's exceptions |

A base-class contract test suite catches these immediately: it fails for the offending subtype.

## Contracts

A signature says almost nothing. `decimal CalculateShippingCost(float packageWeightInKilograms, Size<float> packageDimensionsInInches, RegionInfo destination)` doesn't say that a negative weight is invalid. Units in names help, but the **contract** lives in code.

* **Precondition:** must hold before the method runs.
   * Guard clauses at the top, throwing specific exceptions that name the parameter: `ArgumentOutOfRangeException(nameof(weight), "must be positive")`.
   * Reference only parameters and **publicly visible** state, so a client can check before calling.
* **Postcondition:** guaranteed on exit (a valid return value or state). Check it at the end, after all mutation.
* **Data invariant:** true for the object's whole lifetime.
   * Guard it in the constructor and in any setter.
   * Keep the field private and route every write, including the class's own, through the guarded property.

Fix an invariant in the base, so no subclass *can* write the field directly:

```csharp
public class ShippingStrategy
{
    private decimal flatRate;
    public ShippingStrategy(decimal flatRate) => FlatRate = flatRate;
    protected decimal FlatRate
    {
        get => flatRate;
        set => flatRate = value > 0m ? value
             : throw new System.ArgumentOutOfRangeException(nameof(value), "Flat rate must be positive and non-zero");
    }
}
```

**Encapsulation beats repeated contracts.** A precondition repeated in every method is an invariant of a missing value type:

```csharp
// ✗ "weight must be positive" guarded in every method that takes a weight
decimal CalculateShippingCost(float weightInKilograms, ...) { if (weightInKilograms <= 0) throw ...; ... }

// ✓ the value type owns the invariant; the precondition disappears
public readonly record struct Weight
{
    public float Kilograms { get; }
    public Weight(float kilograms) => Kilograms = kilograms > 0 ? kilograms : throw new System.ArgumentOutOfRangeException(nameof(kilograms));
}
decimal CalculateShippingCost(Weight weight, ...) { ... }
```

## Implementing contracts

* **Guard clauses** work everywhere. Modern .NET throw helpers: `ArgumentNullException.ThrowIfNull(x)`, `ArgumentOutOfRangeException.ThrowIfNegativeOrZero(x)`.
* **Microsoft Code Contracts** (`Contract.Requires/Ensures/Invariant`), which the book covers, is **not supported on .NET Core / .NET 5+**. Its lesson stands: define the contract **once per interface** so every implementation inherits it. Today:
   * an abstract **contract test suite** that every implementation's test class inherits (the book's `ShippingStrategyTestsBase`), and/or
   * a Template Method base: a public non-virtual method checks pre- and postconditions and calls a protected abstract core.
* Nullable reference types and value objects move many contracts into the type system, which is better still.
* **Don't catch contract violations.** A broken contract is a bug, not a recoverable condition. Fail fast (global error page or crash dialog) and log the full stack trace. Catch them in tests instead: **unit-test your contracts**.

## Variance

How subtyping of `T` carries over to types built from `T`:

| Kind | Position | Direction | Example |
|---|---|---|---|
| Covariance (`out T`) | Return values | Preserved: `I<User>` usable as `I<Entity>` | `IEntityRepository<out TEntity> where TEntity : Entity { TEntity GetByID(Guid id); }`: `UserRepository` returns a `User` with no downcast |
| Contravariance (`in T`) | Parameters | Reversed: `I<Entity>` usable as `I<User>` | An `IEqualityComparer<Entity>` works where `IEqualityComparer<User>` is required |
| Invariance | Both | Neither | `IDictionary<TKey, TValue>`: each parameter is both input and output |

* LSP needs contravariant parameters and covariant returns in subtypes. The `where` constraint keeps the generic version from being *more* permissive than the original.
* C# variance annotations exist only on generic interfaces and delegates.
* Since C# 9, overrides may declare covariant return types (`public override User GetByID(...)` over `Entity GetByID(...)`). The book predates this and uses generics. Both are fine.
* Overridden parameters stay invariant in C#. Java uses `? extends` / `? super`; Kotlin uses `out` / `in`.
* Downcasting or type-sniffing a return value (`if (entity is User user)`) is the symptom of variance being worked around.

## Exceptions

* Exceptions separate *reporting* an error from *handling* it.
   * Catch only where you can do something meaningful: roll back, show an error UI.
   * Never catch and ignore. Avoid catching base `Exception`, which also catches unrecoverable failures.
* Give each interface a base exception:

```csharp
// ✗ unrelated types: a client of IEntityRepository must know every implementation, or catch Exception
class EntityNotFoundException : System.Exception { }
class UserNotFoundException   : System.Exception { }

// ✓ implementation-specific exceptions derive from the interface's base exception
class EntityNotFoundException : System.Exception { }
class UserNotFoundException   : EntityNotFoundException { }
```

## Smells that signal a violation

* An override throws `NotImplementedException` / `NotSupportedException`. Example: a static `HeatDetector.Move()` in a `Sensor` hierarchy that assumes every sensor moves. The base is a premature abstraction; split it into capability interfaces ([dip-and-abstraction-design.md](dip-and-abstraction-design.md)).
* Clients decide behavior with `x is SpecialSubtype` or `x as SpecialSubtype`.
* Empty overrides of base methods that don't apply.
* Rectangle/Square-style mutation conflicts: a subtype can't honor a base setter's independent behavior.
* A contract test suite that has to be *skipped* for one subtype.

Treat a violation as technical debt that grows more expensive the longer it stays. Pay it down early.
