# CLAUDE.md

- The backend won't boot without git-ignored local config (`appsettings.Development.json`,
  `launchSettings.json`, `*.LocalDev.json`). Get them from a teammate; don't recreate them.

## IMPORTANT: High-Quality Tokens / High-Quality Density

Write only tokens that carry value for the reader or for future generations. A dense 5-page report beats the same content spread over 30 pages.

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

We don't follow idiomatic standards. No matter the language, We write in a C-like syntax and use explicit namespaces in my API calls. The reference example below shows what that means in practice:

* **Explicit namespaces.** Import each library as a whole namespace, aliased to the library's name in lowercase (`import * as vue from 'vue'`, `import * as threejs from 'three'`). Every call and type goes through it: `vue.ref`, `vue.onMounted`, `threejs.Scene`, `threejs.WebGLRendererParameters`. No named imports like `import { ref } from 'vue'`. Language globals (`Math`, `window`, `ResizeObserver`) and framework macros (`defineProps`, `withDefaults`) stay bare.
   * In C#: don't bring library names into scope with `using X;`. Call through the namespace, and alias long ones (`using io = System.IO;`, then `io.File.ReadAllText(path)`).
* **Config at the top.** Every tunable value lives in a named config object, grouped by what it configures (`cameraConfig`, `rendererConfig`, `animationConfig`). Logic reads from config, with no magic numbers inline. Use the library's type for a config when it has one. Inputs get defaults that callers can override (`withDefaults`).
* **Units.** Put the unit in the name or a comment (`deltaSeconds`, `rotationSpeed: 0.6, // radians per second`). Scale by measured time (`clock.getDelta()`), not per-frame constants.
* **Full names.** No abbreviations, even where the library abbreviates (`fieldOfView`, not `fov`). Functions are verb + noun (`resizeScene`, `destroyScene`).
* **Linear flow.** One file, read top to bottom: imports, inputs, config, state, setup in dependency order, loop, teardown. Use local functions (`const resizeScene = () => { ... }`), not classes or extra modules.
* **Guard clauses.** Check for failure first and return immediately: `if (!element) return`, `if (width === 0 || height === 0) return`.
* **Explicit lifetimes.** Everything that's created gets released, in a teardown written in the same scope as the setup, like `init`/`free` pairs in C. `destroyScene` stops the loop, disconnects the observer, disposes the geometry, material and renderer, and removes the DOM node.
* **`const` by default.** Use `let` only for values that get reassigned (`destroyScene`). Annotate types at boundaries (props, refs, config, handles) and let locals infer.
* **Formatting (TS/Vue).** No semicolons, single quotes, trailing commas, 2-space indent, one argument per line when a call wraps.

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
