# Structural patterns

Structural patterns assemble objects and classes into larger structures while keeping those structures flexible and efficient.

## Contents
- Adapter
- Bridge
- Composite
- Decorator
- Facade
- Flyweight
- Proxy

---

## Adapter
*Also: Wrapper.*

**Intent.** Let objects with incompatible interfaces collaborate.

**Use when**
- You want to use an existing class (legacy, third-party, or heavily depended-on) whose interface doesn't match the rest of your code — e.g. an analytics library that takes JSON while your app produces XML.
- Several existing subclasses lack a common feature that can't be added to their superclass. Instead of duplicating it in new subclasses, wrap them in an adapter that adds it (this approaches Decorator).

**How to implement**
1. Identify the service class you can't (or shouldn't) change and the client(s) that need it.
2. Declare the client interface: how clients want to talk to the service.
3. Create the adapter implementing the client interface, methods empty for now.
4. Give the adapter a reference to the service (usually via constructor; sometimes passed per call).
5. Implement each client-interface method by delegating to the service. The adapter only converts interfaces and data formats — no business logic.
6. Clients use the adapter only through the client interface, so adapters can change or multiply without touching clients.

**Variants.** *Object adapter* (composition — works everywhere) vs *class adapter* (inherits from both interfaces — needs multiple inheritance).

**Pros.** SRP: conversion code separated from business logic. OCP: new adapters without breaking clients.
**Cons.** More interfaces and classes. If you own the service, simply changing it to fit may be simpler.

**Relations**
- vs Bridge: Adapter is retrofitted onto an existing app; Bridge is designed up front.
- vs Decorator: Adapter changes the interface; Decorator keeps and enhances it and supports recursive stacking.
- vs Proxy: different interface vs same interface.
- vs Facade: Adapter makes one existing interface usable; Facade defines a new interface over a subsystem.
- Shares composition-based structure with Bridge, State, and Strategy; the intent differs.

---

## Bridge

**Intent.** Split a large class, or a set of closely related classes, into two hierarchies — abstraction and implementation — that can evolve independently.

**Use when**
- A monolithic class has several variants of some functionality (e.g. works with several database servers), and every change ripples across the whole class.
- A class must be extended along two or more orthogonal dimensions (Shape × Color, Remote × Device). Inheritance would need one subclass per combination.
- You need to swap implementations at runtime (optional; this is why Bridge gets confused with Strategy).

**How to implement**
1. Identify the orthogonal dimensions: abstraction/platform, domain/infrastructure, front-end/back-end, interface/implementation.
2. Put the operations clients need into the base abstraction class.
3. Determine the operations available on every platform; declare the ones the abstraction needs in a general implementation interface.
4. Create a concrete implementation per platform, all following that interface.
5. Give the abstraction a reference field of the implementation type and delegate most work to it.
6. For variants of high-level logic, create refined abstractions by extending the base abstraction.
7. Clients pass an implementation into the abstraction's constructor and then use only the abstraction.

**Pros.** Platform-independent classes and apps. Clients see only high-level abstractions. OCP: new abstractions and implementations independently. SRP: high-level logic vs platform details.
**Cons.** Over-complicates a class that is already highly cohesive.

**Relations**
- vs Adapter (see above). Same structure as State/Strategy; different intent.
- With Abstract Factory: encapsulate which abstractions pair with which implementations.
- With Builder: the director is the abstraction, builders are implementations.

---

## Composite
*Also: Object Tree.*

**Intent.** Compose objects into trees and work with the tree as if it were a single object.

**Use when**
- The core model is a tree: simple leaves plus containers that hold leaves and other containers (boxes containing products and boxes; UI containers; file systems).
- Clients should treat simple and complex elements uniformly through one interface (e.g. "get price" recurses through the whole order).

**How to implement**
1. Confirm the model is a tree; break it into simple elements and containers (containers hold both kinds).
2. Declare the component interface with methods meaningful for both leaves and containers.
3. Create leaf classes for simple elements (there may be several).
4. Create a container class with a child collection typed as the component interface. Its methods delegate to children and combine results.
5. Add child add/remove methods to the container. Declaring them on the component interface lets clients treat everything uniformly while building the tree, but breaks ISP (leaves get empty methods) — pick deliberately.

**Pros.** Polymorphism and recursion make complex trees convenient. OCP: new element types without breaking tree-handling code.
**Cons.** If element types differ too much, the common interface becomes overgeneralized and hard to understand.

**Relations**
- Build trees with Builder; traverse with Iterator; run operations with Visitor; share leaves with Flyweight.
- Chain of Responsibility: a request can bubble from a leaf up through its parents to the root.
- vs Decorator: Decorator has one child and adds responsibilities; Composite sums up its children. Decorators can extend specific nodes of a Composite.
- Prototype lets you clone a whole tree instead of rebuilding it.

---

## Decorator
*Also: Wrapper.*

**Intent.** Attach new behaviors to an object by placing it inside wrapper objects that contain those behaviors.

**Use when**
- Extra behaviors must be added to objects at runtime in arbitrary combinations without breaking the code that uses them (e.g. a notifier that sends via email + SMS + Slack; a data source that compresses + encrypts). Subclassing would need one class per combination.
- Inheritance is awkward or impossible (e.g. the class is `final`/`sealed`).

**How to implement**
1. Confirm the domain is a primary component with optional layers over it.
2. Put the methods common to the component and the layers in a component interface.
3. Write the concrete component with the base behavior.
4. Write a base decorator holding a reference typed as the component interface (so it can wrap components *or* decorators) and delegating everything to it.
5. Make sure every class implements the component interface.
6. Write concrete decorators extending the base decorator; each runs its behavior before or after delegating.
7. The client builds and composes the stack of decorators.

**Pros.** Extend behavior without subclassing. Add or remove responsibilities at runtime. Combine behaviors by stacking. SRP: split a class that implements many behavior variants into small classes.
**Cons.** Hard to remove one specific wrapper from the middle of a stack. Hard to make a decorator's behavior independent of its position in the stack. The setup code that assembles layers can look ugly (DI-container decoration helps).

**Relations**
- vs Adapter, Proxy, Composite, Chain of Responsibility, Strategy: see SKILL.md look-alikes.
- Proxy manages its service's lifecycle itself; decorator composition is always controlled by the client.
- Prototype helps clone heavily decorated structures.

---

## Facade

**Intent.** Provide a simplified interface to a library, framework, or other complex set of classes.

**Use when**
- You need a limited, straightforward interface to a complex subsystem; most clients need only a few of its features (e.g. "convert this video" over a full video-conversion framework).
- You want to layer a subsystem: give each layer a facade as its entry point and make layers communicate only through facades, reducing coupling.

**How to implement**
1. Check that a simpler interface is possible — you're on track if it makes clients independent of many subsystem classes.
2. Declare and implement that interface in a facade class that redirects calls to the right subsystem objects. The facade initializes the subsystem and manages its lifecycle unless the client already does.
3. Route all client code through the facade. Now a subsystem upgrade changes only the facade.
4. If the facade grows too large, extract part of it into an additional, more specific facade.

**Pros.** Isolates your code from subsystem complexity.
**Cons.** Can become a god object coupled to every class in the app.

**Relations**
- vs Adapter, Mediator, Proxy: see SKILL.md look-alikes.
- Abstract Factory can replace a facade whose only job is hiding object creation.
- vs Flyweight: Flyweight makes lots of little objects; Facade makes one object representing a subsystem.
- A facade usually needs only one instance.

---

## Flyweight
*Also: Cache.*

**Intent.** Fit more objects into available RAM by sharing common state between objects instead of storing it in each one.

**Use only when** the program must support a huge number of similar objects that barely fit in RAM, *and* those objects carry duplicated state that can be extracted and shared (e.g. particles in a game sharing color and sprite). Otherwise the complexity isn't worth it.

**How to implement**
1. Split the class's fields into:
   - **intrinsic state**: unchanging data duplicated across many objects (stays in the flyweight);
   - **extrinsic state**: contextual data unique to each object (moves out).
2. Make intrinsic fields immutable, set only in the constructor.
3. In methods that used extrinsic fields, replace each field with a parameter.
4. Optionally add a flyweight factory that returns an existing flyweight for a given intrinsic state before creating a new one; clients then obtain flyweights only through it.
5. Clients store or compute extrinsic state and pass it in. For convenience, move extrinsic state plus the flyweight reference into a separate context class.

**Pros.** Large RAM savings when there really are tons of similar objects.
**Cons.** May trade RAM for CPU if context data must be recomputed on every call. Code becomes much harder to understand ("why is this entity's state split like this?").

**Relations**
- Shared Composite leaves can be flyweights.
- vs Facade, Singleton: see above and SKILL.md look-alikes.

---

## Proxy

**Intent.** Provide a substitute for another object that controls access to it, so you can do something before or after a request reaches the original.

**Use when** (common kinds)
- **Virtual proxy** — lazy initialization of a heavyweight service that is only occasionally needed.
- **Protection proxy** — only certain clients may use the service.
- **Remote proxy** — the service lives on another machine; the proxy handles the network details.
- **Logging proxy** — keep a history of requests.
- **Caching proxy** — cache results of repeated requests (keyed by parameters) and manage the cache's lifecycle.
- **Smart reference** — release a heavyweight object when no clients use it any more; track whether clients modified it.

**How to implement**
1. If there's no service interface, extract one so proxy and service are interchangeable. If you can't change all the service's clients, make the proxy a subclass of the service instead.
2. Create the proxy with a field referencing the service. Usually the proxy creates and manages the service itself; occasionally the client passes it in.
3. Implement each method per its purpose; usually do some work, then delegate.
4. Consider a creation method (static or factory) that decides whether a client gets the proxy or the real service.
5. Consider lazy initialization of the service.

**Pros.** Control the service without clients knowing. Manage the service's lifecycle when clients don't care. Works even when the service isn't ready or available. OCP: new proxies without changing service or clients.
**Cons.** More classes. Responses may be delayed.

**Relations**
- vs Adapter, Decorator, Facade: see SKILL.md look-alikes.
