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
- Run backend: `conda run -n mealmate uvicorn app.main:app --reload` (from backend/)
- Run backend tests: `conda run -n mealmate python -m pytest tests/ -v` (from backend/)
- Run frontend dev: `npm run dev` (from frontend/)
- Run frontend tests: `npm run test` (from frontend/)
- Docker build: `docker compose up --build`
- Install backend deps: `conda run -n mealmate pip install -r requirements.txt`

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
│   │       └── shopping.py   # Consolidated shopping list
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
│   │   │   └── Profiles.tsx
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
