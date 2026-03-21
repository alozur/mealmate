import sqlalchemy
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, settings
from app.routes.profiles import router as profiles_router
from app.routes.meal_plans import router as meal_plans_router
from app.routes.shopping import router as shopping_router
from app.routes.inventory import router as inventory_router
from app.routes.auth import router as auth_router


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


app = FastAPI(
    title="MealMate API",
    lifespan=lifespan,
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(profiles_router)
app.include_router(meal_plans_router)
app.include_router(shopping_router)
app.include_router(inventory_router)
app.include_router(auth_router)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
