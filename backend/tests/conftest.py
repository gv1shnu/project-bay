import pytest
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.database import Base, get_db
from app.config import settings

SQLALCHEMY_TEST_DATABASE_URL = settings.TEST_DATABASE_URL
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def create_user_and_get_token(client):
    """Factory fixture to create users on the fly."""
    def _create(username="testuser", email="test@gmail.com", password="password123"):
        # Register
        client.post("/auth/register", json={
            "username": username,
            "email": email,
            "password": password
        })
        # Login
        login_res = client.post("/auth/login", data={
            "username": username,
            "password": password
        })
        # Ensure token exists to avoid KeyError
        data = login_res.json()
        if "access_token" not in data:
            raise RuntimeError(f"Login failed in fixture: {data}")
        return data["access_token"]
    return _create