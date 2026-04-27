from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
from .config import get_settings

settings = get_settings()

# Configure database connection based on database type
is_sqlite = settings.database_url.startswith("sqlite")

if is_sqlite:
    # SQLite configuration for development
    # SQLite doesn't support connection pooling the same way as PostgreSQL
    # Use StaticPool for SQLite to maintain a single connection
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        poolclass=StaticPool,
    )
else:
    # PostgreSQL configuration for production with connection pooling
    connect_args = {
        "connect_timeout": 10,  # Connection timeout in seconds
        "options": "-c statement_timeout=30000",  # Query timeout: 30 seconds (in milliseconds)
    }
    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        poolclass=QueuePool,
        pool_size=20,  # Number of connections to keep open in the pool
        max_overflow=40,  # Additional connections allowed beyond pool_size
        pool_recycle=3600,  # Recycle connections after 1 hour (3600 seconds)
        pool_pre_ping=True,  # Verify connections are alive before using them
        pool_timeout=30,  # Seconds to wait before giving up on getting a connection
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
