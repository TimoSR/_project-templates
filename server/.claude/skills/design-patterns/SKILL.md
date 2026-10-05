---
name: design-patterns
description: Reviews and refactors toward 22 of the 23 GoF design patterns (all but Interpreter), from Alexander Shvets' "Dive Into Design Patterns". Use when the user asks which pattern fits, wants to implement or refactor to a named pattern, or asks how look-alikes differ (Strategy vs State vs Bridge, Decorator vs Proxy vs Adapter, Facade vs Mediator). Also on pattern-shaped smells, even if no pattern is named — a switch on type or mode, telescoping constructors, subclass explosion across dimensions, an incompatible third-party API, undo/redo or queued operations, objects reacting to another's changes, a huge state machine, near-duplicate algorithms in sibling classes. Also on any GoF pattern name (factory, builder, singleton, adapter, decorator, proxy, observer, strategy, visitor…). Apply once a simple working version exists. Not for up-front design, or for general SOLID, DI or coupling reviews (solid-principles).
---

# Design Patterns: Dive Into Design Patterns

Source: Alexander Shvets, *Dive Into Design Patterns* (Refactoring.Guru, 2019). Sketches here are C#; the roles map to any language (see [Language mapping](#language-mapping)).

A pattern's name tells the next reader *which problem* you solved. Look-alikes share one class diagram but name different problems, so pick by intent, never by structure.

## The principles every pattern serves

* **Encapsulate what varies.** Isolate the parts likely to change, first in a method and then in a class, so a change hits one compartment.
* **Program to an interface.** Declare only what one object needs from another, and depend on that. It adds complexity, so do it where you foresee an extension point.
* **Favor composition over inheritance.** Inheritance can't shrink a parent's interface, leaks its internals, couples subclasses to every parent change, and explodes when a class varies along two dimensions:

```
✗ inheritance: a class per combination        ✓ composition: each dimension varies alone
Shape                                          Shape ──has──► Color
├─ RedCircle    ├─ BlueCircle                  ├─ Circle      ├─ Red
└─ RedSquare    └─ BlueSquare                  └─ Square      └─ Blue
   shapes × colors classes                        shapes + colors classes, swappable at run time
```

* **SOLID.** Most pattern benefits are SRP/OCP wins. For depth, use the `solid-principles` skill.

## The counterweight: every pattern has a price

The usual price is more classes and interfaces. Before proposing a pattern:

* **Name the concrete change or problem it solves in this code.** If you can't, don't apply it.
* **Check its cost** in the reference file. Flyweight pays only when RAM is the bottleneck. Adapter loses to editing the service when you own it.
* **Prefer the language feature when it *is* the pattern:** `event` for Observer, `yield` for Iterator, `AddSingleton` for Singleton ([Language mapping](#language-mapping)).
* **Strategy or State with a few rarely changing variants stays a `switch` statement.** House style bans delegate parameters (`Func<…>`), so a lambda is not the lightweight Strategy here:

```csharp
// ✗ a class hierarchy for one method with two variants that rarely change
interface IDiscountStrategy { decimal Apply(decimal price); }
class HalfPrice : IDiscountStrategy { public decimal Apply(decimal price) { return price / 2; } }

// ✓ a switch statement; grow it into Strategy when variants multiply
switch (discount)
{
    case Discount.Half:
        return price / 2;
    default:
        return price;
}
```

   * Use the class form only when you need what it adds: state, undo, several methods, named types.
* **Start with Factory Method** for creation problems, and grow into Abstract Factory, Prototype or Builder only when the extra flexibility is needed.
* When you recommend a pattern, say what it buys and costs here. When you decline one, say why.

## Workflow

1. **Describe the problem without pattern names.** What varies? What is coupled to what? What change is hard right now? Read the code first.
2. **Shortlist candidates** with the symptom table.
3. **Disambiguate by intent** with the look-alikes table.
4. **Open the reference** for the shortlist: its use cases, its ✗/✓ sketch, its cost, its relations (a combination may fit better).
   * Creational: Factory Method, Abstract Factory, Builder, Prototype, Singleton → [creational.md](references/creational.md)
   * Structural: Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy → [structural.md](references/structural.md)
   * Behavioral: Chain of Responsibility, Command, Iterator, Mediator, Memento, Observer, State, Strategy, Template Method, Visitor → [behavioral.md](references/behavioral.md)
5. **Implement as an incremental refactor:** introduce the interface, move one variant at a time, keep tests green after each move.
6. **Verify.** The original hard change is now "add a class" (or a `switch` case) with no client edits. Delete any interface left with one implementation and no foreseeable second.

## Symptom → candidates

| Symptom in the code | Candidates |
|---|---|
| `new ConcreteX()` scattered through business logic; a new product type edits many places | Factory Method; Abstract Factory for matching families |
| Objects that must be used together (theme, platform, vendor) can get mixed up | Abstract Factory |
| Constructor with many optional parameters or overloads ("telescoping") | Builder |
| The same construction steps produce different representations | Builder (+ Director) |
| Copy an object whose concrete class you don't know; subclasses differing only in initial configuration | Prototype |
| Exactly one shared instance with controlled access | Singleton, but prefer a DI-managed single instance |
| A useful class (legacy, third-party) has the wrong interface | Adapter |
| Class hierarchy grows as a product of dimensions (Shape × Color, Remote × Device) | Bridge |
| Tree of parts and containers treated uniformly (order totals, UI trees, file systems) | Composite |
| Optional behaviors combined in any mix at run time (compress + encrypt + log) | Decorator |
| Client tangled with many classes of a complex library to do one common thing | Facade |
| Millions of similar objects exhaust memory; much state is duplicated | Flyweight |
| Lazy loading, access control, caching, logging or remote access in front of an object, without client changes | Proxy |
| A sequence of checks that may each handle or stop a request (auth → validation → rate limit → cache) | Chain of Responsibility |
| Queue, schedule, log, send or undo operations; many UI elements trigger the same operation | Command (+ Memento for undo) |
| Traversal logic duplicated in clients, or several traversal orders needed | Iterator |
| Many components reference each other directly (form fields enabling each other) | Mediator |
| Snapshots, undo or rollback without exposing private state | Memento |
| When X changes, an open-ended, changing set of objects must react | Observer |
| Big `switch` on the object's *own* current state, with transitions | State |
| Big `switch` choosing *one variant of an algorithm*; siblings differ in one behavior | Strategy |
| Sibling classes hold almost the same algorithm with small step differences | Template Method |
| Many unrelated operations (export, render, lint) over a stable class hierarchy without editing it | Visitor |

## Look-alikes: tell them apart by intent

| Patterns | The difference |
|---|---|
| Strategy vs State | Both delegate to a swappable helper. Strategies are independent and the client picks one. States know each other and switch the context's state themselves. |
| Strategy vs Bridge | Same shape. Bridge is designed up front to split a class into two hierarchies that evolve independently. Strategy swaps one algorithm in a context. |
| Strategy vs Template Method | Strategy: composition, per object, at run time. Template Method: inheritance, per class, fixed. |
| Strategy vs Command | Strategy: different ways of doing *the same* thing. Command: any operation turned into an object to defer, queue, log, send or undo. |
| Strategy vs Decorator | Decorator changes the skin (adds behavior around). Strategy changes the guts (replaces how the work is done). |
| Adapter vs Decorator vs Proxy | Adapter: a *different* interface. Proxy: the *same* interface. Decorator: the same interface, *enhanced*. Decorators stack recursively; adapters typically don't. |
| Decorator vs Proxy | Same structure. The client composes decorators; a proxy usually creates and manages its service itself. |
| Decorator vs Chain of Responsibility | Both pass a call along linked objects. Handlers work independently and may stop the request; decorators must not break the flow. |
| Decorator vs Composite | Decorator: one child, adds responsibilities. Composite: many children, aggregates results. They combine well. |
| Adapter vs Bridge | Adapter is retrofitted onto existing incompatible pieces. Bridge is planned up front. |
| Adapter vs Facade | Adapter makes one existing interface usable. Facade defines a new, simpler interface over a whole subsystem. |
| Facade vs Mediator | Facade simplifies access to a subsystem that doesn't know it exists; parts still talk directly. Mediator centralizes communication; components talk only to it. |
| Facade vs Proxy | Both front a complex thing and may initialize it. A proxy is interchangeable with its service; a facade isn't. |
| Mediator vs Observer | Mediator removes mutual dependencies in a fixed set of components through one hub. Observer sets up dynamic one-way subscriptions. Mediators are often *implemented* with Observer. |
| CoR vs Command vs Mediator vs Observer | Four ways to connect senders and receivers: a chain until handled; one-way sender → command → receiver; all via a hub; dynamic subscribe/unsubscribe. |
| Factory Method vs Abstract Factory | Factory Method: one overridable creation method in a class with other work. Abstract Factory: an object whose whole job is creating a *family* of products. |
| Abstract Factory vs Builder | Abstract Factory returns each product immediately. Builder runs steps before you fetch the result. |
| Factory Method vs Prototype | Factory Method: inheritance, no initialization step. Prototype: no inheritance, but the clone may need complicated setup. |
| Flyweight vs Singleton | Flyweight: many immutable instances, one per intrinsic state. Singleton: one instance, may be mutable. |
| Prototype vs Memento | For simple state with no links to external resources, cloning can replace a memento. |

## Reporting a review or proposal

One entry per finding:

```
PricingService.cs:88  PricingService.Calculate
Problem       switch over customer type picks a discount rule; each new tier edits this method and its tests
Pattern       Strategy, not State: the rule doesn't change the service's own state or trigger transitions
Sketch        IDiscountRule per tier, chosen once from the customer; Calculate calls rule.Apply(price)
Cost / now?   4 small classes vs keeping the switch; worth it now, since 2 more tiers are planned
```

* Close with patterns you deliberately did *not* recommend and why: usually "only two variants that rarely change" or "a `switch` statement already does this".

## Language mapping

| Pattern | Idiomatic shortcut (use the full pattern only when you need more) |
|---|---|
| Strategy, single-method Command | A `switch` statement or a plain method call; no delegate parameters (house style) |
| Iterator | `IEnumerable`/`yield`, Python generators, JS iterators, Rust `Iterator` |
| Observer | Language or framework events (`event`, `IObservable<T>`, `EventEmitter`, signals) |
| Singleton | DI single-instance lifetime (`AddSingleton`), module-level instance |
| Prototype | Copy constructors, `with` on records/data classes, `copy.deepcopy`, `structuredClone` |
| Builder | Named/default arguments or object initializers when there's no step logic or validation |
| Proxy (virtual) | `Lazy<T>`, lazy properties |
| Decorator | DI decoration (Scrutor `Decorate`) |
| Chain of Responsibility | Middleware pipelines (ASP.NET Core, Express), pipeline behaviors |
| Mediator + Command | In-process request/handler dispatchers (MediatR) |
| Visitor | A `switch` statement on type over sealed hierarchies or sum types |

In a codebase with contract folders (here `src/_contracts/` and `src/features/<feature>/_contracts/`), pattern interfaces (strategy, handler, product, visitor, subscriber) go there; implementations stay in their module.
