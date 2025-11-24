"""
Database connection and session management.

Handles SQLAlchemy engine and session creation.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Create database engine with lazy connection
# This allows the app to start even if database is not available
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    connect_args={"connect_timeout": 2}  # Fast timeout for development
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.

    Yields:
        Database session
    """
    db = None
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        # Database connection failed - yield None so routes can handle gracefully
        print(f"Warning: Database session creation failed: {e}")
        yield None
    finally:
        if db:
            db.close()
