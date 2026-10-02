# Dependency injection: the glue

## Contents
- Why inject
- Injection styles
- Building the object graph
- Composition root and resolution root
- Anti-patterns
- Lifetime and ownership

DI done well is **invisible to almost all of the code**: classes declare constructor parameters, and one small area at the entry point knows how the graph is built. Plan for it from the start, because retrofitting it is hard.

## Why inject

```csharp
// ✗ builds its own dependencies, and does work in the constructor
public TaskListController()
{
    taskService = new TaskServiceAdo();     // hidden: ADO.NET, connection strings...
    mapper      = new MapperAutoMapper();
    LoadTasks();
}

// ✓ dependencies are visible and replaceable; loading moves to OnLoad()
public TaskListController(ITaskService taskService, IObjectMapper mapper) { ... }
```

What the ✗ version costs:

* **No isolated unit tests.** Concrete classes usually can't be proxied; interfaces always can.
* **Invisible dependencies.** You read the source to learn what it needs. Constructor parameters advertise it.
* **Leaking transitive dependencies.** A uses B uses C, so A depends on C (the Entourage). A well-generalized interface stops the chain.
* **Lost extension points.** No subclass, decorator or adapter without editing the class.

## Injection styles

| Style | Use when | Cost |
|---|---|---|
| **Constructor** (default) | The dependency lives as long as the object | None; guard against null |
| **Method** | Only one method needs it | Callers must obtain it, and it can get threaded down the call stack |
| **Property** | The dependency must be swappable at run time | Unenforced, order-dependent: calling before setting fails. A serious smell (connascence of execution order) |

## Building the object graph

### Poor Man's DI (manual composition)

```csharp
// composition root (entry point)
var settings    = new ApplicationSettings();            // adapter over configuration
var taskService = new TaskServiceAdo(settings);
var mapper      = new MapperAutoMapper();
var controller  = new TaskListController(taskService, mapper);
var mainWindow  = new TaskListView(controller);
```

* No library, type-checked at compile time, fully flexible: a decorator chain is just more nested `new`s.
* Gets verbose as the graph grows.

### Inversion of Control containers

Every container reduces to **Register, Resolve, Release**:

* **Register** at startup: interface → implementation, many times over.
* **Resolve** only the **resolution root**: the top-level object family (MVC/Web API controllers, view-models, views, message handlers). The container walks constructors recursively.
   * **Never call Resolve inside controllers, services, domain or data-access code.**
* **Release** at the end of a scope (per request in web apps) or at shutdown.

Registration style:

* **Imperative (code):** readable; typos caught at compile time.
* **Declarative (XML, config):** swappable without recompiling, but verbose, errors only at run time, no lambda factories. Avoid unless you truly need configuration-time swapping.

### Convention over configuration

Register by rules: "every class in our assemblies maps to `I<ClassName>`", filtered to your own assembly prefix so framework interfaces (`INotifyPropertyChanged`) aren't mapped.

* Shorter, but algorithmic and harder to verify.
* Struggles in genuinely SOLID code, where interfaces *should* have several implementations (decorators, adapters, strategies).

### Which to choose (after Mark Seemann)

| Graph | Choice |
|---|---|
| Small or simple | Poor Man's DI |
| Large | Conventions for the bulk + explicit registrations for edge cases (decorator chains, named strategies) |
| Any (avoid) | Manually registering every type in a container: weakly typed, errors move to run time, little gain over Poor Man's DI |

Having DI at all matters more than which flavor.

**ASP.NET Core** (`Microsoft.Extensions.DependencyInjection`):

* The built-in container *is* the composition root: `Program.cs`, or per-feature `IServiceCollection` extension methods called from it.
* Controllers and minimal-API handlers are the resolution roots. `Scoped` = per request.
* No native decorators: register them with factory lambdas or Scrutor's `Decorate`.

## Composition root and resolution root

* **Composition root:** the *one* place that knows concrete types, the container and registrations, as close to the entry point as possible (`Main`/`Program.cs`, `Application_Start`, app startup).
   * Recognizable, bootstraps early, and keeps container references from spreading.
   * Each application type has its own. Services are reused across them (the same `ITaskService` behind WPF, MVC and WinForms).
* **Resolution root:** the type you resolve, often a family (all controllers). Frameworks with a factory hook (MVC's controller factory) resolve roots per request.
* Per-feature registration methods (`AddBillingFeature(this IServiceCollection)`) are still part of the composition root as long as only the entry point calls them.

## Anti-patterns

### Service Locator

```csharp
// ✗ inside OnLoad(): the parameterless constructor claims there are no dependencies
var taskService = ServiceLocator.Current.GetInstance<ITaskService>();
```

* Hides dependencies again: you search method bodies to find them.
* Breaks the Hollywood Principle ("don't call us, we'll call you"): the class can fetch *anything*.
* Spreads infrastructure through business classes. It can be mocked, so the cost isn't testability; it's honesty and design pressure.
* Use it only where a framework gives no constructor-injection hook. Even then it beats `new`, because interfaces and extension points survive.
* **Injecting the container** is the same problem. A class that needs twelve services should *show* twelve constructor parameters; that makes "this class does too much" visible.

### Illegitimate Injection

```csharp
public TaskListController(ITaskService taskService, IObjectMapper mapper) { ... }   // ✓
public TaskListController() : this(new TaskServiceAdo(new ApplicationSettings()), new MapperAutoMapper()) { }   // ✗
```

* Brings back the Entourage: the class must reference implementation packages.
* Hard-codes a default that will need editing, and invites "sometimes A, sometimes B".
* Visibility (public, protected, internal, private) doesn't matter. "For testing" is no excuse: tests already pass doubles through the real constructor.

## Lifetime and ownership

* **A class must not dispose a dependency it was handed.** It doesn't know who else shares the instance. The creator (container or composition-root scope) disposes.
* For **short-lived** instances, inject a factory and own what *it* creates:

```csharp
// ✗ disposes a long-lived connection it was handed, then the next call reuses it
public void Save(Order order) { using (connection) { ... } }

// ✓ the class owns the lifetime of what it creates
public void Save(Order order) { using var connection = connectionFactory.CreateConnection(); ... }
```

* Match each registration's lifetime (transient, scoped, singleton) to how long the thing should live.
* Watch for **captive dependencies**: a singleton holding a scoped service.
