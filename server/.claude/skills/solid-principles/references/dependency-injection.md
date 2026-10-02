# Dependency injection: the glue

DI is simple, but everything else in SOLID depends on it. Done well, it is **invisible to almost all of the code**: classes just declare constructor parameters, and one small area at the entry point knows how the graph is built. Plan for DI from the start, because retrofitting it is hard.

## Why inject

Here is a class that builds its own dependencies:

```csharp
public TaskListController()
{
    taskService = new TaskServiceAdo();     // hidden: ADO.NET, connection strings...
    mapper      = new MapperAutoMapper();
    LoadTasks();                            // work in the constructor, too
}
```

This causes four problems:

- **It can't be unit-tested in isolation.** Concrete classes usually can't be proxied; interfaces always can.
- **Its dependencies are invisible.** You have to read the source to discover what it needs, whereas constructor parameters advertise it.
- **Transitive dependencies leak.** If A uses B and B uses C, then A implicitly depends on C (the Entourage again). Depending on a well-generalized interface stops the chain.
- **Extension points are lost.** You can't substitute a subclass, decorator, or adapter without editing this class.

Inject instead: `TaskListController(ITaskService taskService, IObjectMapper mapper)`, and move the loading out of the constructor into an `OnLoad()` method.

## Injection styles

- **Constructor injection** is the default. Guard against null in the constructor. The dependency lives as long as the object.
- **Method injection.** Pass the dependency as a method parameter when only that method needs it. The cost: callers must obtain it, and it can get threaded down the call stack.
- **Property injection** allows the dependency to be swapped at run time, but it creates an **unenforced, order-dependent requirement**: calling the method before setting the property fails. Treat that as a serious smell (connascence of execution order).

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

It needs no library, it is compile-time type-checked, and it is completely flexible: any decorator chain is just more nested `new`s. It gets verbose as the graph grows.

### Inversion of Control containers

A container defers graph construction to run time, and every container reduces to **Register, Resolve, Release**:

- **Register** at startup: map interface → implementation, many times over.
- **Resolve** the **resolution root** only: the top-level object family, such as MVC/Web API controllers, WPF view-models or views, WinForms views, or message handlers. The container walks constructors recursively. **Never call Resolve inside controllers, services, domain, or data-access code.**
- **Release** at the end of a scope (per request in web apps) or at shutdown. Disposing the container clears it.

On registration style:

- Imperative registration in code is readable and catches typos at compile time.
- Declarative XML or config registration can be swapped without recompiling, but it is verbose, it reports errors only at run time, and it can't express lambda factories. Avoid it unless you truly need configuration-time swapping.

### Convention over configuration

Register by rules instead of one line per mapping. For example, "every class in our assemblies maps to the interface named `I<ClassName>`", filtered to your own assembly prefix so framework interfaces like `INotifyPropertyChanged` don't get mapped. It is shorter, but it is algorithmic and harder to verify. It also struggles in genuinely SOLID code, where interfaces *should* have several implementations (decorators, adapters, strategies). An interface with a single implementation is itself a smell, and mocks don't count.

### Which to choose (after Mark Seemann's analysis)

- **Small or simple graphs:** Poor Man's DI. It is simple and valuable.
- **Large graphs:** conventions for the bulk, plus explicit registrations for edge cases (decorator chains, named strategies).
- **Manual container registration of every type** sits in the "pointless" corner: it is weakly typed (errors move to run time) with little gain over Poor Man's DI.
- Having DI at all matters more than which flavor you pick.

For ASP.NET Core / `Microsoft.Extensions.DependencyInjection`: the built-in container *is* the composition root (`Program.cs`, or per-feature `IServiceCollection` extension methods called from it). Controllers and minimal-API handlers are the resolution roots. Use `Scoped` for per-request lifetimes. The built-in container doesn't do decorators natively; register them with factory lambdas or a library such as Scrutor's `Decorate`.

## Composition root and resolution root

- **Composition root:** the *one* place that knows about DI (concrete types, container, registrations), as close to the entry point as possible. Examples: `Main`/`Program.cs`, `Application_Start`, app startup events. It is a recognizable location, it bootstraps early, and it keeps container references from spreading. Each application type has its own composition root, and the services and implementations are reused across them (the same `ITaskService` behind WPF, MVC, and WinForms front ends).
- **Resolution root:** the object type you resolve. It is often a family (all controllers). Frameworks with factory extension points (such as MVC's controller factory) resolve roots for you per request, so only the composition root sets that up.
- If you organize registrations per feature or module (extension methods like `AddBillingFeature(this IServiceCollection)`), they are still part of the composition root as long as only the entry point calls them.

## Anti-patterns

### Service Locator

```csharp
var taskService = ServiceLocator.Current.GetInstance<ITaskService>();   // inside OnLoad()
```

A static "ambient container" that classes pull from. It looks like DI but:

- Dependencies are hidden again. The parameterless constructor *claims* there are none, and you have to search the method bodies to find the real ones.
- It breaks the Hollywood Principle ("don't call us, we'll call you"). The class can fetch *anything*, whether appropriate or not.
- Infrastructure code spreads through business classes. It can still be mocked, so the cost isn't testability; it's honesty and design pressure.

Use it only where a framework gives you no constructor-injection hook at all. Even then it beats `new`, because the interfaces and their extension points survive.

**Injecting the container** into a class is the same problem: the class gets the keys to the safe and the container package spreads everywhere. A class that needs twelve services should *show* twelve constructor parameters, which makes the "this class does too much" smell visible so you split it or group the dependencies meaningfully.

### Illegitimate Injection

```csharp
public TaskListController(ITaskService s, IObjectMapper m) { ... }   // fine
public TaskListController() : this(new TaskServiceAdo(new ApplicationSettings()), new MapperAutoMapper()) { }   // poison
```

A second "default" constructor that `new`s implementations brings back the Entourage (the class must reference implementation packages), hard-codes a default that will need editing later, and invites "but sometimes I want A, sometimes B". Its visibility (public, protected, internal, private) doesn't matter. If it exists "for testing", it is unnecessary: tests already pass doubles through the real constructor.

## Object lifetime and ownership

- Objects don't all live equally long. A long-lived service shouldn't own a long-lived `SqlConnection` that it disposes in one method and then reuses.
- **A class must not dispose dependencies it was handed.** It doesn't know who else shares that instance. Disposal belongs to whoever created the object (the container, or the composition root's scope).
- When a class needs **short-lived** instances, inject a **factory** interface (e.g. `IConnectionFactory.CreateConnection()`) and let the class `using`/dispose what *it* created. This keeps the class decoupled from the concrete type while giving it ownership of the lifetime.
- Containers offer lifetimes (transient, scoped/per-request, singleton). Match each registration to how long the thing should live, and watch for captive dependencies (a singleton holding a scoped service).
