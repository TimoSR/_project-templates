# Tenancy and Security

Tenant isolation, row-level security, tenant session context, roles and grants, for PostgreSQL and SQL Server.

## Contents
1. Choosing the tenancy model
2. Tenant and user context per unit of work
3. Row-level security scripts
4. Roles, grants and schemas
5. Testing isolation

## 1. Choosing the tenancy model

Default: shared schema, `TenantId` on every tenant-owned table, enforced by RLS. A missing `WHERE TenantId = ...` in app code then can't leak data.

| Model | Isolation | Cost and operations | Use |
|---|---|---|---|
| Shared schema + RLS | Logical, enforced by the database | One database to migrate, monitor, back up | Default for all tenants |
| Database per tenant | Full, nothing colocated | Every migration runs once per tenant | Contractual or legal isolation, data residency, a noisy neighbour |
| Schema per tenant | Weak: same database, copied schema | N copies of every table and migration | Never |

* Schemas organize by area (`billing`, `identity`, `audit`, `reporting`), never by tenant.

## 2. Tenant and user context per unit of work

Every request carries a tenant ID and a user ID. The app writes them into the database session in one place (an EF interceptor), never per query. No tenant set → the policy matches nothing → zero rows. Failing closed is the point.

| | PostgreSQL | SQL Server |
|---|---|---|
| Call | `set_config('app.tenant_id', @tenantId, true)` | `sp_set_session_context N'TenantId', @tenantId, @read_only = 1` |
| Lifetime | the transaction (`true` = local) | the physical session until the pool resets it on reuse |
| Set it in | `DbTransactionInterceptor.TransactionStarted(Async)` | `DbConnectionInterceptor.ConnectionOpened(Async)` |
| Why there | poolers in transaction mode (PgBouncer, Neon's pooled endpoint) hand the same server connection to other clients between transactions, so a session-level value leaks | the pool clears session context before reuse, so it must be set again on every open; `@read_only = 1` stops later code changing it |
| Consequence | every unit of work, reads included, runs in an explicit transaction; a query outside one sees zero rows | none; EF opens and closes per operation and the interceptor runs each time |

* `app.user_id` / `UserId` goes in the same call; it can feed `CreatedBy` / `UpdatedBy` and audit rows.
* Always parameters, never string-built SQL.

SQL Server interceptor sketch (register with `options.AddInterceptors(...)` in `AddDbContext`, scoped with the request):

```csharp
public sealed class TenantSessionContextInterceptor : DbConnectionInterceptor
{
    private const string SetTenantSql =
        "EXEC sp_set_session_context @key = N'TenantId', @value = @tenantId, @read_only = 1;";

    private readonly ITenantContext _tenantContext;

    public TenantSessionContextInterceptor(ITenantContext tenantContext)
    {
        _tenantContext = tenantContext;
    }

    public override async Task ConnectionOpenedAsync(DbConnection connection, ConnectionEndEventData eventData, CancellationToken cancellationToken = default)
    {
        if (_tenantContext.TenantId is null) { return; } // fail closed: no tenant, no rows

        await using DbCommand command = connection.CreateCommand();
        command.CommandText = SetTenantSql;
        DbParameter tenantParameter = command.CreateParameter();
        tenantParameter.ParameterName = "@tenantId";
        tenantParameter.Value = _tenantContext.TenantId.Value;
        command.Parameters.Add(tenantParameter);
        await command.ExecuteNonQueryAsync(cancellationToken);
    }

    // Override ConnectionOpened (sync) the same way, or sync paths run without a tenant.
}
```

## 3. Row-level security scripts

Apply through `migrationBuilder.Sql(...)`, one call per batch, with the reverse in `Down`.

**PostgreSQL**

```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders FORCE ROW LEVEL SECURITY; -- also applies to the table owner

CREATE POLICY tenant_isolation ON orders
  USING      (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
```

* `USING` filters reads, updates and deletes; `WITH CHECK` stops writing a row into another tenant.
* Superusers and `BYPASSRLS` roles skip policies. The app never connects as one.

**SQL Server**

```sql
CREATE FUNCTION security.TenantPredicate(@TenantId uniqueidentifier)
    RETURNS TABLE
    WITH SCHEMABINDING
AS
    RETURN SELECT 1 AS IsVisible
    WHERE @TenantId = CAST(SESSION_CONTEXT(N'TenantId') AS uniqueidentifier)
       OR IS_MEMBER(N'rls_admin') = 1;
```

```sql
CREATE SECURITY POLICY security.TenantIsolation
    ADD FILTER PREDICATE security.TenantPredicate(TenantId) ON dbo.Orders,
    ADD BLOCK PREDICATE security.TenantPredicate(TenantId) ON dbo.Orders AFTER INSERT,
    ADD BLOCK PREDICATE security.TenantPredicate(TenantId) ON dbo.Orders AFTER UPDATE
    WITH (STATE = ON);
```

* FILTER = PostgreSQL `USING`; BLOCK `AFTER INSERT/UPDATE` = `WITH CHECK`.
* Applies to `dbo`, `db_owner` and the table owner too; there is no `FORCE` step and no `BYPASSRLS`. The only bypass is the `rls_admin` clause in the predicate.
* Next table: `ALTER SECURITY POLICY security.TenantIsolation ADD FILTER PREDICATE ... ON dbo.Invoices, ADD BLOCK PREDICATE ...`.
* `SCHEMABINDING` blocks altering a column the predicate uses: a later migration that changes `TenantId` drops the predicate first and re-adds it after.

## 4. Roles, grants and schemas

Each kind of access gets its own role with the least privilege it needs. Nobody, the app included, connects as `postgres` / `sa` in normal operation.

| Role | Used by | Can | Cannot |
|---|---|---|---|
| `migrator` | Migrations in CI/CD | Own tables, run DDL | Serve app traffic |
| `app_user` | The application | `SELECT`, `INSERT`, `UPDATE`, `DELETE` on app tables | DDL, bypass RLS, read other tenants |
| `readonly` | Reporting, support, developers | `SELECT` on views without sensitive columns | Write anything |
| `rls_admin` | Manual fixes by named people | Bypass RLS for maintenance | Be used by any service |

* Grant permissions to roles, then add logins to roles. Never grant to a person's login directly.
* Schemas make grants simple: `readonly` gets the `reporting` schema only.

**PostgreSQL**

```sql
CREATE ROLE app_user NOLOGIN;
GRANT USAGE ON SCHEMA billing TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA billing TO app_user;
ALTER DEFAULT PRIVILEGES FOR ROLE migrator IN SCHEMA billing
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user; -- tables migrator creates later

CREATE ROLE api_service LOGIN;
GRANT app_user TO api_service;
ALTER ROLE api_service SET statement_timeout = '30s'; -- settings apply to the login role, not inherited

REVOKE CREATE ON SCHEMA public FROM PUBLIC; -- already the default from PostgreSQL 15
```

**SQL Server**

```sql
CREATE ROLE app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::billing TO app_user; -- covers future tables

CREATE ROLE readonly;
GRANT SELECT ON SCHEMA::reporting TO readonly;

CREATE ROLE rls_admin; -- members are named people; referenced by the RLS predicate

CREATE USER [api-managed-identity] FROM EXTERNAL PROVIDER; -- Azure SQL
ALTER ROLE app_user ADD MEMBER [api-managed-identity];
```

* The app's user is never in `db_owner` or `db_ddladmin`.

## 5. Testing isolation

RLS is a money-and-privacy rule: cover it with an infrastructure test per `tests-as-documentation` (Testcontainers SQL Server, never SQLite, which has no RLS).

```
Arrange  as the migrator: insert an order for tenant A and one for tenant B
Act      as a user in app_user with tenant A in the session context
Assert   only tenant A's order is returned
         inserting an order with TenantId = B fails (block predicate)
         a session with no tenant returns zero rows
```

* Run the Act as an `app_user` member (`CREATE USER app_test WITHOUT LOGIN` + `EXECUTE AS USER = 'app_test'`), never as `sa`: production never connects as sysadmin, so a green test as `sa` proves nothing about the app path.
