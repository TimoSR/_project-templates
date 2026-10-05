# Standards tests

Checks that the code follows the rules we set: interfaces, base classes, generic constraints, DI
registration. Plain reflection over the compiled assemblies: no I/O, unit speed. Existing example:
`FF.Tests/HubSpot/HubSpotMapperRegistrationTests.cs` (every legacy mapper is also registered
through the shared contract).

## Domain conformance

When we implement a domain, check every implementation satisfies its contract: the right interfaces
and abstract classes.

```csharp
[Fact]
public void Every_alarm_policy_implements_IAlarmPolicy()
{
    // Arrange
    var policyTypes = typeof(FF.App.Alarms.Policies.IAlarmPolicy).Assembly.GetTypes()
        .Where(type => type.Namespace == "FF.App.Alarms.Policies" && type.IsClass && !type.IsAbstract)
        .ToArray();

    // Act
    var violations = policyTypes
        .Where(type => !typeof(FF.App.Alarms.Policies.IAlarmPolicy).IsAssignableFrom(type))
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
       var entityParameter = typeof(FF.App.Alarms.Policies.PolicyBase<>).GetGenericArguments()[0];

       // Act
       var constraints = entityParameter.GetGenericParameterConstraints();

       // Assert
       Xunit.Assert.Contains(typeof(Ftb.Core.IEntity), constraints);
   }
   ```

2. **The rule behaves correctly:** a type that satisfies the constraint runs through the generic
   and gets the behavior the base class promises (e.g. a `PolicyBase<Account>` subclass resolves
   alarms against the `Account` entity name). Use a real implementation; it doubles as the usage
   example for the next developer who builds on the generic.

* Name the test as the rule (`PolicyBase_only_accepts_entities`), so the test list reads as the
  architecture's rulebook.
* Every new generic base, marker interface or registration convention ships with its standards
  test in the same change.
