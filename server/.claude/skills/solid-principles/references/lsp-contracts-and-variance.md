# Liskov Substitution Principle: contracts and variance

## Contents
- Definition and the three ingredients
- Contracts: preconditions, postconditions, data invariants
- The LSP contract rules (with failure examples)
- Implementing contracts (guard clauses, modern .NET notes)
- Variance: covariance, contravariance, invariance
- The exception rule
- Smells that signal LSP violations

## Definition

> If S is a subtype of T, then objects of type T may be replaced with objects of type S without breaking the program.

There are three ingredients: the **base type** clients hold a reference to, the **subtype** actually supplied, and the **context** in which the client uses it. LSP is about the client's behavior staying correct no matter which subtype it gets. If a new subtype forces clients to change, the hierarchy is broken. In that sense LSP is what lets OCP and SRP work.

The rules come in two groups:

- **Contract rules:** preconditions can't be strengthened, postconditions can't be weakened, and supertype invariants must be preserved.
- **Variance rules:** method parameters are contravariant, return types are covariant, and no new exceptions are thrown outside the existing exception hierarchy.

## Contracts

A method signature says almost nothing about expectations. `decimal CalculateShippingCost(float packageWeightInKilograms, Size<float> packageDimensionsInInches, RegionInfo destination)` doesn't tell you that a negative weight is invalid. Good names help a lot (units in parameter names prevent centimeter/pound mix-ups), but the **contract** lives in code.

- **Precondition:** something that must hold before the method can run correctly. Enforce it with guard clauses at the top that throw specific exceptions naming the parameter (`ArgumentOutOfRangeException(nameof(weight), "must be positive")`). Preconditions may only reference parameters and **publicly visible** state, because a client must be able to check them before calling.
- **Postcondition:** something guaranteed on exit, such as a valid return value or valid state. Check it at the end, after all mutation.
- **Data invariant:** a predicate true for the object's whole lifetime. Guard it in the constructor, and in the setter if it can change. Keep the field private and route all writes, including writes from the class's own methods, through the guarded property.

**Encapsulation beats repeated contracts.** If "weight must be positive" appears in every method that takes a weight, it is really an invariant of a missing **value type** (`Weight`, `FlatRate`, `Money`). Promote it, and the precondition disappears into the type.

## The contract rules, by failure

**Preconditions cannot be strengthened.** `ShippingStrategy` accepts a `null` destination. A subclass `WorldWideShippingStrategy` adds `if (destination == null) throw`. Every client written against the base can now blow up, and no caller can satisfy both contracts. Tests show this immediately: a base-class contract test suite (an abstract test fixture run against every subtype) fails for the subtype.

**Postconditions cannot be weakened.** The base guarantees cost > 0. The subtype returns 0 for domestic shipping. A client that divides by the cost now throws `DivideByZeroException` on domestic orders, a defect that came purely from substituting the subtype.

**Invariants must be preserved.** The base keeps `flatRate` positive and read-only. The subtype adds a public `FlatRate` setter with no guard, and now `-1` is accepted. Fix it in the base: a private field plus a **protected guarded property**, so no subclass *can* write the field directly.

```csharp
public class ShippingStrategy
{
    private decimal flatRate;
    public ShippingStrategy(decimal flatRate) => FlatRate = flatRate;
    protected decimal FlatRate
    {
        get => flatRate;
        set => flatRate = value > 0m ? value
             : throw new ArgumentOutOfRangeException(nameof(value), "Flat rate must be positive and non-zero");
    }
}
```

## Implementing contracts

- **Manual guard clauses** work everywhere. In modern .NET, prefer the throw helpers: `ArgumentNullException.ThrowIfNull(x)` and `ArgumentOutOfRangeException.ThrowIfNegativeOrZero(x)`.
- The book covers **Microsoft Code Contracts** (`Contract.Requires/Ensures/Invariant`, `[ContractInvariantMethod]`, and interface contracts via `[ContractClass]`/`[ContractClassFor]`). That library is **not supported on .NET Core / .NET 5+**. Its lasting lesson is still useful: define the contract **once per interface** so every implementation inherits it. Today you'd do that with:
  - an abstract **contract test suite** that every implementation's test class inherits (the book's `ShippingStrategyTestsBase` pattern), and/or
  - a Template Method base whose public non-virtual method checks pre- and postconditions and calls a protected abstract core.
- Nullable reference types and value objects move many contracts into the type system, which is better still.
- **Don't catch contract violations.** A broken contract means a bug, not a recoverable condition. Let it fail: global error page or friendly crash dialog, with the full stack trace and context logged. Catch them in tests, which means **unit-test your contracts**.

## Variance

Variance describes how subtyping of `T` carries over to types built from `T`.

- **Covariance** (`out T`, return positions) preserves the direction: `ICovariant<Subtype>` is usable as `ICovariant<Supertype>`. Example: `IEntityRepository<out TEntity> where TEntity : Entity { TEntity GetByID(Guid id); }`, so `UserRepository : IEntityRepository<User>` hands clients a `User` without downcasting. The `where` constraint keeps the generic version from being *more* permissive than the original.
- **Contravariance** (`in T`, parameter positions) reverses the direction: an `IEqualityComparer<Entity>` can be used where an `IEqualityComparer<User>` is required. A more general consumer substitutes for a more specific one.
- **Invariance**: neither applies. `IDictionary<TKey, TValue>` is invariant because each type parameter appears in both input and output positions.

LSP needs **contravariant parameters and covariant returns** in subtypes. Language notes:

- C# variance annotations exist only on generic interfaces and delegates.
- Since **C# 9**, overrides *may* declare covariant return types (`public override User GetByID(...)` overriding `Entity GetByID(...)`). The book predates this and works around it with generics. Both are fine.
- Overridden *parameters* are still invariant in C#. In Java, use `? extends` / `? super`; in Kotlin, `out` / `in`.

Downcasting or type-sniffing a returned value (`if (entity is User u)`) is the symptom that tells you variance is being worked around rather than modeled.

## The exception rule

Exceptions separate *reporting* an error from *handling* it. Catch only where you can do something meaningful (roll back, show an error UI). Never catch-and-ignore, and avoid catching base `Exception`, which also catches unrecoverable failures.

If `EntityRepository.GetByID` throws `EntityNotFoundException` and `UserRepository.GetByID` throws an unrelated `UserNotFoundException`, a client holding `IEntityRepository` must know about every implementation's exception, or catch `Exception`, and every new implementation forces client edits. **Give each interface a base exception and derive implementation-specific exceptions from it** (`UserNotFoundException : EntityNotFoundException`).

## Smells that signal an LSP violation

- An override that throws `NotImplementedException` / `NotSupportedException` (e.g. a static `HeatDetector.Move()` in a `Sensor` hierarchy that assumes every sensor moves). The base type is a premature abstraction; split it into capability interfaces (see dip-and-abstraction-design.md).
- Clients doing `if (x is SpecialSubtype)` or `x as SpecialSubtype` to decide behavior.
- Subclasses that ignore a base method (empty override) because it doesn't apply.
- The classic Rectangle/Square-style mutation conflicts: a subtype that can't honor a base setter's independent behavior.
- A contract test suite that has to be *skipped* for one subtype.

Treat any LSP violation as technical debt that gets more expensive the longer it stays. Pay it down early.
