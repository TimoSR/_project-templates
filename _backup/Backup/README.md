# Frontend

A monorepo frontend that mirrors the backend's vertical architecture: **features split into modules** (the same `feature → module` nesting as `Backend/src/features`), an **`entities` layer** for shared business objects, and thin **apps** that only compose. It scales to large teams and dozens of features.

### Top level: monorepo (pnpm workspaces + Turborepo or Nx)

```
Frontend/
├── apps/                         # deployable apps: thin, composition only
│   ├── web/                      # main customer app
│   ├── admin/                    # back-office app
│   └── storybook/                # design-system docs
│
├── packages/                     # everything reusable, each with its own package.json
│   ├── ui/                       # design system (tokens, primitives, patterns)
│   ├── api-client/               # generated OpenAPI/GraphQL types + http client
│   ├── entities/                 # shared business objects (see below)
│   │   └── user/                 # model/, api/, ui/
│   ├── auth/                     # session, guards, permissions
│   ├── i18n/
│   ├── telemetry/                # logging, analytics, error reporting
│   ├── config-eslint/            # shared lint rules, including boundary rules
│   ├── config-ts/
│   └── testing/                  # test utils, MSW handlers, fixtures, factories
│
├── features/                     # vertical slices as packages (mirror Backend/src/features)
│   └── a-feature/
│       ├── a-module/
│       └── b-module/
│
└── tooling/
    ├── e2e/                      # Playwright, organised by user journey
    ├── generators/               # plop/nx generators (e.g. new module)
    └── scripts/                  # codegen and helper scripts
```

### One app (`apps/web`, `apps/admin`)

```
web/
├── public/             # static assets
└── src/
    ├── app/
    │   ├── providers/          # query client, auth, i18n, theme
    │   ├── router/
    │   ├── layouts/
    │   └── error-boundaries/
    ├── pages/              # route entries: compose widgets; no logic
    ├── widgets/            # large self-contained blocks (Header, DashboardPanel) built from features
    └── processes/          # (optional) flows spanning several features: onboarding, checkout wizard
```

### A feature module (`features/a-feature/a-module`)

Same shape as a backend module. `b-module` is a second copy to show the nesting.

```
a-module/
├── index.ts                # public API: the only thing others may import
├── package.json            # "@features/a-feature-a-module"
├── ui/
│   ├── components/         # private components
│   └── containers/         # connected components (data + UI)
├── application/            # use cases as hooks: useSubmitOrder, useApproveInvoice
├── model/
│   ├── store/              # client state (Zustand/Redux slice), when needed
│   ├── schemas/            # zod validation
│   ├── mappers/            # DTO → view model
│   └── types.ts
├── api/                    # queries, mutations, query keys, cache invalidation
│   ├── queries.ts
│   ├── mutations.ts
│   └── realtime.ts         # websockets/SSE subscriptions (backend `api/EventHandlers`)
├── integration/            # third-party browser SDKs (Stripe, Hubspot widget, maps)
├── _critical/              # constants, enums, feature flags
├── _dto/                   # re-exports of generated API types this module uses
└── test/
    ├── unit/
    ├── component/
    └── mocks/              # MSW handlers for this module
```

### Entities: shared business objects

Several features read the same `User`, `Order` or `Product`. Put those objects in `packages/entities/<name>/`, one folder per object, each holding `model/`, `api/` and `ui/`. The `ui/` folder has display components such as `UserAvatar` and `OrderStatusBadge`. Features act on entities, and entities never import features.

### Dependency rules

These rules are what keep a large codebase maintainable. Enforce them with ESLint (`eslint-plugin-boundaries`) or Nx module tags, not just documentation:

```
apps → pages → widgets → processes → features → entities → packages (ui, api-client, …)
```

- Imports only go downward. Two modules on the same layer never import each other.
- Code outside a module imports only its `index.ts`, never its internals.
- Modules communicate through an **event bus** or shared entity state, not direct imports. This is the frontend version of the backend's domain events.
- `packages/ui` has no business logic and no API calls.

### What else complex projects need

| Concern | Recommendation |
|---|---|
| Server state | TanStack Query, with query keys owned by each module's `api/` |
| Client state | Zustand per module; avoid one global store |
| API contract | Types generated from the backend in CI, so a changed contract breaks the build |
| Permissions | Policies in `packages/auth`, applied through `<Can>` and route guards |
| Feature flags | Checks live in each module's `_critical/flags.ts` |
| Build speed | Turborepo/Nx caching plus the "affected" commands, so only changed packages build and test |
| Code ownership | A `CODEOWNERS` file set per feature folder |
| Scaffolding | A generator in `tooling/generators` that creates a new module with this exact structure |
| Very large orgs | Module Federation or micro-frontends: each `features/*` becomes an independently deployed remote. Only use this when separate teams need separate deploys. |

