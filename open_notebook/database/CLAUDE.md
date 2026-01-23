# Database Module

Supabase abstraction layer providing repository pattern for CRUD operations and migration management.

## Purpose

Encapsulates all database interactions: connection pooling, async CRUD operations, relationship management, and schema migrations. Provides clean interface for domain models and API endpoints to interact with Supabase without direct query knowledge.

## Architecture Overview

Two-tier system:
1. **Repository Layer** (repository.py): Raw async CRUD operations on Supabase via supabase client
2. **Migration Layer** (async_migrate.py): Schema versioning and migration execution

Both leverage connection context manager for lifecycle management and automatic cleanup.

## Component Catalog

### repository.py

**Connection Management**
- `get_supabase_client()`: Creates client using `SUPABASE_URL` and `SUPABASE_ANON_KEY` environment variables

**Query Operations**
- `repo_query(table, select, filters)`: Execute SELECT queries on Supabase tables; returns list of dicts
- `repo_create(table, data)`: Insert record; auto-adds `created`/`updated` timestamps
- `repo_update(table, id, data)`: Update existing record by table+id; auto-adds `updated` timestamp
- `repo_upsert(table, id_column, data)`: UPSERT operation for create-or-update
- `repo_delete(table, id)`: Delete record by table and id
- `repo_relate(from_table, from_id, relationship, to_table, to_id, data)`: Create relationship in join table
- `repo_unrelate(from_table, from_id, relationship, to_table, to_id)`: Delete relationship from join table
- `repo_count(table, filters)`: Execute COUNT queries on Supabase tables
- `repo_vector_search(table, column, query_embedding, similarity_threshold, limit)`: Perform vector similarity search using pgvector

**Utilities**
- Standard CRUD operations using Supabase Python client

### async_migrate.py

**Migration Classes**
- `AsyncMigrationManager`: Main orchestrator for Supabase migrations
  - `get_current_version()`: Query max version from migration_versions table
  - `needs_migration()`: Boolean check for pending migrations
  - `run_migration_up()`: Run all pending migrations with logging

**Version Tracking**
- Standard migration version tracking using Supabase tables
- Designed to work with Supabase migration system

### migrate.py

**Backward Compatibility**
- `MigrationManager`: Sync wrapper around AsyncMigrationManager
  - `get_current_version()`: Wraps async call with asyncio.run()
  - `needs_migration` property: Checks if migration pending
  - `run_migration_up()`: Execute migrations synchronously

## Common Patterns

- **Async-first design**: All operations async via Supabase client
- **Connection reuse**: Supabase client manages connection pooling automatically
- **Auto-timestamping**: repo_create() and repo_update() auto-set `created`/`updated` fields
- **Error resilience**: Proper exception handling with logging
- **Standard SQL operations**: Using standard table-based operations instead of graph queries
- **Graceful degradation**: Migration queries catch exceptions and handle missing tables appropriately

## Key Dependencies

- `supabase`: Supabase Python client
- `loguru`: Logging with context (debug/error/success levels)
- Python stdlib: `os` (env vars), `datetime` (timestamps)

## Important Quirks & Gotchas

- **Supabase connection management**: Supabase client handles connection pooling automatically
- **Table-based relationships**: Relationships managed via join tables instead of native graph relationships
- **Standard SQL operations**: Using standard SQL
- **Foreign key relationships**: Standard PostgreSQL foreign key constraints instead of graph edges
- **Timestamp handling**: Standard datetime field handling with ISO format support

## How to Extend

1. **Add new CRUD operation**: Follow repo_* pattern using Supabase client methods
2. **Add migration**: Create SQL migration files using Supabase CLI; update AsyncMigrationManager to handle new schema changes
3. **Change timestamp behavior**: Modify repo_create()/repo_update() to not auto-set `updated` field if caller-provided
4. **Add vector search functionality**: Implement pgvector-based similarity search functions

## Integration Points

- **API startup** (api/main.py): FastAPI lifespan handler calls AsyncMigrationManager.run_migration_up() on server start
- **Domain models** (domain/*.py): All models call repo_* functions for persistence
- **Commands** (commands/*.py): Background jobs use repo_* for state updates
- **Job Queue** (database/job_queue.py): Supabase-based job queue for background operations

## Usage Example

```python
from open_notebook.database.repository import repo_create, repo_query, repo_update

# Create
record = await repo_create("notebooks", {"title": "Research"})

# Query
results = await repo_query("notebooks", filters={"title": "Research"})

# Update
await repo_update_int_id("notebooks", record["id"], {"title": "Updated Research"})
```
