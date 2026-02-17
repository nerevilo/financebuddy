"""
Shared test fixtures for the Ledgi backend test suite.

Provides:
- In-memory SQLite test database
- FastAPI TestClient with dependency overrides
- Auth helpers for creating users and tokens
"""
import os
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Set env vars BEFORE importing app modules so Settings picks them up
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-for-ci"
os.environ["DEBUG"] = "true"

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models import User
from app.models.models import generate_uuid


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """TestClient with db dependency overridden to use the test session."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass  # session cleanup handled by db_session fixture

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

from app.core.security import get_password_hash


def make_user(db_session, *, email: str = "test@example.com", password: str = "securepass1", name: str = "Test") -> User:
    """Insert a user directly into the test DB and return it."""
    user = User(
        id=generate_uuid(),
        email=email,
        name=name,
        hashed_password=get_password_hash(password),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(user: User) -> dict:
    """Return Authorization header dict with a valid JWT for the given user."""
    token = create_access_token(data={"sub": user.id, "email": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user_a(db_session):
    """Pre-created user A for data isolation tests."""
    return make_user(db_session, email="alice@example.com", name="Alice")


@pytest.fixture()
def user_b(db_session):
    """Pre-created user B for data isolation tests."""
    return make_user(db_session, email="bob@example.com", name="Bob")
