# Behavioral patterns

Behavioral patterns handle communication between objects and the assignment of responsibilities among them.

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
*Also: CoR, Chain of Command.*

**Intent.** Pass a request along a chain of handlers; each handler either processes it or passes it to the next.

**Use when**
- Different kinds of requests must be processed in different ways, but the exact kinds and their sequence aren't known up front (e.g. auth → validation → brute-force filter → cache before an order handler).
- Several handlers must run in a specific order.
- The set or order of handlers must change at runtime.

**Two flavors.** Either each handler may stop the chain (first handler able to handle it wins — e.g. GUI help/event bubbling), or every handler does its part and passes on (pipeline). Decide which one you are building.

**How to implement**
1. Declare the handler interface with one handling method. Pass request data as a single request object — the most flexible option.
2. Optionally write an abstract base handler holding the `next` reference with a default "forward to next if any" implementation. Make it immutable unless chains must change at runtime (then add a setter).
3. Write concrete handlers. Each decides (a) whether to process and (b) whether to pass along.
4. The client assembles the chain itself or receives it prebuilt from a factory driven by configuration.
5. The client may enter the chain at any handler, not only the first.
6. Be ready for: a one-link chain; requests that stop early; requests that fall off the end unhandled.

**Pros.** Control over handling order. SRP: invokers decoupled from performers. OCP: new handlers without breaking clients.
**Cons.** Some requests may go unhandled — decide what happens at the end of the chain.

**Relations**
- CoR, Command, Mediator, Observer: four ways to connect senders and receivers (see SKILL.md).
- Often used with Composite: a leaf passes a request up through its parents.
- Handlers can be Commands (many operations over one request/context), or the request itself can be a Command (one operation across many contexts).
- vs Decorator: see SKILL.md look-alikes.

---

## Command
*Also: Action, Transaction.*

**Intent.** Turn a request into a stand-alone object containing everything about the request, so you can pass requests as arguments, delay or queue them, and support undo.

**Use when**
- You want to parameterize objects with operations — e.g. configurable menu items, buttons, and shortcuts that trigger the same operations without a subclass per button.
- You want to queue, schedule, log, or execute operations remotely. Commands can be serialized like any object.
- You want reversible operations. Keep a history stack of executed commands plus state backups. Backups may need Memento (private state) and cost RAM; the alternative is an inverse operation, which can be hard or impossible to write.

**How to implement**
1. Declare a command interface with a single `execute` method.
2. Extract requests into concrete command classes. Each holds the request arguments and a reference to the receiver, all set via constructor.
3. Identify senders (invokers); give them fields for commands and talk to commands only through the interface. Senders usually receive commands from the client rather than creating them.
4. Change senders to execute the command instead of calling the receiver directly.
5. Client initialization order: create receivers → create commands bound to receivers → create senders bound to commands.

**Pros.** SRP: invokers decoupled from performers. OCP: new commands without breaking clients. Undo/redo. Deferred execution. Simple commands compose into macro commands.
**Cons.** A whole new layer between senders and receivers. If you need none of queue/log/undo, a function reference does the job.

**Relations**
- With Memento for undo: commands act, mementos snapshot state just before.
- vs Strategy: see SKILL.md look-alikes.
- Prototype helps store copies of commands in history.
- Visitor is a more powerful Command that can operate over objects of different classes.

---

## Iterator

**Intent.** Traverse a collection's elements without exposing its underlying representation (list, stack, tree, graph…).

**Use when**
- A collection has a complex structure you want to hide from clients, for convenience or to protect it from careless or malicious access.
- Non-trivial traversal code is duplicated across the app and blurs business logic.
- Code must traverse different data structures, or structures whose type isn't known ahead of time.

**How to implement**
1. Declare the iterator interface: at minimum "next element"; optionally previous, current position, has-more.
2. Declare the collection interface with a method returning an iterator (typed as the iterator interface). Add more such methods for distinct groups of iterators (e.g. depth-first vs breadth-first).
3. Implement concrete iterators for traversable collections. Each iterator is tied to one collection instance, usually via its constructor.
4. Implement the collection interface: the collection passes itself to the iterator's constructor.
5. Replace client traversal code with iterators; fetch a fresh iterator for each traversal.

**Pros.** SRP: bulky traversal extracted. OCP: new collections and iterators plug into existing code. Each iterator has its own state, so the same collection can be iterated in parallel, and an iteration can be paused and resumed.
**Cons.** Overkill for simple collections. Can be less efficient than direct access to specialized collections. Most languages already provide the iterator protocol — implement that rather than a homemade interface.

**Relations**
- Traverse Composite trees. Combine with Factory Method (collection subclasses return matching iterators), Memento (capture and roll back iteration state), Visitor (operate on heterogeneous elements while traversing).

---

## Mediator
*Also: Intermediary, Controller.*

**Intent.** Reduce chaotic dependencies between objects by forbidding direct communication and making them collaborate only through a mediator.

**Use when**
- Classes are hard to change because they're tightly coupled to many others (e.g. dialog form fields that enable, validate, and show each other).
- A component can't be reused in another program because it depends on too many other components.
- You keep creating component subclasses just to reuse basic behavior in different contexts.

**How to implement**
1. Identify a group of tightly coupled classes that would benefit from independence.
2. Declare the mediator interface — usually one notification method (e.g. `notify(sender, event)`). Components depend on this interface, so they can be reused with a different mediator.
3. Implement the concrete mediator, holding references to the components it manages.
4. Optionally make the mediator create and destroy components (it then resembles a factory or facade).
5. Components hold a reference to the mediator, typically passed into their constructor.
6. Change components to notify the mediator instead of calling other components; move that cross-component logic into the mediator, triggered by the notifications.

**Pros.** SRP: communication logic in one place. OCP: new mediators without changing components. Less coupling. Easier component reuse.
**Cons.** Over time the mediator can grow into a god object.

**Relations**
- vs Facade and Observer: see SKILL.md look-alikes. A common implementation makes the mediator a publisher and the components subscribers; another permanently links all components to one mediator — both are Mediator.

---

## Memento
*Also: Snapshot.*

**Intent.** Save and restore an object's previous state without revealing its implementation details.

**Use when**
- You need snapshots to restore previous state — undo, and also transactions (roll back an operation on error).
- Direct access to the object's fields, getters, or setters would break its encapsulation. The originator produces its own snapshot, which no one else can read.

**Roles.** *Originator* (the object whose state is saved), *Memento* (the snapshot), *Caretaker* (decides when to snapshot and restore; stores history — e.g. a command or a history object).

**How to implement**
1. Choose the originator; note whether there is one central object or many small ones.
2. Create the memento class with fields mirroring the originator's.
3. Make the memento immutable: data only through the constructor, no setters.
4. If the language supports nested classes, nest the memento in the originator. Otherwise expose only a narrow interface (metadata such as timestamp/name, nothing that reveals state) to everyone else.
5. Add a `save()` method on the originator that creates a memento from its state (returning the narrow interface type, if any).
6. Add a `restore(memento)` method on the originator; it casts back to the concrete memento for full access.
7. The caretaker decides when to request mementos, how to store them, and when to restore.
8. Alternatively, link each memento to its originator and move `restore` onto the memento — only sensible if the memento is nested or the originator offers enough setters.

**Pros.** Snapshots without breaking encapsulation. Originator stays simple; caretaker keeps history.
**Cons.** RAM cost if snapshots are frequent. Caretakers must track the originator's lifecycle to drop obsolete mementos. Dynamic languages (Python, JS, PHP) can't guarantee the memento stays untouched.

**Relations**
- With Command for undo; with Iterator to capture and restore iteration state.
- Prototype can replace it for simple state without external resource links.

---

## Observer
*Also: Event-Subscriber, Listener.*

**Intent.** Define a subscription mechanism so multiple objects are notified about events on the object they observe.

**Use when**
- Changes in one object may require changes in others, and the set of those others isn't known ahead of time or changes dynamically (e.g. custom GUI buttons that clients hook code into).
- Some objects need to observe others only temporarily or in specific cases; subscribers can join and leave at any time.

**How to implement**
1. Split the logic: the independent core becomes the publisher; the rest becomes subscriber classes.
2. Declare the subscriber interface — at minimum one `update` method.
3. Declare the publisher interface with subscribe and unsubscribe. Publishers talk to subscribers only through the subscriber interface.
4. Decide where the subscription list lives. Usually an abstract base publisher shared by concrete publishers; if retrofitting an existing hierarchy, use composition — a separate subscription-manager object that real publishers delegate to.
5. Concrete publishers notify all subscribers whenever something important happens.
6. Implement `update` in subscribers. Pass event data as arguments, or pass the publisher itself so subscribers can pull what they need (or, least flexibly, bind subscriber to publisher via constructor).
7. The client creates subscribers and registers them with publishers.

**Pros.** OCP: new subscribers without changing the publisher (and vice versa with a publisher interface). Relations established at runtime.
**Cons.** Subscribers are notified in no guaranteed order. Watch for leaks from subscribers that never unsubscribe.

**Relations**
- vs Mediator, and the four sender/receiver patterns: see SKILL.md look-alikes.

---

## State

**Intent.** Let an object change its behavior when its internal state changes, as if it changed its class.

**Use when**
- An object behaves differently depending on its current state, there are many states, and state-specific code changes often (e.g. a document in Draft → Moderation → Published, where `publish()` means something different in each).
- A class is polluted by large conditionals that switch behavior on the current values of its fields.
- Similar states and transitions of a condition-based state machine duplicate code; state classes can share code via abstract base states.

**How to implement**
1. Choose the context class — an existing class with state-dependent code, or a new one if that code is spread across several classes.
2. Declare the state interface; include only methods that have state-specific behavior.
3. Create one class per state and move that state's code out of the context into it. If it needs private context members: make them public, expose the behavior as a public context method (quick and ugly), or nest state classes in the context.
4. Give the context a field of the state interface type and a public setter for it.
5. Replace the state conditionals in context methods with calls to the current state object.
6. Switch states by passing a new state instance to the context — from the context, from states, or from the client. Whoever does it depends on that concrete state class.

**Pros.** SRP: per-state code in separate classes. OCP: new states without changing existing states or context. Context loses its bulky conditionals.
**Cons.** Overkill for a state machine with few states or one that rarely changes — an enum plus `switch` is fine there.

**Relations**
- An extension of Strategy: states may know each other and trigger transitions; strategies don't.
- Same composition structure as Bridge, Strategy, and Adapter; different intent.

---

## Strategy

**Intent.** Define a family of algorithms, put each in its own class, and make them interchangeable.

**Use when**
- An object must use different variants of an algorithm and switch between them at runtime (e.g. route planning by car, walking, or public transport).
- Many similar classes differ only in how they perform one behavior. Extract the behavior into a strategy hierarchy and merge the classes.
- You want to isolate business logic from the implementation details, data, and dependencies of algorithms.
- A class has a massive conditional choosing between variants of the same algorithm.

**How to implement**
1. In the context, find the algorithm that changes often — often a big conditional selecting a variant.
2. Declare a strategy interface common to all variants.
3. Extract each variant into its own class implementing the interface.
4. Give the context a strategy field (with a setter if runtime switching is needed). The context uses it only through the interface and may expose an interface that lets strategies read its data.
5. Clients choose and set the strategy that fits how they want the context to do its job.

**Pros.** Swap algorithms at runtime. Algorithm details isolated from users. Composition replaces inheritance. OCP: new strategies without changing the context.
**Cons.** With only a couple of rarely changing algorithms, the extra classes aren't worth it. Clients must understand the differences between strategies to choose one. In languages with first-class functions, a lambda/delegate often does the same job without new classes.

**Relations**
- vs State, Bridge, Command, Decorator, Template Method: see SKILL.md look-alikes.

---

## Template Method

**Intent.** Define an algorithm's skeleton in a base class and let subclasses override specific steps without changing its structure.

**Use when**
- Clients should be able to extend only particular steps of an algorithm, not the whole thing or its structure.
- Several classes contain almost identical algorithms with small differences, so every algorithm change must be made in all of them (e.g. data miners for DOC, CSV, and PDF that share everything except open/extract/parse).

**How to implement**
1. Break the target algorithm into steps; note which are common to all subclasses and which are always unique.
2. Create an abstract base class with the template method and one method per step; the template method calls the steps in order. Consider making the template method final/sealed.
3. Steps can all be abstract; some may get default implementations that subclasses need not override.
4. Consider adding hooks — empty optional steps — between crucial steps.
5. For each variation, create a subclass implementing all abstract steps and optionally overriding defaults and hooks.

**Pros.** Clients override only parts of a large algorithm and are less affected by changes elsewhere in it. Duplicate code pulled into the superclass.
**Cons.** Clients are limited by the provided skeleton. A subclass that suppresses a default step can violate LSP. The more steps, the harder to maintain.

**Relations**
- Factory Method is a specialization of Template Method and can be one of its steps.
- vs Strategy: inheritance and class-level (static) vs composition and object-level (runtime).

---

## Visitor

**Intent.** Separate algorithms from the objects on which they operate.

**Use when**
- You must perform an operation on every element of a complex object structure (e.g. export each node of a graph or tree to XML) whose elements have different classes.
- You want to keep primary classes focused on their main job by moving auxiliary behaviors (export, reporting, metrics) into visitors.
- A behavior makes sense only for some classes of a hierarchy: implement only the relevant visit methods and leave the rest empty.

**Mechanism.** Double dispatch: `element.accept(visitor)` calls `visitor.visitConcreteElement(this)`, so the right visitor method is chosen by the element's concrete class without type checks.

**How to implement**
1. Declare the visitor interface with one visit method per concrete element class.
2. Declare the element interface — or add an abstract `accept(visitor)` to the existing hierarchy's base class.
3. Implement `accept` in every concrete element: just call the matching visit method on the visitor.
4. Elements know visitors only via the visitor interface; visitors know all concrete element classes (as visit-method parameter types).
5. For each behavior that can't live in the element hierarchy, create a concrete visitor implementing all visit methods. If it needs private element members: make them public (breaks encapsulation) or nest the visitor in the element class where the language allows.
6. The client creates visitors and passes them to elements through `accept`.

**Pros.** OCP: new behaviors over many classes without changing those classes. SRP: all versions of one behavior live in one class. A visitor can accumulate information while walking a structure.
**Cons.** Every visitor must be updated when an element class is added or removed — so use it only when the element hierarchy is stable. Visitors may lack access to private members of elements. In languages with exhaustive pattern matching over sealed types or sum types, a `switch` expression often replaces the visitor machinery.

**Relations**
- A more powerful Command that works over objects of different classes.
- Run over a whole Composite tree; combine with Iterator to traverse heterogeneous structures.
