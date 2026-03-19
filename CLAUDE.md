# MealMate - Meal Planning & Grocery List App

## Project Overview
MealMate is a meal planning and grocery list app for couples with different fitness goals. It generates personalized weekly meal plans (Monday-Saturday) using OpenAI GPT-4o-mini, with shared meals but different portion sizes based on each person's goal (e.g., muscle gain vs fat loss). Includes a consolidated weekly shopping list.

## Tech Stack
- **Backend**: Python 3.12 + FastAPI + async SQLAlchemy + Pydantic v2
- **Frontend**: React 19 + Vite + TypeScript + Tailwind CSS v4 + shadcn/ui
- **Database**: PostgreSQL (external shared instance via `postgres_infra_network`)
- **AI**: OpenAI API (GPT-4o-mini) for meal plan generation
- **Infrastructure**: Docker + docker-compose
- **Testing**: pytest (backend), Vitest (frontend)

## Key Commands
- Run backend: `uv run uvicorn app.main:app --reload` (from backend/)
- Run backend tests: `uv run python -m pytest tests/ -v` (from backend/)
- Run frontend dev: `npm run dev` (from frontend/)
- Run frontend tests: `npm run test` (from frontend/)
- Docker build: `docker compose up --build`
- Install backend deps: `uv pip install -r requirements.txt`

## Project Structure
```
mealmate/
├── CLAUDE.md
├── docker-compose.yml
├── .env                      # Environment variables (not committed)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app + lifespan
│   │   ├── database.py       # Async engine, session, Base
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── dependencies.py   # Shared dependencies
│   │   ├── openai_client.py  # OpenAI integration for meal generation
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── profiles.py   # User profile CRUD (name, goal, restrictions)
│   │       ├── meal_plans.py # Generate & manage weekly meal plans
│   │       ├── shopping.py   # Consolidated shopping list
│   │       └── inventory.py  # Kitchen inventory CRUD (fridge/freezer)
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── api/              # API client functions
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Page components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── MealPlan.tsx
│   │   │   ├── ShoppingList.tsx
│   │   │   ├── Profiles.tsx
│   │   │   └── InventoryPage.tsx
│   │   └── types/            # TypeScript type definitions
│   └── tests/
└── .agents/skills/           # Installed Claude Code skills
```

## Database Schema (PostgreSQL, schema: mealmate)

### profiles
Stores user profiles with their fitness goals and dietary preferences.
- `id` (UUID PK), `name`, `goal` (muscle_gain/fat_loss/maintenance/etc.), `restrictions` (JSON array), `calorie_target`, `protein_target`, `carbs_target`, `fat_target`, `created_at`

### meal_plans
Weekly meal plan metadata.
- `id` (UUID PK), `week_start` (date, Monday), `week_end` (date, Saturday), `status` (draft/active), `created_at`

### meals
Individual meals within a plan, with per-profile portions.
- `id` (UUID PK), `meal_plan_id` (FK), `day_of_week` (1-6), `meal_type` (lunch/dinner), `name`, `description`, `recipe_steps` (JSON), `prep_time_min`, `cook_time_min`, `created_at`

### meal_portions
Per-profile portion details and macros for each meal.
- `id` (UUID PK), `meal_id` (FK), `profile_id` (FK), `serving_size`, `calories`, `protein_g`, `carbs_g`, `fat_g`

### ingredients
Ingredients for each meal with quantities.
- `id` (UUID PK), `meal_id` (FK), `name`, `quantity`, `unit`, `category` (produce/protein/dairy/grains/etc.)

### inventory_items
Kitchen inventory tracking (fridge/freezer).
- `id` (UUID PK), `name`, `quantity`, `unit`, `category`, `storage_location` (fridge/freezer), `created_at`

## API Endpoints

### Profiles
- `GET /api/profiles` - List all profiles
- `POST /api/profiles` - Create profile
- `PUT /api/profiles/{id}` - Update profile
- `DELETE /api/profiles/{id}` - Delete profile

### Meal Plans
- `POST /api/meal-plans/generate` - Generate new weekly meal plan via OpenAI
- `GET /api/meal-plans` - List all meal plans
- `GET /api/meal-plans/{id}` - Get meal plan with all meals
- `POST /api/meal-plans/{id}/regenerate-meal/{meal_id}` - Regenerate a single meal
- `DELETE /api/meal-plans/{id}` - Delete a meal plan

### Shopping List
- `GET /api/meal-plans/{id}/shopping-list` - Get consolidated shopping list for a plan

### Inventory
- `GET /api/inventory` - List all inventory items
- `POST /api/inventory` - Create inventory item
- `PUT /api/inventory/{id}` - Update inventory item
- `DELETE /api/inventory/{id}` - Delete inventory item

### Health
- `GET /health` - Health check

## Development Patterns
- Follow gym-app patterns: async SQLAlchemy, Pydantic schemas, FastAPI routers
- Database uses schema isolation (`mealmate` schema) on shared PostgreSQL
- External `postgres_infra_network` for database connectivity
- Environment variables via `.env` file and pydantic-settings
- All IDs are UUID strings
- Docker port: 3082 (frontend), backend proxied via nginx

## Environment Variables
```
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres_shared:5432/${POSTGRES_DB}?ssl=disable
DB_SCHEMA=mealmate
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
CORS_ORIGINS=http://localhost:3082,http://localhost:5173
```


## Agent Teams Configuration

When asked to create a development team or when a task is complex enough to benefit from parallel work, use the following standard team structure.

### When to Use Agent Teams vs Single Session

Use **agent teams** for:
- New features spanning multiple modules or layers
- Refactoring across several parts of the codebase
- Debugging production issues with unclear root cause (spawn competing hypothesis investigators)
- Security audits and code reviews before deployment
- Performance optimization across the system

Use a **single session or subagents** for:
- Single-file edits, bug fixes, or config changes
- Quick research or exploratory tasks
- Sequential tasks with strong dependencies

### Default Team Roles (5 Agents)

When spawning a development team, use these roles unless the task requires a different composition:

#### 1. Architect
- **Focus:** System design, interfaces, data flow, design patterns
- **Responsibilities:**
  - Define module interfaces and data contracts BEFORE implementation starts
  - Ensure SOLID principles, clean architecture, separation of concerns
  - Document architectural decisions in docstrings and design docs
  - Validate that new code integrates cleanly with existing architecture
- **File ownership:** `docs/`, interface definitions, schemas, contracts

#### 2. Implementer
- **Focus:** Production-grade code following the Architect's design
- **Responsibilities:**
  - Write robust code with proper error handling, logging, and type hints
  - Handle edge cases and failure modes relevant to the project domain
  - Follow existing project conventions and patterns
  - Implement graceful degradation where applicable
- **File ownership:** Core source modules

#### 3. Security & Reliability Reviewer
- **Focus:** Security vulnerabilities, input validation, production resilience
- **Responsibilities:**
  - Audit for injection risks, secrets exposure, unsafe config loading
  - Validate input sanitization on all external inputs
  - Check dependency vulnerabilities
  - Verify error handling covers all failure modes
  - Rate findings by severity (critical/high/medium/low)
- **File ownership:** Read-only reviewer, creates `SECURITY_REVIEW.md`

#### 4. Test Engineer
- **Focus:** Comprehensive testing strategy
- **Responsibilities:**
  - Unit tests for core business logic
  - Integration tests for module interactions
  - Edge case tests for error scenarios and boundary conditions
  - Performance benchmarks where relevant
  - Target >90% coverage on critical paths
- **File ownership:** `tests/`, `benchmarks/`, `fixtures/`

#### 5. DevOps & Quality
- **Focus:** Deployability, observability, CI/CD, code quality
- **Responsibilities:**
  - Container/deployment configuration
  - Health checks and monitoring
  - Linting, formatting, type checking rules
  - CI pipeline configuration
  - Dependency management and pinning
  - Structured logging configuration
- **File ownership:** `Dockerfile`, `docker-compose.yml`, `.github/`, `scripts/`, config files

### Team Coordination Rules

- **Architect shares design FIRST** — No implementation begins until Architect publishes interfaces and data contracts via the task list
- **Security and Test actively challenge Implementer** — They should question assumptions, not just validate
- **No task is "done" until Security and Test approve** — Use TaskCompleted hooks if available
- **File ownership is strict** — Each teammate owns specific directories/files to prevent merge conflicts
- **Lead uses delegate mode** — The lead coordinates only, does not implement (Shift+Tab)
- **Rich spawn prompts** — Always include project context, tech stack, and specific file paths in spawn prompts since teammates don't inherit conversation history. Read the project's CLAUDE.md and README before spawning to gather this context.

### Model Selection for Cost Efficiency

| Role | Model | Rationale |
|------|-------|-----------|
| Team Lead | Opus | Coordination, synthesis, final review |
| Architect | Opus | Design decisions require deep reasoning |
| Implementer | Sonnet | Good balance of speed and quality for code generation |
| Security Reviewer | Sonnet | Pattern matching and vulnerability detection |
| Test Engineer | Sonnet | Test generation is parallelizable |
| DevOps | Sonnet | Config and script generation |

### Example Team Spawn Prompts

**For new feature development:**
```
Create an agent team to implement [feature]. Spawn 5 teammates:
- Architect: Design the module interfaces and data flow. Focus on how it integrates with
  the existing codebase. Publish design before anyone implements.
- Implementer: Build the feature following Architect's design. Handle all edge cases for
  production reliability. Use type hints and proper logging.
- Security: Review all code for vulnerabilities, input validation, and production resilience.
  Rate findings by severity.
- Tester: Write unit tests, integration tests, and edge case tests. Include performance
  benchmarks. Target >90% coverage on critical paths.
- DevOps: Update deployment config, health checks, monitoring, and CI/CD scripts as needed.
Use delegate mode for the lead. Architect must share design before implementation starts.
```

**For debugging issues:**
```
Create an agent team to investigate [issue]. Spawn 3-5 teammates, each investigating
a different hypothesis:
- Hypothesis 1: [description]
- Hypothesis 2: [description]
- Hypothesis 3: [description]
Have them share findings and actively challenge each other's theories.
Update a findings doc with consensus.
```

**For code review / audit:**
```
Create an agent team to review the [module]. Spawn 3 teammates:
- Security reviewer: Audit for vulnerabilities, check input validation, review permissions
- Performance reviewer: Profile bottlenecks, identify resource usage issues
- Test coverage reviewer: Find untested paths, missing edge cases, suggest critical tests
Have them share findings and produce a unified report.
```

### Monitoring and Debugging Agent Teams

```bash
# Navigate between teammates (in-process mode)
Shift+Up / Shift+Down

# Toggle the shared task list
Ctrl+T

# Inspect team state
cat ~/.claude/teams/{team}/config.json | jq '.members[]'

# Check inboxes
cat ~/.claude/teams/{team}/inboxes/{agent}.json | jq '.'

# Check task status
cat ~/.claude/tasks/{team}/*.json | jq '{id, subject, status, owner}'
```

If a task appears stuck, check if work is done and manually update status or tell the lead to nudge.

### Cleanup

Always clean up teams through the lead after teammates have shut down:

1. Lead sends shutdown requests to all teammates
2. Wait for shutdown approvals
3. Lead runs cleanup

> Never let teammates run cleanup — only the lead should do it.
