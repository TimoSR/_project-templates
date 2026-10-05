---
paths:
  - "API/FF-API/FF.Core/**/*.cs"
  - "API/FF-API/FF.App/**/*.cs"
  - "API/FF-API/FF.Api/Features/**/*.cs"
  - "API/**/*.sql"
---

# Persistence

This repository uses SQL Server. New schema follows these standards; narrowly edited legacy tables keep their current key/enum conventions. Flag gaps without unsolicited migrations. PostgreSQL, tenancy/RLS, and migrator roles are conditional target designs, not prerequisites for ordinary work.

- Business rules live in application/domain code. Database constraints enforce integrity. No business procedures or hidden side-effect triggers; a documented purely technical timestamp trigger is allowed.
- New tables use app-generated GUID keys with SQL Server/EF sequential generation, not `Guid.CreateVersion7`. Natural keys get unique indexes; internal lookup tables may use bigint identities.
- Use UTC datetime2 (Utc suffix) or datetimeoffset, date for date-only, decimal with explicit precision for money, bit for flags. New enums store names with bounded length and a generated CHECK.
- Index real query shapes: equality before range/sort, verify FK indexes, filtered indexes for common filters. Add tenant-leading indexes only when an explicitly designed tenant model exists.
- Project only needed columns; filter/aggregate in SQL, avoid N+1, use AsNoTracking for reads, and pass CancellationToken. GraphQL projection/paging conventions remain valid.
- For non-trivial EF queries, sketch SQL first and inspect ToQueryString. Compiled queries/caching need a measured reason; caching needs expiry/invalidation and safe owner scope.
- Paginate list endpoints with bounded size and unique ordering; keyset is the default for large feeds, offset for small/page-number UIs. Compare GUID keyset cursors in SQL, not C# memory.
- Review generated migrations and SQL. Replace destructive drop/add renames with rename operations; review backfills and reverse raw SQL in Down. Expand/backfill/switch/contract breaking schema changes across releases.
- Preserve the current startup migration mechanism unless deployment changes are requested. Do not introduce RLS, new roles, or a migrator pipeline as incidental cleanup.

Example: `decimal` + `HasPrecision` for an amount; a touched legacy int key remains int.
Design/provider recipes: `.claude/skills/database-design/guide.md` and `tenancy-and-security.md`.
