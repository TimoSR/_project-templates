# Behavioral patterns

Communication between objects and the assignment of responsibilities among them. Look-alikes are compared in [SKILL.md](../SKILL.md#look-alikes-tell-them-apart-by-intent), not repeated here.

## Contents
- Chain of Responsibility
- Command
- Iterator
- Mediator
- Memento
- Observer
- State
- Strategy
- Template Method
- Visitor

---

## Chain of Responsibility

*Also: CoR, Chain of Command.* Pass a request along a chain of handlers; each one handles it or passes it on.

* Use when
   * different requests need different processing, but the kinds and sequence aren't known up front (auth → validation → brute-force filter → cache → order handler)
   * handlers must run in a specific order, or the set and order change at run time
* Decide which flavor you're building:
   * **first capable handler wins** and stops the chain (GUI help, event bubbling)
   * **pipeline:** every handler does its part and passes it on

```csharp
// ✗ every check hard-wired in one method; adding or reordering one edits it
if (!IsAuthenticated(request)) return Response.Denied;
if (!IsValid(request)) return Response.Invalid;
if (cache.TryGet(request, out var cached)) return cached;
return orders.Handle(request);

// ✓ each check is a handler; the chain is assembled (or configured) outside
abstract class Handler
{
    private readonly Handler? next;
    protected Handler(Handler? next) { this.next = next; }
    public virtual Response Handle(Request request)
    {
        if (next == null) { return Response.Unhandled; }
        return next.Handle(request);
    }
}
class Authentication : Handler
{
    public Authentication(Handler? next) : base(next) { }
    public override Response Handle(Request request)
    {
        if (!IsAuthenticated(request)) { return Response.Denied; }
        return base.Handle(request);
    }
}
var chain = new Authentication(new Validation(new Caching(new OrderHandler(next: null))));
```

* Gotchas
   * Pass request data as one request object.
   * Be ready for a one-link chain, early stops, and requests falling off the end unhandled. Decide what "unhandled" means.
   * The client may enter the chain at any handler, not only the first.
* Relations: a Composite leaf can pass a request up through its parents. Handlers can be Commands, or the request itself can be a Command.

---

## Command

*Also: Action, Transaction.* Turn a request into a stand-alone object holding everything about it.

* Use when
   * objects are parameterized with operations: menu items, buttons and shortcuts trigger the same operation without a subclass each
   * operations are queued, scheduled, logged or executed remotely (commands serialize like any object)
   * operations must be reversible: a history stack of commands plus state backups (Memento), or inverse operations (which can be hard to write)

```csharp
// ✗ each UI element calls the receiver directly: no queue, no undo, duplicated per shortcut
class CopyButton : Button { protected override void OnClick() { editor.Copy(); } }

// ✓ the operation is an object: share it, queue it, log it, undo it
interface ICommand { void Execute(); void Undo(); }
class CopyCommand : ICommand { public CopyCommand(Editor editor) { ... } ... }
var copy = new CopyCommand(editor);
copyButton.Command = copy;
copyShortcut.Command = copy;
```

* Gotchas
   * The command holds the arguments and the receiver, all set through the constructor.
   * Senders get commands from the client and talk to them only through the interface.
   * Initialization order: receivers → commands bound to receivers → senders bound to commands.
* Cost: a whole layer between senders and receivers. If you need no queue, log or undo, a plain method call does the job.
* Relations: Prototype stores copies of commands in history. Visitor is a more powerful Command that works across objects of different classes.

---

## Iterator

Traverse a collection without exposing its representation (list, stack, tree, graph).

* Use when
   * a complex structure should be hidden from clients, for convenience or protection
   * non-trivial traversal code is duplicated across the app
   * code must traverse different structures, or structures unknown ahead of time, or in several orders

```csharp
// ✗ every client re-implements the tree walk
var stack = new Stack<Node>(new[] { root });
while (stack.Count > 0) { var node = stack.Pop(); Visit(node); foreach (var child in node.Children) stack.Push(child); }

// ✓ the collection hands out traversals through the language's iterator protocol
public IEnumerable<Node> DepthFirst()
{
    yield return this;
    foreach (var child in Children)
    {
        foreach (var node in child.DepthFirst()) { yield return node; }
    }
}
foreach (var node in root.DepthFirst()) { Visit(node); }
```

* Implement the language's protocol (`IEnumerable`, generators), not a homemade iterator interface.
* Each iterator has its own state: the same collection can be iterated in parallel, and an iteration can pause and resume. Fetch a fresh iterator per traversal.
* Cost: overkill for simple collections. Can be slower than direct access to a specialized collection.
* Relations: collection subclasses return matching iterators (Factory Method). Memento captures and rolls back iteration state. Visitor operates on heterogeneous elements while traversing.

---

## Mediator

*Also: Intermediary, Controller.* Forbid direct communication between objects; they collaborate only through a mediator.

* Use when
   * classes are hard to change because they're tightly coupled to many others (dialog fields that enable, validate and show each other)
   * a component can't be reused elsewhere because it depends on too many components
   * you keep subclassing components just to reuse them in different contexts

```csharp
// ✗ fields reference each other directly
agreeCheckbox.Changed += () => { emailField.Enabled = agreeCheckbox.Checked; submitButton.Enabled = IsValid(); };

// ✓ components only notify; the dialog decides
interface IMediator { void Notify(object sender, string eventName); }
class SignupDialog : IMediator
{
    public void Notify(object sender, string eventName)
    {
        if (sender == agreeCheckbox && eventName == "changed")
        {
            emailField.Enabled = agreeCheckbox.Checked;
            submitButton.Enabled = IsValid();
        }
    }
}
```

* Components hold the mediator through its interface (usually from their constructor), so they can be reused with another mediator.
* Two common forms, both Mediator: the mediator as publisher and components as subscribers, or components permanently linked to one mediator.
* Cost: over time the mediator can grow into a god object.

---

## Memento

*Also: Snapshot.* Save and restore an object's state without revealing its implementation.

| Role | Job |
|---|---|
| Originator | The object whose state is saved; produces and restores its own snapshots |
| Memento | The immutable snapshot |
| Caretaker | Decides when to snapshot and restore; stores the history (a command, a history object) |

* Use when
   * you need snapshots to restore state: undo, or rolling back a failed transaction
   * reading the object's fields, getters or setters from outside would break its encapsulation

```csharp
// ✗ the history reads and writes the editor's internals
history.Push((editor.Text, editor.CursorPosition));

// ✓ the originator snapshots itself; others see only metadata
interface IMemento { string Name { get; } System.DateTime CreatedAt { get; } }
class Editor
{
    private string text = "";
    private int cursorPosition;
    public IMemento Save() { return new Snapshot(text, cursorPosition, System.DateTime.UtcNow); }
    public void Restore(IMemento memento)
    {
        var snapshot = (Snapshot)memento;
        text = snapshot.Text;
        cursorPosition = snapshot.CursorPosition;
    }
    private sealed class Snapshot : IMemento
    {
        public readonly string Text;
        public readonly int CursorPosition;
        public System.DateTime CreatedAt { get; }
        public string Name { get { return CreatedAt.ToString("HH:mm:ss"); } }
        public Snapshot(string text, int cursorPosition, System.DateTime createdAt)
        {
            Text = text;
            CursorPosition = cursorPosition;
            CreatedAt = createdAt;
        }
    }
}
```

* Gotchas
   * The memento is immutable: data only through the constructor.
   * Nest it in the originator where the language allows. Otherwise expose only a narrow metadata interface.
* Cost
   * RAM, if snapshots are frequent.
   * Caretakers must track the originator's lifecycle to drop obsolete mementos.
   * Dynamic languages (Python, JS, PHP) can't guarantee the memento stays untouched.

---

## Observer

*Also: Event-Subscriber, Listener.* A subscription mechanism that notifies many objects about events on the one they observe.

* Use when
   * a change in one object requires changes in others, and the set of others isn't known ahead of time or changes at run time
   * objects observe others only temporarily; subscribers join and leave at any time

```csharp
// ✗ the publisher knows every reactor; a new one edits it
public void Save() { Persist(); emailAlerts.OnSaved(this); auditLog.OnSaved(this); }

// ✓ an open-ended set of subscribers, attached at run time
public event System.Action<Document>? Saved;
public void Save() { Persist(); Saved?.Invoke(this); }

document.Saved += auditLog.Record;
```

* Language events *are* the pattern; build the class form only when you need more.
* Retrofitting an existing hierarchy: put the subscription list in a separate subscription-manager object that publishers delegate to.
* Pass event data as arguments, or pass the publisher so subscribers pull what they need.
* Cost: no guaranteed notification order. Subscribers that never unsubscribe leak.

---

## State

Let an object change its behavior when its internal state changes, as if it changed its class.

* Use when
   * behavior depends on the current state, there are many states, and state-specific code changes often (a document in Draft → Moderation → Published, where `Publish()` means something different in each)
   * a class is polluted by large conditionals on its own fields
   * a condition-based state machine duplicates code across similar states and transitions

```csharp
// ✗ every method switches on the current state
public void Publish()
{
    switch (state)
    {
        case "draft":      state = "moderation"; break;
        case "moderation": if (currentUser.IsAdmin) { state = "published"; } break;
        case "published":  break;
    }
}

// ✓ one class per state; states trigger the transitions
interface IDocumentState { void Publish(Document document); }
class Draft : IDocumentState
{
    public void Publish(Document document) { document.State = new Moderation(); }
}
class Moderation : IDocumentState
{
    public void Publish(Document document)
    {
        if (!document.CurrentUser.IsAdmin) { return; }
        document.State = new Published();
    }
}
```

* Gotchas
   * The state interface includes only methods with state-specific behavior.
   * A state that needs private context members: make them public, add a public context method (quick and ugly), or nest the state classes in the context.
   * Whoever switches states (context, states or client) depends on the concrete state classes.
* Cost: overkill for a few states or a rarely changing machine. An enum plus `switch` is fine there.

---

## Strategy

A family of interchangeable algorithms, each in its own class.

* Use when
   * an object switches between variants of an algorithm at run time (route by car, on foot, by transit)
   * many similar classes differ only in one behavior: extract the behavior and merge the classes
   * you want to isolate business logic from an algorithm's details, data and dependencies
   * a massive conditional picks between variants of the same algorithm

```csharp
// ✗ the context switches over the variants
public Route BuildRoute(Point from, Point to)
{
    switch (mode)
    {
        case TravelMode.Car:     return BuildRoadRoute(from, to);
        case TravelMode.Walking: return BuildWalkingRoute(from, to);
        default:                 return BuildTransitRoute(from, to);
    }
}

// ✓ variants are interchangeable objects; the client picks one
interface IRouteStrategy { Route BuildRoute(Point from, Point to); }
class Navigator
{
    public IRouteStrategy Strategy { get; set; }
    public Navigator(IRouteStrategy strategy) { Strategy = strategy; }
    public Route BuildRoute(Point from, Point to) { return Strategy.BuildRoute(from, to); }
}
navigator.Strategy = new WalkingStrategy();
```

* Cost
   * Two rarely changing variants don't justify the classes: keep the `switch` statement (see SKILL.md).
   * Clients must understand how the strategies differ to choose one.

---

## Template Method

A base class defines an algorithm's skeleton; subclasses override specific steps without changing its structure.

* Use when
   * clients should extend only particular steps, not the whole algorithm or its structure
   * several classes hold almost the same algorithm, so every change must be made in all of them (data miners for DOC, CSV and PDF that differ only in open/extract/parse)

```csharp
// ✗ three miners duplicate one pipeline; only Open, Extract and Parse differ
class PdfMiner { public void Mine(string path) { /* open, extract, parse, analyze, report, close */ } }
class CsvMiner { public void Mine(string path) { /* open, extract, parse, analyze, report, close */ } }

// ✓ the base fixes the skeleton; subclasses fill in the steps that differ
abstract class DataMiner
{
    public void Mine(string path)                       // not virtual: the structure is fixed
    {
        var file = Open(path);
        var data = Parse(Extract(file));
        Analyze(data);
        SendReport(data);
        Close(file);
    }
    protected abstract File Open(string path);          // required steps
    protected abstract RawData Extract(File file);
    protected abstract Data Parse(RawData rawData);
    protected virtual void Analyze(Data data) { ... }   // default step
    protected virtual void SendReport(Data data) { }    // hook: empty, optional
    protected virtual void Close(File file) { ... }
}
class PdfMiner : DataMiner { ... }
```

* Cost
   * Clients are limited by the skeleton.
   * A subclass that suppresses a default step can violate LSP.
   * The more steps, the harder it is to maintain.

---

## Visitor

Separate an algorithm from the objects it operates on.

* Use when
   * one operation must run on every element of a complex structure whose elements have different classes (export each node to XML)
   * auxiliary behaviors (export, reporting, metrics) would clutter classes with a different main job
   * a behavior makes sense for only some classes of a hierarchy: implement only those visit methods

```csharp
// ✗ export code added to every shape class, or a type switch somewhere

// ✓ double dispatch: Accept picks the visit method by the element's concrete type
interface IShapeVisitor { void VisitCircle(Circle circle); void VisitRectangle(Rectangle rectangle); }
interface IShape { void Accept(IShapeVisitor visitor); }
class Circle    : IShape { public void Accept(IShapeVisitor visitor) { visitor.VisitCircle(this); } }
class Rectangle : IShape { public void Accept(IShapeVisitor visitor) { visitor.VisitRectangle(this); } }
class XmlExportVisitor : IShapeVisitor { ... }   // one behavior for every shape, in one class

foreach (var shape in shapes) { shape.Accept(xmlExport); }
```

* Elements know visitors only through the visitor interface; visitors know every concrete element class.
* Cost
   * Every visitor changes when an element class is added or removed: use it only for stable hierarchies.
   * Visitors can't reach private members, unless you make them public (breaking encapsulation) or nest the visitor.
* Modern alternative: over sealed types or sum types, a `switch` statement on type replaces the machinery:

```csharp
string ToXml(IShape shape)
{
    switch (shape)
    {
        case Circle circle:       return $"<circle r=\"{circle.Radius}\"/>";
        case Rectangle rectangle: return $"<rect w=\"{rectangle.Width}\" h=\"{rectangle.Height}\"/>";
        default:                  throw new System.ArgumentOutOfRangeException(nameof(shape));
    }
}
```

* Relations: runs over a whole Composite tree; combine with Iterator to traverse heterogeneous structures.
