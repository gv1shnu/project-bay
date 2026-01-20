import pytest

class TestUserRegistration:
    def test_register_success(self, client):
        response = client.post("/auth/register", json={
            "username": "testuser",
            "email": "test@gmail.com",
            "password": "securepassword123"
        })
        assert response.status_code == 201
        assert response.json()["username"] == "testuser"

    def test_register_duplicate_username(self, client):
        payload = {"username": "testuser", "email": "t1@gmail.com", "password": "password123"}
        client.post("/auth/register", json=payload)
        response = client.post("/auth/register", json={**payload, "email": "t2@gmail.com"})
        assert response.status_code == 409

class TestUserLogin:
    def test_login_success(self, client, create_user_and_get_token):
        # The factory handles registration and login
        token = create_user_and_get_token("loginuser", "login@gmail.com")
        assert token is not None

    def test_login_wrong_password(self, client):
        client.post("/auth/register", json={
            "username": "user", "email": "u@gmail.com", "password": "correct"
        })
        response = client.post("/auth/login", data={"username": "user", "password": "wrong"})
        assert response.status_code == 401

class TestUserProfile:
    def test_get_current_user(self, client, create_user_and_get_token):
        token = create_user_and_get_token("profileuser", "profile@gmail.com")
        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["username"] == "profileuser"