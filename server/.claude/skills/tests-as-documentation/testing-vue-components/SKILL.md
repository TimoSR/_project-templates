---
name: testing-vue-components
description: >-
  Strategy for testing .vue components in Web/, per the official Vue testing
  guide adapted to this repo — route logic that already lives in plain
  modules to the unit suite first, decide whether the template contract
  deserves a component test, then test only the public contract (props/slots
  in → rendered output, interaction → emitted events). Use when the user says
  "test this component", "test <X>.vue", "write component tests", "should this
  component be tested", or asks how we test Vue components.
---

# testing-vue-components

This skill is the *strategy* layer: what the official Vue testing guide
(https://vuejs.org/guide/scaling-up/testing.html) prescribes for components,
adapted to our test suites. The *mechanics* live in the sibling skills —
`write-frontend-unit-tests` (plain-node logic tests) and
`write-frontend-integration-tests` (its mock-policy and GraphQL bullets, see
Phases 3 and 4). A distilled version of the official guidance, and where we
deviate, is in `references/vue-official-guidance.md`.

## Phase 1 — Route plain-module logic to the unit suite first (the pyramid)

The Vue guide's testing pyramid, applied here: most coverage belongs in cheap
plain-node unit tests; a component test covers only what *cannot* be tested
without a template.

- Logic that already lives in a plain `.js` module the component imports →
  unit suite via `write-frontend-unit-tests`. Model: `useSupportContact` in
  `Web/components/util/useSupportContact.js` — its component consumers need no
  component test for that logic.
- Logic inline in the component's `setup()` → don't extract it yourself; don't
  restructure production code to enable a test. Report the extraction as a
  suggestion to the user and test only the template contract here.
- Never mount a component just to reach logic through it — that's the unit
  suite's job.

What remains for a component test is the **template contract**: conditional
rendering, slot wiring, and the props-in → events-out surface.

## Phase 2 — Decide whether the component deserves a test

Worth a component test:
- Conditional rendering the next change could silently break (`v-if` chains,
  readonly/disabled states, empty states).
- Emit contracts: which events fire, with what payload, on which interaction —
  especially `update:modelValue` on form inputs.
- Slot behavior: fallback content, scoped-slot payloads.

Not worth one:
- Purely presentational markup (static template, styling only).
- Thin pass-through wrappers around PrimeVue/library components with no
  branching of their own.
- Pages — they need routing + real data, and E2E is out of scope by policy.

## Phase 3 — Test the public contract only (the Vue-docs rules)

Scope and bans: the "Component scope" section of `Web/test/README.md`; the
reasons, and where we go further than the guide, are in
`references/vue-official-guidance.md`. On top of those, do NOT:
- Assert DOM shape or a class — implementation detail — unless that class
  *is* the contract (e.g. `sr-only` making a control accessible). Prefer text
  content and `data-test` attributes as selectors.
- Stub child components to isolate the parent — mount the real tree; if that
  needs the network, see the GraphQL caveat in
  `write-frontend-integration-tests`.
- Re-test the framework: reactivity flushing, `v-model` plumbing itself,
  happy-dom rendering.

## Phase 4 — Write it in the component suite

Place, name and run the test per `Web/test/README.md` (its component scope,
the `nuxt` environment notes that scope inherits, and the shared conventions)
and the `component` project in `Web/vitest.config.mjs`. When a test needs a
mock, the mock-policy bullet in `write-frontend-integration-tests`
(`mockNuxtImport` hoisting) applies unchanged.

For a form input's emit contract, mirror the test "emits update:modelValue and the legacy
input event with the toggled value" in
`Web/test/component/base/ffInputYesNoSwitch/FfInputYesNoSwitch.test.js` — not the rest of
that file, some of which selects by class.
