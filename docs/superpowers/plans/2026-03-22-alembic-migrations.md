# Alembic Migration Setup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `create_all()` with Alembic as the single source of truth for database schema management and integrate migrations into CI/CD.

**Architecture:** Alembic manages all schema changes via versioned migration files. The `env.py` handles schema creation before running migrations. CI validates migrations against a fresh PostgreSQL. Deploy runs migrations as a separate step before starting services.

**Tech Stack:** Alembic, async SQLAlchemy 2.0, PostgreSQL, GitHub Actions, Docker Compose

**Spec:** `docs/superpowers/specs/2026-03-22-alembic-migrations-design.md`

**Important:** All tasks must be merged and deployed together. Deploying Task 4 (remove create_all) without Task 5 (deploy migration step) would leave a fresh database with no tables.

---

### Task 1: Add Alembic dependency to requirements.txt

**Files:**
- Modify: `backend/requirements.txt:1-14`

- [ ] **Step 1: Add alembic to requirements.txt**

Add `alembic>=1.13.0` after the `aiosqlite` line (line 5). This keeps dependencies grouped logically (SQLAlchemy ecosystem together):

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy[asyncio]==2.0.35
asyncpg==0.29.0
aiosqlite==0.20.0
alembic>=1.13.0
pydantic==2.9.2
pydantic-settings==2.5.2
openai==1.58.0
httpx==0.27.2
pytest==8.3.3
pytest-asyncio==0.24.0
PyJWT>=2.8.0
bcrypt>=4.0.0
email-validator>=2.1.0
```

- [ ] **Step 2: Verify install works**

Run: `cd /home/alozur/alonso/repos/mealmate/backend && uv pip install -r requirements.txt`
Expected: Installs successfully, alembic is now available.

- [ ] **Step 3: Commit**

```bash
cd /home/alozur/alonso/repos/mealmate
git add backend/requirements.txt
git commit -m "chore: add alembic to requirements.txt"
```

---

### Task 2: Update alembic/env.py with schema creation

**Files:**
- Modify: `backend/alembic/env.py:60-72`

The current `run_async_migrations()` function (lines 60-72) connects and runs migrations but does NOT create the schema first. We need to add `CREATE SCHEMA IF NOT EXISTS` before `do_run_migrations`, with a commit so the schema exists before the migration transaction begins.

- [ ] **Step 1: Add text import**

At the top of `backend/alembic/env.py`, the existing imports are:

```python
import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
```

Add `text` to the sqlalchemy imports. Change:

```python
from sqlalchemy import pool
```

to:

```python
from sqlalchemy import pool, text
```

- [ ] **Step 2: Update run_async_migrations()**

Replace the current `run_async_migrations()` function (lines 60-72):

```python
async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()
```

With this version that creates the schema first:

```python
async def run_async_migrations() -> None:
    """Create an async engine, ensure schema exists, then run migrations."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.execute(
            text(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}")
        )
        await connection.commit()
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()
```

Key details:
- `text()` is required for raw SQL execution.
- `await connection.commit()` is required — the schema must exist before migrations begin their own transaction.
- `settings.DB_SCHEMA` (not hardcoded "mealmate") so it works across environments.

- [ ] **Step 3: Verify env.py is syntactically valid**

Run: `cd /home/alozur/alonso/repos/mealmate/backend && python -c "import alembic; print('ok')"`
Expected: `ok` (confirms alembic is importable; full env.py validation happens when we run migrations later).

- [ ] **Step 4: Commit**

```bash
cd /home/alozur/alonso/repos/mealmate
git add backend/alembic/env.py
git commit -m "feat(alembic): add schema creation before migrations in env.py"
```

---

### Task 3: Write the initial migration (all 7 tables)

**Files:**
- Delete: `backend/alembic/versions/ca642ebdac27_add_users_table_and_user_id_to_profiles.py`
- Create: `backend/alembic/versions/0001_initial_schema.py`

The existing migration `ca642ebdac27` only covers `users` + `user_id` on `profiles`. It was never applied via Alembic (tables were created by `create_all()`). Replace it with a comprehensive initial migration covering all 7 tables exactly as defined in `backend/app/models.py`.

- [ ] **Step 1: Delete the old migration**

```bash
rm /home/alozur/alonso/repos/mealmate/backend/alembic/versions/ca642ebdac27_add_users_table_and_user_id_to_profiles.py
```

- [ ] **Step 2: Create the initial migration file**

Create `backend/alembic/versions/0001_initial_schema.py` with this content:

```python
"""initial schema - all tables

Revision ID: 0001
Revises:
Create Date: 2026-03-22

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "mealmate"


def upgrade() -> None:
    """Create all tables."""
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        schema=SCHEMA,
    )

    # profiles
    op.create_table(
        "profiles",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("goal", sa.String(50), nullable=False),
        sa.Column("restrictions", sa.Text(), nullable=True),
        sa.Column("calorie_target", sa.Integer(), nullable=False),
        sa.Column("protein_target", sa.Integer(), nullable=False),
        sa.Column("carbs_target", sa.Integer(), nullable=False),
        sa.Column("fat_target", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=True, unique=True),
        sa.ForeignKeyConstraint(["user_id"], ["mealmate.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    # meal_plans
    op.create_table(
        "meal_plans",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    # meals
    op.create_table(
        "meals",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("meal_plan_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(
            ["meal_plan_id"], ["mealmate.meal_plans.id"], ondelete="CASCADE"
        ),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("meal_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("recipe_steps", sa.Text(), nullable=True),
        sa.Column("prep_time_min", sa.Integer(), nullable=True),
        sa.Column("cook_time_min", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    # meal_portions
    op.create_table(
        "meal_portions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("meal_id", sa.String(36), nullable=False),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(
            ["meal_id"], ["mealmate.meals.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["mealmate.profiles.id"]),
        sa.Column("serving_size", sa.String(100), nullable=False),
        sa.Column("calories", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Numeric(6, 1), nullable=False),
        sa.Column("carbs_g", sa.Numeric(6, 1), nullable=False),
        sa.Column("fat_g", sa.Numeric(6, 1), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    # ingredients
    op.create_table(
        "ingredients",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("meal_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(
            ["meal_id"], ["mealmate.meals.id"], ondelete="CASCADE"
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.String(50), nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    # inventory_items
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.String(50), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("storage_location", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("inventory_items", schema=SCHEMA)
    op.drop_table("ingredients", schema=SCHEMA)
    op.drop_table("meal_portions", schema=SCHEMA)
    op.drop_table("meals", schema=SCHEMA)
    op.drop_table("meal_plans", schema=SCHEMA)
    op.drop_table("profiles", schema=SCHEMA)
    op.drop_table("users", schema=SCHEMA)
```

Key details:
- Revision ID is `"0001"` (human-readable, since this is a hand-written baseline).
- `down_revision = None` — this is the first migration.
- Foreign keys use `sa.ForeignKeyConstraint()` with fully qualified `mealmate.<table>.<column>` references. This is the standard Alembic pattern for schema-qualified tables and avoids autogenerate drift.
- `downgrade()` drops in reverse dependency order (children before parents).
- `SCHEMA = "mealmate"` constant at the top — matches the hardcoded schema in the existing migration pattern. The schema name is not dynamic here because migration files are static records of what happened.

- [ ] **Step 3: Verify the migration file is syntactically valid**

Run: `cd /home/alozur/alonso/repos/mealmate/backend && python -c "import alembic.versions" 2>&1 || python -c "import importlib.util; spec = importlib.util.spec_from_file_location('m', 'alembic/versions/0001_initial_schema.py'); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
cd /home/alozur/alonso/repos/mealmate
git add backend/alembic/versions/
git commit -m "feat(alembic): replace partial migration with full initial schema (all 7 tables)"
```

---

### Task 4: Remove create_all() from main.py lifespan

**Files:**
- Modify: `backend/app/main.py:1-29`

Remove the schema creation and `create_all()` from the lifespan. Alembic now owns both. The lifespan becomes a simple no-op yield.

- [ ] **Step 1: Simplify the lifespan**

Replace the current lifespan function (lines 15-29 of `backend/app/main.py`):

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print(f"[LIFESPAN] Connecting to DB, schema={settings.DB_SCHEMA}")
        async with engine.begin() as conn:
            await conn.execute(
                sqlalchemy.text(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}")
            )
            print("[LIFESPAN] Schema created/verified")
            await conn.run_sync(Base.metadata.create_all)
            print("[LIFESPAN] Tables created")
    except Exception as e:
        print(f"[LIFESPAN] ERROR: {e}")
        raise
    yield
```

With:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
```

- [ ] **Step 2: Remove unused imports**

The `import sqlalchemy` on line 1 and the `Base, engine` imports from `app.database` (line 7) are no longer needed by the lifespan. Update the imports:

Change line 1 from:
```python
import sqlalchemy
```
Remove this line entirely.

Change line 7 from:
```python
from app.database import Base, engine, settings
```
to:
```python
from app.database import settings
```

`settings` is still needed for CORS configuration on line 39.

- [ ] **Step 3: Run existing backend tests to verify nothing broke**

Run: `cd /home/alozur/alonso/repos/mealmate/backend && uv run python -m pytest tests/ -v`
Expected: All tests pass. Tests use their own in-memory SQLite with `create_all()` in the `setup_db` fixture (`backend/tests/conftest.py:42-58`), so they are unaffected by this change.

- [ ] **Step 4: Commit**

```bash
cd /home/alozur/alonso/repos/mealmate
git add backend/app/main.py
git commit -m "feat(alembic): remove create_all() from lifespan, Alembic owns schema"
```

---

### Task 5: Update deploy.yml with migration step

**Files:**
- Modify: `.github/workflows/deploy.yml:42-45`

Split the current single `docker compose` step (lines 42-45) into four discrete steps: down, build, migrate, up. Also add `workflow_dispatch` trigger so deployments can be triggered manually from the GitHub Actions UI.

- [ ] **Step 1: Add workflow_dispatch trigger**

Add `workflow_dispatch` to the `on:` block at the top of `.github/workflows/deploy.yml` (line 3-4). Change:

```yaml
on:
  push:
    branches: [main, dev]
```

To:

```yaml
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
```

Then update the `env:` block (lines 17-19) to use the workflow_dispatch input when available. Change:

```yaml
    env:
      ENV: ${{ github.ref == 'refs/heads/main' && 'prod' || 'dev' }}
```

To:

```yaml
    env:
      ENV: ${{ inputs.environment || (github.ref == 'refs/heads/main' && 'prod' || 'dev') }}
```

Do the same for `environment:` on line 15:

```yaml
    environment: ${{ inputs.environment || (github.ref == 'refs/heads/main' && 'prod' || 'dev') }}
```

- [ ] **Step 2: Replace the deploy step**

Replace the current "Deploy with docker compose" step (lines 42-45):

```yaml
      - name: Deploy with docker compose
        run: |
          docker compose -p mealmate-${ENV} down
          docker compose -p mealmate-${ENV} up --build -d
```

With these four steps:

```yaml
      - name: Stop existing services
        run: docker compose -p mealmate-${ENV} down

      - name: Build images
        run: docker compose -p mealmate-${ENV} build

      - name: Run database migrations
        run: docker compose -p mealmate-${ENV} run --rm backend alembic upgrade head

      - name: Start services
        run: docker compose -p mealmate-${ENV} up -d
```

Key details:
- `docker compose run --rm backend` inherits the backend service's network configuration (`postgres_infra_network`), environment variables from `.env`, and working directory. It runs `alembic upgrade head` and exits.
- `--rm` cleans up the one-off migration container.
- If migrations fail, the step exits non-zero and deployment stops before `up -d`.
- Images must be built before `run` so the backend image exists.

- [ ] **Step 2: Commit**

```bash
cd /home/alozur/alonso/repos/mealmate
git add .github/workflows/deploy.yml
git commit -m "feat(ci): add migration step and workflow_dispatch to deploy workflow"
```

---

### Task 6: Add migration validation job to ci.yml

**Files:**
- Modify: `.github/workflows/ci.yml` (add new job after line 55)

Add a `migrate` job that spins up a PostgreSQL service container and runs `alembic upgrade head` to verify all migrations apply cleanly from scratch. Also add `workflow_dispatch` trigger so CI can be triggered manually.

- [ ] **Step 1: Add workflow_dispatch trigger to ci.yml**

Add `workflow_dispatch:` to the `on:` block at the top of `.github/workflows/ci.yml` (lines 3-8). Change:

```yaml
on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main, dev]
  workflow_call:
```

To:

```yaml
on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main, dev]
  workflow_call:
  workflow_dispatch:
```

- [ ] **Step 2: Add the migrate job**

Append the following job at the end of `.github/workflows/ci.yml` (after the `frontend-tests` job, which ends at line 55):

```yaml

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
          DB_SCHEMA: mealmate
          JWT_SECRET: test-secret-for-ci
          INVITE_CODE: test-invite
        run: alembic upgrade head
```

Key details:
- PostgreSQL 16 service container with health checks ensures the DB is ready before the step runs.
- `JWT_SECRET` and `INVITE_CODE` are required by `Settings` (imported when `env.py` loads `app.database`). Dummy values are fine here.
- `DATABASE_URL` points at the service container via `localhost:5432`.
- `DB_SCHEMA=mealmate` — the `env.py` schema creation will create it.
- This job runs in parallel with lint, backend-tests, and frontend-tests.

- [ ] **Step 2: Commit**

```bash
cd /home/alozur/alonso/repos/mealmate
git add .github/workflows/ci.yml
git commit -m "feat(ci): add migration validation job and workflow_dispatch trigger"
```

---

### Task 7: Final verification — run all backend tests

**Files:** None (verification only)

- [ ] **Step 1: Run the full backend test suite**

Run: `cd /home/alozur/alonso/repos/mealmate/backend && uv run python -m pytest tests/ -v`
Expected: All tests pass. The test suite uses its own in-memory SQLite with `create_all()` in `conftest.py:setup_db`, completely independent of Alembic.

- [ ] **Step 2: Verify ruff passes**

Run: `cd /home/alozur/alonso/repos/mealmate/backend && uv run ruff check app/ tests/ && uv run ruff format --check app/ tests/`
Expected: No lint or format issues.

- [ ] **Step 3: Verify alembic can show migration history**

Run: `cd /home/alozur/alonso/repos/mealmate/backend && JWT_SECRET=test INVITE_CODE=test uv run alembic history`
Expected: Shows the single initial migration `0001 -> head, initial schema - all tables`

---

### Post-Implementation: Stamp existing databases (manual, one-time)

This is NOT part of the automated implementation. After deploying the changes, run this once per environment:

**Dev environment:**
```bash
docker compose -p mealmate-dev run --rm backend alembic stamp head
```

**Prod environment:**
```bash
docker compose -p mealmate-prod run --rm backend alembic stamp head
```

This writes revision `0001` to `mealmate.alembic_version` without executing any SQL. From this point forward, `alembic upgrade head` in the deploy pipeline handles all future migrations.
