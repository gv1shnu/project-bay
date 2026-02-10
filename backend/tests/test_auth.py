"""Tests for user authentication functionality including registration, login, and profile access."""
import pytest

class TestUserRegistration:
    """Test user registration endpoint and validation."""
    
    def test_register_success(self, client):
        """Verify successful user registration creates a new account with correct credentials."""
        response = client.post("/auth/register", json={
            "username": "testuser",
            "email": "test@gmail.com",
            "password": "securepassword123"
        })
        assert response.status_code == 201, "Registration should return 201 Created"
        assert response.json()["username"] == "testuser", "Response should contain registered username"

    def test_register_duplicate_username(self, client):
        """Verify that registering with a duplicate username is rejected."""
        payload = {"username": "testuser", "email": "t1@gmail.com", "password": "password123"}
        client.post("/auth/register", json=payload)
        # Attempt to register the same username with a different email
        response = client.post("/auth/register", json={**payload, "email": "t2@gmail.com"})
        assert response.status_code == 409, "Duplicate username should return 409 Conflict"

class TestUserLogin:
    """Test user login functionality and authentication."""
    
    def test_login_success(self, client, create_user_and_get_token):
        """Verify successful login returns a valid authentication token."""
        # Use fixture to create and authenticate user
        token = create_user_and_get_token("loginuser", "login@gmail.com")
        assert token is not None, "Login should return a non-null access token"

    def test_login_wrong_password(self, client):
        """Verify login fails with incorrect password."""
        # Register user with correct password
        client.post("/auth/register", json={
            "username": "user", "email": "u@gmail.com", "password": "correct"
        })
        # Attempt login with wrong password
        response = client.post("/auth/login", data={"username": "user", "password": "wrong"})
        assert response.status_code == 401, "Wrong password should return 401 Unauthorized"

class TestUserProfile:
    """Test user profile access and retrieval."""
    
    def test_get_current_user(self, client, create_user_and_get_token):
        """Verify authenticated user can retrieve their own profile information."""
        # Create and authenticate a user
        token = create_user_and_get_token("profileuser", "profile@gmail.com")
        # Fetch current user info using token
        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200, "Profile endpoint should return 200 OK"
        assert response.json()["username"] == "profileuser", "Profile should contain correct username"