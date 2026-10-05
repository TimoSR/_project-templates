# Interface Segregation: designing interfaces

## Contents
- Core idea
- 1. Split for decoration
- 2. Split by client need
- 3. Split by architectural need
- Supplying segregated interfaces
- Single-method interfaces

## Core idea

* Interfaces are **small** and **shaped by their clients**.
* Every implementer, *including every decorator and adapter*, must implement every member. A big interface forces contracts nobody uses in full.
* The book's test: **for every member, there should be a meaningful analogue of each decoration you'd want to apply.**
* Three reasons to split: **decoration**, **client need**, **architectural need**.
* Segregate when you *create* an interface: it's far cheaper at design time than as a refactor.

## 1. Split for decoration

Start from a generic CRUD interface:

```csharp
public interface ICreateReadUpdateDelete<TEntity>
{
    void Create(TEntity entity);
    TEntity ReadOne(Guid id);
    IEnumerable<TEntity> ReadAll();
    void Update(TEntity entity);
    void Delete(TEntity entity);
}
```

* A generic *interface* (not generic methods) makes clients declare the entity type up front, which keeps dependencies explicit.
* Logging and transactions apply to every member. They're cross-cutting, so consider AOP.
* Other decorators apply to part of the interface, and that creates the pressure to split:

```csharp
// ✗ delete confirmation on the fat interface: four pass-throughs, and each still needs a test
class DeleteConfirmation<T> : ICreateReadUpdateDelete<T>
{
    private readonly ICreateReadUpdateDelete<T> inner;
    public DeleteConfirmation(ICreateReadUpdateDelete<T> inner) { this.inner = inner; }
    public void Create(T entity) { inner.Create(entity); }
    public T ReadOne(Guid id) { return inner.ReadOne(id); }
    public IEnumerable<T> ReadAll() { return inner.ReadAll(); }
    public void Update(T entity) { inner.Update(entity); }
    public void Delete(T entity) { if (Confirm()) { inner.Delete(entity); } }
}

// ✓ split off IDelete<T>: the decorator is one method, and the prompt is its own abstraction
class DeleteConfirmation<T> : IDelete<T>
{
    private readonly IDelete<T> inner;
    private readonly IUserInteraction userInteraction;
    public DeleteConfirmation(IDelete<T> inner, IUserInteraction userInteraction)
    {
        this.inner = inner;
        this.userInteraction = userInteraction;
    }
    public void Delete(T entity) { if (userInteraction.Confirm("Delete?")) { inner.Delete(entity); } }
}
```

* `IUserInteraction.Confirm` lets console, desktop and web supply their own prompt: SRP inside the decorator.
* **Caching** applies only to reads → `IRead<T>` (`ReadOne`, `ReadAll`) with a `ReadCaching<T>` decorator.
* **Create + Update** share a signature and, for the client, an intent → unify as `ISave<T>.Save` and let the implementation choose insert or update. That enables `SaveAuditing<T>(ISave<T> inner, ISave<AuditInfo> auditSave)`.
* Result: `IRead<T>`, `ISave<T>`, `IDelete<T>`, each with meaningful decorators and no pass-throughs.
* **Multi-interface decorators** are fine *when the decoration context is shared*: `ModificationEventPublishing<T> : ISave<T>, IDelete<T>`. Decorators that pull in different dependencies (event publishing + auditing) belong in separate classes and packages.

## 2. Split by client need

Large interfaces hand clients more power than they should have, blur intent and invite misuse. No documentation fully prevents that.

* **Read vs write.** Even one read/write property can be too much:

```csharp
// ✗ the reading controller can also write
interface IUserSettings { string Theme { get; set; } }

// ✓ each client gets only its half; one class implements both
interface IUserSettingsReader { string Theme { get; } }
interface IUserSettingsWriter { string Theme { set; } }
class UserSettingsConfig : IUserSettingsReader, IUserSettingsWriter { ... }
```

   * Writers that must also read: `IUserSettingsWriter : IUserSettingsReader`. Use methods (`GetTheme`/`SetTheme`), because C# properties don't compose cleanly across interface inheritance.
* **State-dependent operations.** Privileged operations stay unreachable until the client holds the interface that only a successful login returns:

```csharp
interface IUnauthorized { IAuthorized Login(string user, string password); void RequestPasswordReminder(string email); }
interface IAuthorized   { void ChangePassword(...); void AddToBasket(...); void Checkout(); void Logout(); }
```

## 3. Split by architectural need

* `IPersistence` holds queries (`GetAll`, `GetByID`, `FindByCriteria`) backed by a document store, and commands (`Save`, `Delete`) backed by an ORM.
   * One implementation, two unrelated heavy dependencies, two reasons to change.
* Split into `IPersistenceQueries` and `IPersistenceCommands`, with implementations **in separate packages**, so reusing one doesn't drag in the other's dependency chain.
* This is CQRS (Command/Query Responsibility Segregation) at the interface level.

## Supplying segregated interfaces

```csharp
public OrderController(IRead<Order> reader, ISave<Order> saver, IDelete<Order> deleter) { ... }
```

| Option | Code | When |
|---|---|---|
| One instance per interface | `new OrderController(new Reader<Order>(), new Saver<Order>(), new Deleter<Order>())` | Most flexible; each part decorated independently |
| One instance, passed three times | `var crud = new CreateReadUpdateDelete<Order>(); new OrderController(crud, crud, crud);` | The **leaf** implementation (real ORM or library work) where all operations share context. Looks odd, is correct: each parameter asks for a different facet |

* A generic client (`GenericController<TEntity>`) forces all three dependencies to agree on the entity type.

### Anti-pattern: Interface Soup

```csharp
// ✗ re-merging the parts, usually to avoid the "same instance three times" look
interface IInterfaceSoup<T> : IRead<T>, ISave<T>, IDelete<T> { }
```

It brings back every cost of the fat interface: implementers and decorators must cover everything again.

## Single-method interfaces

ISP taken to its conclusion gives the most composable interfaces:

```csharp
public interface ITask              { void Do(); }                 // fire-and-forget; can be decorated async
public interface IAction<TContext>  { void Do(TContext context); }
public interface IFunction<TReturn> { TReturn Do(); }
public interface IPredicate         { bool Test(); }               // encapsulates an if or loop condition
```

They mirror `Action`, `Func` and `Predicate`, but interfaces can be decorated, adapted and composed, and an implementation can carry extra context through its constructor.
