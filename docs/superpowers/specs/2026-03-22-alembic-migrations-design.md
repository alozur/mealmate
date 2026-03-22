# Alembic Migration Setup — Design Spec

**Date:** 2026-03-22
**Status:** Approved
**Scope:** Replace `create_all()` with Alembic as the single source of truth for database schema management, and integrate migrations into the CI/CD pipeline.

---

## 1. Problem Statement

MealMate currently uses a hybrid approach to database schema management:
- `Base.metadata.create_all()` in the FastAPI lifespan creates/updates tables on every startup
- An Alembic directory exists with one migration (`ca642ebdac27`) but is not wired into deployment
- `alembic` is not listed in `requirements.txt`

This makes schema changes untracked, unreviewable, and error-prone in production.

## 2. Goals

1. Alembic becomes the **single source of truth** for all schema changes
2. Migrations run automatically during CI/CD deployment, **before** the application starts
3. CI validates that migrations apply cleanly on every PR
4. Existing data in prod/dev databases is **not affected**

## 3. Design

### 3.1 Alembic Configuration & Initial Migration

**Prerequisite:** The existing migration `ca642ebdac27` was never applied via `alembic upgrade` — tables were created by `create_all()`. No `alembic_version` table exists in any environment. It is safe to replace this migration.

**Changes:**

1. **Add `alembic` to `backend/requirements.txt`.**

2. **Replace the existing migration** (`ca642ebdac27_add_users_table_and_user_id_to_profiles.py`) with a comprehensive **initial migration** that captures all 7 tables:
   - `users`
   - `profiles` (with `user_id` FK to users)
   - `meal_plans`
   - `meals`
   - `meal_portions`
   - `ingredients`
   - `inventory_items`

   This migration includes all columns, constraints, foreign keys, and indexes as defined in `models.py`.

3. **Update `alembic/env.py`** — Add schema creation before migrations run. This must be placed inside `run_async_migrations()`, executed on the connection before `do_run_migrations`:

   ```python
   async with connectable.connect() as connection:
       await connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}"))
       await connection.commit()
       await connection.run_sync(do_run_migrations)
   ```

   The `CREATE SCHEMA` requires a commit before the migration transaction begins. The schema name comes from `settings.DB_SCHEMA` (not hardcoded).

4. **Remove both `create_all()` AND schema creation from `backend/app/main.py` lifespan.** Alembic now owns schema creation and all table management. The lifespan becomes a no-op (or just yields).

5. **Note:** The `alembic_version` table lives in the `mealmate` schema, controlled by `version_table_schema=settings.DB_SCHEMA` already configured in `env.py`.

### 3.2 CI/CD Integration

**Deploy workflow (`deploy.yml`) — split into separate steps:**

The current `docker compose down` + `up --build` must be split into discrete steps:

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

**Updated deploy order:**
1. CI passes (lint, backend tests, frontend tests)
2. Create `.env` file with secrets/vars
3. Stop existing services (`docker compose down`)
4. Build images (`docker compose build`)
5. **Run migrations** (`docker compose run --rm backend alembic upgrade head`)
6. Start services (`docker compose up -d`)

**CI workflow (`ci.yml`) — migration validation job:**

A new job with a PostgreSQL service container. Must set dummy values for required env vars (`JWT_SECRET`, `INVITE_CODE`) that `Settings` requires on import:

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
    - run: pip install -r requirements.txt
    - name: Run migrations against fresh DB
      env:
        DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/testdb?ssl=disable
        DB_SCHEMA: mealmate
        JWT_SECRET: test-secret-for-ci
        INVITE_CODE: test-invite
      run: alembic upgrade head
```

### 3.3 Stamping Existing Databases

Existing prod/dev databases already have all tables. Running `alembic upgrade head` would fail trying to create them again.

**One-time step per environment (manual):**

```bash
docker compose -p mealmate-${ENV} run --rm backend alembic stamp head
```

This writes the current revision to `mealmate.alembic_version` without executing any SQL. No data is modified, no tables are created or dropped.

- **Existing databases:** `stamp head` → Alembic tracks from here forward
- **Fresh databases (CI, new environments):** `upgrade head` → runs full migration normally

### 3.4 Developer Workflow

Going forward, schema changes follow this process:

1. Modify models in `backend/app/models.py`
2. Generate migration: `uv run alembic revision --autogenerate -m "description"`
3. **Review the generated migration file** — autogenerate is not perfect
4. Apply locally: `uv run alembic upgrade head`
5. Commit the migration file alongside the model changes
6. CI validates, deploy executes automatically

**Rollbacks:**
```bash
alembic downgrade -1       # one step back
alembic downgrade <rev>    # to specific revision
```

## 4. Files Modified

| File | Change |
|------|--------|
| `backend/requirements.txt` | Add `alembic` dependency |
| `backend/app/main.py` | Remove `create_all()` and schema creation entirely |
| `backend/alembic/env.py` | Add schema creation in `run_async_migrations()` before `do_run_migrations` |
| `backend/alembic/versions/` | Replace existing migration with full initial migration (all 7 tables) |
| `.github/workflows/deploy.yml` | Split into build/migrate/up steps |
| `.github/workflows/ci.yml` | Add migration validation job with PostgreSQL service |

## 5. Data Safety

- `alembic stamp head` is metadata-only — zero DDL, zero data changes
- The initial migration only runs on fresh/empty databases
- Future migrations only execute the specific DDL statements defined in the migration file
- Data loss can only happen if a migration explicitly contains `DROP` statements, which would be caught in code review

## 6. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Forgot to stamp existing DB | Migration fails loudly (tries to create existing tables) — stamp and retry |
| Autogenerate misses something | Developer review of generated migration is mandatory |
| Migration fails mid-deploy | `docker compose run --rm` exits non-zero, deploy stops before starting services |
| Concurrent migrations | Single deploy pipeline per environment; no replicas running migrations simultaneously |
| CI fails on Settings import | Dummy env vars (`JWT_SECRET`, `INVITE_CODE`) provided in CI job |
| Existing migration was applied via Alembic | Verified: it was not — `create_all()` managed all tables, no `alembic_version` table exists |
