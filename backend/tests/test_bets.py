import pytest

class TestBetCreation:
    def test_create_bet_success(self, client, create_user_and_get_token):
        token = create_user_and_get_token()
        response = client.post("/bets/", json={
            "title": "Run 5km",
            "criteria": "App screenshot",
            "amount": 5
        }, headers={"Authorization": f"Bearer {token}"})
        
        assert response.status_code == 201
        assert response.json()["amount"] == 5

    def test_create_bet_insufficient_funds(self, client, create_user_and_get_token):
        token = create_user_and_get_token("pooruser", "poor@gmail.com")
        response = client.post("/bets/", json={
            "title": "Big bet", "criteria": "None", "amount": 50
        }, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 400

class TestChallenge:
    def test_challenge_bet_success(self, client, create_user_and_get_token):
        # Create creator and their bet
        c_token = create_user_and_get_token("creator", "c@gmail.com")
        bet = client.post("/bets/", json={"title": "Test", "criteria": "X", "amount": 3},
                          headers={"Authorization": f"Bearer {c_token}"}).json()
        
        # Create challenger
        ch_token = create_user_and_get_token("challenger", "ch@gmail.com")
        response = client.post(f"/bets/{bet['id']}/challenge", json={"amount": 5},
                               headers={"Authorization": f"Bearer {ch_token}"})
        
        assert response.status_code == 201
        assert response.json()["status"] == "pending"

    def test_challenge_own_bet_fails(self, client, create_user_and_get_token):
        token = create_user_and_get_token("selfie", "s@gmail.com")
        bet = client.post("/bets/", json={"title": "Self", "criteria": "X", "amount": 1},
                          headers={"Authorization": f"Bearer {token}"}).json()
        
        response = client.post(f"/bets/{bet['id']}/challenge", json={"amount": 1},
                               headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 400

class TestBetStatus:
    def test_update_bet_status(self, client, create_user_and_get_token):
        token = create_user_and_get_token()
        bet = client.post("/bets/", json={"title": "Status", "criteria": "X", "amount": 1},
                          headers={"Authorization": f"Bearer {token}"}).json()
        
        response = client.patch(f"/bets/{bet['id']}", json={"status": "won"},
                                headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["status"] == "won"