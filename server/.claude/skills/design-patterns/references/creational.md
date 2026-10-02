# Creational patterns

Creational patterns provide object-creation mechanisms that increase flexibility and reuse of existing code.

## Contents
- Factory Method
- Abstract Factory
- Builder
- Prototype
- Singleton

---

## Factory Method
*Also: Virtual Constructor.*

**Intent.** Declare an interface for creating objects in a base class, and let subclasses change which concrete type gets created.

**Use when**
- You don't know ahead of time the exact types and dependencies of the objects your code works with. Construction is separated from use, so a new product type means a new creator subclass that overrides the factory method.
- You ship a library or framework and want users to extend its internal components: funnel component construction through one overridable method so a subclass can substitute its own component (e.g. a `RoundButton` in place of the default `Button`).
- You want to reuse existing objects (pools, caches, connections) instead of rebuilding them. A constructor must return a new object; a regular method can return a cached one.

**How to implement**
1. Make all products implement one interface whose methods make sense for every product.
2. Add an empty factory method to the creator whose return type is that product interface.
3. Replace every product constructor call in the creator with a call to the factory method, moving the creation code into it. A temporary type parameter (and an ugly `switch`) is fine at this stage.
4. Create a creator subclass per product type; override the factory method and move the matching branch of construction code into it.
5. If there are too many product types for one subclass each, a subclass may keep using the control parameter (e.g. `GroundMail` choosing between `Truck` and `Train`).
6. If the base factory method ends up empty, make it abstract; otherwise keep what's left as the default.

**Notes.** Creation is rarely the creator's main job; the creator has its own business logic, and the factory method just decouples it from concrete products. The factory method need not create new instances — it may return from a cache or pool.

**Pros.** No tight coupling between creator and concrete products. SRP: creation code in one place. OCP: new products without breaking clients.
**Cons.** Many new subclasses. Best when you already have a creator hierarchy to hang it on.

**Relations**
- Designs often start here and evolve toward Abstract Factory, Prototype, or Builder as flexibility needs grow.
- Abstract Factory is usually a set of Factory Methods.
- Pairs with Iterator: collection subclasses return matching iterator types.
- Factory Method is a specialization of Template Method, and can be one step of a larger template method.
- vs Prototype: Factory Method uses inheritance but needs no initialization step; Prototype avoids inheritance but may need complicated initialization of the clone.

---

## Abstract Factory

**Intent.** Produce families of related objects without specifying their concrete classes.

**Use when**
- Code must work with several *families* of related products (e.g. Modern/Victorian chair+sofa+table, Windows/Mac button+checkbox) and must never mix variants, while not depending on concrete classes.
- A class has accumulated several factory methods that blur its main responsibility. Extract them into a standalone factory.

**How to implement**
1. Draw a matrix: distinct product types × variants.
2. Declare an abstract interface per product type; make every concrete product implement its interface.
3. Declare the abstract factory interface with one creation method per product type.
4. Implement one concrete factory per variant.
5. Somewhere at startup, pick the concrete factory from configuration or environment, and pass it to every class that constructs products.
6. Replace direct product constructor calls with calls to the factory.

**Pros.** Products from one factory are guaranteed compatible. Clients decoupled from concrete products. SRP and OCP (new *variants* without breaking clients).
**Cons.** Many new interfaces and classes. Adding a new *product type* touches every factory.

**Relations**
- vs Builder: Abstract Factory returns each product immediately; Builder lets you run extra steps before fetching.
- Its methods can be Factory Methods, or composed via Prototype (clone pre-configured prototypes).
- Alternative to Facade when you only want to hide how subsystem objects are *created*.
- With Bridge: encapsulates which abstractions go with which implementations.
- Often a single instance (Singleton or DI singleton).

---

## Builder

**Intent.** Construct complex objects step by step, and produce different representations using the same construction code.

**Use when**
- A "telescoping constructor" has appeared: many optional parameters and a pile of overloads delegating to each other.
- You need different representations of one product (stone vs wooden house; a car vs its manual) built through similar steps that differ in detail.
- You build Composite trees or other complex objects. Steps can be deferred or called recursively, and the builder never hands out an unfinished product.

**How to implement**
1. Confirm you can define common construction steps for every representation. If not, stop — the pattern doesn't fit.
2. Declare those steps in a builder interface.
3. Write one concrete builder per representation. Give each a method to fetch the result. That method usually *can't* live on the interface because products may not share a type; put it on the interface only if they share a hierarchy.
4. Optionally add a Director that encodes common build sequences (recipes) using a builder.
5. The client creates the builder and the director and hands the builder to the director (via constructor, or per build call).
6. Fetch the result from the director only if all products share an interface; otherwise from the builder.

**Pros.** Step-by-step, deferred, or recursive construction. One construction routine reused for multiple representations. SRP: complex construction isolated from product logic.
**Cons.** More classes overall. In languages with named/default arguments, a builder without step logic or validation is just ceremony.

**Relations**
- vs Abstract Factory: see above.
- Good for building Composite trees recursively.
- With Bridge: the director is the abstraction, builders are the implementations.
- Can be a single instance.

---

## Prototype
*Also: Clone.*

**Intent.** Copy existing objects without making your code depend on their classes.

**Use when**
- Code must copy objects it only knows through an interface (e.g. objects handed over by third-party code). Copying "from outside" fails anyway because of private fields and unknown concrete classes; the object itself must do it.
- Many subclasses exist only to produce differently configured instances. Replace them with a set of pre-configured prototypes that clients clone.

**How to implement**
1. Declare a prototype interface with `clone()`, or add `clone()` to every class of the existing hierarchy.
2. Give each class a copy constructor that takes an instance of that class and copies all its fields; subclasses call the parent copy constructor so the parent copies its private fields. (Without overloading, use a dedicated copy method.)
3. `clone()` is usually one line: `return new ThisClass(this)`. **Every class must override it** with its own class name, or clones come out as the parent type.
4. Optionally add a prototype registry (a factory class or a static lookup on the base) that finds a prototype by tag or criteria, clones it, and returns the copy. Replace subclass constructor calls with registry lookups.

**Pros.** Clone without coupling to concrete classes. Replace repeated initialization with cloning pre-built prototypes. Convenient for complex objects. An alternative to inheritance for configuration presets.
**Cons.** Cloning objects with circular references is tricky. Decide deliberately between shallow and deep copy.

**Relations**
- Alternative to Factory Method (see above). Can compose Abstract Factory methods.
- Useful for saving copies of Commands in history.
- Designs heavy in Composite and Decorator benefit: clone a complex structure instead of rebuilding it.
- Can replace Memento when the state is simple and has no (or easily re-established) links to external resources.
- Can be a single instance.

---

## Singleton

**Intent.** Ensure a class has only one instance while giving global access to it.

**Use when**
- A class must have exactly one instance available to all clients (e.g. one shared database object).
- You need stricter control than a global variable: nothing but the class itself can replace the cached instance. (The limit can be relaxed later by changing only the access method.)

**How to implement**
1. Add a private static field to hold the instance.
2. Add a public static access method (`getInstance()`).
3. Lazily create the instance there on first call; return it on every later call. In multithreaded code, guard creation (lock / double-checked locking / language-provided lazy initialization).
4. Make the constructor private.
5. Replace all direct constructor calls in clients with the access method.

**Pros.** One instance guaranteed. Global access point. Lazy initialization.
**Cons.**
- Violates SRP: it solves two problems at once (single instance + global access).
- Can mask bad design where components know too much about each other.
- Needs special care with threads.
- Hard to unit-test clients: private constructor and static access defeat most mocking.

**Prefer instead.** Where a DI container exists, register the class with a single-instance lifetime and inject it. You keep "one instance" and lose the global access and the testability problems.

**Relations**
- A Facade often needs only one instance.
- vs Flyweight: see SKILL.md look-alikes.
- Abstract Factories, Builders, and Prototypes can all be single instances.
