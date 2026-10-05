---
paths:
  - "src/features/**/infrastructure/**"
  - "src/_config/infrastructure/databases/**"
  - "_tools/sql/**"
  - "**/*.sql"
---

# Persistence

The template's database is PostgreSQL (`infrastructure/postgress/`, `src/_config/infrastructure/databases/supabase.json`). Use the PostgreSQL column of the `database-design` provider map; its SQL Server column and FlexFunding notes (`FF.*` paths, startup migrator) don't apply here. Tenancy/RLS and database roles are opt-in target designs, not prerequisites for ordinary work.

- Each module owns its stores in `infrastructure/postgress/<store>/` and `infrastructure/cache/<cache>/`. Other modules reach that data through the feature's `_contracts/`, never through the DbContext or tables.
- Business rules live in `domain/` and `application/`. Database constraints enforce integrity. No business procedures or hidden side-effect triggers; a documented purely technical timestamp trigger is allowed.
- New tables use app-generated UUIDv7 keys (Npgsql 9+ default for `Guid` keys, or `Guid.CreateVersion7()`). Natural keys get unique indexes; internal lookup tables may use bigint identities.
- `timestamptz` for points in time, `date` for date-only, `numeric(p, s)` with explicit precision for money, `boolean` for flags, `snake_case` names, one schema per feature. Enums store names as bounded text with a generated CHECK.
- Index real query shapes: equality before range/sort, verify FK indexes, partial indexes for common filters. Add tenant-leading indexes only when an explicitly designed tenant model exists.
- Project only needed columns; filter/aggregate in SQL, avoid N+1, use AsNoTracking for reads, and pass CancellationToken.
- For non-trivial EF queries, sketch SQL first and inspect ToQueryString. Compiled queries/caching need a measured reason; caching needs expiry/invalidation and safe owner scope.
- Paginate list endpoints with bounded size and unique ordering; keyset is the default for large feeds, offset for small/page-number UIs.
- Review generated migrations and SQL. Replace destructive drop/add renames with rename operations; review backfills and reverse raw SQL in Down. Expand/backfill/switch/contract breaking schema changes across releases.
- No migration mechanism exists yet. The first module that needs one picks it (migrate at startup vs a bundle applied in CI), states the trade-off, and records the choice here. Do not introduce RLS, new roles, or a migrator pipeline as incidental cleanup.

Example: `amount numeric(19, 4)` + `HasPrecision(19, 4)`; `status text CHECK (status IN ('Draft', 'Issued', 'Paid'))`.
Design/provider recipes: `.claude/skills/database-design/SKILL.md` and `tenancy-and-security.md`.
