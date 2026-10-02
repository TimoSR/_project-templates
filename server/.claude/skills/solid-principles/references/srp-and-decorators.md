# Single Responsibility Principle and the patterns that enforce it

## Contents
- Definition and how to find responsibilities
- The two-stage refactor (clarity, then abstraction)
- Rules for the extracted interfaces
- Adapter: turning third-party into first-party
- The Decorator family (composite, predicate, branching, lazy, logging, profiling)
- Limits

## Definition

A class (or method, or module) should have **one and only one reason to change**. When a class has several reasons, it has several responsibilities. Give each responsibility to another class behind an abstraction, and keep in the original class only the part that coordinates them.

### Finding responsibilities

Describe what the code does, step by step. Then, for each step, ask what real-world change would force an edit. The book's running example is a `TradeProcessor.ProcessTrades(Stream)` that reads lines, parses and validates fields, logs warnings to the console, maps to records, and inserts through a stored procedure. It changes when any of the following happen:

- the input source changes (a stream becomes a web service)
- the input format changes (a new "broker" field)
- the validation rules change
- the logging destination changes (console doesn't work in a hosted service)
- the storage changes (a stored-procedure parameter, a document DB, storage moved behind an API)

Each of these is a responsibility, and for each one, `TradeProcessor` would have to be edited.

## The two-stage refactor

### Stage 1: refactor for clarity

Extract a method per responsibility so the top-level method reads like the process:

```csharp
public void ProcessTrades(Stream stream)
{
    var lines  = ReadTradeData(stream);
    var trades = ParseTrades(lines);      // delegates to ValidateTradeData + MapTradeDataToTradeRecord
    StoreTrades(trades);                  // logging goes through a LogMessage helper
}
```

This step is worth doing on its own because it is cheap and makes the code readable. It does **not** make the code adaptive: changing how logging works still means editing this class. Treat it as a stepping stone.

### Stage 2: refactor for abstraction

Move each responsibility into its own class behind an interface, and inject the interfaces:

```csharp
public class TradeProcessor
{
    private readonly ITradeDataProvider provider;
    private readonly ITradeParser parser;
    private readonly ITradeStorage storage;

    public TradeProcessor(ITradeDataProvider provider, ITradeParser parser, ITradeStorage storage)
    { this.provider = provider; this.parser = parser; this.storage = storage; }

    public void ProcessTrades()
    {
        var lines  = provider.GetTradeData();
        var trades = parser.Parse(lines);
        storage.Persist(trades);
    }
}
```

`TradeProcessor` now holds the blueprint of the process and nothing else. Its only reason to change is a change to the process itself. Repeat **recursively**: `SimpleTradeParser` delegates to `ITradeValidator` and `ITradeMapper`, and validator and storage both log through an `ILogger`.

Once the refactor is done, every original change request becomes "add or replace one implementation":

| Change | Handled by |
|---|---|
| Read from a web service | New `ITradeDataProvider` |
| New broker field | Edit validator, mapper, and storage implementations only |
| New validation rules | Edit or replace the `ITradeValidator` implementation |
| New log destination | Logging adapter (e.g. `Log4NetLoggerAdapter : ILogger`) |
| Document DB / web service storage | New `MongoTradeStorage` / `WebServiceTradeStorage` |

## Rules for the extracted interfaces

- **Keep technology out of interface signatures.** `ITradeDataProvider.GetTradeData()` takes no `Stream`. Instead, `StreamTradeDataProvider` receives the `Stream` in its *constructor*. Constructors can depend on anything without polluting the interface.
- **Naming convention.** Drop the `I` and prefix the implementation context: `StreamTradeDataProvider`, `AdoNetTradeStorage`, `DapperTradeStorage`. Use `Simple…` for implementations with no special dependency.
- **Packaging.** Interfaces go in their own package. Implementations that share only core-framework dependencies can share a package. An implementation that pulls in a third-party or non-core dependency gets its own package (e.g. `Services.Dapper`), so clients never inherit that dependency transitively. See the Stairway pattern in dip-and-abstraction-design.md.
- **Return read-only shapes** (`IEnumerable<T>` rather than `List<T>`) so later steps can't mutate what earlier steps produced.

## Adapter: third-party → first-party

An adapter implements *your* interface and delegates to a third-party type:

```csharp
public class Log4NetLoggerAdapter : ILogger
{
    private readonly ILog log;
    public Log4NetLoggerAdapter(ILog log) { this.log = log; }
    public void LogWarning(string message, params object[] args) => log.WarnFormat(message, args);
}
```

With the adapter in place, only the composition root and the adapter's own package reference log4net. Everything else depends on `ILogger`. Adapters also smooth over semantic mismatches. The book's `StopwatchAdapter : IStopwatch` calls `Stop`, reads the elapsed time, then `Reset`s, because `Stopwatch.Start` *resumes* rather than restarting.

> Pragmatic exception: for truly ubiquitous cross-cutting libraries, depending on the third-party type directly can be the better trade. Decide this deliberately.

## The Decorator pattern

A decorator **implements an interface and wraps another instance of the same interface**. It adds behavior before or after delegating, and the client can't tell it's there. Use it when some functionality is too entangled with a class's intent to move out any other way.

```csharp
public class LoggingCalculator : ICalculator
{
    private readonly ICalculator inner;
    public LoggingCalculator(ICalculator inner) { this.inner = inner; }
    public int Add(int x, int y)
    {
        Console.WriteLine($"Add(x={x}, y={y})");
        var result = inner.Add(x, y);
        Console.WriteLine($"result={result}");
        return result;
    }
}
// composition root: ICalculator calc = new LoggingCalculator(new ConcreteCalculator());
```

### Variants

- **Composite.** Implements `IComponent` and holds a list of `IComponent`s, forwarding each call to all of them, so clients treat many as one. `Add`/`Remove` aren't on the interface; the factory or composition root populates the composite. The children can be different concrete types, or other composites, which gives you trees.
- **Predicate decorator.** Hides conditional execution from the client: `PredicatedComponent(IComponent inner, IPredicate predicate)` calls `inner` only when `predicate.Test()` is true. This beats both a client that `new`s a `DateTester` and a client whose method gains a `DateTester` parameter, which breaks its public interface. Prefer an `IPredicate` interface over `Func<bool>`, because interfaces can themselves be decorated, adapted, and composed.
- **Branching decorator.** `BranchedComponent(IComponent whenTrue, IComponent whenFalse, IPredicate predicate)`.
- **Lazy decorator.** Don't hand clients a `Lazy<IComponent>`, because that forces laziness on every caller. Wrap it instead: `LazyComponent(Lazy<IComponent>) : IComponent`, so the client sees a plain `IComponent`.
- **Logging decorator.** Removes logging noise from implementations. Limits: it can't see private state, and it needs one decorator per interface. For logging that touches everything, prefer aspect-oriented programming (an interceptor or attribute-based aspect).
- **Profiling decorator.** `ProfilingComponent(IComponent inner, IStopwatch stopwatch)` times calls. First extract `IStopwatch` so the stopwatch can be decorated too (`LoggingStopwatch : IStopwatch`). Replacing a concrete dependency with an interface is often the step that must come before any decorator.
- **Properties and events** can be decorated too. Write explicit get/set or add/remove accessors that delegate to the inner instance; auto-properties and auto-events can't be decorated.

## Limits and judgment

- SRP yields **more, smaller classes**. That is the point, but it does spread logic across files. Spend that cost only where change is predicted (see ocp-and-protected-variation.md).
- Stage 1 alone is a legitimate stopping point for code you don't expect to change.
- Interfaces with very many members make decorators painful. That is the signal to apply ISP.
