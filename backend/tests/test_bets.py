"""Tests for betting functionality including bet creation, challenges, and status updates."""
import pytest

class TestBetCreation:
    """Test bet creation endpoint and validation."""
    
    def test_create_bet_success(self, client, create_user_and_get_token):
        """Verify successful bet creation with valid amount and details."""
        from datetime import datetime, timedelta
        token = create_user_and_get_token()
        deadline = (datetime.now() + timedelta(days=7)).isoformat()
        response = client.post("/bets/", json={
            "title": "I will run 5km",
            "criteria": "App screenshot",
            "amount": 5,
            "deadline": deadline
        }, headers={"Authorization": f"Bearer {token}"})
        
        assert response.status_code == 201, f"Bet creation should return 201 Created. Got {response.status_code}: {response.text}"
        assert response.json()["amount"] == 5, "Bet should have the specified amount"

    def test_create_bet_insufficient_funds(self, client, create_user_and_get_token):
        """Verify bet creation fails when user has insufficient funds."""
        from datetime import datetime, timedelta
        token = create_user_and_get_token("pooruser", "poor@gmail.com")
        deadline = (datetime.now() + timedelta(days=7)).isoformat()
        # Attempt to create a bet with amount exceeding user's balance
        response = client.post("/bets/", json={
            "title": "I will win big", "criteria": "None", "amount": 50,
            "deadline": deadline
        }, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 400, f"Insufficient funds should return 400 Bad Request. Got {response.status_code}: {response.text}"

class TestChallenge:
    """Test bet challenge functionality between users."""
    
    def test_challenge_bet_success(self, client, create_user_and_get_token):
        """Verify successful challenge of another user's bet."""
        from datetime import datetime, timedelta
        # Create initial bet by creator
        c_token = create_user_and_get_token("creator", "c@gmail.com")
        deadline = (datetime.now() + timedelta(days=7)).isoformat()
        bet_response = client.post("/bets/", json={"title": "I will complete test", "criteria": "X", "amount": 3, "deadline": deadline},
                          headers={"Authorization": f"Bearer {c_token}"})
        assert bet_response.status_code == 201, f"Bet creation failed: {bet_response.text}"
        bet = bet_response.json()
        
        # Different user challenges the bet
        ch_token = create_user_and_get_token("challenger", "ch@gmail.com")
        response = client.post(f"/bets/{bet['id']}/challenge", json={"amount": 5},
                               headers={"Authorization": f"Bearer {ch_token}"})
        
        assert response.status_code == 201, f"Challenge creation should return 201 Created. Got {response.status_code}: {response.text}"
        assert response.json()["status"] == "pending", "New challenge should have pending status"

    def test_challenge_own_bet_fails(self, client, create_user_and_get_token):
        """Verify that a user cannot challenge their own bet."""
        from datetime import datetime, timedelta
        token = create_user_and_get_token("selfie", "s@gmail.com")
        deadline = (datetime.now() + timedelta(days=7)).isoformat()
        # Create a bet
        bet_response = client.post("/bets/", json={"title": "I will complete self bet", "criteria": "X", "amount": 1, "deadline": deadline},
                          headers={"Authorization": f"Bearer {token}"})
        assert bet_response.status_code == 201, f"Bet creation failed: {bet_response.text}"
        bet = bet_response.json()
        
        # Same user attempts to challenge their own bet
        response = client.post(f"/bets/{bet['id']}/challenge", json={"amount": 1},
                               headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 400, f"Cannot challenge own bet, should return 400 Bad Request. Got {response.status_code}: {response.text}"

class TestBetStatus:
    """Test bet status updates and state transitions."""
    
    def test_update_bet_status(self, client, create_user_and_get_token):
        """Verify bet status can be updated to different states."""
        from datetime import datetime, timedelta
        token = create_user_and_get_token()
        deadline = (datetime.now() + timedelta(days=7)).isoformat()
        # Create a bet
        bet_response = client.post("/bets/", json={"title": "I will complete status bet", "criteria": "X", "amount": 1, "deadline": deadline},
                          headers={"Authorization": f"Bearer {token}"})
        assert bet_response.status_code == 201, f"Bet creation failed: {bet_response.text}"
        bet = bet_response.json()
        
        # Update bet status to won
        response = client.patch(f"/bets/{bet['id']}", json={"status": "won"},
                                headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200, f"Status update should return 200 OK. Got {response.status_code}: {response.text}"
        assert response.json()["status"] == "won", "Bet status should be updated to won"