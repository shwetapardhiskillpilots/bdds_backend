import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

from urllib.parse import quote_plus

# Database connection details
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "bdds")

# SQLAlchemy async URL
# Note: Using aiomysql for async MySQL connection
DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{quote_plus(DB_NAME)}"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,              # Disable SQL logging for production speed
    pool_size=5,             # Keep 5 connections warm
    max_overflow=10,         # Allow up to 10 extra under load
    pool_pre_ping=True,      # Test connections before use (avoid stale)
    pool_recycle=1800,       # Recycle connections every 30 min
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
