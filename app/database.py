import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


# Create engine with SSL support for production (Aiven/Render)
connect_args = {}
db_url = settings.database_url

if "sslmode=require" in db_url:
    # asyncpg uses 'ssl' instead of 'sslmode'
    if "?" in db_url:
        base_url, query = db_url.split("?", 1)
        params = [p for p in query.split("&") if not p.startswith("sslmode=")]
        db_url = f"{base_url}?{'&'.join(params)}" if params else base_url
    
    # Create insecure SSL context to handle self-signed certs (common on Aiven)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ctx

engine = create_async_engine(
    db_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args=connect_args
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
