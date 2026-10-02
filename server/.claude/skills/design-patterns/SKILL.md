---
name: design-patterns
description: Choose, apply, review, and refactor toward the 22 classic GoF design patterns as taught in Alexander Shvets' "Dive Into Design Patterns". Use whenever the user asks which pattern fits a problem, wants to implement or refactor to a named pattern, asks how look-alike patterns differ (Strategy vs State vs Bridge, Decorator vs Proxy vs Adapter, Facade vs Mediator, Command vs Strategy), or shows code with pattern-shaped smells — a switch/if-chain on type or mode, telescoping constructors, subclass explosion across dimensions, an incompatible third-party API, undo/redo or queued operations, objects reacting to another's changes, a huge state machine, or near-duplicate algorithms in sibling classes — even if no pattern is named. Also when the user mentions factory, builder, singleton, prototype, adapter, bridge, composite, decorator, facade, flyweight, proxy, chain of responsibility, command, iterator, mediator, memento, observer, state, strategy, template method, or visitor.
---

# Design Patterns — Dive Into Design Patterns

Source: Alexander Shvets, *Dive Into Design Patterns* (Refactoring.Guru, 2019). The book uses language-neutral pseudocode; this skill keeps that neutrality and maps to concrete languages at the end.

A pattern is a **blueprint, not a recipe**: a named, general solution to a recurring design problem that you adapt to your program. Its name is also vocabulary — choosing a pattern tells the next reader *which problem* you were solving, which is why look-alike patterns are not interchangeable.

## The principles every pattern serves

- **Encapsulate what varies.** Find the parts likely to change and isolate them (first in a method, then in a class) so a change hits one compartment, not the whole ship.
- **Program to an interface, not an implementation.** Decide what one object actually needs from another, declare just that as an interface, and depend on it. This adds complexity, so do it where you foresee an extension point.
- **Favor composition over inheritance.** Inheritance can't shrink a parent's interface, leaks the parent's internals, couples subclasses to every parent change, and explodes combinatorially when a class varies along two or more dimensions. Composition ("has a") lets each dimension vary independently and be swapped at runtime.
- **SOLID.** Most pattern benefits are stated as SRP/OCP wins. For depth, use the `solid-principles` skill rather than repeating it here.

## The counterweight: every pattern has a price

The book lists a cost for every pattern, and the most common one is *more classes and interfaces*. Before proposing a pattern:

- **Name the concrete change or problem it solves in this code.** If you can't, don't apply it.
- **Check the pattern's "don't" case** (in the reference files). Examples: Strategy or State with two rarely-changing variants is overkill; Flyweight only pays off when RAM is genuinely the bottleneck; Iterator is overkill for simple collections; Adapter loses to simply editing the service class when you own it.
- **Prefer the language feature when it is the pattern.** A function/lambda is a one-method Strategy or Command; generators are Iterators; built-in events are Observer; a DI container lifetime replaces most Singletons. Use the class-based form only when you need what it adds (state, undo, multiple methods, named types).
- **Many designs should start with Factory Method** (simple, subclass-based) and evolve toward Abstract Factory, Prototype, or Builder only when the extra flexibility is actually needed.

When you recommend a pattern, name what it buys and what it costs here. When you decline one, say why.

## Workflow

1. **Describe the problem without pattern names.** What varies? What is coupled to what? What change is hard right now? Read the code first if there is code.
2. **Shortlist candidates** with the symptom table below.
3. **Disambiguate by intent** with the look-alikes table. Structure alone doesn't decide it — several patterns share the same class diagram.
4. **Open the reference file** for the shortlisted pattern: check its "Use when", its cons, and its relations (a combination may fit better than either alone).
   - Creational (Factory Method, Abstract Factory, Builder, Prototype, Singleton) → [references/creational.md](references/creational.md)
   - Structural (Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy) → [references/structural.md](references/structural.md)
   - Behavioral (Chain of Responsibility, Command, Iterator, Mediator, Memento, Observer, State, Strategy, Template Method, Visitor) → [references/behavioral.md](references/behavioral.md)
5. **Implement by following the pattern's "How to implement" steps** in order, as an incremental refactor: introduce the interface, move one variant at a time, keep tests green after each move.
6. **Verify.** The original hard change should now be "add a class" (or "add a function") without editing clients. Delete any interface that ended up with one implementation and no foreseeable second one.

## Symptom → candidate patterns

| Symptom in the code | Candidates |
|---|---|
| `new ConcreteX()` scattered through business logic; adding a product type edits many places | Factory Method; Abstract Factory if products come in matching families |
| Objects that must be used together (same theme/platform/vendor) can get mixed up | Abstract Factory |
| Constructor with many optional parameters, or several overloads ("telescoping constructor") | Builder |
| Same construction steps produce different representations | Builder (+ Director) |
| Need a copy of an object whose concrete class you don't know, or subclasses that differ only in initial configuration | Prototype |
| Exactly one shared instance needed, with controlled access | Singleton — but prefer a DI-managed single instance |
| A useful class (legacy, third-party) has the wrong interface | Adapter |
| Class hierarchy grows as a product of dimensions (Shape × Color, Remote × Device) | Bridge |
| Tree of parts and containers that clients should treat uniformly (order totals, UI trees, file systems) | Composite |
| Optional behaviors that must be combined in any mix at runtime (compress + encrypt + log); subclass per combination | Decorator |
| Client code tangled with many classes of a complex library just to do one common thing | Facade |
| Millions of similar objects exhaust memory; much of their state is duplicated | Flyweight |
| Need lazy loading, access control, caching, logging, or remote access in front of an object — without clients changing | Proxy |
| Sequence of checks/handlers that may each handle or stop a request (auth → validation → rate limit → cache) | Chain of Responsibility |
| Need to queue, schedule, log, send, or undo operations; many UI elements trigger the same operation | Command (+ Memento for undo) |
| Traversal logic for a complex structure duplicated in clients, or several traversal orders needed | Iterator |
| Many components reference each other directly (form fields enabling/disabling each other) | Mediator |
| Need snapshots/undo/rollback without exposing private state | Memento |
| When X changes, an open-ended, changing set of other objects must react | Observer |
| Big `switch`/if-chain on the object's *own* current state, with transitions between states | State |
| Big `switch`/if-chain choosing *one variant of an algorithm*; sibling classes differ only in one behavior | Strategy |
| Sibling classes contain almost the same algorithm with small step differences | Template Method |
| Need many unrelated operations (export, render, lint) over a stable class hierarchy without editing it | Visitor |

## Look-alikes: tell them apart by intent

| Patterns | The difference |
|---|---|
| **Strategy vs State** | Both delegate to a swappable helper. Strategies are independent and unaware of each other; the client picks one. States know about each other and switch the context's state themselves. |
| **Strategy vs Bridge** | Same shape. Bridge is designed up front to split a class into two hierarchies (abstraction/platform) that evolve independently; Strategy swaps one algorithm inside a context. |
| **Strategy vs Template Method** | Strategy uses composition and works per object at runtime. Template Method uses inheritance and is fixed per class. |
| **Strategy vs Command** | Strategy = different ways of doing *the same* thing. Command = any operation turned into an object so it can be deferred, queued, logged, sent, or undone. |
| **Strategy vs Decorator** | Decorator changes the object's skin (adds behavior around it); Strategy changes its guts (replaces how it does the work). |
| **Adapter vs Decorator vs Proxy** | Adapter gives the wrapped object a *different* interface; Proxy keeps the *same* interface; Decorator keeps it and *enhances* it. Decorators stack recursively; adapters typically don't. |
| **Decorator vs Proxy** | Same structure. Client composes decorators; a proxy usually creates and manages its service's lifecycle itself. |
| **Decorator vs Chain of Responsibility** | Both pass a call along linked objects. CoR handlers do independent work and may stop the request; decorators must not break the flow and must honor the base interface. |
| **Decorator vs Composite** | Decorator has one child and adds responsibilities; Composite has many children and aggregates their results. They combine well. |
| **Adapter vs Bridge** | Adapter is retrofitted to make existing incompatible pieces work together; Bridge is planned up front. |
| **Adapter vs Facade** | Adapter makes one existing interface usable; Facade defines a new, simpler interface over a whole subsystem. |
| **Facade vs Mediator** | Facade simplifies access to a subsystem that is unaware of it, and parts still talk directly. Mediator centralizes communication; components only talk to the mediator. |
| **Facade vs Proxy** | Both front a complex thing and may initialize it. A proxy is interchangeable with its service (same interface); a facade isn't. |
| **Mediator vs Observer** | Mediator removes mutual dependencies among a fixed set of components via one hub. Observer sets up dynamic one-way subscriptions. A mediator is often *implemented* with Observer. |
| **CoR vs Command vs Mediator vs Observer** | Four ways to connect senders and receivers: pass along a chain until handled; one-way sender→command→receiver; all via a hub; dynamic subscribe/unsubscribe. |
| **Factory Method vs Abstract Factory** | Factory Method is one overridable creation method in a class that has other work. Abstract Factory is a separate object whose whole job is creating a *family* of related products. |
| **Abstract Factory vs Builder** | Abstract Factory returns each product immediately; Builder runs a sequence of steps before you fetch the result. |
| **Factory Method vs Prototype** | Factory Method relies on inheritance but needs no initialization step; Prototype avoids inheritance but the clone may need complicated setup. |
| **Flyweight vs Singleton** | Flyweights have many instances (one per intrinsic state) and are immutable; a singleton has one instance and may be mutable. |
| **Prototype vs Memento** | For simple state with no links to external resources, cloning the object can replace a memento. |

## Useful combinations

- **Command + Memento** for undo: the command acts; a memento saved just before restores.
- **Composite + Builder** (build trees recursively), **+ Iterator** (traverse), **+ Visitor** (run operations over the whole tree), **+ Flyweight** (share leaf nodes), **+ Chain of Responsibility** (bubble a request from leaf to root).
- **Bridge + Abstract Factory** when certain abstractions only work with certain implementations.
- **Abstract Factory / Builder / Prototype / Facade** are often single-instance; register them as singletons in DI rather than implementing the Singleton pattern.

## When reviewing or proposing, report like this

For each finding or proposal give:

- **Where**: `file:line`, class or method.
- **Problem**: the symptom in plain words and the concrete change it makes hard.
- **Pattern**: the pattern, and in one line why it beats its look-alike here.
- **Sketch**: the smallest refactor, following the pattern's implementation steps; short code when it clarifies.
- **Cost / worth it now?**: classes added, indirection, any listed con that applies (ordering issues, god-object risk, unhandled requests, RAM vs CPU).

Close with patterns you deliberately did *not* recommend and why — usually "only two variants that rarely change" or "a lambda/language feature already does this".

## Language mapping

Roles are language-neutral: *interface* means a Java/C#/TS interface, a Python `Protocol`/ABC, a Rust trait, or a Go interface.

| Pattern | Idiomatic shortcut (use the full pattern only when you need more) |
|---|---|
| Strategy, single-method Command | Function, lambda, delegate (`Func<…>`/`Action<…>`), closure |
| Iterator | `IEnumerable`/`yield`, Python generators, JS iterators/generators, Rust `Iterator` |
| Observer | Language/framework events (`event`, `IObservable<T>`, `EventEmitter`, signals) |
| Singleton | DI container single-instance lifetime (`AddSingleton`), module-level instance |
| Prototype | Copy constructors, `with` on records/data classes, `copy.deepcopy`, `structuredClone` |
| Builder | Named/default arguments or object initializers when there's no step logic or validation |
| Proxy (virtual) | `Lazy<T>`, lazy properties |
| Decorator | Registering decorators in DI (e.g. Scrutor `Decorate`), Python decorators for functions |
| Chain of Responsibility | Middleware pipelines (ASP.NET Core, Express), pipeline behaviors |
| Mediator + Command | In-process request/handler dispatchers (e.g. MediatR) |
| Visitor | Pattern matching / `switch` expressions over sealed hierarchies or sum types |

In a codebase with dedicated contract folders (for example `_contracts/`), pattern interfaces (strategy, handler, product, visitor, subscriber) go there and concrete implementations stay in their module.
