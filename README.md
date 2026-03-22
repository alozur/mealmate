# MealMate

Meal planning and grocery list app for couples with different fitness goals. Generates personalized weekly meal plans (Monday-Saturday) using OpenAI GPT-4o-mini, with shared meals but different portion sizes based on each person's goal (e.g., muscle gain vs fat loss). Includes a consolidated weekly shopping list.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, async SQLAlchemy 2.0, Pydantic v2 |
| Frontend | React 19, Vite, TypeScript, Tailwind CSS v4, shadcn/ui |
| Database | PostgreSQL (shared instance, `mealmate` schema) |
| Migrations | Alembic (async, single source of truth) |
| AI | OpenAI API (GPT-4o-mini) |
| Auth | JWT cookies (30-day expiry), bcrypt password hashing, invite-code registration |
| Infra | Docker, docker-compose, GitHub Actions CI/CD |
| Testing | pytest + pytest-asyncio (backend), Vitest (frontend) |

## Quick Start

### Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 22+
- PostgreSQL (or use Docker)
- OpenAI API key

### Local Development

```bash
# Backend
cd backend
cp .env.example .env  # fill in your values
uv pip install -r requirements.txt
uv run alembic upgrade head          # run migrations
uv run uvicorn app.main:app --reload # start API on :8000

# Frontend
cd frontend
npm ci
npm run dev  # start dev server on :5173
```

### Docker

```bash
# Create .env with required variables (see Environment Variables below)
docker compose up --build

# Run migrations (first time or after model changes)
docker compose run --rm backend alembic upgrade head
```

Frontend: `http://localhost:3082` | Backend API: `http://localhost:3082/api`

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No* | SQLite fallback | Full PostgreSQL async URL |
| `POSTGRES_USER` | No* | — | PostgreSQL username |
| `POSTGRES_PASSWORD` | No* | — | PostgreSQL password |
| `POSTGRES_DB` | No* | — | PostgreSQL database name |
| `DB_SCHEMA` | No | `mealmate` | PostgreSQL schema name |
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI model to use |
| `JWT_SECRET` | Yes | — | Secret key for JWT token signing |
| `INVITE_CODE` | Yes | — | Required code for user registration |
| `CORS_ORIGINS` | No | `http://localhost:3082,http://localhost:5173` | Allowed CORS origins |

*Either `DATABASE_URL` or all three `POSTGRES_*` variables must be set. Without them, falls back to SQLite.

## Database Migrations (Alembic)

Alembic is the **single source of truth** for all database schema changes. The FastAPI app does not create tables — Alembic manages everything.

### Making schema changes

```bash
cd backend

# 1. Edit models in app/models.py
# 2. Generate a migration
uv run alembic revision --autogenerate -m "add column X to table Y"

# 3. Review the generated file in alembic/versions/ (autogenerate isn't perfect)
# 4. Apply locally
uv run alembic upgrade head

# 5. Commit both the model change and migration file together
```

### Useful commands

```bash
uv run alembic history              # show migration history
uv run alembic current              # show current revision
uv run alembic upgrade head         # apply all pending migrations
uv run alembic downgrade -1         # rollback one migration
uv run alembic downgrade <rev>      # rollback to specific revision
```

### How it works in CI/CD

- **CI**: A `migrate` job runs `alembic upgrade head` against a fresh PostgreSQL to validate migrations
- **Deploy**: Migrations run automatically (`docker compose run --rm backend alembic upgrade head`) before services start
- Both workflows support `workflow_dispatch` for manual triggering

## Project Structure

```
mealmate/
├── README.md
├── CLAUDE.md                         # AI assistant context
├── docker-compose.yml
├── .github/workflows/
│   ├── ci.yml                        # Lint, tests, migration validation
│   └── deploy.yml                    # Deploy to Synology (dev/prod)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py                    # Async migration runner + schema creation
│   │   └── versions/                 # Migration files
│   ├── app/
│   │   ├── main.py                   # FastAPI app + lifespan
│   │   ├── database.py               # Async engine, session, settings
│   │   ├── models.py                 # SQLAlchemy ORM models (7 tables)
│   │   ├── schemas.py                # Pydantic request/response schemas
│   │   ├── auth.py                   # JWT + bcrypt authentication
│   │   ├── dependencies.py           # Shared FastAPI dependencies
│   │   ├── openai_client.py          # OpenAI meal plan generation
│   │   └── routes/
│   │       ├── auth.py               # Register, login, logout, me
│   │       ├── profiles.py           # User profile CRUD
│   │       ├── meal_plans.py         # Generate & manage meal plans
│   │       ├── shopping.py           # Consolidated shopping list
│   │       └── inventory.py          # Kitchen inventory CRUD
│   └── tests/                        # pytest async tests (47 tests)
├── frontend/
│   ├── Dockerfile                    # Multi-stage: Node build + nginx
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx                   # Router + auth guard
│       ├── api/                      # API client functions
│       ├── components/               # Reusable UI (shadcn/ui)
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── MealPlanPage.tsx
│       │   ├── ShoppingListPage.tsx
│       │   ├── ProfilesPage.tsx
│       │   ├── InventoryPage.tsx
│       │   ├── LoginPage.tsx
│       │   └── RegisterPage.tsx
│       └── types/                    # TypeScript type definitions
└── docs/superpowers/                 # Design specs and implementation plans
```

## API Endpoints

All routes (except `/health` and auth) require authentication via `mealmate_auth` cookie.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/auth/register` | Register (requires invite code) |
| `POST` | `/api/auth/login` | Login (sets JWT cookie) |
| `POST` | `/api/auth/logout` | Logout (clears cookie) |
| `GET` | `/api/auth/me` | Current user info |
| `POST` | `/api/auth/link-profile/{id}` | Link profile to user |
| `GET` | `/api/profiles` | List profiles |
| `POST` | `/api/profiles` | Create profile |
| `PUT` | `/api/profiles/{id}` | Update profile |
| `DELETE` | `/api/profiles/{id}` | Delete profile |
| `POST` | `/api/meal-plans/generate` | Generate weekly meal plan (AI) |
| `GET` | `/api/meal-plans` | List meal plans |
| `GET` | `/api/meal-plans/{id}` | Get meal plan with meals |
| `POST` | `/api/meal-plans/{id}/regenerate-meal/{meal_id}` | Regenerate single meal (AI) |
| `DELETE` | `/api/meal-plans/{id}` | Delete meal plan |
| `GET` | `/api/meal-plans/{id}/shopping-list` | Consolidated shopping list |
| `GET` | `/api/inventory` | List inventory items |
| `POST` | `/api/inventory` | Create inventory item |
| `PUT` | `/api/inventory/{id}` | Update inventory item |
| `DELETE` | `/api/inventory/{id}` | Delete inventory item |

## Database Schema

PostgreSQL schema: `mealmate` (7 tables)

- **users** — Authentication accounts (email, hashed_password)
- **profiles** — Fitness profiles linked to users (goal, macro targets, dietary restrictions)
- **meal_plans** — Weekly meal plan containers (week_start, week_end, status)
- **meals** — Individual meals (day_of_week, meal_type, recipe, prep/cook time)
- **meal_portions** — Per-profile portions with macros (calories, protein, carbs, fat)
- **ingredients** — Meal ingredients with quantities and categories
- **inventory_items** — Kitchen inventory tracking (fridge/freezer)

## Testing

```bash
# Backend (47 tests)
cd backend
uv run python -m pytest tests/ -v

# Frontend
cd frontend
npm run test

# Lint
cd backend
uv run ruff check app/ tests/
uv run ruff format --check app/ tests/
```

## Deployment

Deploys automatically via GitHub Actions to a self-hosted Synology runner:

- Push to `dev` → deploys to dev environment (port 3083)
- Push to `main` → deploys to prod environment (port 3082)
- Manual trigger via GitHub Actions UI (`workflow_dispatch`)

Deploy order: CI passes → build images → run migrations → start services.
