# Test matrices

Fold variants of one behavior into a `[Theory]`, expected value in each row. Name the input state
with a function, so the row says what it's aiming for without a comment.

```csharp
// ✗ the intent lives in a comment; -15 means nothing on its own
[InlineData(100000, 40000, 10000, AutoInvestStrategyEnum.Monthly, -15)] // Days 15-21: factor = 4

// ✓ the state has a name
public static TheoryData<System.DateTime, int> MonthlyWeeks => new()
{
    { FirstWeekOfMonth(), 2500 },
    { ThirdWeekOfMonth(), 10000 },
    { AfterThirdWeek(),   5000 },
};
private static System.DateTime ThirdWeekOfMonth() { return System.DateTime.UtcNow.AddDays(-15); }

[Theory]
[MemberData(nameof(MonthlyWeeks))]
public void Monthly_strategy_invests_less_as_the_month_runs_out(System.DateTime startedAt, int expectedAmount) { ... }
```

* `[InlineData]` takes only compile-time constants: a `DateTime` as a string (xUnit converts it),
  anything else via `[MemberData]` / `TheoryData`.
* Rows that need different assertions are different tests.
