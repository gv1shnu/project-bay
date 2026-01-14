"""Comprehensive tests for bet and challenge endpoints."""
import pytest


def get_auth_token(client, username="testuser", email="test@gmail.com"):
    """Helper to register and login a user, returning the auth token."""
    client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "password123"
    })
    login_response = client.post("/auth/login", data={
        "username": username,
        "password": "password123"
    })
    return login_response.json()["access_token"]


class TestBetCreation:
    """Test bet creation endpoint."""
    
    def test_create_bet_success(self, client):
        """Test successful bet creation."""
        token = get_auth_token(client)
        
        response = client.post("/bets/", json={
            "title": "Run 5km every day",
            "criteria": "Screenshot from fitness app",
            "amount": 5
        }, headers={"Authorization": f"Bearer {token}"})
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Run 5km every day"
        assert data["amount"] == 5
        assert data["status"] == "active"
    
    def test_create_bet_deducts_points(self, client):
        """Test that creating a bet deducts points from user."""
        token = get_auth_token(client)
        
        # Create bet with 5 points
        client.post("/bets/", json={
            "title": "Test bet",
            "criteria": "Test criteria",
            "amount": 5
        }, headers={"Authorization": f"Bearer {token}"})
        
        # Check user's remaining points
        user_response = client.get("/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert user_response.json()["points"] == 5  # 10 - 5 = 5
    
    def test_create_bet_insufficient_funds(self, client):
        """Test bet creation fails with insufficient points."""
        token = get_auth_token(client)
        
        # Try to create bet with more points than available
        response = client.post("/bets/", json={
            "title": "Big bet",
            "criteria": "Test criteria",
            "amount": 50  # User only has 10 points
        }, headers={"Authorization": f"Bearer {token}"})
        
        assert response.status_code == 400
        assert "insufficient" in response.json()["detail"].lower()
    
    def test_create_bet_unauthenticated(self, client):
        """Test bet creation without auth fails."""
        response = client.post("/bets/", json={
            "title": "Test bet",
            "criteria": "Test criteria",
            "amount": 5
        })
        assert response.status_code == 401


class TestPublicBets:
    """Test public bets endpoint."""
    
    def test_get_public_bets(self, client):
        """Test fetching public bets."""
        token = get_auth_token(client)
        
        # Create a bet
        client.post("/bets/", json={
            "title": "Public bet",
            "criteria": "Public criteria",
            "amount": 3
        }, headers={"Authorization": f"Bearer {token}"})
        
        # Get public bets (no auth required)
        response = client.get("/bets/public")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Public bet"
        assert "username" in data["items"][0]


class TestChallenge:
    """Test challenge endpoints."""
    
    def test_challenge_bet_success(self, client):
        """Test successful bet challenge."""
        # Create bet creator
        creator_token = get_auth_token(client, "creator", "creator@gmail.com")
        
        # Create a bet
        bet_response = client.post("/bets/", json={
            "title": "Challenge me",
            "criteria": "Proof needed",
            "amount": 3
        }, headers={"Authorization": f"Bearer {creator_token}"})
        bet_id = bet_response.json()["id"]
        
        # Create challenger
        challenger_token = get_auth_token(client, "challenger", "challenger@gmail.com")
        
        # Challenge the bet
        response = client.post(f"/bets/{bet_id}/challenge", json={
            "amount": 5
        }, headers={"Authorization": f"Bearer {challenger_token}"})
        
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == 5
        assert data["status"] == "pending"
    
    def test_challenge_own_bet_fails(self, client):
        """Test that challenging your own bet fails."""
        token = get_auth_token(client)
        
        # Create a bet
        bet_response = client.post("/bets/", json={
            "title": "Self challenge",
            "criteria": "Proof",
            "amount": 3
        }, headers={"Authorization": f"Bearer {token}"})
        bet_id = bet_response.json()["id"]
        
        # Try to challenge own bet
        response = client.post(f"/bets/{bet_id}/challenge", json={
            "amount": 2
        }, headers={"Authorization": f"Bearer {token}"})
        
        assert response.status_code == 400
        assert "own bet" in response.json()["detail"].lower()
    
    def test_challenge_deducts_points(self, client):
        """Test that challenging deducts points from challenger."""
        # Create bet creator
        creator_token = get_auth_token(client, "creator", "creator@gmail.com")
        
        # Create a bet
        bet_response = client.post("/bets/", json={
            "title": "Test bet",
            "criteria": "Proof",
            "amount": 3
        }, headers={"Authorization": f"Bearer {creator_token}"})
        bet_id = bet_response.json()["id"]
        
        # Create challenger
        challenger_token = get_auth_token(client, "challenger", "challenger@gmail.com")
        
        # Challenge the bet with 4 points
        client.post(f"/bets/{bet_id}/challenge", json={
            "amount": 4
        }, headers={"Authorization": f"Bearer {challenger_token}"})
        
        # Check challenger's remaining points
        user_response = client.get("/auth/me", headers={
            "Authorization": f"Bearer {challenger_token}"
        })
        assert user_response.json()["points"] == 6  # 10 - 4 = 6
    
    def test_challenge_insufficient_funds(self, client):
        """Test challenge fails with insufficient points."""
        # Create bet creator
        creator_token = get_auth_token(client, "creator", "creator@gmail.com")
        
        # Create a bet
        bet_response = client.post("/bets/", json={
            "title": "Test bet",
            "criteria": "Proof",
            "amount": 3
        }, headers={"Authorization": f"Bearer {creator_token}"})
        bet_id = bet_response.json()["id"]
        
        # Create challenger
        challenger_token = get_auth_token(client, "challenger", "challenger@gmail.com")
        
        # Try to challenge with more points than available
        response = client.post(f"/bets/{bet_id}/challenge", json={
            "amount": 50
        }, headers={"Authorization": f"Bearer {challenger_token}"})
        
        assert response.status_code == 400


class TestBetStatus:
    """Test bet status update endpoint."""
    
    def test_update_bet_status(self, client):
        """Test updating bet status (resolution)."""
        token = get_auth_token(client)
        
        # Create a bet
        bet_response = client.post("/bets/", json={
            "title": "Win this",
            "criteria": "Proof",
            "amount": 3
        }, headers={"Authorization": f"Bearer {token}"})
        bet_id = bet_response.json()["id"]
        
        # Update status to won
        response = client.patch(f"/bets/{bet_id}", json={
            "status": "won"
        }, headers={"Authorization": f"Bearer {token}"})
        
        assert response.status_code == 200
        assert response.json()["status"] == "won"