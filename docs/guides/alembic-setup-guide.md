# Alembic Migration Setup Guide

Step-by-step guide to set up Alembic as the single source of truth for database migrations in a FastAPI + async SQLAlchemy + PostgreSQL project, with CI/CD integration via GitHub Actions.

**Prerequisites:**
- FastAPI app with async SQLAlchemy and `DeclarativeBase`
- PostgreSQL database (with schema isolation)
- Docker + docker-compose deployment
- GitHub Actions CI/CD

---

## Step 1: Add Alembic dependency

```bash
# Add to requirements.txt (after sqlalchemy/asyncpg)
alembic>=1.13.0
```

Install:
```bash
uv pip install -r requirements.txt
```

## Step 2: Initialize Alembic (if not already done)

```bash
cd backend
alembic init alembic
```

This creates:
- `alembic.ini` — config file
- `alembic/env.py` — migration runner
- `alembic/versions/` — migration files
- `alembic/script.py.mako` — template for new migrations

## Step 3: Configure alembic/env.py for async + schema

Replace the default `env.py` with an async-aware version that:
1. Imports your app's models and settings
2. Overrides the database URL from your app settings
3. Creates the schema before running migrations
4. Uses `async_engine_from_config` for async support

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import your app's models so autogenerate can detect them
import app.models  # noqa: F401
from app.database import Base, settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url from app settings
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema=settings.DB_SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema=settings.DB_SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine, ensure schema exists, then run migrations."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Create schema before migrations (requires commit before migration transaction)
        await connection.execute(
            text(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}")
        )
        await connection.commit()
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Key points:**
- `version_table_schema=settings.DB_SCHEMA` — stores `alembic_version` table in your schema, not public
- `include_schemas=True` — required for autogenerate to detect schema-qualified tables
- `CREATE SCHEMA IF NOT EXISTS` + `commit()` — schema must exist before migration transaction begins
- Schema name comes from `settings.DB_SCHEMA` (not hardcoded)

## Step 4: Write the initial migration

If your database already has tables (created by `create_all()`), write an idempotent initial migration that skips existing tables:

```bash
# Delete any partial/unused migration files first
rm backend/alembic/versions/*.py  # if needed
```

Create `backend/alembic/versions/0001_initial_schema.py`:

```python
"""initial schema - all tables

Revision ID: 0001
Revises:
Create Date: YYYY-MM-DD
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "your_schema_name"


def _table_exists(table_name: str) -> bool:
    """Check if a table already exists in the schema."""
    bind = op.get_bind()
    insp = inspect(bind)
    return table_name in insp.get_table_names(schema=SCHEMA)


def upgrade() -> None:
    """Create all tables (skips any that already exist)."""
    if not _table_exists("your_table"):
        op.create_table(
            "your_table",
            sa.Column("id", sa.String(36), nullable=False),
            # ... all columns ...
            sa.PrimaryKeyConstraint("id"),
            schema=SCHEMA,
        )

    # For tables with foreign keys to other schema-qualified tables:
    if not _table_exists("child_table"):
        op.create_table(
            "child_table",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("parent_id", sa.String(36), nullable=False),
            sa.ForeignKeyConstraint(
                ["parent_id"], ["your_schema.parent_table.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            schema=SCHEMA,
        )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("child_table", schema=SCHEMA)
    op.drop_table("your_table", schema=SCHEMA)
```

**Why idempotent?** If your existing database already has tables (from `create_all()`), `alembic upgrade head` will skip them instead of failing. No manual `alembic stamp` needed. Fresh databases (like CI) will create everything from scratch.

**FK pattern:** Use `sa.ForeignKeyConstraint()` with fully qualified `schema.table.column` references. This is the standard Alembic pattern for schema-qualified tables and avoids autogenerate drift.

## Step 5: Remove create_all() from FastAPI lifespan

Before (managing tables on startup):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}"))
        await conn.run_sync(Base.metadata.create_all)
    yield
```

After (Alembic owns everything):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
```

Remove unused imports (`Base`, `engine`, `sqlalchemy`) from the file too.

**Note:** Tests typically use their own in-memory SQLite with `create_all()` in fixtures — this is fine and unaffected.

## Step 6: Create the CI migration validation job

Add a `migrate` job to your `ci.yml` that runs migrations against a fresh PostgreSQL:

```yaml
name: CI

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main, dev]
  workflow_call:
  workflow_dispatch:

jobs:
  # ... your existing lint, test jobs ...

  migrate:
    name: Validate Migrations
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install --no-cache-dir -r requirements.txt
      - name: Run migrations against fresh DB
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/testdb?ssl=disable
          DB_SCHEMA: your_schema_name
          # Add any required env vars that your Settings class needs:
          JWT_SECRET: test-secret-for-ci
          INVITE_CODE: test-invite
        run: alembic upgrade head
```

**Important:** Your `Settings` class may have required fields with no defaults (like `JWT_SECRET`). The CI job must provide dummy values for these, or the import will fail before migrations even run.

## Step 7: Create the standalone migrate workflow

Create `.github/workflows/migrate.yml` — a workflow that can be called by deploy or triggered manually:

```yaml
name: Migrate

on:
  workflow_call:
    inputs:
      environment:
        description: "Target environment"
        required: true
        type: string
  workflow_dispatch:
    inputs:
      environment:
        description: "Target environment"
        required: true
        default: "dev"
        type: choice
        options:
          - dev
          - prod

jobs:
  migrate:
    name: Run Database Migrations
    runs-on: [self-hosted, your-runner]
    environment: ${{ inputs.environment }}
    env:
      ENV: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@v4

      - name: Create .env file
        run: |
          cat <<EOF > .env
          POSTGRES_USER=${{ vars.POSTGRES_USER }}
          POSTGRES_PASSWORD=${{ secrets.POSTGRES_PASSWORD }}
          POSTGRES_DB=${{ vars.POSTGRES_DB }}
          DB_SCHEMA=${{ vars.DB_SCHEMA }}
          JWT_SECRET=${{ secrets.JWT_SECRET }}
          INVITE_CODE=${{ vars.INVITE_CODE }}
          EOF

      - name: Build backend image
        run: docker compose -p yourapp-${ENV} build backend

      - name: Run alembic upgrade head
        run: docker compose -p yourapp-${ENV} run --rm backend alembic upgrade head

      - name: Cleanup .env
        if: always()
        run: rm -f .env
```

## Step 8: Update the deploy workflow

Update `.github/workflows/deploy.yml` to call migrate before deploying:

```yaml
name: Deploy

on:
  push:
    branches: [main, dev]
  workflow_dispatch:
    inputs:
      environment:
        description: "Target environment"
        required: true
        default: "dev"
        type: choice
        options:
          - dev
          - prod

jobs:
  ci:
    uses: ./.github/workflows/ci.yml

  migrate:
    needs: ci
    uses: ./.github/workflows/migrate.yml
    with:
      environment: ${{ inputs.environment || (github.ref == 'refs/heads/main' && 'prod' || 'dev') }}
    secrets: inherit

  deploy:
    name: Deploy
    needs: migrate
    runs-on: [self-hosted, your-runner]
    environment: ${{ inputs.environment || (github.ref == 'refs/heads/main' && 'prod' || 'dev') }}
    env:
      ENV: ${{ inputs.environment || (github.ref == 'refs/heads/main' && 'prod' || 'dev') }}
    steps:
      - uses: actions/checkout@v4

      - name: Create .env file
        run: |
          cat <<EOF > .env
          # ... your env vars ...
          EOF

      - name: Stop existing services
        run: docker compose -p yourapp-${ENV} down

      - name: Build and start services
        run: docker compose -p yourapp-${ENV} up --build -d

      - name: Cleanup .env
        if: always()
        run: rm -f .env
```

**Pipeline order:** CI → Migrate → Deploy

**`secrets: inherit`** is required so the called workflow can access GitHub secrets.

## Day-to-Day Developer Workflow

After initial setup, making schema changes is simple:

```bash
cd backend

# 1. Edit models
vim app/models.py

# 2. Generate migration
uv run alembic revision --autogenerate -m "add email_verified to users"

# 3. ALWAYS review the generated file — autogenerate misses things
vim alembic/versions/<hash>_add_email_verified_to_users.py

# 4. Apply locally
uv run alembic upgrade head

# 5. Commit model + migration together
git add app/models.py alembic/versions/
git commit -m "feat: add email_verified column to users"

# 6. Push — CI validates, deploy runs it automatically
git push
```

### Useful commands

```bash
uv run alembic history              # show all migrations
uv run alembic current              # show current revision
uv run alembic upgrade head         # apply all pending
uv run alembic downgrade -1         # rollback one step
uv run alembic downgrade <rev>      # rollback to revision
uv run alembic heads                # show head revisions
uv run alembic show <rev>           # show migration details
```

### Running migrations manually (via GitHub Actions)

Go to Actions → "Migrate" → Run workflow → select environment. No redeploy needed.

## Checklist

- [ ] `alembic` in `requirements.txt`
- [ ] `alembic/env.py` configured for async + schema creation
- [ ] Initial migration covers all existing tables (idempotent with `_table_exists`)
- [ ] `create_all()` removed from FastAPI lifespan
- [ ] `ci.yml` has `migrate` job with PostgreSQL service
- [ ] `migrate.yml` standalone workflow created
- [ ] `deploy.yml` calls `migrate.yml` before deploying
- [ ] `workflow_dispatch` on all workflows for manual triggering
- [ ] Required env vars (JWT_SECRET, etc.) provided in CI job
- [ ] All existing tests still pass
