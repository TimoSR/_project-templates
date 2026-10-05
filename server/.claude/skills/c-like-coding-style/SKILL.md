---
name: c-like-coding-style
description: Enforces the user's C-like, C#-manner coding style in every language (Rust, C#, TypeScript, JavaScript, Vue and others) - braces and explicit returns, plain loops instead of lambda chains, delegates / arrow functions / closures only as named local rules at the top of a function, and Rust APIs that own the ownership so callers just pass plain values like "hello world" or [73, 67] with no &, .clone(), .to_string() or lifetimes. Use whenever writing, refactoring, generating or reviewing code in any language, even if style is never mentioned - snippets, examples, katas, tests and full features. Not for explaining a concept with no code to write.
---

# C-Like Style

Code reads like C written by a C# developer: explicit, imperative, top to bottom. These rules apply in every language; the per-language sections only add what differs. A project's `CLAUDE.md` or formatter config overrides this skill where they disagree.

## Rules for every language

The [reference example](#reference-example) at the end shows each of these in one file.

* **Explicit namespaces.** Import each library as a whole namespace, aliased to the library's name in lowercase (`import * as vue from 'vue'`, `import * as threejs from 'three'`). Every call and type goes through it: `vue.ref`, `vue.onMounted`, `threejs.Scene`, `threejs.WebGLRendererParameters`. No named imports like `import { ref } from 'vue'`. Language globals (`Math`, `window`, `ResizeObserver`) and framework macros (`defineProps`, `withDefaults`) stay bare.
   * In C#: don't bring library names into scope with `using X;`. Call through the namespace, and alias long ones (`using io = System.IO;`, then `io.File.ReadAllText(path)`).
* **Config at the top.** Every tunable value lives in a named config object, grouped by what it configures (`cameraConfig`, `rendererConfig`, `animationConfig`). Logic reads from config, with no magic numbers inline. Use the library's type for a config when it has one. Inputs get defaults that callers can override (`withDefaults`).
* **Units.** Put the unit in the name or a comment (`deltaSeconds`, `rotationSpeed: 0.6, // radians per second`). Scale by measured time (`clock.getDelta()`), not per-frame constants.
* **Full names.** No abbreviations, even where the library abbreviates (`fieldOfView`, not `fov`). Functions are verb + noun (`resizeScene`, `destroyScene`).
* **Linear flow.** One file, read top to bottom: imports, inputs, config, state, setup in dependency order, loop, teardown. No extra classes or modules for single-use logic; the only class is the feature's namespace (a static class in C#, a unit struct in Rust, table below). TS/Vue local helpers: § TypeScript.
* **Guard clauses.** Check for failure first and return immediately: `if (!element) return`, `if (width === 0 || height === 0) return`.
* **Explicit lifetimes.** Everything that's created gets released, in a teardown written in the same scope as the setup, like `init`/`free` pairs in C. `destroyScene` stops the loop, disconnects the observer, disposes the geometry, material and renderer, and removes the DOM node.
* **Types at boundaries.** Annotate props, refs, config and handles; let locals infer. TS/JS: `const` by default, `let` only for values that get reassigned (`destroyScene`).

On top of those:

| Rule | ✗ | ✓ |
|---|---|---|
| Braces even on one-line bodies; brace placement follows the language's formatter. TS/Vue exception: a one-statement guard (§ TypeScript) | `if (x) return;` | `if (x) { return; }` |
| Explicit `return` at the end of every function body | tail expression `result` | `return result;` |
| Plain loops and `if`/`switch` statements for logic | `.filter().map().reduce()`, ternary chains | `for` + `if` + `push` |
| Delegates, arrow functions, closures: only as named local rules (next section) | `items.filter(x => …)`, `Func<T,bool>` params | rules declared at the top, used by `if` |
| Duplicate ten explicit lines rather than share them through a function parameter | `process(items, x => x.Total)` | two readable functions |
| Return the object itself; null/`None` when absent; `bool` for "applied or not" | `Result { IsSuccess, Errors }` wrappers | `return loan;` / `return null;` / `return false;` |
| No exceptions or panics in the domain | `throw` / `panic!` on bad input | validate at the boundary, return null/`false` |
| Domain type aliases name the concept | `Vec<i32>` everywhere | `type Grade = i32;` |
| A static class (C#) / unit struct + `impl` (Rust) is the namespace for a feature | loose free functions | `GradingStudents::round_grades(…)` |

* Don't add decoration: no `// region` comment pairs, no banner comments, no demo functions the task didn't ask for.

## Delegates, arrow functions and closures

Your own code uses one form: **named local rules**. These are small named closures declared at the top of a function body; the function's statements below use them.

| Use | Allowed | Instead |
|---|---|---|
| Named local rule at the top of a function | ✓ | — |
| Callback a framework requires: event handler, `vue.onMounted`, `vue.computed`, EF/LINQ predicate, DI `options => …`, Moq `Setup(x => …)` | ✓ unavoidable. Keep the body short and call a named function for real work | — |
| Closure as a local helper with statements (C#, Rust; TS/Vue allows it, § TypeScript) | ✗ | a named function that takes what it needs as parameters |
| Your own function taking a delegate: `Func<T, bool>`, `impl Fn(T) -> bool`, `callback: (x) => …` | ✗ | two explicit functions |
| Stored or module-level delegate: `const IS_FAILING: fn(i32) -> bool = …`, a `static Func<…>` field (TS/Vue exception: the teardown handle, § TypeScript) | ✗ | a plain function |
| Returning a closure, currying, function factories | ✗ | a plain function |
| Passing a rule to a chain: `.filter(isPassing)`, `.Where(isPassing)` | ✗ | `for` + `if (isPassing(x))` |

A named local rule:
* is declared before any logic, smallest rule first, composed rules after it.
* is named like a predicate or a value: `isPassing`, `shouldRound`, `deltaToNextMultiple`.
* is one pure expression. It reads only its parameters and config constants: no mutation, no I/O, no `throw` / `panic!`.
* has its parameter types written out.
* has a positive form only. Negate at the call site with `!`; don't define both `isPassing` and `isFailing`.
* stays inside its function: it is never passed, stored or returned. If a second function needs the rule, promote it to a plain function.

The Rust form is `round_grade` in [rust.md](rust.md) §6.

```csharp
public static class GradingStudents
{
    private const int MinimumPassingGrade = 38;
    private const int RoundingBase = 5;
    private const int RoundingDeltaLimit = 3; // round only when the gap is below this

    public static int RoundGrade(int grade)
    {
        System.Func<int, bool> isPassing = (int grade) => grade >= MinimumPassingGrade;
        System.Func<int, int> deltaToNextMultiple = (int grade) => RoundingBase - grade % RoundingBase;
        System.Func<int, bool> shouldRound = (int grade) => isPassing(grade) && deltaToNextMultiple(grade) < RoundingDeltaLimit;

        if (!shouldRound(grade))
        {
            return grade;
        }

        return grade + deltaToNextMultiple(grade);
    }
}
```

```ts
function roundGrade(grade: number): number {
  const isPassing = (grade: number): boolean => grade >= gradingConfig.minimumPassingGrade
  const deltaToNextMultiple = (grade: number): number => gradingConfig.roundingBase - (grade % gradingConfig.roundingBase)
  const shouldRound = (grade: number): boolean => isPassing(grade) && deltaToNextMultiple(grade) < gradingConfig.roundingDeltaLimit

  if (!shouldRound(grade)) {
    return grade
  }

  return grade + deltaToNextMultiple(grade)
}
```

## Rust

* The API owns the ownership: the caller passes literals and values (`"hello"`, `73`, `[73, 67]`) and never writes `String::from`, `.to_string()`, `&`, `.clone()` or a lifetime.
* **Never `.unwrap()`**, nor `.expect()` or `panic!`, anywhere: library code, `main` or tests.
* Before writing Rust, read [rust.md](rust.md): signatures that take `impl Into<…>`, owned returns, no-unwrap patterns, crate and module layout, imports, lint and rustfmt config, a full example, tests.

## C#

* Block bodies for methods and properties: `{ return x; }`, never `=> x`. Named local rules are the only `=>` you write yourself.
* `switch` statement with `case X: return …;` and `default:`, not switch expressions.
* Explicit constructor assigning `private readonly` fields; no primary constructors.
* Write the type: `new LoanResponse(…)`, not target-typed `new()`. No range tricks (`[..20]`): use `Substring(0, 20)`.

## TypeScript / JavaScript / Vue

* Formatting: no semicolons, single quotes, trailing commas, 2-space indent, one argument per line when a call wraps.

The reference example below sets three exceptions to the rules above:

* Local helpers inside a setup scope are arrow-function constants: `const resizeScene = () => { … }`. They may read that scope's handles (`camera`, `renderer`, `element`) instead of taking them as parameters.
* A guard clause that is one statement stays unbraced: `if (!element) return`. Any other `if` body gets braces.
* The teardown handle is the one stored closure: `let destroyScene: (() => void) | undefined`, assigned at the end of setup and called in `vue.onBeforeUnmount`.

### Reference example

```vue
<!-- components/Scene.vue -->
<script setup lang="ts">
import * as vue from 'vue'
import * as threejs from 'three'

const props = withDefaults(defineProps<{ height?: string }>(), {
  height: '400px',
})

const cameraConfig = {
  fieldOfView: 75,
  nearPlane: 0.1,
  farPlane: 100,
  distance: 3,
}

const rendererConfig: threejs.WebGLRendererParameters = {
  antialias: true,
}

const animationConfig = {
  rotationSpeed: 0.6, // radians per second
  maxPixelRatio: 2,
}

const container = vue.ref<HTMLDivElement>()
let destroyScene: (() => void) | undefined

vue.onMounted(() => {
  const element = container.value
  if (!element) return

  const scene = new threejs.Scene()

  const camera = new threejs.PerspectiveCamera(
    cameraConfig.fieldOfView,
    1,
    cameraConfig.nearPlane,
    cameraConfig.farPlane,
  )
  camera.position.z = cameraConfig.distance

  const renderer = new threejs.WebGLRenderer(rendererConfig)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, animationConfig.maxPixelRatio))
  element.appendChild(renderer.domElement)

  const geometry = new threejs.BoxGeometry()
  const material = new threejs.MeshNormalMaterial()
  const cube = new threejs.Mesh(geometry, material)
  scene.add(cube)

  const resizeScene = () => {
    const width = element.clientWidth
    const height = element.clientHeight
    if (width === 0 || height === 0) return

    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
  }

  const resizeObserver = new ResizeObserver(resizeScene)
  resizeObserver.observe(element)
  resizeScene()

  const clock = new threejs.Clock()

  renderer.setAnimationLoop(() => {
    const deltaSeconds = clock.getDelta()
    cube.rotation.x += animationConfig.rotationSpeed * deltaSeconds
    cube.rotation.y += animationConfig.rotationSpeed * deltaSeconds
    renderer.render(scene, camera)
  })

  destroyScene = () => {
    renderer.setAnimationLoop(null)
    resizeObserver.disconnect()
    geometry.dispose()
    material.dispose()
    renderer.dispose()
    renderer.domElement.remove()
  }
})

vue.onBeforeUnmount(() => {
  destroyScene?.()
})
</script>

<template>
  <div ref="container" class="scene" :style="{ height: props.height }" />
</template>

<style scoped>
.scene {
  width: 100%;
  overflow: hidden;
}
</style>
```
