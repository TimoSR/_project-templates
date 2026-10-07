---
name: write-frontend-integration-tests
description: >-
  Writes Vitest integration tests for the Web/ frontend the FlexFunding way — the
  `nuxt` test environment, real objects first with mocks only at genuine
  boundaries. For runtime-entangled non-component code the unit suite excludes —
  needing window/localStorage/document, Nuxt auto-imports or runtime config.
  (.vue components belong to the testing-vue-components skill.) Use when the user
  says "write an integration test" or "integration-test this composable" in Web/.
---

# write-frontend-integration-tests

Integration suite only. The sibling of `write-frontend-unit-tests` (same
philosophy: tests are documentation, real objects over fakes) for the
runtime-entangled non-component code that suite excludes.

Conventions live in `Web/test/README.md` ("Integration scope" plus the shared
conventions) — read it before writing. This skill is the process; that file is
the style.

## Phase 1 — Classify the target

- **Pure logic** (deps as arguments, no browser/Nuxt globals) → wrong suite; use
  `write-frontend-unit-tests`. This suite is not an escape hatch from that one.
- **Runtime-entangled** non-component code (as the README defines it) →
  belongs here. So does a composable that needs a component instance (lifecycle
  hooks, `inject`): host it in a minimal probe component — model: `mountProbe` in
  `Web/test/integration/components/util/useUrlHashParams.test.js`. That is not a
  component test.
- **A `.vue` component** → wrong suite; that's the component suite via the
  `testing-vue-components` skill.
- **Needs the real backend** (the real `$ftb` service boot, real GraphQL/auth/ws
  traffic, navigation across real pages) → out of scope; say so and stop.

## Phase 2 — Know what the environment does and doesn't have

Read the "Integration scope" section of `Web/test/README.md` for what the `nuxt`
environment deliberately leaves out and how a test works around each gap.

Short real waits are fine; for anything longer, scope fake timers to that one
test and restore real timers in a `finally` (model: `toastStore` tests in
`Web/test/integration/state/useToastStore.test.js`).

## Phase 3 — Place and name the file

Place it as `Web/test/README.md` says and name it to match the integration
project's `include` glob in `Web/vitest.config.mjs` — a file outside that glob
is silently skipped. Don't add per-file environment pragmas — the environment
is set per Vitest project.

## Phase 4 — Write the tests

Follow the README's shared conventions. Also: no dates or amounts that age out,
and whatever a test mutates in singleton state it puts back.

On top of those:
- **Mock policy — real objects first**, per the README. `mockNuxtImport` is
  hoisted and applies once per file — wrap state in `vi.hoisted` for per-test
  control. An all-mocks test is a finding to surface, not a test to write.
- **GraphQL/Apollo-backed code (modules or components):** if
  `Web/test/README.md` has no proven pattern for faking Apollo traffic
  (`registerEndpoint` targets `$fetch`-style endpoints; don't assume it reaches
  our Apollo link chain), treat the first such test as infrastructure work:
  prove the pattern, then record it in the README.
- Don't test the framework: mounting succeeding, reactivity flushing, or
  happy-dom's DOM are not assertions — this module's contract is.

## Phase 5 — Run and verify

Run the integration project on its own, as the README's "Running" section
shows.

Green is not done: re-read each assert and check it would fail on a regression.
If a test exposes a live bug, apply the "If a test exposes a live bug" rule in
`write-frontend-unit-tests` unchanged.
