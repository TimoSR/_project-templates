# Standards tests

Checks that the code follows the rules we set: interfaces, base classes, generic constraints, DI
registration. Plain reflection over the compiled assemblies: no I/O, unit speed. They live in the `test/`
folder of the module whose rules they guard (`payment-module/test/DunningPolicyStandardsTests.cs`).

## Domain conformance

When we implement a domain, check every implementation satisfies its contract: the right interfaces
and abstract classes.

```csharp
[Fact]
public void Every_dunning_policy_implements_IDunningPolicy()
{
    // Arrange
    var policyTypes = typeof(Billing.Payment.Domain.Policies.IDunningPolicy).Assembly.GetTypes()
        .Where(type => type.Namespace == "Billing.Payment.Domain.Policies" && type.IsClass && !type.IsAbstract)
        .ToArray();

    // Act
    var violations = policyTypes
        .Where(type => !typeof(Billing.Payment.Domain.Policies.IDunningPolicy).IsAssignableFrom(type))
        .ToArray();

    // Assert
    Xunit.Assert.NotEmpty(policyTypes); // a scan that finds nothing passes every rule
    Xunit.Assert.Empty(violations);     // the failure message lists the offending types
}
```

* Find the types by a stable marker (namespace, base type, attribute), and assert the scan found
  some. A renamed namespace would otherwise make the rule pass vacuously.
* Assert on the list of violations, so one run names every offender.

## Generic architecture rules

A generic building block (`PolicyBase<TEntity> where TEntity : IEntity`,
`ObjectTypeBase<T> where T : EntityBase`) encodes an inheritance rule. The compiler enforces the
`where` only while it exists; deleting it compiles fine and drops the rule. So the generic owns
tests for both halves:

1. **The rule is in place:** the constraint is declared.

   ```csharp
   [Fact]
   public void PolicyBase_only_accepts_entities()
   {
       // Arrange
       var entityParameter = typeof(Billing.Payment.Domain.Policies.PolicyBase<>).GetGenericArguments()[0];

       // Act
       var constraints = entityParameter.GetGenericParameterConstraints();

       // Assert
       Xunit.Assert.Contains(typeof(Architecture.Domain.IEntity), constraints);
   }
   ```

2. **The rule behaves correctly:** a type that satisfies the constraint runs through the generic
   and gets the behavior the base class promises (e.g. a `PolicyBase<Invoice>` subclass evaluates
   its rule against the `Invoice` entity). Use a real implementation; it doubles as the usage
   example for the next developer who builds on the generic.

* Name the test as the rule (`PolicyBase_only_accepts_entities`), so the test list reads as the
  architecture's rulebook.
* Every new generic base, marker interface or registration convention ships with its standards
  test in the same change.
