import json
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models import User

# In-memory SQLite for tests (no schema support, so override schema_translate_map)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    execution_options={"schema_translate_map": {None: None, "mealmate": None}},
)
TestSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    # Override metadata schema for SQLite compatibility
    original_schema = Base.metadata.schema
    Base.metadata.schema = None
    for table in Base.metadata.tables.values():
        table.schema = None

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    Base.metadata.schema = original_schema
    for table in Base.metadata.tables.values():
        table.schema = original_schema


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user and return it."""
    user = User(
        email="test@example.com",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_client(
    db_session: AsyncSession, test_user: User
) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with Authelia headers for the test user."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={
            "Remote-User": "testuser",
            "Remote-Email": test_user.email,
            "Remote-Name": "Test User",
            "Remote-Groups": "users",
        },
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


def make_openai_response(data: dict) -> MagicMock:
    """Create a mock OpenAI chat completion response."""
    content = json.dumps(data)
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


SAMPLE_AI_MEALS = {
    "meals": [
        {
            "day_of_week": 1,
            "meal_type": "lunch",
            "name": "Grilled Chicken Salad",
            "description": "Fresh salad with grilled chicken",
            "recipe_steps": ["Grill chicken", "Toss salad", "Serve"],
            "prep_time_min": 10,
            "cook_time_min": 15,
            "ingredients": [
                {
                    "name": "Chicken breast",
                    "quantity": "400",
                    "unit": "g",
                    "category": "protein",
                },
                {
                    "name": "Mixed greens",
                    "quantity": "200",
                    "unit": "g",
                    "category": "produce",
                },
            ],
            "portions": [
                {
                    "profile_name": "Alonso",
                    "serving_size": "1.5 portions",
                    "calories": 650,
                    "protein_g": 55,
                    "carbs_g": 30,
                    "fat_g": 20,
                },
                {
                    "profile_name": "Maria",
                    "serving_size": "1 portion",
                    "calories": 450,
                    "protein_g": 40,
                    "carbs_g": 25,
                    "fat_g": 15,
                },
            ],
        },
        {
            "day_of_week": 1,
            "meal_type": "dinner",
            "name": "Salmon with Rice",
            "description": "Baked salmon with steamed rice",
            "recipe_steps": ["Season salmon", "Bake at 200C", "Cook rice"],
            "prep_time_min": 10,
            "cook_time_min": 25,
            "ingredients": [
                {
                    "name": "Salmon fillet",
                    "quantity": "500",
                    "unit": "g",
                    "category": "protein",
                },
                {"name": "Rice", "quantity": "300", "unit": "g", "category": "grains"},
            ],
            "portions": [
                {
                    "profile_name": "Alonso",
                    "serving_size": "2 portions",
                    "calories": 800,
                    "protein_g": 60,
                    "carbs_g": 70,
                    "fat_g": 25,
                },
                {
                    "profile_name": "Maria",
                    "serving_size": "1 portion",
                    "calories": 550,
                    "protein_g": 45,
                    "carbs_g": 50,
                    "fat_g": 18,
                },
            ],
        },
    ]
}

SAMPLE_AI_REGENERATED = {
    "meals": [
        {
            "day_of_week": 1,
            "meal_type": "lunch",
            "name": "Turkey Wrap",
            "description": "Healthy turkey wrap",
            "recipe_steps": ["Prepare wrap", "Add turkey", "Roll"],
            "prep_time_min": 5,
            "cook_time_min": 0,
            "ingredients": [
                {
                    "name": "Turkey slices",
                    "quantity": "200",
                    "unit": "g",
                    "category": "protein",
                },
                {
                    "name": "Tortilla",
                    "quantity": "2",
                    "unit": "pcs",
                    "category": "grains",
                },
            ],
            "portions": [
                {
                    "profile_name": "Alonso",
                    "serving_size": "2 wraps",
                    "calories": 600,
                    "protein_g": 50,
                    "carbs_g": 40,
                    "fat_g": 18,
                },
                {
                    "profile_name": "Maria",
                    "serving_size": "1 wrap",
                    "calories": 400,
                    "protein_g": 35,
                    "carbs_g": 30,
                    "fat_g": 12,
                },
            ],
        }
    ]
}
