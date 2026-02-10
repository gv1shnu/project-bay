"""Test configuration and fixtures for the betting application tests.

This module provides pytest fixtures for database setup, API client initialization,
and user creation utilities used across test modules.
"""
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

# Configure test database
SQLALCHEMY_TEST_DATABASE_URL = settings.TEST_DATABASE_URL
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    """Provides a clean database session for each test.
    
    Creates all tables before the test and drops them after, ensuring
    test isolation and a fresh database state for each test function.
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    """Provides a FastAPI test client with database dependency overridden.
    
    Overrides the application's database dependency to use the test database
    session, allowing tests to make HTTP requests against the API with a
    controlled test database.
    """
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
    """Factory fixture to create users and retrieve authentication tokens.
    
    Provides a callable that registers a new user and logs them in,
    returning their JWT access token for use in authenticated requests.
    Useful for quickly setting up test users with authentication.
    """
    def _create(username="testuser", email="test@gmail.com", password="password123"):
        # Register the new user
        client.post("/auth/register", json={
            "username": username,
            "email": email,
            "password": password
        })
        # Log in the user and get token
        login_res = client.post("/auth/login", data={
            "username": username,
            "password": password
        })
        # Validate that token was returned successfully
        data = login_res.json()
        if "access_token" not in data:
            raise RuntimeError(f"Login failed in fixture: {data}")
        return data["access_token"]
    return _create