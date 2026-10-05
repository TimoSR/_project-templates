---
name: database-design
description: Applies the FlexFunding database standard for EF Core on SQL Server and PostgreSQL - logic placement, column types and enums, keys, multi-tenancy and row-level security, roles, indexes, queries, pagination and migration review. Use when adding or changing a table, entity, column, enum, index, view, DbContext, OnModelCreating or EF Core migration, designing tenant isolation, writing EF Core or SQL queries, adding a list endpoint or pagination, setting up database roles or grants, or reviewing a migration, even if the database is never mentioned. Also when the user mentions RLS, tenant_id, UUIDv7, stored procedures, triggers, SELECT *, N+1, AsNoTracking, compiled queries, query caching, keyset pagination or dotnet ef migrations. Covers a module's infrastructure/ folder (postgres, cache) and _tools/sql. Not for test database setup (tests-as-documentation).
---

# Database Design

The database stores data, enforces integrity and isolates tenants. Business logic lives in the application, where it is versioned, tested and reviewed. Every rule below applies to both providers; [the provider map](#provider-map) gives the SQL Server and PostgreSQL form.

## Scope: new code follows the standard, legacy gets flagged

This repo is SQL Server only (no Npgsql reference), so the PostgreSQL forms don't apply here yet. Most existing tables predate this standard (`int` keys, enums as `int`). Tenancy and RLS are target-only: no table has `TenantId` and there is no `Tenants` table yet.

* New table, column, enum, index, view or DbContext → follow this skill.
* Touching an existing table → match its current convention, and name the gap in your reply instead of migrating it:

```
Note: Factorings.Status is stored as a string but has no CHECK constraint (database-design).
Not changed here; adding it is a separate migration.
```

* Known repo-wide gap: migrations run at app startup (`TryMigrateDatabase` in `FF.Api/Program.cs` calls `DatabaseMigrator`, then `Migrate<Name>Feature` per feature module). That is the current deploy path, and `soft-extract-feature` relies on it. Keep using it, don't add a new mechanism, and flag it when relevant. Target: bundles applied in CI/CD by the migrator role.

## Core principles

| Rule | ✗ | ✓ |
|---|---|---|
| No business logic in the database | `CREATE PROCEDURE ApproveLoan` with eligibility rules | Rules in an FF.App command; the database checks `NOT NULL`, `UNIQUE`, `CHECK`, foreign keys |
| No hidden side effects: editing a row by hand must not trigger anything | Trigger that inserts into `AuditLog` or calls out | The app writes an outbox row in the same transaction, a dispatcher processes it (`FactoringOutboxMessage` + `FactoringOutboxDispatcher`) |
| Data is readable without the source code | `Status = 3` | `Status = 'Cancelled'` with a CHECK listing the allowed values |
| Proper types | money as `float`, dates as `nvarchar` | see the provider map |
| Clear names, no abbreviations | `cust_amt` | `CustomerAmount` / `customer_amount` |

* Allowed exception: a purely technical trigger (set `UpdatedAtUtc`), documented in the migration that creates it.

## Provider map

| Concept | PostgreSQL | SQL Server (this repo) |
|---|---|---|
| Primary key | `uuid`; Npgsql 9+ generates UUIDv7 for `Guid` keys by default, or `Guid.CreateVersion7()` | `uniqueidentifier`; EF's default `SequentialGuidValueGenerator` for `Guid` keys. **Never `Guid.CreateVersion7()`**: SQL Server sorts `uniqueidentifier` by its last bytes first, so v7 fragments the index like a random v4 |
| Point in time | `timestamptz` | `datetime2` holding UTC with a `Utc` suffix (`CreatedAtUtc`, repo convention) or `datetimeoffset` |
| Date only | `date` | `date` |
| Money | `numeric(p, s)` | `decimal(p, s)`; set `HasPrecision(p, s)` explicitly |
| Flag | `boolean` | `bit` |
| Naming | `snake_case` (`UseSnakeCaseNamingConvention()` from EFCore.NamingConventions) | PascalCase, EF default, matches existing tables |
| Organize by area | schema per area (`billing`, `identity`, `audit`, `reporting`) | schema per area or feature (`factoring`) |
| Partial index | `HasFilter("deleted_at IS NULL")` | `HasFilter("[IsDeleted] = 0")` |
| Build index without blocking writes | `IsCreatedConcurrently()` | `IsCreatedOnline()` (Enterprise or Azure SQL) |
| Tenant per unit of work | `set_config('app.tenant_id', @id, true)` inside the transaction | `sp_set_session_context N'TenantId', @id, @read_only = 1` on every connection open |
| RLS | `ENABLE` + `FORCE ROW LEVEL SECURITY` + `CREATE POLICY` | predicate function + `CREATE SECURITY POLICY`; already applies to `dbo` and the table owner |
| Views keep RLS | `WITH (security_invoker = true)` (PostgreSQL 15+) | automatic: the policy sits on the base table |
| Query plan | `EXPLAIN (ANALYZE, BUFFERS)` | `SET STATISTICS IO, TIME ON` + actual execution plan |
| Unused indexes | `pg_stat_user_indexes` where `idx_scan = 0` | `sys.dm_db_index_usage_stats` |
| Statement timeout | `ALTER ROLE app_user SET statement_timeout = '30s'` | no per-login timeout; `CommandTimeout(30)` in `UseSqlServer` options |

Tenancy, RLS scripts, the tenant interceptor, roles and grants: [tenancy-and-security.md](tenancy-and-security.md).

## Keys

* Every table: GUID primary key per the provider map, generated in the app before the insert, safe to expose.
* `bigint` identity only for internal lookup tables: it is guessable, leaks row counts and clashes when merging databases.
* Natural keys (email, loan number) get a `UNIQUE` index, never the primary key.
* Tenant-owned table: `TenantId` non-null `Guid` with a foreign key to `Tenants`.

```csharp
// ✗ natural key as primary key
builder.HasKey(order => order.OrderNumber);

// ✓ Guid key (value generated by EF before the insert), natural key unique
builder.HasKey(order => order.Id);
builder.HasIndex(order => order.OrderNumber).IsUnique();
```

## Enums as strings

Store the name, cap the length, and generate the CHECK from the enum so it can't drift. Adding an enum member then produces a migration that updates the constraint.

```csharp
builder.Property(order => order.Status)
    .HasConversion<string>()
    .HasMaxLength(50);

string allowedStatuses = "'" + string.Join("', '", Enum.GetNames<OrderStatus>()) + "'";
builder.ToTable(table =>
{
    table.HasCheckConstraint("CK_Orders_Status", $"[Status] IN ({allowedStatuses})");
});
```

* PostgreSQL: `"status IN (...)"` with the snake_case column name.

## Indexing

Index the queries we actually run.

* Composite indexes on tenant-owned tables start with `TenantId`: RLS adds it to every query.

```csharp
builder.HasIndex(order => new { order.TenantId, order.CreatedAtUtc })
    .IsDescending(false, true);
```

* Equality columns first, then range or sort columns.
* Foreign keys: EF creates a single-column index per FK by convention, which hand-written SQL does not. Check the migration has it; on tenant-owned tables prefer `(TenantId, ForeignKeyId)`.
* Partial/filtered index for a common filter (soft delete), per the provider map.
* Large live table → build the index online/concurrently.
* Measure the plan before and after; drop indexes the usage stats show are never read. Every index slows writes.

## Querying

Fetch only the rows and columns the caller needs, paginate every list, let every query be cancelled.

### SQL first, then EF Core

Write the query in SQL first, then the LINQ that produces it, then decide tracking, compiled queries and caching.

```
1. SQL     SELECT Id, Status FROM Orders WHERE CustomerId = @customerId ORDER BY CreatedAtUtc DESC
2. LINQ    db.Orders.Where(...).OrderByDescending(...).Select(order => new OrderDto { ... })
3. Verify  query.ToQueryString() matches step 1 (no extra columns, joins or client evaluation)
4. Decide  tracking → compiled query → caching
```

| Decision | Default | Choose otherwise when |
|---|---|---|
| Tracking | `.AsNoTracking()` for reads; tracked only when loading to change and `SaveChangesAsync` | no-tracking query with `.Include()` repeats the same entity → `.AsNoTrackingWithIdentityResolution()` |
| Compiled queries | none: EF already caches the translated plan per query shape | a measured hot path with a fixed shape → `EF.CompileAsyncQuery` in a `static readonly` field |
| Caching | none: the database is the source of truth | read-heavy, rarely-changing data (lookups, settings) → Redis/`IMemoryCache` with an explicit expiry and invalidation on write |

```csharp
private static readonly Func<FFCoreDbContext, Guid, CancellationToken, Task<OrderDto?>> GetOrderById =
    EF.CompileAsyncQuery((FFCoreDbContext db, Guid orderId, CancellationToken cancellationToken) =>
        db.Orders
            .AsNoTracking()
            .Where(order => order.Id == orderId)
            .Select(order => new OrderDto { Id = order.Id, Status = order.Status })
            .FirstOrDefault());
```

* Cache keys on tenant-owned data include `TenantId`; keys and values hold no sensitive data (security).

| Rule | ✗ | ✓ |
|---|---|---|
| Project, don't load entities | `await db.Orders.ToListAsync()` then map | `.Select(order => new OrderDto { Id = order.Id, Status = order.Status })` |
| Read-only → no tracking | tracked read | `.AsNoTracking()` |
| No N+1 | `foreach` loading each customer | one projection or `.Include()` |
| Filter and aggregate in SQL | `.ToList().Where(...)` | `.Where(...).SumAsync(...)` |
| Pass the request's token | `ToListAsync()` | `ToListAsync(cancellationToken)`, `SaveChangesAsync(cancellationToken)` |
| No `SELECT *` in raw SQL | `SELECT * FROM Orders` | named columns |

* GraphQL: `[UseProjection]` already selects only requested fields. A resolver takes `CancellationToken cancellationToken` as a parameter and Hot Chocolate passes the request-aborted token.
* Views for reporting, support and read-only roles leave out sensitive columns: password hashes, tokens, personal IDs (CPR), bank and card details. Grant the view, not the base table.

### Pagination

Every list endpoint is paginated with a server-side maximum page size.

| Method | Query | Use for |
|---|---|---|
| Keyset (default) | `WHERE (CreatedAtUtc, Id) < (@lastCreatedAtUtc, @lastId) ORDER BY CreatedAtUtc DESC, Id DESC` + page size | feeds, infinite scroll, large tables; constant speed on any page |
| Offset | `ORDER BY ... OFFSET 500 ROWS FETCH NEXT 50 ROWS ONLY` | small tables or UIs that need page numbers; slows as the offset grows |

* `ORDER BY` is always unique: add `Id` as the tie-breaker, or rows repeat or vanish between pages.
* SQL Server and EF LINQ have no row-value comparison; write keyset as `CreatedAtUtc < @last OR (CreatedAtUtc = @last AND Id < @lastId)`.
* Keyset on `Guid`: in LINQ write `order.Id.CompareTo(lastId) < 0`, and confirm with `ToQueryString()` that it became `[o].[Id] < @lastId`. SQL Server orders `uniqueidentifier` differently from C#, so compare cursors only in SQL, never in memory, and test against SQL Server, not SQLite.
* GraphQL lists use `[UsePaging]`; set `MaxPageSize` when the default (50) doesn't fit.

## Migrations

Review every generated migration before committing it, C# and SQL.

```bash
# from API/FF-API/; feature context (migrations in FF.Api)
dotnet ef migrations script <PreviousMigration> <NewMigration> --context <Name>DbContext --project FF.Api
# FFCoreDbContext (migrations in FF.Core, same flags as scripts/add-migration.sh)
dotnet ef migrations script <PreviousMigration> <NewMigration> --context FFCoreDbContext --project FF.Core --startup-project FF.Api
```

| EF gets it wrong or can't generate it | Do |
|---|---|
| Rename generated as drop + add (deletes the data) | Replace with `RenameColumn` / `RenameTable` |
| RLS policies, `FORCE ROW LEVEL SECURITY`, security policies, grants, views | `migrationBuilder.Sql(...)`, with the reverse in `Down` |
| Backfills and transforms | Explicit SQL in the migration, reviewed like code |

* Breaking change in releases: add the new column → deploy → backfill → switch reads → drop the old column in a later release.
* CHECK constraints, filtered indexes and online indexes are generated from the model (`HasCheckConstraint`, `HasFilter`, `IsCreatedOnline`); no raw SQL needed.

## Checklist for a new table or feature

Copy into the reply or PR and tick off:

```
- [ ] Primary key is a GUID generated per the provider map (SQL Server: EF sequential, not CreateVersion7)
- [ ] TenantId non-null with a foreign key, if tenant-owned
- [ ] RLS enabled (PostgreSQL: and forced) with a tenant policy, and a test proving tenant B can't see tenant A
- [ ] Enums stored as strings with a CHECK built from Enum.GetNames
- [ ] Types: UTC datetime2/timestamptz, decimal with explicit precision, bit/boolean
- [ ] No business-logic procedures, no side-effect triggers; side effects go through an outbox
- [ ] Indexes start with TenantId; foreign keys indexed
- [ ] Queries project needed columns, AsNoTracking for reads, pass a CancellationToken
- [ ] Lists paginated with a unique ORDER BY and a max page size
- [ ] Reporting views leave out sensitive columns
- [ ] Migration reviewed, including the generated SQL script; Down reverses raw SQL
- [ ] Grants given to roles, not to people's logins
- [ ] Gaps in touched legacy tables named in the reply
```

## Sources

* PostgreSQL: [docs](https://www.postgresql.org/docs/current/), [row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
* SQL Server: [T-SQL reference](https://learn.microsoft.com/sql/t-sql/language-reference), [row-level security](https://learn.microsoft.com/sql/relational-databases/security/row-level-security)
* EF Core: [managing migrations](https://learn.microsoft.com/ef/core/managing-schemas/migrations/managing), [SQL Server value generation](https://learn.microsoft.com/ef/core/providers/sql-server/value-generation)
* Tenancy decision: Neon, [Multi-tenancy and database-per-user design in Postgres](https://neon.com/blog/multi-tenancy-and-database-per-user-design-in-postgres)
