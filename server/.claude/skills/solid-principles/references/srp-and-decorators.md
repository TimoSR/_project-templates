# Single Responsibility and the patterns that enforce it

## Contents
- Definition and finding responsibilities
- The two-stage refactor
- Rules for extracted interfaces
- Adapter
- Decorator and its variants
- Limits

## Definition

A class, method or module has **one reason to change**. Several reasons mean several responsibilities: give each to another class behind an abstraction, and keep only the coordination.

### Finding responsibilities

Describe the code step by step, then ask which real-world change would force an edit to each step. The book's running example is `TradeProcessor.ProcessTrades(Stream)`. It reads lines, parses and validates fields, logs warnings to the console, maps the lines to records, and inserts them through a stored procedure. It must change when:

* the input source changes (stream → web service)
* the input format changes (a new broker field)
* the validation rules change
* the log destination changes (console doesn't work in a hosted service)
* the storage changes (a stored-procedure parameter, a document DB, an API)

Five reasons to change, so five responsibilities.

## The two-stage refactor

### Stage 1: clarity

Extract one method per responsibility so the top method reads as the process:

```csharp
public void ProcessTrades(Stream stream)
{
    var lines  = ReadTradeData(stream);
    var trades = ParseTrades(lines);   // → ValidateTradeData + MapTradeDataToTradeRecord
    StoreTrades(trades);               // logs through a LogMessage helper
}
```

* Cheap and readable, but not adaptive: changing the logging still edits this class.
* A legitimate stopping point for code you don't expect to change.

### Stage 2: abstraction

Move each responsibility behind an interface and inject it:

```csharp
public class TradeProcessor(ITradeDataProvider provider, ITradeParser parser, ITradeStorage storage)
{
    public void ProcessTrades()
    {
        var lines  = provider.GetTradeData();
        var trades = parser.Parse(lines);
        storage.Persist(trades);
    }
}
```

* `TradeProcessor` now holds only the blueprint of the process. Its one reason to change is a change to the process itself.
* Repeat recursively: `SimpleTradeParser` delegates to `ITradeValidator` and `ITradeMapper`, and the validator and storage log through `ILogger`.

Every original change becomes "add or replace one implementation":

| Change | Handled by |
|---|---|
| Read from a web service | New `ITradeDataProvider` |
| New broker field | Validator, mapper and storage implementations only |
| New validation rules | Replace the `ITradeValidator` implementation |
| New log destination | Logging adapter (`Log4NetLoggerAdapter : ILogger`) |
| Document DB or web service storage | New `MongoTradeStorage` / `WebServiceTradeStorage` |

## Rules for extracted interfaces

* **Keep technology out of interface signatures.** Constructors can depend on anything without polluting the interface.

```csharp
// ✗ every implementation must accept a Stream
interface ITradeDataProvider { IEnumerable<string> GetTradeData(Stream stream); }

// ✓ the context goes into the implementation's constructor
interface ITradeDataProvider { IEnumerable<string> GetTradeData(); }
class StreamTradeDataProvider(Stream stream) : ITradeDataProvider { ... }
```

* **Naming:** drop the `I` and prefix the implementation context (`StreamTradeDataProvider`, `AdoNetTradeStorage`, `DapperTradeStorage`). Use `Simple…` when there is no special dependency.
* **Packaging:** interfaces get their own package. An implementation that pulls in a third-party dependency gets its own package too (`Services.Dapper`), so clients never inherit it transitively. See the Stairway in [dip-and-abstraction-design.md](dip-and-abstraction-design.md).
* **Return read-only shapes** (`IEnumerable<T>`, not `List<T>`) so later steps can't mutate what earlier steps produced.

## Adapter: third-party → first-party

The adapter implements *your* interface and delegates to the third-party type:

```csharp
public class Log4NetLoggerAdapter(ILog log) : ILogger
{
    public void LogWarning(string message, params object[] args) => log.WarnFormat(message, args);
}
```

* Only the composition root and the adapter's package reference log4net. Everything else sees `ILogger`.
* Adapters also fix semantic mismatches. `StopwatchAdapter : IStopwatch` calls `Stop`, reads the elapsed time and then `Reset`s, because `Stopwatch.Start` *resumes* instead of restarting.
* Pragmatic exception: for a truly ubiquitous cross-cutting library, depending on its types directly can be the better trade. Decide it deliberately.

## Decorator

A decorator implements an interface and wraps another instance of the same interface. It adds behavior before or after delegating, and the client can't tell. Use it when a concern is too entangled with a class's intent to move out any other way.

```csharp
public class LoggingCalculator(ICalculator inner) : ICalculator
{
    public int Add(int x, int y)
    {
        System.Console.WriteLine($"Add(x={x}, y={y})");
        var result = inner.Add(x, y);
        System.Console.WriteLine($"result={result}");
        return result;
    }
}
// composition root: ICalculator calculator = new LoggingCalculator(new ConcreteCalculator());
```

### Variants

* **Composite:** holds a list of `IComponent`s and forwards each call to all of them, so clients treat many as one.
   * `Add`/`Remove` stay off the interface; the composition root populates it.
   * Children can be other composites, which gives you trees.
* **Predicate decorator:** hides a condition from the client.

```csharp
// ✗ the client owns the condition and depends on its source
if (dateTester.TodayIsAnEvenDayOfTheMonth) component.Something();

// ✓ the condition is a decorator; the client just calls
IComponent component = new PredicatedComponent(new RealComponent(), new TodayIsAnEvenDayOfTheMonthPredicate());
component.Something();
```

   * This beats both a client that `new`s a `DateTester` and a method that gains a `DateTester` parameter, which breaks its public interface.
   * Prefer `IPredicate` over `Func<bool>`, because an interface can itself be decorated, adapted and composed.
* **Branching decorator:** `BranchedComponent(IComponent whenTrue, IComponent whenFalse, IPredicate predicate)`.
* **Lazy decorator:** `LazyComponent(Lazy<IComponent>) : IComponent`. Handing clients a `Lazy<IComponent>` forces laziness on every caller; the decorator hides it.
* **Logging decorator:** removes logging noise from implementations.
   * Limits: it can't see private state, and it takes one decorator per interface.
   * For logging that touches everything, prefer AOP (an interceptor or an attribute-based aspect).
* **Profiling decorator:** `ProfilingComponent(IComponent inner, IStopwatch stopwatch)` times calls.
   * First extract `IStopwatch` so the stopwatch can be decorated too (`LoggingStopwatch : IStopwatch`).
   * Replacing a concrete dependency with an interface is often the step that must come before any decorator.
* **Properties and events:** write explicit get/set or add/remove accessors that delegate. Auto-properties and auto-events can't be decorated.

## Limits

* SRP yields more, smaller classes. That's the point, but it spreads logic across files. Pay that cost only where change is predicted ([ocp-and-protected-variation.md](ocp-and-protected-variation.md)).
* An interface with very many members makes decorators painful. That's the signal to apply ISP.
