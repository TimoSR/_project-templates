# Structural patterns

Assemble objects and classes into larger structures that stay flexible. Look-alikes are compared in [SKILL.md](../SKILL.md#look-alikes-tell-them-apart-by-intent), not repeated here.

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

*Also: Wrapper.* Let objects with incompatible interfaces collaborate.

* Use when
   * an existing class (legacy, third-party, heavily depended-on) has the wrong interface: the analytics library takes JSON, your app produces XML
   * several subclasses lack a feature that can't go in their superclass: wrap them instead of duplicating it (this approaches Decorator)

```csharp
// ✗ every call site converts by hand
analytics.Track(ConvertXmlToJson(stockData));

// ✓ one adapter speaks the interface the app wants; it converts and nothing more
interface IStockAnalytics { void Track(System.Xml.XmlDocument stockData); }
class JsonAnalyticsAdapter(AnalyticsLibrary library) : IStockAnalytics
{
    public void Track(System.Xml.XmlDocument stockData) => library.Track(ConvertXmlToJson(stockData));
}
```

* No business logic in the adapter: it converts interfaces and data formats only.
* Variants: *object adapter* (composition, works everywhere) vs *class adapter* (inherits both sides, needs multiple inheritance).
* Cost: more interfaces and classes. If you own the service, changing it to fit is often simpler.

---

## Bridge

Split a large class, or a set of related classes, into two hierarchies (abstraction and implementation) that evolve independently.

* Use when
   * a monolithic class has several variants of one functionality (it works with several database servers), and every change ripples through it
   * a class must extend along two or more orthogonal dimensions
   * implementations must be swappable at run time (optional; this is why Bridge gets confused with Strategy)

```
✗ one subclass per combination: Remote × Device
Remote
├─ BasicTvRemote      ├─ BasicRadioRemote
└─ AdvancedTvRemote   └─ AdvancedRadioRemote

✓ two hierarchies joined by one reference
Remote ──device──► IDevice
├─ BasicRemote        ├─ Tv
└─ AdvancedRemote     └─ Radio
```

```csharp
class Remote(IDevice device)
{
    public void TogglePower() { if (device.IsEnabled) device.Disable(); else device.Enable(); }
}
class AdvancedRemote(IDevice device) : Remote(device)
{
    public void Mute() => device.SetVolume(0);
}
var remote = new AdvancedRemote(new Radio());
```

* Steps that matter
   1. Name the dimensions: abstraction/platform, domain/infrastructure, front end/back end.
   2. The abstraction holds the operations clients need. The implementation interface declares only the platform operations the abstraction uses.
   3. Variants of high-level logic become refined abstractions; platforms become implementations.
   4. Clients pass an implementation into the abstraction's constructor, then use only the abstraction.
* Cost: over-complicates a class that is already highly cohesive.
* Relations: Abstract Factory encapsulates which abstractions pair with which implementations. With Builder, the director is the abstraction.

---

## Composite

*Also: Object Tree.* Compose objects into trees and treat the tree like a single object.

* Use when
   * the core model is a tree: leaves plus containers holding leaves and other containers (boxes of products and boxes; UI containers; file systems)
   * clients should treat simple and complex elements alike ("get price" recurses through the whole order)

```csharp
// ✗ the client walks the tree and type-checks every node
decimal total = 0;
foreach (var item in box.Items) total += item is Box inner ? SumBox(inner) : ((Product)item).Price;

// ✓ one interface; containers recurse
interface IOrderItem { decimal Price(); }
class Product(decimal price) : IOrderItem { public decimal Price() => price; }
class Box(List<IOrderItem> children) : IOrderItem
{
    public decimal Price() => children.Sum(child => child.Price());
}
```

* Decide deliberately: `Add`/`Remove` on the component interface lets clients build trees uniformly but breaks ISP, because leaves get empty methods.
* Cost: if element types differ too much, the shared interface becomes overgeneralized.
* Relations: Builder builds trees, Iterator traverses them, Visitor runs operations over them, Flyweight shares leaves, Chain of Responsibility bubbles requests from a leaf to the root, Prototype clones a whole tree.

---

## Decorator

*Also: Wrapper.* Attach behaviors by wrapping an object in objects that contain them.

* Use when
   * behaviors are combined at run time in any mix (a notifier sending email + SMS + Slack; a data source that compresses + encrypts), and subclassing would need one class per combination
   * inheritance is awkward or impossible (`sealed`)

```csharp
// ✗ a subclass per combination
class EncryptedCompressedFileDataSource : FileDataSource { ... }

// ✓ wrappers stack in any order, chosen at run time
class Compression(IDataSource inner) : IDataSource
{
    public void Write(byte[] data) => inner.Write(Compress(data));
    public byte[] Read() => Decompress(inner.Read());
}
IDataSource source = new Encryption(new Compression(new FileDataSource("data.bin")));
```

* The wrapped reference is typed as the component interface, so a decorator wraps components *or* other decorators.
* Cost
   * Hard to remove one wrapper from the middle of a stack.
   * Hard to make a decorator's behavior independent of its position in the stack.
   * The assembly code gets ugly; DI-container decoration helps.

---

## Facade

Give a complex library, framework or subsystem a simplified interface.

* Use when
   * most clients need only a few features of a complex subsystem ("convert this video" over a full conversion framework)
   * you layer a subsystem: each layer gets a facade as its entry point, and layers talk only through facades

```csharp
// ✗ the client is wired to a dozen framework classes to do one thing
var file   = new VideoFile(fileName);
var codec  = CodecFactory.Extract(file);
var buffer = BitrateReader.Read(file, codec);
var result = BitrateReader.Convert(buffer, new Mpeg4CompressionCodec());
var output = new AudioMixer().Fix(result);

// ✓ one entry point; a framework upgrade changes only the facade
var mp4 = new VideoConverter().Convert(fileName, VideoFormat.Mp4);
```

* The facade initializes the subsystem and manages its lifecycle unless the client already does.
* If the facade grows too large, extract a second, more specific facade.
* Cost: it can become a god object coupled to every class in the app.
* Relations: Abstract Factory can replace a facade that only hides creation. Flyweight makes many small objects; Facade makes one that represents a subsystem. Usually a single instance.

---

## Flyweight

*Also: Cache.* Fit more objects in RAM by sharing common state instead of storing it in each one.

* Use **only** when a huge number of similar objects barely fits in RAM *and* their duplicated state can be extracted and shared. Otherwise the complexity isn't worth it.

```csharp
// ✗ one million particles, each holding its own sprite and color
class Particle { public double X, Y, Speed; public Color Color; public Sprite Sprite; }

// ✓ intrinsic state (shared, immutable) vs extrinsic state (per particle, passed in)
sealed class ParticleType(Color color, Sprite sprite)
{
    public void Draw(Canvas canvas, double x, double y) { ... }
}
record struct Particle(double X, double Y, double Speed, ParticleType Type);   // Type comes from a factory cache
```

* Steps that matter
   1. Split fields into **intrinsic** (unchanging, duplicated across objects; stays) and **extrinsic** (unique per object; moves out).
   2. Intrinsic fields are immutable and set only in the constructor.
   3. Methods that used extrinsic fields take them as parameters.
   4. A flyweight factory returns the existing flyweight for an intrinsic state before creating a new one; clients get flyweights only through it.
* Cost: may trade RAM for CPU if context data is recomputed on every call. The code gets much harder to understand ("why is this entity's state split?").

---

## Proxy

A substitute that controls access to another object, doing work before or after the request reaches it.

| Kind | Purpose |
|---|---|
| Virtual | Lazy initialization of a heavyweight service that's rarely needed |
| Protection | Only certain clients may use the service |
| Remote | The service lives on another machine; the proxy handles the network |
| Logging | Keep a history of requests |
| Caching | Cache results of repeated requests (keyed by parameters) and manage the cache's lifecycle |
| Smart reference | Release a heavyweight object when no client uses it; track modifications |

```csharp
// ✗ every client caches results itself, or none does
var video = youTube.GetVideo(id);

// ✓ caching proxy: same interface, clients unchanged
class CachedYouTube(IYouTube service) : IYouTube
{
    private readonly Dictionary<string, Video> cache = new();
    public Video GetVideo(string id) =>
        cache.TryGetValue(id, out var video) ? video : cache[id] = service.GetVideo(id);
}
```

* Gotchas
   * No service interface? Extract one so proxy and service are interchangeable. If you can't change every client, subclass the service instead.
   * The proxy usually creates and manages its service itself; occasionally the client passes it in.
   * A creation method (static or factory) can decide whether a client gets the proxy or the real service.
* Cost: more classes; responses may be delayed.
