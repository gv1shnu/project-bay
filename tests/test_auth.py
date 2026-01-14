"""Comprehensive tests for authentication endpoints."""
import pytest
from app.auth import get_password_hash


class TestUserRegistration:
    """Test user registration endpoint."""
    
    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post("/auth/register", json={
            "username": "testuser",
            "email": "test@gmail.com",
            "password": "securepassword123"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@gmail.com"
        assert data["points"] == 10  # Default starting points
        assert "hashed_password" not in data
    
    def test_register_duplicate_username(self, client):
        """Test registration with duplicate username fails."""
        # First registration
        client.post("/auth/register", json={
            "username": "testuser",
            "email": "test1@gmail.com",
            "password": "password123"
        })
        # Second registration with same username
        response = client.post("/auth/register", json={
            "username": "testuser",
            "email": "test2@gmail.com",
            "password": "password123"
        })
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()
    
    def test_register_duplicate_email(self, client):
        """Test registration with duplicate email fails."""
        # First registration
        client.post("/auth/register", json={
            "username": "testuser1",
            "email": "test@gmail.com",
            "password": "password123"
        })
        # Second registration with same email
        response = client.post("/auth/register", json={
            "username": "testuser2",
            "email": "test@gmail.com",
            "password": "password123"
        })
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()
    
    def test_register_invalid_email_domain(self, client):
        """Test registration with disallowed email domain fails."""
        response = client.post("/auth/register", json={
            "username": "testuser",
            "email": "test@randomdomain.com",
            "password": "password123"
        })
        assert response.status_code == 422  # Validation error


class TestUserLogin:
    """Test user login endpoint."""
    
    def test_login_success(self, client):
        """Test successful login."""
        # Register first
        client.post("/auth/register", json={
            "username": "loginuser",
            "email": "login@gmail.com",
            "password": "password123"
        })
        # Login
        response = client.post("/auth/login", data={
            "username": "loginuser",
            "password": "password123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client):
        """Test login with wrong password fails."""
        # Register first
        client.post("/auth/register", json={
            "username": "loginuser",
            "email": "login@gmail.com",
            "password": "password123"
        })
        # Login with wrong password
        response = client.post("/auth/login", data={
            "username": "loginuser",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user fails."""
        response = client.post("/auth/login", data={
            "username": "nonexistent",
            "password": "password123"
        })
        assert response.status_code == 401


class TestUserProfile:
    """Test user profile endpoints."""
    
    def test_get_current_user(self, client):
        """Test getting current user info."""
        # Register and login
        client.post("/auth/register", json={
            "username": "profileuser",
            "email": "profile@gmail.com",
            "password": "password123"
        })
        login_response = client.post("/auth/login", data={
            "username": "profileuser",
            "password": "password123"
        })
        token = login_response.json()["access_token"]
        
        # Get current user
        response = client.get("/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "profileuser"
        assert data["points"] == 10
    
    def test_get_user_by_username(self, client):
        """Test getting user profile by username."""
        # Register
        client.post("/auth/register", json={
            "username": "publicuser",
            "email": "public@gmail.com",
            "password": "password123"
        })
        
        # Get public profile
        response = client.get("/auth/user/publicuser")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "publicuser"
    
    def test_get_nonexistent_user(self, client):
        """Test getting non-existent user fails."""
        response = client.get("/auth/user/nonexistent")
        assert response.status_code == 404


class TestUserCount:
    """Test user count endpoint."""
    
    def test_get_user_count(self, client):
        """Test getting total user count."""
        # Register some users
        client.post("/auth/register", json={
            "username": "user1",
            "email": "user1@gmail.com",
            "password": "password123"
        })
        client.post("/auth/register", json={
            "username": "user2",
            "email": "user2@gmail.com",
            "password": "password123"
        })
        
        response = client.get("/auth/stats/count")
        assert response.status_code == 200
        assert response.json()["count"] == 2