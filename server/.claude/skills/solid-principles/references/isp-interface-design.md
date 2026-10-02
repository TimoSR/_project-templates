# Interface Segregation Principle: designing interfaces

## Core idea

Interfaces should be **small** and **shaped by their clients**. Every member of an interface must be implemented by every implementer, *including every decorator and adapter*. Unless every client needs every member, a big interface forces implementations to fulfil a contract nobody uses in full. The test the book uses: **for every member of an interface, there should be a meaningful analogue of each decoration you'd want to apply.**

There are three reasons to split an interface: **decoration**, **client need**, and **architectural need**.

## 1. Split for decoration

Start from a typical generic CRUD interface:

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

(Making the *interface* generic rather than each method forces clients to declare the entity type they depend on up front. That keeps dependencies explicit.)

Some decorators apply to every member: logging, transactions. These are cross-cutting, so consider AOP for them. Others apply to only part of the interface, and those create the pressure to split:

- **Delete confirmation** decorates only `Delete`. On the big interface it needs four pass-through methods, and each of those *still needs tests* to prove it delegates. Split off `IDelete<T>` and the decorator shrinks to one method. Less code means fewer tests. Taking it further, the prompt itself becomes `IUserInteraction.Confirm(string)` so console, desktop, and web can each supply their own, which is SRP applied inside the decorator.
- **Caching** applies only to reads, so split off `IRead<T>` (`ReadOne`, `ReadAll`) with a `ReadCaching<T>` decorator.
- **Create + Update** have identical signatures and the same intent from the client's point of view. Unify them as `ISave<T>.Save` and let the implementation decide insert vs. update. That enables `SaveAuditing<T>(ISave<T> inner, ISave<AuditInfo> auditSave)`.

The result is `IRead<T>`, `ISave<T>`, `IDelete<T>`, each with meaningful decorators and no pass-throughs.

**Multi-interface decorators:** one class can decorate several segregated interfaces *when the decoration context is shared*. For example, `ModificationEventPublishing<T> : ISave<T>, IDelete<T>` publishes events for both. Don't combine decorators that pull in different dependencies (event publishing + auditing). Those belong in separate classes and packages.

## 2. Split by client need

**Clients need only what they need.** Large interfaces hand clients more power than they should have, blur intent, and invite misuse, and no amount of documentation fully prevents that.

- **Read vs. write.** Even a single read/write property can be too much. Split `IUserSettings { string Theme { get; set; } }` into `IUserSettingsReader { string Theme { get; } }` and `IUserSettingsWriter { string Theme { set; } }`. The reading controller can no longer write, and the writer can no longer read. One `UserSettingsConfig` class implements both, and clients never see that.
  - If writers legitimately need to read, use **segregation plus inheritance**: `IUserSettingsWriter : IUserSettingsReader`. Use methods (`GetTheme`/`SetTheme`) rather than properties, because C# properties don't compose cleanly across interface inheritance.
- **State-dependent operations.** `IUnauthorized { IAuthorized Login(user, pass); void RequestPasswordReminder(email); }`, where `IAuthorized` holds `ChangePassword`, `AddToBasket`, `Checkout`, `Logout`. Privileged operations become unreachable until the client holds the interface that only a successful login returns.

## 3. Split by architectural need

An `IPersistence` with both queries (`GetAll`, `GetByID`, `FindByCriteria`) and commands (`Save`, `Delete`), where queries use a document store and commands use an ORM, produces an implementation with two unrelated heavy dependencies, and so two reasons to change. Split it into `IPersistenceQueries` and `IPersistenceCommands`, with implementations **in separate packages**, so reusing one doesn't drag in the other's dependency chain. This is CQRS (Command/Query Responsibility Segregation) showing up at the interface level.

## Supplying segregated interfaces to clients

A client that used to take one fat interface now takes several:

```csharp
public OrderController(IRead<Order> reader, ISave<Order> saver, IDelete<Order> deleter) { ... }
```

- **Multiple implementations, multiple instances:** `new OrderController(new Reader<Order>(), new Saver<Order>(), new Deleter<Order>())`. This is the most flexible option, and each part can be decorated independently.
- **Single implementation, single instance:** `var crud = new CreateReadUpdateDelete<Order>(); new OrderController(crud, crud, crud);`. Passing the same instance three times looks odd but is correct: each parameter asks for a different facet. This works best for the **leaf** implementation (the one that does the real work with a specific ORM or library), because all operations share that context. Decorators and adapters are usually per interface.
- A generic client (`GenericController<TEntity>`) forces all three dependencies to agree on the entity type.

### Anti-pattern: Interface Soup

```csharp
interface IInterfaceSoup<T> : IRead<T>, ISave<T>, IDelete<T> { }
```

Re-merging segregated interfaces, usually to avoid the "same instance three times" look, puts back every cost of the fat interface: implementers and decorators must cover everything again. Don't do it.

## Single-method interfaces

Taken to its conclusion, ISP gives the most composable interfaces of all:

```csharp
public interface ITask              { void Do(); }                 // fire-and-forget; can even be decorated async
public interface IAction<TContext>  { void Do(TContext context); }
public interface IFunction<TReturn> { TReturn Do(); }
public interface IPredicate         { bool Test(); }               // encapsulates an if / loop condition
```

They look like delegates (`Action`, `Func`, `Predicate`), but interfaces are more versatile. They can be decorated, adapted, and composed, and an implementation can carry extra context through its constructor or through other interfaces it implements.

## Checklist

- Does any decorator, adapter, or test double have pass-through or `throw NotImplemented` members? Then split.
- Do different clients use disjoint subsets of the members? Then split by client.
- Would the implementation need two unrelated infrastructure dependencies? Then split by architecture and package separately.
- Did someone build an aggregate "soup" interface? Then remove it.
- Interface segregation is far cheaper to get right at design time than to refactor in later. Think about it whenever you *create* an interface.
