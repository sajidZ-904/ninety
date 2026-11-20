import os

# Tests always run against a disposable SQLite database and the seed clock,
# even when invoked directly, so they never touch the development database.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_ninety.db")
os.environ.setdefault("APP_NOW", "2026-11-11T15:00:00Z")

import pytest
from fastapi.testclient import TestClient

from backend.app.database import Base, engine, SessionLocal
from backend.app.main import app
from backend.app.seeder import seed_database

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_database(db=db)
    db.close()
    yield

@pytest.fixture(scope="function")
def client():
    with TestClient(app) as c:
        yield c
