# Server Template

A C# server architecture template. It is **opt-out**: new projects copy it and delete the parts they don't need, instead of adding structure from memory. It's a skeleton: most folders hold only `.gitkeep`, `src/program.cs` is empty, and there's no project file or build, run or test command yet.

- The config files in `src/_config/` are tracked, empty placeholders. Secrets never go in them; they come from a secret store or git-ignored local config (see `rules/security.md`).

<!-- Copying this template? Once the .sln exists, add a "## Commands" section here
     (build: dotnet build, test: dotnet test, format: dotnet format) and delete this comment.
     Block comments like this one are stripped before Claude sees the file. -->

## IMPORTANT: High-Quality Tokens / High-Quality Density

Write only tokens that carry value for the reader or for future generations. A dense 5-page report beats the same content spread over 30 pages.

* "Cut" means cut what carries no value, never cut to save tokens: a line the reader needs stays, however long.
* Bullets are the default form.
* Every concept gets a concrete, visual example: a tree, flow, table, before → after, code, or a Mermaid diagram (for loops, sequences and states, where it renders). The standard forms are in `.claude/skills/high-quality-tokens/examples.md`.
* Cut preamble, repetition, filler, decoration and closing offers.
* Keep decisions with their reasons, and concrete facts.
* Match the depth to what was asked.
* Dense does not mean cryptic: a reader new to the topic must understand it from the text alone. Naming something is not showing it.
* This applies to everything you write, especially files that later sessions load (`CLAUDE.md`, skills, memory).
* Full rules: `.claude/skills/high-quality-tokens/SKILL.md`.

# How We Work

For any non-trivial feature, go through the Approach and Data questions before writing code, and state the answers briefly.

## Layout

```
src/
├── program.cs                                        entry point
├── _architecture/                                    cross-cutting architecture code
├── _contracts/                                       contracts shared between features
├── _config/                                          appsettings, per-feature and infrastructure config
├── _libs/                                            shared libraries
└── features/
    └── <feature>/
        ├── <feature>-serviceServiceExtensions.cs     registers the feature's modules
        ├── _contracts/                               contracts the feature exposes
        └── <module>/
            ├── <module>-serviceServiceExtensions.cs  registers the module
            ├── _dto/                                 requests / commands, validated here (fail early)
            ├── _critical/                            constants, enums
            ├── api/                                  REST, GraphQL, event handlers
            ├── application/                          use cases, orchestration
            ├── domain/                               aggregates, events, policies, value objects
            ├── infrastructure/                       cache, postgres
            ├── integration/                          third-party services (Hubspot, Twilio)
            └── test/
_tools/                                               docker, scripts, sql, terraform
```

Config follows `src/_config/config_guidelines.md`: defaults first, override per case.

`a-feature` and `b-feature` are blank templates to copy. `billing-feature-example` shows a real split: invoicing, payment and subscription modules.

## Rules for this repo

* A feature can be a folder, a module or a separate library. Pick the smallest one the requirement needs. Starting in a single file is fine, so not every folder has to be used.
* Keep things that belong together close, so it's obvious where to look. Avoid overly generic collections and catch-all folders.
* The skills in `.claude/skills/` (`solid-principles`, `design-patterns`) are for review and refactoring once the simple version exists. Don't use them to design up front.
* Folder names keep the existing spelling (`postgress`, `Twillio`) unless asked to rename them.

See `../design_of_applications.md` and `../README.md` for the broader template philosophy.

## Skills by where you work

Invoke the matching skill before writing code there.

| Working in | Skill |
|---|---|
| `api/`, `_dto/` | `api-design`, `security` |
| `infrastructure/`, `_tools/sql` | `database-design` |
| `integration/` | `system-integration` |
| `test/`, or reproducing a bug | `tests-as-documentation` |
| Splitting a feature, `_contracts/` | `microservices-patterns` |
| `domain/`, `application/`, once the simple version works | `solid-principles`, `design-patterns` |
| Any code | `c-like-coding-style`, `logging` |
| Formulas, money, rates, units | `codemath` |
| Slow or large code | `low-level-optimizations` |
| Docs, READMEs, PR descriptions | `high-quality-tokens` |
| Non-trivial or unattended changes | `claude-best-practices` |
| Claude setup: `.claude/`, CLAUDE.md, AGENTS.md, auto memory | `claude-core-concepts`, `claude-memory`; per-file map in `rules/claude-config.md` (loads when you open one of those files) |

## Approach

* KISS.
* SOLID.
* What feature do we want?
* What is the data?
   * What data views do we need to support?
* What is the flow?
* What are the inputs, outputs and side effects of the flow?
* What is the simplest functional form of the logic we want to implement?
   * From there we can worry about objects and organisation.
* Start by writing it in one file, break it apart after.
* Less code is better.
   * That does not mean more compact code that is hard to read.
   * Code not written is less to debug.
* Go back to the basics.
   * Return the object type we create back.
   * Use Booleans.
   * Fail early.
      * DTO (request / command): validate it before it reaches the domain.
   * No exceptions in the domain.
   * The domain controls what is valid.
* Use tests to replicate bugs: write a failing test that reproduces the bug before fixing it.
* The work saved is time gained.

## Code Style

C-like in every language, not idiomatic: guard clauses, plain loops instead of lambda chains, braces and explicit returns, full names, config at the top, explicit namespaces (`using io = System.IO;` → `io.File.ReadAllText(path)`). Invoke `c-like-coding-style` before writing any code: the full rules and the reference example live there. `rules/code-style.md` is the short form that loads with code files.

## Data

* Data layout.
* How do we want to process / transform the data?
   * Do we want to keep the original form?
   * Do we want to keep the in-between?
* Should we include metadata?
* In any system, layers are the foundation for complex systems.
   * A node within a graph can be a graph.
   * A node within a graph can be a tree.
   * An image is layers of color.
   * Audio is layers of sounds.

### Data State

* In process
* Persistence
* Cache
* Events

## Base Computer Science Rules

When proposing a design, name which side of these trade-offs it takes:

* Speed vs Simplicity
* Speed vs Memory vs Accuracy
* Lossless vs Lossy
* Compression vs Time

## Building Blocks

* Data
   * Structured
   * Unstructured
* Initiation Control
* Processing / Transforming Data
* Input / Output Listeners
* Reading / Writing Data
* Storing Data
   * Short: Cache
   * Medium: RAM
   * Long: Storage (different formats)
   * Indexed: Database
* Directing Data To Computing Units
* Activating Hardware Firmware
* Distributed System Communication
* Failure Handling
* Scheduling & Synchronization
   * Every program/system can be viewed as a network of nodes.
      * Latency
      * Time of transfer
   * The scale does not matter:
      * CPU, memory and GPU communicating together
      * Communication of processes
      * Application communication
      * The World Wide Web
   * The techniques used to solve computing problems at the smallest scale are the same as those used at the largest. Many of the mental models are universal; the only difference is the scale of time and data.
   * Data doesn't just move; it waits to move, and that waiting is 90% of what software engineering actually manages.

## Actual Data Instead of Guesses

* Use CLI tools to gather data.
* Use debuggers to track bugs.
