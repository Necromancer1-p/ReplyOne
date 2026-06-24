import os
import logging
from dotenv import load_dotenv
load_dotenv()

from contextvars import ContextVar
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import event, pool
from sqlalchemy.pool import NullPool

logger = logging.getLogger("replyone.db")

# Context variable to hold the current tenant ID for request scope
tenant_context: ContextVar[int | None] = ContextVar("tenant_context", default=None)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite+aiosqlite:///../replyone.db"
    logger.info(f"Using SQLite database fallback: {DATABASE_URL}")
else:
    logger.info(f"Using database: {DATABASE_URL}")

# Create engine with appropriate parameters
connect_args = {}
poolclass = None
if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = 30.0
    poolclass = NullPool

engine = create_async_engine(
    DATABASE_URL,
    connect_args=connect_args,
    poolclass=poolclass,
    echo=False,
    pool_pre_ping=True
)

# Enable foreign keys and WAL mode for SQLite
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in DATABASE_URL:
        dbapi_connection.isolation_level = None
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
        logger.info("Enforced SQLite foreign keys, WAL mode, normal sync, and isolation_level=None")

@event.listens_for(engine.sync_engine, "begin")
def do_begin(conn):
    if "sqlite" in DATABASE_URL:
        conn.exec_driver_sql("BEGIN IMMEDIATE")

# Session maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()

# SQLAlchemy interceptor to assert or enforce tenant isolation
# As per TRD Layer 2: A custom Session class or execution interceptor that asserts 
# or automatically applies the tenant filter where applicable.
class TenantViolationError(Exception):
    pass

async def get_db():
    """FastAPI Dependency for database session."""
    session = AsyncSessionLocal()
    try:
        logger.debug("Database session opened")
        yield session
    except Exception as e:
        logger.error(f"Database session error: {e}", exc_info=True)
        raise
    finally:
        await session.close()
        logger.debug("Database session closed")
