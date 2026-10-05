# Units as types: C# pattern for money formulas

## Contents

* [Types](#types)
* [Formula](#formula)
* [Rejected at compile time](#rejected-at-compile-time)
* [Test: the §3 check as the test body](#test-the-3-check-as-the-test-body)

§2 of `SKILL.md` applied to the annuity running example. Compiled and run on .NET 10: both tests pass, both wrong-unit lines are rejected with the errors shown.

## Types

* One struct per unit. The value inside is in one base unit; the unit is in the property name or comment.
* Operators are the laws: `Money × MonthlyRate → Money` is one month's interest. There is no `Money × AnnualRate`, so the classic "annual rate used as monthly" bug does not compile.
* Conversions between units are named functions that state their convention (`ToMonthlyNominal`): the convention is a model assumption (§5).

```csharp
namespace Loans.Calculations;

public readonly struct Money
{
    public decimal Value { get; } // currency, full precision; round only when booking or displaying

    public Money(decimal value)
    {
        Value = value;
    }

    public static Money operator +(Money left, Money right)
    {
        return new Money(left.Value + right.Value);
    }

    public static Money operator -(Money left, Money right)
    {
        return new Money(left.Value - right.Value);
    }

    public static Money operator *(Money money, decimal scalar)
    {
        return new Money(money.Value * scalar);
    }

    public static Money operator /(Money money, decimal scalar)
    {
        return new Money(money.Value / scalar);
    }

    public static decimal operator /(Money left, Money right) // same unit / same unit → dimensionless ratio
    {
        return left.Value / right.Value;
    }

    public static Money operator *(Money balance, MonthlyRate monthlyRate) // one month's interest
    {
        return new Money(balance.Value * monthlyRate.Fraction);
    }

    public bool ApproximatelyEquals(Money other, decimal toleranceCurrency)
    {
        return System.Math.Abs(Value - other.Value) <= toleranceCurrency;
    }
}

public readonly struct MonthlyRate
{
    public decimal Fraction { get; } // per month, 0.005 = 0.5 %

    public MonthlyRate(decimal fraction)
    {
        Fraction = fraction;
    }
}

public readonly struct AnnualRate
{
    public decimal Fraction { get; } // per year, 0.06 = 6 %

    public AnnualRate(decimal fraction)
    {
        Fraction = fraction;
    }

    public MonthlyRate ToMonthlyNominal() // model assumption: nominal ÷ 12, not effective (1 + r)^(1/12) − 1
    {
        return new MonthlyRate(Fraction / 12m);
    }
}
```

## Formula

The last line reads like the notation, and every intermediate value carries its unit: `Money × MonthlyRate → Money`, `× decimal → Money`, `÷ decimal → Money`.

```csharp
public static class Annuity
{
    // M = P · r(1+r)ⁿ / ((1+r)ⁿ − 1)
    public static Money? CalculateMonthlyPayment(Money principal, MonthlyRate monthlyRate, int paymentCount)
    {
        if (paymentCount <= 0)
        {
            return null;
        }
        if (monthlyRate.Fraction == 0m)
        {
            return principal / paymentCount;
        }

        var growthFactor = 1m;
        for (var month = 1; month <= paymentCount; month += 1)
        {
            growthFactor *= 1m + monthlyRate.Fraction;
        }
        return principal * monthlyRate * growthFactor / (growthFactor - 1m);
    }
}
```

* `decimal` has no `Pow`: the loop is the `(1+r)ⁿ`, and it stays exact in `decimal`.
* Partial operation → `null` for outside the domain (house rule: no exceptions in the domain). The Rust crate's equivalent is `checked_calculate` returning `Err(DivisionByZero { operation })`.

## Rejected at compile time

```csharp
var wrongSum = principal + monthlyRate;     // error CS0019: Operator '+' cannot be applied to operands of type 'Money' and 'MonthlyRate'
var wrongInterest = principal * annualRate; // error CS0019: Operator '*' cannot be applied to operands of type 'Money' and 'AnnualRate'
```

## Test: the §3 check as the test body

```csharp
namespace Loans.Calculations.Tests;

public class AnnuityTests
{
    [Xunit.Fact]
    public void Monthly_payment_repays_the_loan_to_zero()
    {
        // Arrange
        var principal = new Money(100_000m);
        var monthlyRate = new AnnualRate(0.06m).ToMonthlyNominal();
        var paymentCount = 360; // months
        var toleranceCurrency = 0.01m; // one cent

        // Act
        var payment = Annuity.CalculateMonthlyPayment(principal, monthlyRate, paymentCount);

        // Assert
        Xunit.Assert.NotNull(payment);
        var balance = principal;
        for (var month = 1; month <= paymentCount; month += 1)
        {
            balance = balance + balance * monthlyRate - payment.Value;
        }
        Xunit.Assert.True(balance.ApproximatelyEquals(new Money(0m), toleranceCurrency));
        Xunit.Assert.True(payment.Value.ApproximatelyEquals(new Money(599.55m), toleranceCurrency));
    }

    [Xunit.Fact]
    public void Zero_payment_count_returns_null()
    {
        var payment = Annuity.CalculateMonthlyPayment(new Money(100_000m), new MonthlyRate(0.005m), 0);

        Xunit.Assert.Null(payment);
    }
}
```
