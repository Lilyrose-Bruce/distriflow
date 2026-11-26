"""Database connection. SQLite for development, PostgreSQL when DATABASE_URL is set."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import DATABASE_URL

# SQLite needs this extra option because FastAPI uses several threads.
# PostgreSQL does not need it.
connect_args = {}


engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Each request gets its own short-lived session (a "conversation" with the database).
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Every model class inherits from this Base.
Base = declarative_base()


def get_db():
    """FastAPI dependency: open a database session, and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

