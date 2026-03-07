from collections.abc import AsyncGenerator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Settings(BaseSettings):
    DATABASE_URL: str | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = None
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DB_SCHEMA: str = "mealmate"
    CORS_ORIGINS: str = "http://localhost:3082,http://localhost:5173"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB:
            return (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return "sqlite+aiosqlite:///./mealmate.db"


settings = Settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    execution_options={"schema_translate_map": {None: settings.DB_SCHEMA}},
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    metadata = MetaData(schema=settings.DB_SCHEMA)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
