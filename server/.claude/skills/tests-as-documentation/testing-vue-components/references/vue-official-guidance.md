# Official Vue testing guidance — distilled, with our deviations

Source: https://vuejs.org/guide/scaling-up/testing.html.

## Vue-docs test types, mapped to this repo

| Vue-docs type | Docs recommend | Our home |
| --- | --- | --- |
| Unit (logic, composables) | Vitest | Unit suite |
| Component | Vitest + @vue/test-utils or @testing-library/vue, jsdom/happy-dom | Component suite |
| End-to-end | Playwright / Cypress | None (see deviations) |

## Component testing — the docs' do/don't (we adopt)

Do: assert render output from props/slots; assert emitted events and updates
from user input; test the public interface only ("test what it does, not how").
Don't: test private state or private methods; rely exclusively on snapshot
tests; stub child components; over-mock (docs: "mock as little as possible" —
matches our boundary-mocks-only rule).

## Composables — the docs' cases, mapped

- **Reactivity-only** composables: call directly, assert `.value` — Vue's
  `ref`/`computed` work in plain node, so these belong in the unit suite
  (model: `describe('useSupportContact')` in
  `Web/test/unit/components/util/useSupportContact.test.js`).
- **Lifecycle / provide-inject** composables: still need a host component, as
  the docs' `withSetup` helper does — the `nuxt` environment adds only
  app-level context (auto-imports, runtime config, plugins), not a component
  instance for the hooks to register on. Call the composable inside a minimal
  probe component's `setup()` and test it in the integration suite (model:
  `mountProbe` in
  `Web/test/integration/components/util/useUrlHashParams.test.js`).

## Where we knowingly deviate

- **No mocks in the unit suite** (docs permit mocking in unit tests): our
  boundary is environment-based instead — anything needing a mock moves to the
  integration suite.
- **No snapshot tests** (docs merely caution): explicit asserts only.
- **No E2E tier** (docs recommend one): out of scope by policy. A request for
  browser/multi-page coverage is a scope conversation — say so rather than
  approximating it with a bigger component test.
