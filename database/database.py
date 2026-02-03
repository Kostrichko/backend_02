from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from shared.config import settings


engine = create_async_engine(settings.DATABASE_URL)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
