"""
Shared pytest fixtures.

Runs the real FastAPI app against a fresh in-memory SQLite database per test,
with the get_db dependency overridden and the background LLM validation stubbed
out. TestClient is used WITHOUT a context manager so the app lifespan (which would
start the deadline-checker thread and hit the real Postgres engine) never runs.
"""
import os

# Env must be set before app modules import (config reads it at import time).
os.environ.setdefault("SECRET_KEY", "testsecret")
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost/db")  # never actually connected
os.environ.setdefault("TEST_DATABASE_URL", "sqlite://")
os.environ.setdefault("ADMIN_PASSPHRASE", "secret")
os.environ.setdefault("GROQ_API_KEY", "x")
os.environ.setdefault("RATELIMIT_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "100000")
os.environ.setdefault("RATE_LIMIT_LOGIN_PER_MINUTE", "100000")

from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app import models
from app.main import app

# One shared in-memory SQLite DB (StaticPool keeps a single connection alive).
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _fresh_db(monkeypatch):
    """Fresh schema per test; stub the background LLM validation task."""
    Base.metadata.create_all(engine)
    monkeypatch.setattr("app.routers.bets.bet_crud.process_validation_queue", lambda: None)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── Helpers ──────────────────────────────────────────────────────────────

def register_and_login(client, username, password="secret123", email=None):
    """Create a user (10 starting points) and return an auth-header dict."""
    email = email or f"{username}@gmail.com"
    r = client.post("/auth/register", json={"username": username, "email": email, "password": password})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def create_bet(client, headers, title="I will run 5km today", amount=5, criteria="Timestamped photo", days=1):
    deadline = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    r = client.post("/bets/", json={"title": title, "criteria": criteria, "amount": amount, "deadline": deadline}, headers=headers)
    return r


def follow(client, headers, username):
    return client.post(f"/follows/{username}", headers=headers)


def points(client, headers):
    return client.get("/auth/me", headers=headers).json()["points"]
