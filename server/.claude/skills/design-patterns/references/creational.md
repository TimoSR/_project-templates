# Creational patterns

Object creation that doesn't hard-wire concrete classes. Look-alikes are compared in [SKILL.md](../SKILL.md#look-alikes-tell-them-apart-by-intent), not repeated here.

## Contents
- Factory Method
- Abstract Factory
- Builder
- Prototype
- Singleton

---

## Factory Method

*Also: Virtual Constructor.* A base class declares a creation method; subclasses decide the concrete type.

* Use when
   * the exact product types aren't known up front: a new product = a new creator subclass
   * a library lets users swap its internal components (`RoundButton` for `Button`) through one overridable method
   * you want to return pooled or cached objects: a constructor must return a new object, a method needn't
* Creation is rarely the creator's main job. It has its own logic; the factory method only decouples that logic from concrete products.

```csharp
// ✗ the creator is welded to one product
class Logistics
{
    public void PlanDelivery() { var transport = new Truck(); transport.Deliver(); }
}

// ✓ subclasses pick the product; PlanDelivery never changes
abstract class Logistics
{
    protected abstract ITransport CreateTransport();
    public void PlanDelivery() { var transport = CreateTransport(); transport.Deliver(); }
}
class RoadLogistics : Logistics { protected override ITransport CreateTransport() { return new Truck(); } }
class SeaLogistics  : Logistics { protected override ITransport CreateTransport() { return new Ship(); } }
```

* Steps that matter
   1. All products share one interface whose methods make sense for every product.
   2. Move every product constructor call in the creator into the factory method. A temporary `switch` on a type parameter is fine at this stage.
   3. One creator subclass per product type takes over its branch. Too many types? A subclass may keep a control parameter (`GroundMail` picks `Truck` or `Train`).
   4. If the base method ends up empty, make it abstract; otherwise it's the default.
* Cost: a subclass per product. Best when a creator hierarchy already exists.
* Relations: designs often start here and grow into Abstract Factory, Prototype or Builder. It's a specialization of Template Method and can be one of its steps. It pairs with Iterator: collection subclasses return matching iterators.

---

## Abstract Factory

Produce families of related objects without naming their concrete classes.

* Use when
   * code works with several *families* of products that must never mix (Modern vs Victorian furniture; Windows vs Mac widgets)
   * a class has accumulated several factory methods that blur its main job: extract them into a factory
* Draw the matrix first. Rows become concrete factories, columns become product interfaces:

| | `IChair` | `ISofa` | `ITable` |
|---|---|---|---|
| `ModernFurnitureFactory` | ModernChair | ModernSofa | ModernTable |
| `VictorianFurnitureFactory` | VictorianChair | VictorianSofa | VictorianTable |

```csharp
// ✗ nothing stops a mismatched set
var chair = new ModernChair();
var sofa  = new VictorianSofa();

// ✓ one factory per family; picked once at startup and passed to everything that creates products
interface IFurnitureFactory { IChair CreateChair(); ISofa CreateSofa(); ITable CreateTable(); }
IFurnitureFactory factory = settings.Style == Style.Modern ? new ModernFurnitureFactory() : new VictorianFurnitureFactory();
var chair = factory.CreateChair();
var sofa  = factory.CreateSofa();
```

* Cost: many interfaces and classes. A new *variant* (row) is cheap; a new *product type* (column) touches every factory.
* Relations: its methods are often Factory Methods, or clone pre-configured Prototypes. It can replace a Facade whose only job is hiding creation. With Bridge, it pairs abstractions with matching implementations. Usually a single instance.

---

## Builder

Construct a complex object step by step; the same steps can produce different representations.

* Use when
   * a telescoping constructor has appeared: many optional parameters and overloads delegating to each other
   * one product needs several representations built through similar steps (stone vs wooden house; a car vs its manual)
   * you build Composite trees: steps can be deferred or recursive, and the builder never hands out an unfinished product

```csharp
// ✗ telescoping: which flag is which?
var house = new House(4, 2, 1, true, false, true, null);

// ✓ named steps, validated when the product is fetched
var house = new HouseBuilder().Walls(4).Doors(2).Windows(1).Garage().Pool().Build();
```

* Don't: with named/default arguments and no step logic or validation, a builder is ceremony. `new House(walls: 4, doors: 2, hasGarage: true)` is enough.
* Steps that matter
   1. Confirm every representation shares the same construction steps. If not, the pattern doesn't fit.
   2. The result-fetch method usually *can't* live on the builder interface, because products may not share a type. Put it there only if they share a hierarchy.
   3. A Director is optional: it encodes common build sequences (recipes) using any builder.
* Relations: builds Composite trees recursively. With Bridge, the director is the abstraction and the builders are implementations. Can be a single instance.

---

## Prototype

*Also: Clone.* Copy objects without depending on their classes.

* Use when
   * code copies objects it knows only through an interface (handed over by third-party code). Copying "from outside" fails anyway: private fields are unreachable and the concrete class is unknown.
   * many subclasses exist only to produce differently configured instances: replace them with pre-configured prototypes that clients clone

```csharp
// ✗ copy from outside: private fields unreachable, and which Shape subclass is it?
var copy = new Shape { X = shape.X, Y = shape.Y };

// ✓ the object copies itself through a copy constructor
abstract class Shape
{
    public int X, Y;
    protected Shape(Shape source) { X = source.X; Y = source.Y; }
    public abstract Shape Clone();
}
class Circle : Shape
{
    public int Radius;
    public Circle(Circle source) : base(source) { Radius = source.Radius; }
    public override Shape Clone() { return new Circle(this); }
}
```

* Gotchas
   * **Every class must override `Clone`** with its own type, or clones come out as the parent type.
   * Each copy constructor calls the parent's, so the parent copies its own private fields.
   * Optional registry: look a prototype up by tag, clone it, return the copy. It replaces subclass constructor calls.
* Cost: circular references are tricky. Decide shallow vs deep copy deliberately.
* Relations: useful for storing copies of Commands in history, and for cloning complex Composite or Decorator structures instead of rebuilding them. Can replace Memento for simple state. Can be a single instance.

---

## Singleton

One instance of a class, with global access to it.

* Use when
   * exactly one instance must be shared by all clients (one database object)
   * you need stricter control than a global variable: only the class itself can replace the instance

```csharp
// ✗ global access: a hidden dependency that tests can't replace
var database = Database.Instance;

// ✓ one instance through the DI lifetime, injected where needed
services.AddSingleton<IDatabase, Database>();
class OrderService
{
    private readonly IDatabase database;
    public OrderService(IDatabase database) { this.database = database; }
}
```

* Prefer the DI form wherever a container exists: you keep "one instance" and lose the global access and the testing problems.
* If you must implement it: private static field, private constructor, lazy creation in the access method, thread-safe (`System.Lazy<T>` or double-checked locking).
* Cost
   * Violates SRP: it solves two problems (one instance + global access).
   * Masks bad design where components know too much about each other.
   * Needs care with threads.
   * Private constructor and static access defeat most mocking.
* Relations: Facades, Abstract Factories, Builders and Prototypes often need only one instance: register them as DI singletons rather than implementing Singleton.
